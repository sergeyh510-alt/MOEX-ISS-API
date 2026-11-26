"""Интеграционный тест /health против живой тестовой БД (этап 1).

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


def test_health_reports_db_ok() -> None:
    """При живой БД /health отдаёт db.status == ok и 200."""

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["db"]["status"] == "ok"
        assert body["status"] == "ok"

