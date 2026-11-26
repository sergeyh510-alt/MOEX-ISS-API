"""Запросы к mart.index_compare (сравнение бумаги с индексом). Только SELECT."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mart import IndexCompare
from app.schemas.common import Order
from app.services.dates import date_to_date_key


async def list_compare(
    session: AsyncSession,
    *,
    security_key: int,
    index_code: str,
    from_date: date | None,
    to_date: date | None,
    order: Order,
    limit: int,
    offset: int,
) -> tuple[list[IndexCompare], int]:
    """Вернуть страницу сравнения бумаги с индексом и общее число строк."""

    conditions = [
        IndexCompare.security_key == security_key,
        func.lower(IndexCompare.index_code) == index_code.lower(),
    ]
    if from_date is not None:
        conditions.append(IndexCompare.date_key >= date_to_date_key(from_date))
    if to_date is not None:
        conditions.append(IndexCompare.date_key <= date_to_date_key(to_date))

    total_stmt = select(func.count()).select_from(IndexCompare).where(*conditions)
    column = IndexCompare.date_key
    direction = column.asc() if order == Order.asc else column.desc()
    rows_stmt = (
        select(IndexCompare)
        .where(*conditions)
        .order_by(direction)
        .limit(limit)
        .offset(offset)
    )

    total = (await session.execute(total_stmt)).scalar_one()
    rows = list((await session.execute(rows_stmt)).scalars().all())
    return rows, int(total)
