"""Юнит-тесты служебных эндпоинтов (этап 0)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_ok() -> None:
    """GET / отвечает 200 и содержит базовые поля."""

    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "MOEX-ISS API"
    assert "version" in body
    assert body["docs"] == "/docs"
    assert body["health"] == "/health"


def test_health_ok() -> None:
    """GET /health отвечает 200 и status == ok."""

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
