"""Юнит-тесты обработчика /health с подменой доступа к БД (этап 1)."""

from fastapi.testclient import TestClient

from app import db
from app.main import app

client = TestClient(app)


async def _ping_ok() -> bool:
    return True


async def _ping_fail() -> bool:
    return False


async def _freshness() -> dict:
    return {
        "last_load_at": "2026-10-09T15:02:05+00:00",
        "last_data_date": "2026-10-10",
        "layers": {"mart.stock_returns": "2026-10-09T15:02:05+00:00"},
    }


def test_health_db_ok(monkeypatch) -> None:
    """Когда ping успешен: 200, status ok, корректная схема ответа."""

    monkeypatch.setattr(db, "ping", _ping_ok)
    monkeypatch.setattr(db, "load_freshness", _freshness)

    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["time_utc"]
    assert body["db"]["status"] == "ok"
    assert isinstance(body["db"]["latency_ms"], (int, float))
    assert body["data"]["last_load_at"] == "2026-10-09T15:02:05+00:00"
    assert body["data"]["last_data_date"] == "2026-10-10"


def test_health_db_unavailable(monkeypatch) -> None:
    """Когда ping недоступен: 503, status degraded, latency_ms None."""

    monkeypatch.setattr(db, "ping", _ping_fail)

    response = client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["db"]["status"] == "unavailable"
    assert body["db"]["latency_ms"] is None
    assert body["data"]["last_load_at"] is None
    assert body["data"]["last_data_date"] is None

