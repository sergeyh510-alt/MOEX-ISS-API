"""Эндпоинты доходности: список метрик и сводка по периоду."""

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
from app.repositories import returns as returns_repo
from app.schemas.common import Order, Page
from app.schemas.returns import ReturnRow, Summary
from app.services.market import build_summary, to_return_row

router = APIRouter(tags=["Returns"])


@router.get(
    "/securities/{secid}/returns",
    response_model=Page[ReturnRow],
    summary="Метрики доходности бумаги",
)
async def list_returns(
    secid: str,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[Pagination, Depends(get_pagination)],
    period: Annotated[PeriodDates, Depends(get_period)],
    boardid: Annotated[str | None, Query(description="Режим торгов, если их несколько")] = None,
    order: Annotated[Order, Query(description="Направление сортировки")] = Order.asc,
) -> Page[ReturnRow]:
    """Метрики доходности из mart.stock_returns за период, по date_key.

    NULL-поля (например ma_20, когда истории мало) отдаются как null, это норма.
    """

    security = await resolve_security(session, secid=secid, boardid=boardid)
    rows, total = await returns_repo.list_returns(
        session,
        security_key=security.security_key,
        from_date=period.from_date,
        to_date=period.to_date,
        order=resolve_order(order),
        limit=page.limit,
        offset=page.offset,
    )
    set_pagination_headers(response, total, page.limit, page.offset)
    items = [to_return_row(row) for row in rows]
    return Page[ReturnRow](items=items, total=total, limit=page.limit, offset=page.offset)


@router.get(
    "/securities/{secid}/summary",
    response_model=Summary,
    tags=["Analytics"],
    summary="Сводка по бумаге за период",
)
async def get_summary(
    secid: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    period: Annotated[PeriodDates, Depends(get_period)],
    boardid: Annotated[str | None, Query(description="Режим торгов, если их несколько")] = None,
) -> Summary:
    """Сводка по бумаге за период из mart.stock_returns.

    Если период не задан, берётся весь доступный период бумаги. Если данных
    за период нет: 200 и trading_days = 0, остальные метрики null.
    """

    security = await resolve_security(session, secid=secid, boardid=boardid)
    rows = await returns_repo.list_returns_in_period(
        session,
        security_key=security.security_key,
        from_date=period.from_date,
        to_date=period.to_date,
    )
    return build_summary(
        secid=security.secid,
        boardid=security.boardid,
        rows=rows,
        from_date=period.from_date,
        to_date=period.to_date,
    )
