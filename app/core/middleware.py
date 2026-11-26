"""Middleware: идентификатор запроса и access-лог."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging_setup import set_request_id

ACCESS_LOGGER = logging.getLogger("app.access")

REQUEST_ID_HEADER = "X-Request-ID"


def resolve_request_id(incoming: str | None) -> str:
    """Взять идентификатор из заголовка или сгенерировать новый."""

    if incoming:
        candidate = incoming.strip()
        # Ограничиваем длину и состав, чтобы чужой заголовок не ломал логи.
        if candidate and len(candidate) <= 128 and all(ch.isprintable() for ch in candidate):
            return candidate
    return uuid.uuid4().hex


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Проставляет X-Request-ID и пишет одну строку access-лога на запрос."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        # Идентификатор кладём в contextvar; задача запроса изолирована, поэтому
        # отдельная очистка не нужна и не мешает обработчику ошибок прочитать его.
        set_request_id(request_id)

        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)

        response.headers[REQUEST_ID_HEADER] = request_id
        ACCESS_LOGGER.info(
            "%s %s -> %s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
