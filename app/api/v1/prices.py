"""Эндпоинт дневных цен бумаги: GET /api/v1/securities/{secid}/prices."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    Pagination,
    PeriodDates,
    get_pagination,
    get_period,
    resolve_order,
    resolve_security,
    set_pagination_headers,
)
from app.db import get_session
from app.repositories import prices as prices_repo
from app.schemas.common import Order, Page
from app.schemas.prices import PriceBar
from app.services.market import to_price_bar

router = APIRouter(tags=["Prices"])


@router.get(
    "/securities/{secid}/prices",
    response_model=Page[PriceBar],
    summary="Дневные цены OHLCV бумаги",
)
async def list_prices(
    secid: str,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[Pagination, Depends(get_pagination)],
    period: Annotated[PeriodDates, Depends(get_period)],
    boardid: Annotated[str | None, Query(description="Режим торгов, если их несколько")] = None,
    order: Annotated[Order, Query(description="Направление сортировки")] = Order.asc,
) -> Page[PriceBar]:
    """Цены OHLCV из core.fact_daily_prices за период, сортировка по date_key."""

    security = await resolve_security(session, secid=secid, boardid=boardid)
    rows, total = await prices_repo.list_prices(
        session,
        security_key=security.security_key,
        from_date=period.from_date,
        to_date=period.to_date,
        order=resolve_order(order),
        limit=page.limit,
        offset=page.offset,
    )
    set_pagination_headers(response, total, page.limit, page.offset)
    items = [to_price_bar(row) for row in rows]
    return Page[PriceBar](items=items, total=total, limit=page.limit, offset=page.offset)
