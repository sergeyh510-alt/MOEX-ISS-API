"""Эндпоинт торгового календаря: GET /api/v1/dates."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    Pagination,
    PeriodDates,
    get_pagination,
    get_period,
    resolve_order,
    set_pagination_headers,
)
from app.db import get_session
from app.repositories import dates as dates_repo
from app.schemas.common import Order, Page
from app.schemas.dates import CalendarDay

router = APIRouter(tags=["Calendar"])


@router.get("/dates", response_model=Page[CalendarDay], summary="Торговый календарь")
async def list_dates(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[Pagination, Depends(get_pagination)],
    period: Annotated[PeriodDates, Depends(get_period)],
    trading_only: Annotated[bool, Query(description="Только торговые дни")] = False,
    sort: Annotated[
        dates_repo.DateSortField,
        Query(description="Поле сортировки"),
    ] = dates_repo.DateSortField[dates_repo.DEFAULT_SORT],
    order: Annotated[Order, Query(description="Направление сортировки")] = Order.desc,
) -> Page[CalendarDay]:
    """Дни торгового календаря из core.dim_date с фильтрами и пагинацией."""

    rows, total = await dates_repo.list_dates(
        session,
        from_date=period.from_date,
        to_date=period.to_date,
        trading_only=trading_only,
        sort=sort.value,
        order=resolve_order(order),
        limit=page.limit,
        offset=page.offset,
    )
    set_pagination_headers(response, total, page.limit, page.offset)
    items = [
        CalendarDay(
            date_key=row.date_key,
            date=row.calendar_date,
            year=row.year,
            quarter=row.quarter,
            month=row.month,
            day=row.day,
            iso_week=row.iso_week,
            day_of_week=row.day_of_week,
            day_name=row.day_name,
            is_weekend=row.is_weekend,
            is_trading_day=row.is_trading_day,
        )
        for row in rows
    ]
    return Page[CalendarDay](items=items, total=total, limit=page.limit, offset=page.offset)
