"""Запросы к core.fact_daily_prices (дневные цены OHLCV). Только SELECT."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import FactDailyPrice
from app.schemas.common import Order
from app.services.dates import date_to_date_key


async def list_prices(
    session: AsyncSession,
    *,
    security_key: int,
    from_date: date | None,
    to_date: date | None,
    order: Order,
    limit: int,
    offset: int,
) -> tuple[list[FactDailyPrice], int]:
    """Вернуть страницу дневных цен бумаги и общее число строк по фильтру."""

    conditions = [FactDailyPrice.security_key == security_key]
    if from_date is not None:
        conditions.append(FactDailyPrice.date_key >= date_to_date_key(from_date))
    if to_date is not None:
        conditions.append(FactDailyPrice.date_key <= date_to_date_key(to_date))

    total_stmt = select(func.count()).select_from(FactDailyPrice).where(*conditions)
    column = FactDailyPrice.date_key
    direction = column.asc() if order == Order.asc else column.desc()
    rows_stmt = (
        select(FactDailyPrice)
        .where(*conditions)
        .order_by(direction)
        .limit(limit)
        .offset(offset)
    )

    total = (await session.execute(total_stmt)).scalar_one()
    rows = list((await session.execute(rows_stmt)).scalars().all())
    return rows, int(total)
