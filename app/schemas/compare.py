"""Схемы сравнения бумаги с индексом (mart.index_compare)."""

from datetime import date

from pydantic import BaseModel


class CompareRow(BaseModel):
    """Строка сравнения доходности бумаги и индекса за день."""

    date: date
    date_key: int
    secid: str
    index_code: str
    stock_return_pct: float | None
    index_return_pct: float | None
    excess_return_pct: float | None
