"""Точка входа FastAPI-приложения MOEX-ISS API.

Приложение только читает готовые слои мини-DWH Московской биржи (mart / core)
и отдаёт их клиентам в виде документированных JSON-ответов.
"""

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings

settings = get_settings()

DESCRIPTION = """
**MOEX-ISS API** это HTTP-слой поверх мини-DWH Московской биржи.

API ничего не считает сам: он читает готовые слои `mart` и `core` (проект
мини-DWH Мосбиржи) и отдаёт их по HTTP в виде документированных JSON-ответов
со Swagger / OpenAPI.

Источник данных: https://github.com/sergeyh510-alt/MOEX-ISS-mini-DWH
"""

OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "Проверка живости сервиса. Health / service liveness.",
    },
    {
        "name": "Meta",
        "description": "Метаданные: версия API, свежесть данных, проверки качества. Meta / metadata.",
    },
    {
        "name": "Calendar",
        "description": "Торговый календарь (core.dim_date). Trading calendar.",
    },
    {
        "name": "Securities",
        "description": "Справочник бумаг (core.dim_security). Securities reference.",
    },
    {
        "name": "Prices",
        "description": "Цены OHLCV по бумагам (core.fact_daily_prices). Daily prices.",
    },
    {
        "name": "Returns",
        "description": "Метрики доходности и волатильность (mart.stock_returns). Returns metrics.",
    },
    {
        "name": "Indices",
        "description": "Индексы и их история (core.fact_daily_index). Indices and history.",
    },
    {
        "name": "Compare",
        "description": "Сравнение бумаги с индексом (mart.index_compare). Stock vs index.",
    },
    {
        "name": "Movers",
        "description": "Лидеры роста и падения (mart.daily_movers). Daily movers.",
    },
    {
        "name": "Analytics",
        "description": "Аналитические агрегаты и рейтинги (mart.stock_returns). Analytics and ranking.",
    },
]

app = FastAPI(
    title="MOEX-ISS API",
    version=__version__,
    description=DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
)

# CORS: только для dev (портфолио). В продакшене так делать нельзя:
# список источников должен быть явным.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"], summary="Корневая информация")
async def root() -> dict:
    """Краткая информация о сервисе: имя, версия, ссылки на документацию."""

    return {
        "name": "MOEX-ISS API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Health"], summary="Проверка живости")
async def health() -> dict:
    """Проверка живости сервиса.

    Пока проверяется только сам процесс API. Пинг БД и свежесть данных из
    meta.freshness добавим на этапе 1.
    """

    return {
        "status": "ok",
        "version": __version__,
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }
