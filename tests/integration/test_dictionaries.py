"""Интеграционные тесты справочников против живой БД со слепком (этап 2).

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
    """TestClient с поднятым lifespan (инициализация пула соединений)."""

    with TestClient(app) as test_client:
        yield test_client


def test_dates_returns_total_and_header(client: TestClient) -> None:
    """/api/v1/dates отдаёт total > 0 и заголовок X-Total-Count."""

    response = client.get("/api/v1/dates", params={"limit": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] > 0
    assert len(body["items"]) <= 5
    assert response.headers.get("X-Total-Count") == str(body["total"])


def test_securities_search_finds_sber(client: TestClient) -> None:
    """Поиск q=sber находит бумагу SBER."""

    response = client.get("/api/v1/securities", params={"q": "sber"})
    assert response.status_code == 200
    body = response.json()
    secids = {item["secid"] for item in body["items"]}
    assert "SBER" in secids


def test_security_detail_ok(client: TestClient) -> None:
    """Карточка существующей бумаги отдаёт 200 и coverage."""

    response = client.get("/api/v1/securities/SBER")
    assert response.status_code == 200
    body = response.json()
    assert body["secid"] == "SBER"
    assert "coverage" in body
    assert body["coverage"]["price_rows"] >= 0


def test_security_detail_not_found(client: TestClient) -> None:
    """Карточка несуществующей бумаги отдаёт 404."""

    response = client.get("/api/v1/securities/ZZZZZZNOPE")
    assert response.status_code == 404


def test_meta_version_and_freshness(client: TestClient) -> None:
    """/meta/version и /meta/freshness отвечают 200."""

    version = client.get("/api/v1/meta/version")
    assert version.status_code == 200
    assert version.json()["name"] == "MOEX-ISS API"

    freshness = client.get("/api/v1/meta/freshness")
    assert freshness.status_code == 200
    assert "generated_at" in freshness.json()
    assert "layers" in freshness.json()
