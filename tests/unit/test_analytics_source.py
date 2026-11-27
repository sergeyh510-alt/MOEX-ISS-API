"""Юнит-тесты выбора источника аналитики (этап 8).

Проверяем, что выбор источника сосредоточен в app.services.analytics, что при
USE_CLICKHOUSE=false берётся PostgreSQL, при true ClickHouse, и что недоступный
ClickHouse при поднятом флаге даёт 503, а не тихий откат на PostgreSQL.
"""

import pytest

from app import analytics_ch
from app.core.errors import AppError
from app.services import analytics


class _FakeSettings:
    """Простая заглушка настроек с одним значимым полем."""

    def __init__(self, use_clickhouse: bool) -> None:
        self.USE_CLICKHOUSE = use_clickhouse


def test_select_source_postgres_by_default(monkeypatch) -> None:
    """При USE_CLICKHOUSE=false источник это PostgreSQL."""

    monkeypatch.setattr(analytics, "get_settings", lambda: _FakeSettings(False))
    assert analytics.clickhouse_enabled() is False
    assert analytics.select_source() is analytics.AnalyticsSource.postgres


def test_select_source_clickhouse_when_enabled(monkeypatch) -> None:
    """При USE_CLICKHOUSE=true источник это ClickHouse."""

    monkeypatch.setattr(analytics, "get_settings", lambda: _FakeSettings(True))
    assert analytics.clickhouse_enabled() is True
    assert analytics.select_source() is analytics.AnalyticsSource.clickhouse


async def test_clickhouse_unavailable_raises_503(monkeypatch) -> None:
    """Поднятый флаг и недоступный ClickHouse дают 503, а не откат на PostgreSQL."""

    monkeypatch.setattr(analytics, "get_settings", lambda: _FakeSettings(True))
    monkeypatch.setattr(analytics_ch, "available", lambda: False)

    with pytest.raises(AppError) as excinfo:
        await analytics.load_ranking_data(None, from_date=None, to_date=None)

    assert excinfo.value.status_code == 503
    assert excinfo.value.code == "service_unavailable"


async def test_clickhouse_query_error_raises_503(monkeypatch) -> None:
    """Сбой запроса в ClickHouse (после успешной проверки) тоже даёт 503."""

    monkeypatch.setattr(analytics, "get_settings", lambda: _FakeSettings(True))
    monkeypatch.setattr(analytics_ch, "available", lambda: True)

    def _boom(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(analytics.ch_analytics, "fetch_returns_bounds", _boom)

    with pytest.raises(AppError) as excinfo:
        await analytics.load_ranking_data(None, from_date=None, to_date=None)

    assert excinfo.value.status_code == 503


async def test_postgres_path_does_not_touch_clickhouse(monkeypatch) -> None:
    """При выключенном флаге ClickHouse не вызывается вообще."""

    pytest.importorskip("sqlalchemy")

    from app.repositories import ranking as ranking_repo

    monkeypatch.setattr(analytics, "get_settings", lambda: _FakeSettings(False))

    def _fail() -> bool:
        raise AssertionError("ClickHouse не должен вызываться при выключенном флаге")

    monkeypatch.setattr(analytics_ch, "available", _fail)

    calls: dict[str, int] = {}

    async def fake_bounds(_session):
        calls["bounds"] = calls.get("bounds", 0) + 1
        return 20240110, 20240111

    async def fake_window(_session, **_kwargs):
        return ["pg-row"]

    async def fake_leadership(_session, **_kwargs):
        return {1: (1, 0)}

    # Подменяем три функции настоящего модуля. analytics.load_ranking_data
    # импортирует его локально как from app.repositories import ranking, и
    # получит тот же объект модуля с уже подменёнными функциями. Подстановка
    # в sys.modules тут не работает: атрибут пакета уже указывает на реальный
    # модуль, если он был импортирован раньше.
    monkeypatch.setattr(ranking_repo, "get_returns_bounds", fake_bounds)
    monkeypatch.setattr(ranking_repo, "list_returns_window", fake_window)
    monkeypatch.setattr(ranking_repo, "count_leadership", fake_leadership)

    rows, leadership = await analytics.load_ranking_data(None, from_date=None, to_date=None)

    assert rows == ["pg-row"]
    assert leadership == {1: (1, 0)}
    assert calls.get("bounds") == 1
