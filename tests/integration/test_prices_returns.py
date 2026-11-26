"""Интеграционные тесты цен и доходности против живой БД (этап 3).

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


def test_prices_for_sber(client: TestClient) -> None:
    """/prices по SBER отдаёт 200 и непустой список с датой YYYY-MM-DD."""

    response = client.get("/api/v1/securities/SBER/prices", params={"limit": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] > 0
    assert body["items"]
    assert DATE_RE.match(body["items"][0]["date"])


def test_returns_for_sber(client: TestClient) -> None:
    """/returns по SBER отдаёт 200."""

    response = client.get("/api/v1/securities/SBER/returns", params={"limit": 5})
    assert response.status_code == 200
    assert "items" in response.json()


def test_summary_for_sber_period(client: TestClient) -> None:
    """/summary по SBER за 2024-01-03..2024-01-10 отдаёт 200 и trading_days > 0."""

    response = client.get(
        "/api/v1/securities/SBER/summary",
        params={"from": "2024-01-03", "to": "2024-01-10"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["secid"] == "SBER"
    assert body["trading_days"] > 0


def test_missing_security_returns_404(client: TestClient) -> None:
    """Несуществующая бумага даёт 404 на всех трёх эндпоинтах."""

    assert client.get("/api/v1/securities/ZZZZZZNOPE/prices").status_code == 404
    assert client.get("/api/v1/securities/ZZZZZZNOPE/returns").status_code == 404
    assert client.get("/api/v1/securities/ZZZZZZNOPE/summary").status_code == 404
