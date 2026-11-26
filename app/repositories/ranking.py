"""Запросы для рейтинга бумаг: витрина mart.stock_returns и счётчики лидеров.

Слой работает только на чтение (SELECT). Тяжёлые агрегаты считает сервис
app.services.ranking, здесь только выборка строк и счётчиков.
"""

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mart import DailyMover, StockReturn


async def get_returns_bounds(session: AsyncSession) -> tuple[int | None, int | None]:
    """Границы доступного периода всей витрины: (min date_key, max date_key)."""

    stmt = select(func.min(StockReturn.date_key), func.max(StockReturn.date_key))
    row = (await session.execute(stmt)).one()
    return row[0], row[1]


async def list_returns_window(
    session: AsyncSession,
    *,
    from_date_key: int,
    to_date_key: int,
) -> list[StockReturn]:
    """Все строки витрины за окно, в порядке (security_key, date_key) возрастания."""

    stmt = (
        select(StockReturn)
        .where(
            StockReturn.date_key >= from_date_key,
            StockReturn.date_key <= to_date_key,
        )
        .order_by(StockReturn.security_key.asc(), StockReturn.date_key.asc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def count_leadership(
    session: AsyncSession,
    *,
    from_date_key: int,
    to_date_key: int,
) -> dict[int, tuple[int, int]]:
    """Число дней-лидеров и дней-аутсайдеров по каждой бумаге за окно.

    Возвращает отображение security_key -> (times_best_of_day, times_worst_of_day).
    """

    best_sum = func.sum(case((DailyMover.is_best_of_day.is_(True), 1), else_=0))
    worst_sum = func.sum(case((DailyMover.is_worst_of_day.is_(True), 1), else_=0))
    stmt = (
        select(DailyMover.security_key, best_sum, worst_sum)
        .where(
            DailyMover.date_key >= from_date_key,
            DailyMover.date_key <= to_date_key,
        )
        .group_by(DailyMover.security_key)
    )
    rows = (await session.execute(stmt)).all()
    return {int(row[0]): (int(row[1] or 0), int(row[2] or 0)) for row in rows}
