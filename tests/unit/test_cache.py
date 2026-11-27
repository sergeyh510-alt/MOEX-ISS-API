"""Юнит-тесты Redis-кэша (этап 9).

Проверяем построение ключа кэша, что при CACHE_ENABLED=false кэш не
используется, и что недоступный Redis не ломает запрос (ответ всё равно 200).
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import cache
from app.cache import CacheMiddleware, build_cache_key


class _FakeSettings:
    """Заглушка настроек с полями кэша."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        ttl: int = 60,
        prefix: str = "moex-api",
    ) -> None:
        self.CACHE_ENABLED = enabled
        self.CACHE_TTL_SECONDS = ttl
        self.CACHE_KEY_PREFIX = prefix


def test_build_cache_key_is_stable_and_order_independent(monkeypatch) -> None:
    """Ключ стабилен и не зависит от порядка параметров."""

    monkeypatch.setattr(cache, "get_settings", lambda: _FakeSettings())
    first = build_cache_key("/api/v1/securities", {"q": "sber", "limit": "10"})
    second = build_cache_key("/api/v1/securities", {"limit": "10", "q": "sber"})
    assert first == second
    assert first == "moex-api:/api/v1/securities?limit=10&q=sber"


def test_build_cache_key_differs_for_different_params(monkeypatch) -> None:
    """Разные параметры дают разные ключи."""

    monkeypatch.setattr(cache, "get_settings", lambda: _FakeSettings())
    key_a = build_cache_key("/api/v1/securities", {"q": "sber"})
    key_b = build_cache_key("/api/v1/securities", {"q": "gazp"})
    key_c = build_cache_key("/api/v1/dates", {"q": "sber"})
    assert key_a != key_b
    assert key_a != key_c


def test_cache_disabled_does_not_use_redis(monkeypatch) -> None:
    """При CACHE_ENABLED=false кэш не вызывается и нет заголовка X-Cache."""

    monkeypatch.setattr(cache, "get_settings", lambda: _FakeSettings(enabled=False))

    async def _boom(*_args, **_kwargs):
        raise AssertionError("кэш не должен вызываться при CACHE_ENABLED=false")

    monkeypatch.setattr(cache, "get_json", _boom)
    monkeypatch.setattr(cache, "set_json", _boom)

    app = FastAPI()
    app.add_middleware(CacheMiddleware)

    @app.get("/api/v1/ping")
    async def ping() -> dict:
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/api/v1/ping")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert "X-Cache" not in response.headers


def test_unavailable_redis_still_returns_200(monkeypatch) -> None:
    """При недоступном Redis клиент бросает исключение, но ответ всё равно 200."""

    monkeypatch.setattr(cache, "get_settings", lambda: _FakeSettings(enabled=True))

    class _ExplodingClient:
        async def ping(self) -> bool:
            raise RuntimeError("redis down")

        async def get(self, _key):
            raise RuntimeError("redis down")

        async def set(self, *_args, **_kwargs):
            raise RuntimeError("redis down")

    async def _exploding_client():
        return _ExplodingClient()

    monkeypatch.setattr(cache, "get_client", _exploding_client)
    monkeypatch.setattr(cache, "_warned_unavailable", False)

    app = FastAPI()
    app.add_middleware(CacheMiddleware)

    @app.get("/api/v1/ping")
    async def ping() -> dict:
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/api/v1/ping")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert response.headers["X-Cache"] == "MISS"
