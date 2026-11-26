"""Запросы к core.dim_date (торговый календарь). Только SELECT."""

from datetime import date
from enum import Enum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import DimDate
from app.schemas.common import Order

# Допустимые для сортировки колонки dim_date.
SORT_COLUMNS = {
    "date_key": DimDate.date_key,
    "calendar_date": DimDate.calendar_date,
    "year": DimDate.year,
    "quarter": DimDate.quarter,
    "month": DimDate.month,
    "day": DimDate.day,
    "iso_week": DimDate.iso_week,
    "day_of_week": DimDate.day_of_week,
    "day_name": DimDate.day_name,
    "is_weekend": DimDate.is_weekend,
    "is_trading_day": DimDate.is_trading_day,
}

# Enum для Swagger: допустимые поля сортировки (валидируется FastAPI).
# Имя уникально, чтобы не конфликтовать со схемой сортировки других роутеров.
DateSortField = Enum("DateSortField", {name: name for name in SORT_COLUMNS}, type=str)

DEFAULT_SORT = "calendar_date"


def _order_by(sort: str, order: Order):
    """Построить выражение ORDER BY с учётом направления."""

    column = SORT_COLUMNS[sort]
    expression = column.asc() if order == Order.asc else column.desc()
    # Вторичный ключ для стабильной сортировки.
    return [expression, DimDate.date_key.desc()]


async def list_dates(
    session: AsyncSession,
    *,
    from_date: date | None,
    to_date: date | None,
    trading_only: bool,
    sort: str,
    order: Order,
    limit: int,
    offset: int,
) -> tuple[list[DimDate], int]:
    """Вернуть страницу календаря и общее число строк по фильтру."""

    conditions = []
    if from_date is not None:
        conditions.append(DimDate.calendar_date >= from_date)
    if to_date is not None:
        conditions.append(DimDate.calendar_date <= to_date)
    if trading_only:
        conditions.append(DimDate.is_trading_day.is_(True))

    total_stmt = select(func.count()).select_from(DimDate)
    rows_stmt = select(DimDate)
    if conditions:
        total_stmt = total_stmt.where(*conditions)
        rows_stmt = rows_stmt.where(*conditions)

    total = (await session.execute(total_stmt)).scalar_one()
    rows_stmt = rows_stmt.order_by(*_order_by(sort, order)).limit(limit).offset(offset)
    rows = list((await session.execute(rows_stmt)).scalars().all())
    return rows, int(total)
