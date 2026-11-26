"""Юнит-тесты служебных эндпоинтов (этапы 0 и 1)."""

from fastapi.testclient import TestClient

from app import db
from app.main import app

client = TestClient(app)


async def _ping_ok() -> bool:
    """Заглушка ping: БД как будто доступна."""

    return True


async def _freshness_stub() -> dict:
    """Заглушка свежести данных."""

    return {
        "last_load_at": "2026-10-09T15:02:05+00:00",
        "last_data_date": "2026-10-10",
        "layers": {},
    }


def test_root_ok() -> None:
    """GET / отвечает 200 и содержит базовые поля."""

    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "MOEX-ISS API"
    assert "version" in body
    assert body["docs"] == "/docs"
    assert body["health"] == "/health"


def test_health_ok(monkeypatch) -> None:
    """GET /health отвечает 200 и status == ok, когда БД доступна."""

    monkeypatch.setattr(db, "ping", _ping_ok)
    monkeypatch.setattr(db, "load_freshness", _freshness_stub)

    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "time_utc" in body


def test_docs_ok() -> None:
    """GET /docs отвечает 200 (Swagger доступен)."""

    response = client.get("/docs")
    assert response.status_code == 200
