"""Схемы индексов (core.fact_daily_index)."""

from datetime import date

from pydantic import BaseModel


class IndexInfo(BaseModel):
    """Сводка по индексу: код и покрытие в витрине."""

    index_code: str
    first_date: date
    last_date: date
    rows: int


class IndexBar(BaseModel):
    """Один дневной бар индекса."""

    date: date
    date_key: int
    open: float
    low: float
    high: float
    close: float
    value: float | None
    prev_close: float | None
    close_change: float | None
    close_change_pct: float | None
