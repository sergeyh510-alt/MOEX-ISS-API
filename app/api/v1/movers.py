"""Эндпоинт лидеров роста и падения: GET /api/v1/movers (mart.daily_movers)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PeriodDates, get_valid_period
from app.db import get_session
from app.repositories import movers as movers_repo
from app.schemas.movers import MoversDay, MoversPeriod
from app.services.dates import date_key_to_date, date_to_date_key
from app.services.market import to_mover_row

router = APIRouter(tags=["Movers"])

DEFAULT_LIMIT = 5
MIN_LIMIT = 1
MAX_LIMIT = 50


def clamp_movers_limit(limit: int) -> int:
    """Ограничить размер каждого списка диапазоном 1..50."""

    return max(MIN_LIMIT, min(MAX_LIMIT, limit))


@router.get(
    "/movers",
    response_model=MoversDay | MoversPeriod,
    summary="Лидеры за день или период",
)
async def get_movers(
    session: Annotated[AsyncSession, Depends(get_session)],
    period: Annotated[PeriodDates, Depends(get_valid_period)],
    date_value: Annotated[
        date | None,
        Query(alias="date", description="Один торговый день, YYYY-MM-DD"),
    ] = None,
    limit: Annotated[
        int,
        Query(description="Размер каждого списка, клампится в 1..50"),
    ] = DEFAULT_LIMIT,
) -> MoversDay | MoversPeriod:
    """Лучшие и худшие бумаги за день либо лучшие и худшие дни за период.

    Режимы взаимоисключающие. Если задан date: берём этот торговый день. Если
    заданы from/to и date не задан: ищем лучшие и худшие дни внутри окна по
    всем бумагам. Если ни date, ни период не заданы: берём самый поздний день,
    который есть в mart.daily_movers. Одновременная передача date и периода
    даёт HTTP 422.
    """

    has_period = period.from_date is not None or period.to_date is not None
    if date_value is not None and has_period:
        raise HTTPException(
            status_code=422,
            detail="укажите либо date, либо период from/to, но не оба одновременно",
        )

    size = clamp_movers_limit(limit)

    if date_value is not None:
        return await _build_day(session, date_value, size)

    if has_period:
        return await _build_period(session, period, size)

    latest = await movers_repo.get_latest_date_key(session)
    if latest is None:
        return MoversDay(mode="day", date=None, best=[], worst=[])
    return await _build_day(session, date_key_to_date(latest), size)


async def _build_day(session: AsyncSession, day: date, size: int) -> MoversDay:
    """Собрать ответ режима дня для конкретной даты."""

    date_key = date_to_date_key(day)
    best = await movers_repo.list_movers(
        session,
        from_date_key=date_key,
        to_date_key=date_key,
        best=True,
        limit=size,
    )
    worst = await movers_repo.list_movers(
        session,
        from_date_key=date_key,
        to_date_key=date_key,
        best=False,
        limit=size,
    )
    return MoversDay(
        mode="day",
        date=day,
        best=[to_mover_row(row) for row in best],
        worst=[to_mover_row(row) for row in worst],
    )


async def _build_period(session: AsyncSession, period: PeriodDates, size: int) -> MoversPeriod:
    """Собрать ответ режима периода по окну from/to."""

    from_key = date_to_date_key(period.from_date) if period.from_date is not None else 0
    to_key = date_to_date_key(period.to_date) if period.to_date is not None else 99991231
    best = await movers_repo.list_movers(
        session,
        from_date_key=from_key,
        to_date_key=to_key,
        best=True,
        limit=size,
    )
    worst = await movers_repo.list_movers(
        session,
        from_date_key=from_key,
        to_date_key=to_key,
        best=False,
        limit=size,
    )
    return MoversPeriod(
        mode="period",
        from_=period.from_date,
        to=period.to_date,
        best=[to_mover_row(row) for row in best],
        worst=[to_mover_row(row) for row in worst],
    )
