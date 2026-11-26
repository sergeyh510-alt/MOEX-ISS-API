"""Чистая математика рейтинга бумаг за период плюс ранжирование.

Функции работают со списками чисел и простыми объектами и не зависят от БД,
поэтому покрываются юнит-тестами. Проценты округляются тем же хелпером
``round_pct`` из ``app.services.returns``, чтобы не заводить второй способ.
"""

from dataclasses import dataclass
from enum import Enum

from app.schemas.common import Order
from app.services import returns as math


class RankingMetric(str, Enum):
    """Метрика сортировки рейтинга."""

    period_return = "period_return"
    avg_daily_return = "avg_daily_return"
    volatility = "volatility"
    cumulative_return = "cumulative_return"


# Какое поле агрегата соответствует каждой метрике сортировки.
METRIC_FIELDS = {
    RankingMetric.period_return: "period_return_pct",
    RankingMetric.avg_daily_return: "avg_daily_return_pct",
    RankingMetric.volatility: "volatility_pct",
    RankingMetric.cumulative_return: "cumulative_return_pct",
}


@dataclass
class RankingAggregate:
    """Агрегаты одной бумаги за период (без ранга)."""

    secid: str
    security_key: int
    boardid: str
    trading_days: int
    first_close: float | None
    last_close: float | None
    period_return_pct: float | None
    avg_daily_return_pct: float | None
    volatility_pct: float | None
    cumulative_return_pct: float | None
    best_day: float | None
    worst_day: float | None
    times_best_of_day: int = 0
    times_worst_of_day: int = 0


def aggregate_series(
    *,
    secid: str,
    security_key: int,
    boardid: str,
    closes: list[float],
    daily_returns: list[float | None],
    cumulative_last: float | None,
    times_best_of_day: int = 0,
    times_worst_of_day: int = 0,
) -> RankingAggregate:
    """Собрать агрегаты бумаги из ряда цен и дневной доходности.

    ``closes`` и ``daily_returns`` идут в порядке возрастания даты.
    ``daily_returns`` может содержать None (пропускаются в статистике).
    ``cumulative_last`` это значение cumulative_return_pct последней строки.
    Пустой ряд даёт trading_days = 0 и остальные метрики None.
    """

    trading_days = len(closes)
    if trading_days == 0:
        return RankingAggregate(
            secid=secid,
            security_key=security_key,
            boardid=boardid,
            trading_days=0,
            first_close=None,
            last_close=None,
            period_return_pct=None,
            avg_daily_return_pct=None,
            volatility_pct=None,
            cumulative_return_pct=None,
            best_day=None,
            worst_day=None,
            times_best_of_day=times_best_of_day,
            times_worst_of_day=times_worst_of_day,
        )

    first_close = closes[0]
    last_close = closes[-1]
    clean = [value for value in daily_returns if value is not None]

    return RankingAggregate(
        secid=secid,
        security_key=security_key,
        boardid=boardid,
        trading_days=trading_days,
        first_close=first_close,
        last_close=last_close,
        period_return_pct=math.period_return_pct(first_close, last_close),
        avg_daily_return_pct=math.average_return_pct(daily_returns),
        volatility_pct=math.sample_volatility_pct(daily_returns),
        cumulative_return_pct=math.round_pct(cumulative_last),
        best_day=math.round_pct(max(clean)) if clean else None,
        worst_day=math.round_pct(min(clean)) if clean else None,
        times_best_of_day=times_best_of_day,
        times_worst_of_day=times_worst_of_day,
    )


def build_aggregates(series, leadership) -> list[RankingAggregate]:
    """Сгруппировать строки витрины по бумаге и посчитать агрегаты.

    ``series`` это последовательность Row с полями security_key, secid, boardid,
    date_key, close, daily_return_pct, cumulative_return_pct, упорядоченная по
    (security_key, date_key). ``leadership`` это отображение security_key ->
    (times_best_of_day, times_worst_of_day).
    """

    grouped: dict[int, list] = {}
    for row in series:
        grouped.setdefault(row.security_key, []).append(row)

    aggregates: list[RankingAggregate] = []
    for security_key, rows in grouped.items():
        first = rows[0]
        closes = [float(row.close) for row in rows]
        daily_returns = [
            None if row.daily_return_pct is None else float(row.daily_return_pct)
            for row in rows
        ]
        cumulative_last = rows[-1].cumulative_return_pct
        best, worst = leadership.get(security_key, (0, 0))
        aggregates.append(
            aggregate_series(
                secid=first.secid,
                security_key=security_key,
                boardid=first.boardid,
                closes=closes,
                daily_returns=daily_returns,
                cumulative_last=None if cumulative_last is None else float(cumulative_last),
                times_best_of_day=best,
                times_worst_of_day=worst,
            )
        )
    return aggregates


def metric_value(aggregate: RankingAggregate, metric: RankingMetric) -> float | None:
    """Значение метрики сортировки у агрегата."""

    return getattr(aggregate, METRIC_FIELDS[metric])


def _sort_key(aggregate: RankingAggregate, metric: RankingMetric, order: Order):
    """Ключ сортировки: None всегда в конце, вторичный ключ secid asc.

    Для направления desc числовое значение берётся с минусом, чтобы обычная
    сортировка по возрастанию давала убывание.
    """

    value = metric_value(aggregate, metric)
    is_none = value is None
    primary = 0.0 if value is None else (-value if order == Order.desc else value)
    return (is_none, primary, aggregate.secid)


def sort_aggregates(
    aggregates: list[RankingAggregate],
    metric: RankingMetric,
    order: Order,
) -> list[RankingAggregate]:
    """Отсортировать агрегаты по метрике и направлению."""

    return sorted(aggregates, key=lambda item: _sort_key(item, metric, order))


def rank_aggregates(
    aggregates: list[RankingAggregate],
    metric: RankingMetric,
    order: Order,
    offset: int,
    limit: int,
) -> list[tuple[int, RankingAggregate]]:
    """Отсортировать, взять страницу и пронумеровать строки с учётом offset.

    Возвращает список пар (rank, aggregate), где rank начинается с offset + 1.
    """

    ordered = sort_aggregates(aggregates, metric, order)
    page = ordered[offset : offset + limit]
    return [(offset + index + 1, aggregate) for index, aggregate in enumerate(page)]
