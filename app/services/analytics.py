"""Единственное место выбора источника для тяжёлой аналитики.

По умолчанию источник это PostgreSQL (истина в последней инстанции). При
``USE_CLICKHOUSE=true`` тяжёлые агрегаты (/summary и /ranking) читаются из
ClickHouse. Математику мы НЕ дублируем: оба источника отдают одни и те же
сырые строки витрин, а агрегаты считают общие функции из app.services.returns
и app.services.ranking. Поэтому результаты двух источников совпадают по
построению.

Если флаг поднят, а ClickHouse недоступен, поднимаем HTTP 503 в едином формате
ошибок. Молчаливого отката на PostgreSQL нет.

Модуль импортируется без sqlalchemy и clickhouse-connect: и репозитории, и
драйвер ClickHouse подтягиваются лениво внутри функций.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from enum import Enum
from typing import Any

from starlette.concurrency import run_in_threadpool

from app import analytics_ch
from app.config import get_settings
from app.core.errors import service_unavailable
from app.repositories import ch_analytics
from app.services.dates import date_to_date_key

# Границы date_key (int YYYYMMDD) для открытых концов периода.
MIN_DATE_KEY = 0
MAX_DATE_KEY = 99991231


class AnalyticsSource(str, Enum):
    """Источник тяжёлой аналитики."""

    postgres = "postgres"
    clickhouse = "clickhouse"


def clickhouse_enabled() -> bool:
    """Включён ли ClickHouse флагом USE_CLICKHOUSE."""

    return bool(get_settings().USE_CLICKHOUSE)


def select_source() -> AnalyticsSource:
    """Выбрать источник аналитики по настройке."""

    return AnalyticsSource.clickhouse if clickhouse_enabled() else AnalyticsSource.postgres


def _bounds_from_period(
    from_date: date | None,
    to_date: date | None,
    min_key: int | None,
    max_key: int | None,
) -> tuple[int, int]:
    """Преобразовать период в границы date_key, подставив доступный диапазон."""

    from_key = date_to_date_key(from_date) if from_date is not None else None
    to_key = date_to_date_key(to_date) if to_date is not None else None
    if from_key is None:
        from_key = min_key if min_key is not None else MIN_DATE_KEY
    if to_key is None:
        to_key = max_key if max_key is not None else MAX_DATE_KEY
    return from_key, to_key


async def _run_ch(func: Callable[..., Any], **kwargs: Any) -> Any:
    """Выполнить синхронный запрос ClickHouse в потоке.

    Сначала короткая проверка доступности. Любая ошибка (недоступность или
    сбой запроса) превращается в HTTP 503 в едином формате ошибок, а не в
    тихий откат на PostgreSQL.
    """

    if not await run_in_threadpool(analytics_ch.available):
        raise service_unavailable(
            "ClickHouse недоступен. Проверьте сервис api_ch "
            "или выключите USE_CLICKHOUSE.",
        )
    try:
        return await run_in_threadpool(lambda: func(**kwargs))
    except Exception as exc:
        raise service_unavailable(
            "Ошибка запроса к ClickHouse.",
            details=str(exc),
        ) from exc


async def load_summary_rows(
    session: Any,
    *,
    security_key: int,
    from_date: date | None,
    to_date: date | None,
) -> list:
    """Ряд витрины одной бумаги за период из выбранного источника.

    Возвращает строки с теми же полями, что и PostgreSQL-репозиторий
    list_returns_in_period, поэтому build_summary работает без изменений.
    """

    if clickhouse_enabled():
        from_key, to_key = _bounds_from_period(from_date, to_date, None, None)
        return await _run_ch(
            ch_analytics.fetch_stock_return_series,
            security_key=security_key,
            from_date_key=from_key,
            to_date_key=to_key,
        )

    from app.repositories import returns as returns_repo

    return await returns_repo.list_returns_in_period(
        session,
        security_key=security_key,
        from_date=from_date,
        to_date=to_date,
    )


async def load_ranking_data(
    session: Any,
    *,
    from_date: date | None,
    to_date: date | None,
) -> tuple[list, dict[int, tuple[int, int]]]:
    """Строки витрины за окно и счётчики лидеров из выбранного источника.

    Возвращает (rows, leadership), где rows с теми же полями, что и
    PostgreSQL-репозиторий list_returns_window, а leadership это отображение
    security_key -> (times_best_of_day, times_worst_of_day). Оба подходят
    напрямую для build_aggregates.
    """

    if clickhouse_enabled():
        min_key, max_key = await _run_ch(ch_analytics.fetch_returns_bounds)
        from_key, to_key = _bounds_from_period(from_date, to_date, min_key, max_key)
        rows = await _run_ch(
            ch_analytics.fetch_returns_window,
            from_date_key=from_key,
            to_date_key=to_key,
        )
        leadership = await _run_ch(
            ch_analytics.fetch_leadership_counts,
            from_date_key=from_key,
            to_date_key=to_key,
        )
        return rows, leadership

    # Импорт PostgreSQL-репозитория только в ветке PostgreSQL, чтобы модуль и
    # ветка ClickHouse не тянули sqlalchemy (нужно для юнит-тестов).
    from app.repositories import ranking as ranking_repo

    min_key, max_key = await ranking_repo.get_returns_bounds(session)
    from_key, to_key = _bounds_from_period(from_date, to_date, min_key, max_key)
    rows = await ranking_repo.list_returns_window(
        session,
        from_date_key=from_key,
        to_date_key=to_key,
    )
    leadership = await ranking_repo.count_leadership(
        session,
        from_date_key=from_key,
        to_date_key=to_key,
    )
    return rows, leadership
