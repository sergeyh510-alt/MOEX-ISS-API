"""Интеграционные тесты индексов и сравнения против живой БД (этап 4).

Запускаются только при TEST_DB=1 и наличии доступной БД со слепком.
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_DB") != "1",
    reason="интеграционный тест: нужен TEST_DB=1 и живая БД",
)


@pytest.fixture
def client() -> TestClient:
    """TestClient с поднятым lifespan."""

    with TestClient(app) as test_client:
        yield test_client


def test_indices_list(client: TestClient) -> None:
    """/api/v1/indices отдаёт 200 и total >= 1."""

    response = client.get("/api/v1/indices")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert body["items"]
    assert {"index_code", "first_date", "last_date", "rows"} <= set(body["items"][0])


def test_index_history_imoex(client: TestClient) -> None:
    """/api/v1/indices/IMOEX отдаёт 200 и непустой список."""

    response = client.get("/api/v1/indices/IMOEX", params={"limit": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] > 0
    assert body["items"]
    assert {"date", "date_key", "open", "close"} <= set(body["items"][0])


def test_unknown_index_404(client: TestClient) -> None:
    """/api/v1/indices/NOSUCH даёт 404."""

    assert client.get("/api/v1/indices/NOSUCH").status_code == 404


def test_compare_sber_imoex(client: TestClient) -> None:
    """/api/v1/compare для SBER и IMOEX отдаёт 200 и согласованный excess_return_pct."""

    response = client.get(
        "/api/v1/compare",
        params={"secid": "SBER", "index": "IMOEX", "limit": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["items"]
    first = body["items"][0]
    assert first["secid"] == "SBER"
    assert first["index_code"] == "IMOEX"
    expected = first["stock_return_pct"] - first["index_return_pct"]
    assert abs(first["excess_return_pct"] - expected) < 0.01


def test_compare_unknown_security_404(client: TestClient) -> None:
    """/api/v1/compare с несуществующей бумагой даёт 404."""

    response = client.get("/api/v1/compare", params={"secid": "NOSUCH", "index": "IMOEX"})
    assert response.status_code == 404
