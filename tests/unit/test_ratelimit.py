"""Юнит-тесты ограничения частоты запросов (этап 6)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.ratelimit import RateLimiter, RateLimitMiddleware


def test_limiter_allows_up_to_limit() -> None:
    """В пределах лимита запросы проходят, следующий блокируется."""

    limiter = RateLimiter(per_minute=2)

    assert limiter.check("client", now=0.0)[0] is True
    assert limiter.check("client", now=1.0)[0] is True

    allowed, retry_after = limiter.check("client", now=2.0)
    assert allowed is False
    assert retry_after > 0


def test_window_slides() -> None:
    """После окна слот освобождается."""

    limiter = RateLimiter(per_minute=1, window_seconds=60.0)

    assert limiter.check("client", now=0.0)[0] is True
    assert limiter.check("client", now=30.0)[0] is False
    assert limiter.check("client", now=61.0)[0] is True


def test_clients_are_counted_separately() -> None:
    """Разные клиенты не мешают друг другу."""

    limiter = RateLimiter(per_minute=1)

    assert limiter.check("first", now=0.0)[0] is True
    assert limiter.check("second", now=0.0)[0] is True


def _build_app(per_minute: int, enabled: bool = True) -> FastAPI:
    """Мини-приложение с лимитером."""

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, per_minute=per_minute, enabled=enabled)

    @app.get("/api/v1/ping")
    async def ping() -> dict:
        return {"ok": True}

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True}

    return app


def test_third_request_is_blocked() -> None:
    """При лимите 2 в минуту третий запрос получает 429 в едином формате."""

    client = TestClient(_build_app(per_minute=2))

    assert client.get("/api/v1/ping").status_code == 200
    assert client.get("/api/v1/ping").status_code == 200

    response = client.get("/api/v1/ping")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"
    assert "Retry-After" in response.headers


def test_disabled_limiter_does_not_block() -> None:
    """При выключенном лимите запросы не блокируются."""

    client = TestClient(_build_app(per_minute=1, enabled=False))

    for _ in range(4):
        assert client.get("/api/v1/ping").status_code == 200


def test_health_is_outside_the_limit() -> None:
    """Служебный /health не попадает под лимит прикладных эндпоинтов."""

    client = TestClient(_build_app(per_minute=1))

    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200
