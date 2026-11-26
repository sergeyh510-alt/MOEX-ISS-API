"""Интеграционные тесты лидеров и рейтинга против живой БД (этап 5).

Запускаются только при TEST_DB=1 и наличии доступной БД со слепком.
"""

import os
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_DB") != "1",
    reason="интеграционный тест: нужен TEST_DB=1 и живая БД",
)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@pytest.fixture
def client() -> TestClient:
    """TestClient с поднятым lifespan."""

    with TestClient(app) as test_client:
        yield test_client


def test_movers_latest_day(client: TestClient) -> None:
    """/movers без параметров отдаёт 200 и непустой best в режиме дня."""

    response = client.get("/api/v1/movers")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "day"
    assert body["best"]
    assert DATE_RE.match(body["best"][0]["date"])


def test_movers_by_date(client: TestClient) -> None:
    """/movers?date=2024-01-10 отдаёт 200 и режим day с этой датой."""

    response = client.get("/api/v1/movers", params={"date": "2024-01-10"})
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "day"
    assert body["date"] == "2024-01-10"
    assert body["best"]


def test_movers_period(client: TestClient) -> None:
    """/movers с периодом отдаёт 200 и режим period."""

    response = client.get("/api/v1/movers", params={"from": "2024-01-04", "to": "2024-01-10"})
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "period"
    assert body["best"]


def test_movers_date_and_period_conflict(client: TestClient) -> None:
    """/movers с date и периодом одновременно даёт 422."""

    response = client.get(
        "/api/v1/movers",
        params={"date": "2024-01-10", "from": "2024-01-04"},
    )
    assert response.status_code == 422


def test_ranking_default(client: TestClient) -> None:
    """/ranking отдаёт 200, первый элемент rank 1."""

    response = client.get("/api/v1/ranking", params={"limit": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["items"]
    assert body["items"][0]["rank"] == 1


def test_ranking_volatility_ascending(client: TestClient) -> None:
    """/ranking с metric=volatility&order=asc отдаёт значения по возрастанию."""

    response = client.get(
        "/api/v1/ranking",
        params={"metric": "volatility", "order": "asc", "limit": 10},
    )
    assert response.status_code == 200
    values = [
        item["volatility_pct"]
        for item in response.json()["items"]
        if item["volatility_pct"] is not None
    ]
    assert values == sorted(values)
