"""Схемы рейтинга бумаг за период."""

from pydantic import BaseModel


class RankingRow(BaseModel):
    """Строка рейтинга: агрегаты бумаги за период и место в рейтинге."""

    rank: int
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
    times_best_of_day: int
    times_worst_of_day: int
