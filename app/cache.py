"""Redis-кэш ответов: необязательный ускоритель.

Кэш включается настройкой ``CACHE_ENABLED`` (по умолчанию выключен) и служит
только ускорению ответов. Если Redis недоступен, приложение продолжает
работать без кэша: пишем одно предупреждение в лог (без спама на каждый запрос)
и отдаём ответ как обычно. Из-за кэша 503 не бывает.

Кэшируем только успешные (HTTP 200) GET-ответы под /api/v1. Ключ строится из
пути и параметров запроса. В ответ добавляется заголовок X-Cache: HIT или MISS.
Ошибки не кэсируем, /health не кэсируем никогда.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

logger = logging.getLogger(__name__)

CACHE_HEADER = "X-Cache"
CACHE_PATH_PREFIX = "/api/v1"

# Короткие таймауты, чтобы недоступный Redis не тормозил запросы.
CONNECT_TIMEOUT_S = 1.0
SOCKET_TIMEOUT_S = 1.0

# Заголовки, которые не восстанавливаем из кэша: либо зависят от запроса,
# либо рассчитываются заново.
VOLATILE_HEADERS = {
    "content-length",
    "content-type",
    "date",
    "server",
    "x-request-id",
    "x-cache",
}

_client: Any | None = None
_warned_unavailable = False


def cache_enabled() -> bool:
    """Включён ли кэш настройкой CACHE_ENABLED."""

    return bool(get_settings().CACHE_ENABLED)


def _iter_params(query_params: Any) -> list[tuple[str, str]]:
    """Развернуть параметры запроса в список пар (умеет и MultiDict)."""

    multi = getattr(query_params, "multi_items", None)
    if callable(multi):
        pairs = list(multi())
    else:
        pairs = list(query_params.items())
    return [(str(key), str(value)) for key, value in pairs]


def build_cache_key(path: str, query_params: Any) -> str:
    """Стабильный ключ из пути и параметров запроса.

    Параметры сортируются, поэтому порядок в URL на ключ не влияет, а разные
    значения параметров дают разные ключи.
    """

    prefix = get_settings().CACHE_KEY_PREFIX
    pairs = sorted(_iter_params(query_params))
    query = "&".join(f"{key}={value}" for key, value in pairs)
    return f"{prefix}:{path}?{query}" if query else f"{prefix}:{path}"


def _warn_once(message: str) -> None:
    """Записать предупреждение о недоступном Redis один раз на процесс."""

    global _warned_unavailable
    if not _warned_unavailable:
        logger.warning(message)
        _warned_unavailable = True


async def get_client() -> Any | None:
    """Вернуть ленивый клиент redis.asyncio (или None, если создать не удалось).

    Импорт redis сделан внутри функции, чтобы модуль оставался импортируемым
    без установленного пакета (нужно для юнит-тестов).
    """

    global _client
    if _client is not None:
        return _client
    try:
        from redis import asyncio as aioredis
    except Exception:
        _warn_once("Пакет redis недоступен, кэш выключен.")
        return None
    try:
        _client = aioredis.from_url(
            get_settings().REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=CONNECT_TIMEOUT_S,
            socket_timeout=SOCKET_TIMEOUT_S,
        )
    except Exception:
        _warn_once("Не удалось создать клиент Redis, кэш выключен.")
        return None
    return _client


async def available() -> bool:
    """Короткая проверка соединения с Redis (признак доступности)."""

    client = await get_client()
    if client is None:
        return False
    try:
        return bool(await client.ping())
    except Exception:
        _warn_once("Redis недоступен, кэш выключен.")
        return False


async def get_json(key: str) -> Any | None:
    """Прочитать значение из кэша; None при промахе или недоступном Redis."""

    client = await get_client()
    if client is None:
        return None
    try:
        raw = await client.get(key)
    except Exception:
        _warn_once("Redis недоступен, кэш выключен.")
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


async def set_json(key: str, value: Any, ttl: int) -> None:
    """Записать значение в кэш на ttl секунд; ошибки только логируем."""

    client = await get_client()
    if client is None:
        return
    try:
        payload = json.dumps(value, ensure_ascii=False, default=str)
        await client.set(key, payload, ex=max(1, int(ttl)))
    except Exception:
        _warn_once("Redis недоступен, кэш выключен.")


async def close() -> None:
    """Закрыть соединение с Redis (вызывается в lifespan приложения)."""

    global _client
    if _client is None:
        return
    try:
        await _client.aclose()
    except Exception:
        pass
    _client = None


def _should_cache(request: Request) -> bool:
    """Кэсируем только GET-запросы под /api/v1 при включённом кэше."""

    if not cache_enabled():
        return False
    if request.method != "GET":
        return False
    return request.url.path.startswith(CACHE_PATH_PREFIX)


def _copy_headers(response: Response) -> dict[str, str]:
    """Скопировать заголовки ответа без нестабильных."""

    return {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in VOLATILE_HEADERS
    }


async def _read_body(response: Response) -> bytes:
    """Прочитать тело потокового ответа в байты."""

    chunks: list[bytes] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk if isinstance(chunk, bytes) else str(chunk).encode("utf-8"))
    return b"".join(chunks)


def _try_json(body: bytes) -> Any | None:
    """Разобрать тело как JSON; None, если это не JSON."""

    if not body:
        return None
    try:
        return json.loads(body)
    except Exception:
        return None


class CacheMiddleware(BaseHTTPMiddleware):
    """Кэсирует успешные GET-ответы под /api/v1 и ставит заголовок X-Cache."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not _should_cache(request):
            return await call_next(request)

        key = build_cache_key(request.url.path, request.query_params)
        cached = await get_json(key)
        if isinstance(cached, dict) and "body" in cached:
            response = JSONResponse(content=cached["body"])
            for header, value in cached.get("headers", {}).items():
                response.headers[header] = value
            response.headers[CACHE_HEADER] = "HIT"
            return response

        response = await call_next(request)
        if response.status_code != 200:
            return response

        body = await _read_body(response)
        new_response = Response(
            content=body,
            status_code=response.status_code,
            headers=_copy_headers(response),
            media_type=response.media_type,
        )
        new_response.headers[CACHE_HEADER] = "MISS"

        payload = _try_json(body)
        if payload is not None:
            entry: Mapping[str, Any] = {
                "body": payload,
                "headers": _copy_headers(response),
            }
            await set_json(key, entry, get_settings().CACHE_TTL_SECONDS)
        return new_response
