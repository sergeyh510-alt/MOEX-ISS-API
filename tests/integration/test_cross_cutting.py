"""Интеграционные тесты сквозных механизмов (этап 6).

Запускается только при TEST_DB=1 и наличии доступной БД со слепком.
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_DB") != "1",
    reason="интеграционный тест: нужен TEST_DB=1 и живая БД",
)


def test_request_id_header_is_present() -> None:
    """Ответ содержит заголовок X-Request-ID."""

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID")


def test_request_id_is_echoed() -> None:
    """Переданный идентификатор возвращается тем же."""

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/meta/version",
            headers={"X-Request-ID": "test-request-id-123"},
        )
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == "test-request-id-123"


def test_not_found_uses_unified_envelope() -> None:
    """404 приходит в едином формате и содержит request_id."""

    with TestClient(app) as client:
        response = client.get("/api/v1/securities/NOSUCH")

        assert response.status_code == 404
        error = response.json()["error"]
        assert error["code"] == "not_found"
        assert error["request_id"] == response.headers["X-Request-ID"]


def test_validation_uses_unified_envelope() -> None:
    """422 на неверный параметр тоже в едином формате."""

    with TestClient(app) as client:
        response = client.get("/api/v1/dates", params={"sort": "bogus"})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"


def test_service_routes_stay_open() -> None:
    """/health, /docs и /openapi.json не закрыты ключом и без БД не падают."""

    with TestClient(app) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200
        assert client.get("/health").status_code in (200, 503)
