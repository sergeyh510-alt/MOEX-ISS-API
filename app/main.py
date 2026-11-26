"""Точка входа FastAPI-приложения MOEX-ISS API.

Приложение только читает готовые слои мини-DWH Московской биржи (mart / core)
и отдаёт их клиентам в виде документированных JSON-ответов.
"""

import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app import db
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
        "description": (
            "Метаданные: версия API, свежесть данных, проверки качества. Meta / metadata."
        ),
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
        "description": (
            "Аналитические агрегаты и рейтинги (mart.stock_returns). Analytics and ranking."
        ),
    },
]

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Жизненный цикл приложения: поднять и закрыть пул соединений с БД."""

    await db.init_engine()
    try:
        yield
    finally:
        await db.dispose_engine()


app = FastAPI(
    title="MOEX-ISS API",
    version=__version__,
    description=DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
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


@app.get("/health", tags=["Health"], summary="Проверка живости и БД")
async def health() -> JSONResponse:
    """Проверка живости сервиса и доступности БД.

    Пингуем БД с коротким таймаутом. Если БД доступна: status "ok" и 200.
    Если недоступна: status "degraded" и HTTP 503. Свежесть данных берём
    из meta.load_run и max(date_key) по mart.stock_returns.
    """

    started = time.perf_counter()
    db_ok = await db.ping()
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    data: dict = {"last_load_at": None, "last_data_date": None}
    if db_ok:
        try:
            freshness = await db.load_freshness()
            data = {
                "last_load_at": freshness["last_load_at"],
                "last_data_date": freshness["last_data_date"],
            }
        except Exception:
            # БД ответила на ping, но свежесть получить не удалось.
            pass

    payload = {
        "status": "ok" if db_ok else "degraded",
        "version": __version__,
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "db": {
            "status": "ok" if db_ok else "unavailable",
            "latency_ms": latency_ms if db_ok else None,
        },
        "data": data,
    }
    return JSONResponse(status_code=200 if db_ok else 503, content=payload)
