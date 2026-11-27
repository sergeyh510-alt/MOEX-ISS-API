"""Паритет PostgreSQL и ClickHouse для /summary и /ranking (этап 8).

Запускается только при TEST_CH=1 и наличии обоих источников: PostgreSQL со
слепком и ClickHouse с залитыми витринами (scripts/ch_load.py). Сравниваем
числа двух источников: они должны совпадать, потому что оба отдают одни и те
же сырые строки витрин, а агрегаты считают общие функции.

Тест пропускается без TEST_CH, поэтому CI без ClickHouse остаётся зелёным.
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import analytics

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_CH") != "1",
    reason="интеграционный тест паритета ClickHouse: нужен TEST_CH=1 и оба источника",
)

# Период с данными слепка.
PERIOD = {"from": "2024-01-03", "to": "2024-01-10"}


@pytest.fixture
def client() -> TestClient:
    """TestClient с поднятым lifespan."""

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def force_source(monkeypatch):
    """Переключатель источника: подменяет USE_CLICKHOUSE в analytics."""

    real_get_settings = analytics.get_settings

    def set_clickhouse(use_clickhouse: bool) -> None:
        base = real_get_settings()
        monkeypatch.setattr(analytics, "get_settings", lambda: _with_flag(base, use_clickhouse))

    return set_clickhouse


def _with_flag(settings, use_clickhouse: bool):
    """Вернуть копию настроек с нужным значением USE_CLICKHOUSE."""

    clone = settings.model_copy(update={"USE_CLICKHOUSE": use_clickhouse})
    return clone


def test_summary_parity(client: TestClient, force_source) -> None:
    """/summary по SBER совпадает у PostgreSQL и ClickHouse."""

    force_source(False)
    pg = client.get("/api/v1/securities/SBER/summary", params=PERIOD)
    force_source(True)
    ch = client.get("/api/v1/securities/SBER/summary", params=PERIOD)

    assert pg.status_code == 200, pg.text
    assert ch.status_code == 200, ch.text
    assert ch.json() == pg.json()


def test_ranking_parity(client: TestClient, force_source) -> None:
    """/ranking за период совпадает у PostgreSQL и ClickHouse."""

    force_source(False)
    pg = client.get("/api/v1/ranking", params=PERIOD)
    force_source(True)
    ch = client.get("/api/v1/ranking", params=PERIOD)

    assert pg.status_code == 200, pg.text
    assert ch.status_code == 200, ch.text

    pg_items = {item["secid"]: item for item in pg.json()["items"]}
    ch_items = {item["secid"]: item for item in ch.json()["items"]}
    assert ch_items.keys() == pg_items.keys()
    for secid, pg_item in pg_items.items():
        ch_item = ch_items[secid]
        assert ch_item["trading_days"] == pg_item["trading_days"]
        for field in (
            "first_close",
            "last_close",
            "period_return_pct",
            "avg_daily_return_pct",
            "volatility_pct",
            "cumulative_return_pct",
            "best_day",
            "worst_day",
            "times_best_of_day",
            "times_worst_of_day",
        ):
            assert ch_item[field] == pg_item[field], f"{secid}.{field}"
