"""Эндпоинты индексов: список с покрытием и история за период."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    Pagination,
    PeriodDates,
    get_pagination,
    get_valid_period,
    resolve_order,
    set_pagination_headers,
)
from app.db import get_session
from app.repositories import indices as indices_repo
from app.schemas.common import Order, Page
from app.schemas.indices import IndexBar, IndexInfo
from app.services.market import to_index_bar, to_index_info

router = APIRouter(tags=["Indices"])


@router.get("/indices", response_model=Page[IndexInfo], summary="Список индексов")
async def list_indices(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[Pagination, Depends(get_pagination)],
) -> Page[IndexInfo]:
    """Уникальные коды индексов с покрытием, сортировка по index_code."""

    infos, total = await indices_repo.list_index_infos(
        session,
        limit=page.limit,
        offset=page.offset,
    )
    set_pagination_headers(response, total, page.limit, page.offset)
    items = [
        to_index_info(code, first_dk, last_dk, rows)
        for code, first_dk, last_dk, rows in infos
    ]
    return Page[IndexInfo](items=items, total=total, limit=page.limit, offset=page.offset)


@router.get(
    "/indices/{code}",
    response_model=Page[IndexBar],
    summary="История индекса за период",
)
async def list_index_history(
    code: str,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[Pagination, Depends(get_pagination)],
    period: Annotated[PeriodDates, Depends(get_valid_period)],
    order: Annotated[Order, Query(description="Направление сортировки")] = Order.asc,
) -> Page[IndexBar]:
    """Дневные бары индекса из core.fact_daily_index, сортировка по date_key."""

    stored_code = await indices_repo.get_index_code(session, code=code)
    if stored_code is None:
        raise HTTPException(status_code=404, detail=f"индекс {code!r} не найден")

    rows, total = await indices_repo.list_index_bars(
        session,
        index_code=stored_code,
        from_date=period.from_date,
        to_date=period.to_date,
        order=resolve_order(order),
        limit=page.limit,
        offset=page.offset,
    )
    set_pagination_headers(response, total, page.limit, page.offset)
    items = [to_index_bar(row) for row in rows]
    return Page[IndexBar](items=items, total=total, limit=page.limit, offset=page.offset)
