"""Запросы к mart.daily_movers (лидеры роста и падения). Только SELECT."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mart import DailyMover


async def get_latest_date_key(session: AsyncSession) -> int | None:
    """Самый поздний торговый день, который есть в mart.daily_movers."""

    stmt = select(func.max(DailyMover.date_key))
    return (await session.execute(stmt)).scalar_one()


async def list_movers(
    session: AsyncSession,
    *,
    from_date_key: int,
    to_date_key: int,
    best: bool,
    limit: int,
) -> list[DailyMover]:
    """Лидеры окна: лучшие (best) по доходности убыв., иначе худшие по возрастанию.

    Вторичный ключ secid asc, чтобы порядок был стабильным при равной доходности.
    """

    conditions = [
        DailyMover.date_key >= from_date_key,
        DailyMover.date_key <= to_date_key,
    ]
    column = DailyMover.daily_return_pct
    direction = column.desc() if best else column.asc()
    stmt = (
        select(DailyMover)
        .where(*conditions)
        .order_by(direction, DailyMover.secid.asc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())
