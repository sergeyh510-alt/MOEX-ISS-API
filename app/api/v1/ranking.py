"""Эндпоинт рейтинга бумаг: GET /api/v1/ranking (тег Analytics).

Рейтинг строится из mart.stock_returns (агрегаты по бумаге за период) плюс
счётчики дней-лидеров из mart.daily_movers (is_best_of_day, is_worst_of_day).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    Pagination,
    PeriodDates,
    get_pagination,
    get_valid_period,
    set_pagination_headers,
)
from app.db import get_session
from app.repositories import ranking as ranking_repo
from app.schemas.common import Order, Page
from app.schemas.ranking import RankingRow
from app.services.dates import date_to_date_key
from app.services.market import to_ranking_row
from app.services.ranking import RankingMetric, build_aggregates, rank_aggregates

router = APIRouter(tags=["Analytics"])


@router.get("/ranking", response_model=Page[RankingRow], summary="Рейтинг бумаг за период")
async def get_ranking(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[Pagination, Depends(get_pagination)],
    period: Annotated[PeriodDates, Depends(get_valid_period)],
    metric: Annotated[
        RankingMetric,
        Query(description="Метрика сортировки рейтинга"),
    ] = RankingMetric.period_return,
    order: Annotated[Order, Query(description="Направление сортировки")] = Order.desc,
) -> Page[RankingRow]:
    """Рейтинг бумаг за период по выбранной метрике.

    Если период не задан, берётся весь доступный период витрины. Ранг
    нумеруется с 1 в порядке сортировки и учитывает offset.
    """

    from_key, to_key = await _resolve_bounds(session, period)
    rows = await ranking_repo.list_returns_window(
        session,
        from_date_key=from_key,
        to_date_key=to_key,
    )
    leadership = await ranking_repo.count_leadership(
        session,
        from_date_key=from_key,
        to_date_key=to_key,
    )
    aggregates = build_aggregates(rows, leadership)
    total = len(aggregates)
    ranked = rank_aggregates(aggregates, metric, order, page.offset, page.limit)

    set_pagination_headers(response, total, page.limit, page.offset)
    items = [to_ranking_row(rank, aggregate) for rank, aggregate in ranked]
    return Page[RankingRow](items=items, total=total, limit=page.limit, offset=page.offset)


async def _resolve_bounds(session: AsyncSession, period: PeriodDates) -> tuple[int, int]:
    """Границы периода в date_key: из параметров либо весь доступный диапазон."""

    min_key, max_key = await ranking_repo.get_returns_bounds(session)
    if period.from_date is not None:
        from_key = date_to_date_key(period.from_date)
    else:
        from_key = min_key if min_key is not None else 0
    if period.to_date is not None:
        to_key = date_to_date_key(period.to_date)
    else:
        to_key = max_key if max_key is not None else 99991231
    return from_key, to_key
