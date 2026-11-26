"""Схемы торгового календаря (core.dim_date)."""

from datetime import date

from pydantic import BaseModel


class CalendarDay(BaseModel):
    """Один день торгового календаря."""

    date_key: int
    date: date
    year: int
    quarter: int
    month: int
    day: int
    iso_week: int
    day_of_week: int
    day_name: str
    is_weekend: bool
    is_trading_day: bool

