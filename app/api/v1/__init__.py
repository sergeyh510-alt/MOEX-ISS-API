"""Роутеры версии v1: сборка единого APIRouter под префиксом /api/v1.

Здесь же подключаются сквозные механизмы уровня API: обязательная проверка
X-API-Key (если ключ включён в настройках) и общие ответы об ошибках для
OpenAPI-документации.
"""

from fastapi import APIRouter, Depends

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
from app.schemas.common import ErrorResponse
from app.security import require_api_key

# Общие ответы об ошибках: показываем их в Swagger у каждого эндпоинта.
COMMON_ERROR_RESPONSES: dict[int | str, dict] = {
    401: {
        "model": ErrorResponse,
        "description": "Требуется корректный X-API-Key (если ключ включён в настройках).",
    },
    404: {"model": ErrorResponse, "description": "Объект не найден."},
    422: {"model": ErrorResponse, "description": "Некорректные параметры запроса."},
    429: {"model": ErrorResponse, "description": "Превышен лимит частоты запросов."},
}

api_router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_api_key)],
    responses=COMMON_ERROR_RESPONSES,
)
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
