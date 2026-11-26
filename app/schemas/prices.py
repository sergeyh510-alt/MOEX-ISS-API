"""Схемы дневных цен OHLCV (core.fact_daily_prices)."""

from datetime import date

from pydantic import BaseModel


class PriceBar(BaseModel):
    """Один дневной бар цены."""

    date: date
    date_key: int
    open: float
    low: float
    high: float
    close: float
    waprice: float | None
    value: float | None
    volume: int | None
    numtrades: int | None
    prev_close: float | None
    close_change: float | None
    close_change_pct: float | None
