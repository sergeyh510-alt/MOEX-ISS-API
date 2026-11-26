"""Роутеры версии v1: сборка единого APIRouter под префиксом /api/v1."""

from fastapi import APIRouter

from app.api.v1 import (
    compare,
    dates,
    indices,
    meta,
    movers,
    prices,
    ranking,
    returns,
    securities,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(dates.router)
api_router.include_router(securities.router)
api_router.include_router(prices.router)
api_router.include_router(returns.router)
api_router.include_router(indices.router)
api_router.include_router(compare.router)
api_router.include_router(meta.router)
api_router.include_router(movers.router)
api_router.include_router(ranking.router)

__all__ = ["api_router"]
