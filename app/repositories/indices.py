"""Запросы к core.fact_daily_index (индексы). Только SELECT."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import FactDailyIndex
from app.schemas.common import Order
from app.services.dates import date_to_date_key


async def list_index_infos(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
) -> tuple[list[tuple[str, int, int, int]], int]:
    """Список уникальных index_code с покрытием: (код, min, max, число строк).

    Возвращает страницу и общее число уникальных индексов, сортировка по коду.
    """

    total_stmt = select(func.count(func.distinct(FactDailyIndex.index_code)))
    total = (await session.execute(total_stmt)).scalar_one()

    stmt = (
        select(
            FactDailyIndex.index_code,
            func.min(FactDailyIndex.date_key),
            func.max(FactDailyIndex.date_key),
            func.count(),
        )
        .group_by(FactDailyIndex.index_code)
        .order_by(FactDailyIndex.index_code.asc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).all()
    infos = [(row[0], int(row[1]), int(row[2]), int(row[3])) for row in rows]
    return infos, int(total)


async def get_index_code(session: AsyncSession, *, code: str) -> str | None:
    """Вернуть код индекса так, как он записан в БД (поиск без учёта регистра).

    Сравнение делаем через нижний регистр, наружу отдаём исходное написание
    первой найденной строки. None, если кода нет.
    """

    stmt = (
        select(FactDailyIndex.index_code)
        .where(func.lower(FactDailyIndex.index_code) == code.lower())
        .limit(1)
    )
    return (await session.execute(stmt)).scalars().first()


async def list_index_bars(
    session: AsyncSession,
    *,
    index_code: str,
    from_date: date | None,
    to_date: date | None,
    order: Order,
    limit: int,
    offset: int,
) -> tuple[list[FactDailyIndex], int]:
    """Вернуть страницу дневных баров индекса и общее число строк по фильтру."""

    conditions = [func.lower(FactDailyIndex.index_code) == index_code.lower()]
    if from_date is not None:
        conditions.append(FactDailyIndex.date_key >= date_to_date_key(from_date))
    if to_date is not None:
        conditions.append(FactDailyIndex.date_key <= date_to_date_key(to_date))

    total_stmt = select(func.count()).select_from(FactDailyIndex).where(*conditions)
    column = FactDailyIndex.date_key
    direction = column.asc() if order == Order.asc else column.desc()
    rows_stmt = (
        select(FactDailyIndex)
        .where(*conditions)
        .order_by(direction)
        .limit(limit)
        .offset(offset)
    )

    total = (await session.execute(total_stmt)).scalar_one()
    rows = list((await session.execute(rows_stmt)).scalars().all())
    return rows, int(total)
