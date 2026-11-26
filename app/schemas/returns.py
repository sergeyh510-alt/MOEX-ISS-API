"""Схемы доходности (mart.stock_returns) и сводки по периоду."""

from datetime import date

from pydantic import BaseModel


class ReturnRow(BaseModel):
    """Строка метрик доходности за день."""

    date: date
    date_key: int
    close: float
    prev_close: float | None
    daily_return_pct: float | None
    gap_pct: float | None
    amplitude_pct: float | None
    ma_5: float | None
    ma_20: float | None
    volatility_5_pct: float | None
    volatility_20_pct: float | None
    cumulative_return_pct: float | None


class ClosePoint(BaseModel):
    """Точка экстремума цены закрытия."""

    date: date
    close: float


class DayReturn(BaseModel):
    """День с экстремальной доходностью."""

    date: date
    daily_return_pct: float | None


class Summary(BaseModel):
    """Сводка по бумаге за период (без конверта)."""

    secid: str
    boardid: str
    from_date: date | None
    to_date: date | None
    trading_days: int
    first_close: float | None
    last_close: float | None
    period_return_pct: float | None
    cumulative_return_pct: float | None
    avg_daily_return_pct: float | None
    volatility_pct: float | None
    best_day: DayReturn | None
    worst_day: DayReturn | None
    max_close: ClosePoint | None
    min_close: ClosePoint | None
    max_drawdown_pct: float | None
