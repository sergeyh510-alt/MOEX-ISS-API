"""Юнит-тесты математики ранжирования и рейтинга (этап 5)."""

from types import SimpleNamespace

from app.schemas.common import Order
from app.services.ranking import (
    RankingAggregate,
    RankingMetric,
    aggregate_series,
    build_aggregates,
    rank_aggregates,
)


def _aggregate(
    secid: str,
    *,
    period_return: float | None,
    volatility: float | None = None,
    security_key: int = 1,
) -> RankingAggregate:
    """Собрать агрегат с заданными метриками напрямую для проверки сортировки."""

    return RankingAggregate(
        secid=secid,
        security_key=security_key,
        boardid="TQBR",
        trading_days=2,
        first_close=100.0,
        last_close=110.0,
        period_return_pct=period_return,
        avg_daily_return_pct=period_return,
        volatility_pct=volatility,
        cumulative_return_pct=period_return,
        best_day=None,
        worst_day=None,
    )


def test_aggregate_series_period_return() -> None:
    """Период, среднее и волатильность на явном ряде.

    Ряд close [100, 110, 121]: доходность за период 21 процент.
    Дневная доходность [None, 10, 10]: среднее 10, выборочное stddev 0.
    """

    aggregate = aggregate_series(
        secid="SBER",
        security_key=1,
        boardid="TQBR",
        closes=[100.0, 110.0, 121.0],
        daily_returns=[None, 10.0, 10.0],
        cumulative_last=21.0,
    )
    assert aggregate.trading_days == 3
    assert aggregate.first_close == 100.0
    assert aggregate.last_close == 121.0
    assert aggregate.period_return_pct == 21.0
    assert aggregate.avg_daily_return_pct == 10.0
    assert aggregate.volatility_pct == 0.0
    assert aggregate.cumulative_return_pct == 21.0
    assert aggregate.best_day == 10.0
    assert aggregate.worst_day == 10.0


def test_aggregate_series_volatility() -> None:
    """Выборочная волатильность ряда [1.0, 3.0] равна 1.4142."""

    aggregate = aggregate_series(
        secid="GAZP",
        security_key=2,
        boardid="TQBR",
        closes=[100.0, 101.0, 103.0],
        daily_returns=[1.0, 3.0],
        cumulative_last=None,
    )
    assert aggregate.volatility_pct is not None
    assert abs(aggregate.volatility_pct - 1.4142) < 1e-4
    assert aggregate.cumulative_return_pct is None
    assert aggregate.best_day == 3.0
    assert aggregate.worst_day == 1.0


def test_aggregate_series_single_and_empty() -> None:
    """Ряд из одного элемента: волатильность None, период 0. Пустой: всё None."""

    one = aggregate_series(
        secid="LKOH",
        security_key=3,
        boardid="TQBR",
        closes=[100.0],
        daily_returns=[5.0],
        cumulative_last=5.0,
    )
    assert one.trading_days == 1
    assert one.period_return_pct == 0.0
    assert one.volatility_pct is None
    assert one.best_day == 5.0
    assert one.worst_day == 5.0

    empty = aggregate_series(
        secid="LKOH",
        security_key=3,
        boardid="TQBR",
        closes=[],
        daily_returns=[],
        cumulative_last=None,
    )
    assert empty.trading_days == 0
    assert empty.period_return_pct is None
    assert empty.volatility_pct is None
    assert empty.first_close is None
    assert empty.best_day is None


def test_rank_order_desc_with_offset() -> None:
    """Сортировка по убыванию и нумерация с учётом offset.

    period_return: A 10, B 30, C 20. По убыванию: B(1), C(2), A(3).
    Со offset 1 и limit 2 получаем (2, C) и (3, A).
    """

    aggregates = [
        _aggregate("A", period_return=10.0),
        _aggregate("B", period_return=30.0),
        _aggregate("C", period_return=20.0),
    ]
    ranked = rank_aggregates(aggregates, RankingMetric.period_return, Order.desc, 1, 2)
    assert [(rank, item.secid) for rank, item in ranked] == [(2, "C"), (3, "A")]


def test_rank_order_asc() -> None:
    """Сортировка по возрастанию: A(1), C(2), B(3)."""

    aggregates = [
        _aggregate("A", period_return=10.0),
        _aggregate("B", period_return=30.0),
        _aggregate("C", period_return=20.0),
    ]
    ranked = rank_aggregates(aggregates, RankingMetric.period_return, Order.asc, 0, 10)
    assert [(rank, item.secid) for rank, item in ranked] == [
        (1, "A"),
        (2, "C"),
        (3, "B"),
    ]


def test_rank_none_last_both_orders() -> None:
    """None-значения метрики всегда в конце, независимо от направления."""

    aggregates = [
        _aggregate("A", period_return=5.0, volatility=5.0),
        _aggregate("B", period_return=None, volatility=None),
        _aggregate("C", period_return=2.0, volatility=2.0),
    ]
    asc = rank_aggregates(aggregates, RankingMetric.volatility, Order.asc, 0, 10)
    desc = rank_aggregates(aggregates, RankingMetric.volatility, Order.desc, 0, 10)
    assert [item.secid for _, item in asc] == ["C", "A", "B"]
    assert [item.secid for _, item in desc] == ["A", "C", "B"]


def test_build_aggregates_groups_by_security() -> None:
    """build_aggregates группирует строки по бумаге и считает счётчики лидеров."""

    series = [
        SimpleNamespace(
            security_key=1,
            secid="SBER",
            boardid="TQBR",
            date_key=20240110,
            close=100.0,
            daily_return_pct=1.0,
            cumulative_return_pct=1.0,
        ),
        SimpleNamespace(
            security_key=1,
            secid="SBER",
            boardid="TQBR",
            date_key=20240111,
            close=110.0,
            daily_return_pct=2.0,
            cumulative_return_pct=10.0,
        ),
        SimpleNamespace(
            security_key=2,
            secid="GAZP",
            boardid="TQBR",
            date_key=20240110,
            close=50.0,
            daily_return_pct=-1.0,
            cumulative_return_pct=-1.0,
        ),
    ]
    leadership = {1: (1, 0), 2: (0, 1)}
    aggregates = {item.security_key: item for item in build_aggregates(series, leadership)}

    assert aggregates[1].secid == "SBER"
    assert aggregates[1].trading_days == 2
    assert aggregates[1].period_return_pct == 10.0
    assert aggregates[1].cumulative_return_pct == 10.0
    assert aggregates[1].times_best_of_day == 1
    assert aggregates[1].times_worst_of_day == 0
    assert aggregates[2].secid == "GAZP"
    assert aggregates[2].trading_days == 1
    assert aggregates[2].times_best_of_day == 0
    assert aggregates[2].times_worst_of_day == 1
