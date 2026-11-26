"""Эндпоинты справочника бумаг: список и карточка с покрытием."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    Pagination,
    get_pagination,
    resolve_order,
    resolve_security,
    set_pagination_headers,
)
from app.db import get_session
from app.repositories import securities as securities_repo
from app.schemas.common import Order, Page
from app.schemas.securities import Security, SecurityDetail
from app.services.securities import to_security, to_security_detail

router = APIRouter(tags=["Securities"])


@router.get("/securities", response_model=Page[Security], summary="Список бумаг")
async def list_securities(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[Pagination, Depends(get_pagination)],
    q: Annotated[
        str | None,
        Query(description="Поиск по secid и shortname (регистронезависимо)"),
    ] = None,
    boardid: Annotated[str | None, Query(description="Точный код режима торгов")] = None,
    sort: Annotated[
        securities_repo.SecuritySortField,
        Query(description="Поле сортировки"),
    ] = securities_repo.SecuritySortField[securities_repo.DEFAULT_SORT],
    order: Annotated[Order, Query(description="Направление сортировки")] = Order.asc,
) -> Page[Security]:
    """Справочник бумаг из core.dim_security с поиском и пагинацией."""

    rows, total = await securities_repo.list_securities(
        session,
        q=q,
        boardid=boardid,
        sort=sort.value,
        order=resolve_order(order),
        limit=page.limit,
        offset=page.offset,
    )
    set_pagination_headers(response, total, page.limit, page.offset)
    items = [to_security(row) for row in rows]
    return Page[Security](items=items, total=total, limit=page.limit, offset=page.offset)


@router.get(
    "/securities/{secid}",
    response_model=SecurityDetail,
    summary="Карточка бумаги с покрытием",
)
async def get_security(
    secid: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    boardid: Annotated[
        str | None,
        Query(description="Режим торгов, если у бумаги их несколько"),
    ] = None,
) -> SecurityDetail:
    """Карточка бумаги из core.dim_security плюс покрытие mart.stock_returns.

    Если boardid не задан, а строк несколько (у одной secid бывает несколько
    режимов торгов), берётся строка с самым поздним last_tradedate.
    """

    row = await resolve_security(session, secid=secid, boardid=boardid)

    min_date_key, max_date_key, price_rows = await securities_repo.get_coverage(
        session,
        security_key=row.security_key,
    )
    return to_security_detail(row, min_date_key, max_date_key, price_rows)
