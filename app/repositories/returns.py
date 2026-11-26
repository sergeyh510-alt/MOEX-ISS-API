"""Запросы к mart.stock_returns (метрики доходности). Только SELECT."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mart import StockReturn
from app.schemas.common import Order
from app.services.dates import date_to_date_key


async def list_returns(
    session: AsyncSession,
    *,
    security_key: int,
    from_date: date | None,
    to_date: date | None,
    order: Order,
    limit: int,
    offset: int,
) -> tuple[list[StockReturn], int]:
    """Вернуть страницу метрик доходности бумаги и общее число строк."""

    conditions = [StockReturn.security_key == security_key]
    if from_date is not None:
        conditions.append(StockReturn.date_key >= date_to_date_key(from_date))
    if to_date is not None:
        conditions.append(StockReturn.date_key <= date_to_date_key(to_date))

    total_stmt = select(func.count()).select_from(StockReturn).where(*conditions)
    column = StockReturn.date_key
    direction = column.asc() if order == Order.asc else column.desc()
    rows_stmt = (
        select(StockReturn)
        .where(*conditions)
        .order_by(direction)
        .limit(limit)
        .offset(offset)
    )

    total = (await session.execute(total_stmt)).scalar_one()
    rows = list((await session.execute(rows_stmt)).scalars().all())
    return rows, int(total)


async def get_data_bounds(
    session: AsyncSession,
    *,
    security_key: int,
) -> tuple[int | None, int | None]:
    """Границы доступного периода бумаги в витрине: (min date_key, max date_key)."""

    stmt = select(
        func.min(StockReturn.date_key),
        func.max(StockReturn.date_key),
    ).where(StockReturn.security_key == security_key)
    row = (await session.execute(stmt)).one()
    return row[0], row[1]


async def list_returns_in_period(
    session: AsyncSession,
    *,
    security_key: int,
    from_date: date | None,
    to_date: date | None,
) -> list[StockReturn]:
    """Все строки витрины бумаги за период, в порядке возрастания даты."""

    conditions = [StockReturn.security_key == security_key]
    if from_date is not None:
        conditions.append(StockReturn.date_key >= date_to_date_key(from_date))
    if to_date is not None:
        conditions.append(StockReturn.date_key <= date_to_date_key(to_date))

    stmt = select(StockReturn).where(*conditions).order_by(StockReturn.date_key.asc())
    return list((await session.execute(stmt)).scalars().all())
