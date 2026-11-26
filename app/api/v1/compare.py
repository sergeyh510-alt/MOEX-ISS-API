"""Эндпоинт сравнения бумаги с индексом: GET /api/v1/compare."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    Pagination,
    PeriodDates,
    get_pagination,
    get_valid_period,
    resolve_order,
    resolve_security,
    set_pagination_headers,
)
from app.db import get_session
from app.repositories import compare as compare_repo
from app.repositories import indices as indices_repo
from app.schemas.common import Order, Page
from app.schemas.compare import CompareRow
from app.services.market import to_compare_row

router = APIRouter(tags=["Compare"])


@router.get("/compare", response_model=Page[CompareRow], summary="Бумага против индекса")
async def compare(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[Pagination, Depends(get_pagination)],
    period: Annotated[PeriodDates, Depends(get_valid_period)],
    secid: Annotated[str, Query(description="Код бумаги, например SBER")],
    index_code: Annotated[str, Query(alias="index", description="Код индекса, например IMOEX")],
    boardid: Annotated[str | None, Query(description="Режим торгов, если их несколько")] = None,
    order: Annotated[Order, Query(description="Направление сортировки")] = Order.asc,
) -> Page[CompareRow]:
    """Сравнение доходности бумаги и индекса из mart.index_compare за период.

    Если бумаги нет: 404. Если индекса нет в core.fact_daily_index: 404.
    Если оба есть, но пересечений за период нет: 200 и пустой список.
    """

    security = await resolve_security(session, secid=secid, boardid=boardid)

    stored_index = await indices_repo.get_index_code(session, code=index_code)
    if stored_index is None:
        raise HTTPException(status_code=404, detail=f"индекс {index_code!r} не найден")

    rows, total = await compare_repo.list_compare(
        session,
        security_key=security.security_key,
        index_code=stored_index,
        from_date=period.from_date,
        to_date=period.to_date,
        order=resolve_order(order),
        limit=page.limit,
        offset=page.offset,
    )
    set_pagination_headers(response, total, page.limit, page.offset)
    items = [to_compare_row(row) for row in rows]
    return Page[CompareRow](items=items, total=total, limit=page.limit, offset=page.offset)
