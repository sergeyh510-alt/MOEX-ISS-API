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
from app.schemas.common import Order, Page
from app.schemas.ranking import RankingRow
from app.services import analytics
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

    rows, leadership = await analytics.load_ranking_data(
        session,
        from_date=period.from_date,
        to_date=period.to_date,
    )
    aggregates = build_aggregates(rows, leadership)
    total = len(aggregates)
    ranked = rank_aggregates(aggregates, metric, order, page.offset, page.limit)

    set_pagination_headers(response, total, page.limit, page.offset)
    items = [to_ranking_row(rank, aggregate) for rank, aggregate in ranked]
    return Page[RankingRow](items=items, total=total, limit=page.limit, offset=page.offset)
