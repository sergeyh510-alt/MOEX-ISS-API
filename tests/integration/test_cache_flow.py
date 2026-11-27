"""Интеграционный тест сквозного кэширования (этап 9).

Запускается только при TEST_REDIS=1 и доступном Redis. Проверяет, что первый
одинаковый запрос даёт X-Cache: MISS, а повторный HIT с тем же телом.
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_REDIS") != "1",
    reason="интеграционный тест: нужен TEST_REDIS=1 и доступный Redis",
)


def _enable_cache() -> None:
    """Включить кэш в настройках процесса и сбросить клиент Redis."""

    from app import cache
    from app.config import get_settings

    get_settings.cache_clear()
    os.environ["CACHE_ENABLED"] = "true"
    get_settings.cache_clear()
    cache._client = None


def test_second_request_is_cache_hit() -> None:
    """/api/v1/securities: первый ответ MISS, повторный HIT и то же тело."""

    _enable_cache()
    with TestClient(app) as client:
        first = client.get("/api/v1/securities", params={"limit": 5})
        second = client.get("/api/v1/securities", params={"limit": 5})

    assert first.status_code == 200
    assert first.headers.get("X-Cache") == "MISS"
    assert second.status_code == 200
    assert second.headers.get("X-Cache") == "HIT"
    assert first.json() == second.json()
