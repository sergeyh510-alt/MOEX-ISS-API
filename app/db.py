"""Асинхронный слой доступа к данным (PostgreSQL, мини-DWH Мосбиржи).

Слой работает только на чтение. Репозитории выполняют исключительно SELECT:
мы не вызываем commit()/rollback() для записи и не меняем данные DWH.
Вся схема принадлежит проекту мини-DWH, тут лишь доступ по SELECT.
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

# Короткий таймаут для проверки живости, чтобы /health не подвисал.
PING_TIMEOUT_SECONDS = 2.0

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Вернуть единственный async engine (создаётся лениво при первом вызове)."""

    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Вернуть фабрику сессий (создаётся лениво вместе с engine)."""

    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
        )
    return _sessionmaker


async def init_engine() -> None:
    """Инициализировать engine на старте приложения (lifespan startup)."""

    get_engine()


async def dispose_engine() -> None:
    """Закрыть пул соединений на остановке приложения (lifespan shutdown)."""

    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-зависимость: выдать сессию и закрыть её после запроса."""

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session


async def ping() -> bool:
    """Проверить доступность БД запросом SELECT 1 с коротким таймаутом.

    Любая ошибка (нет соединения, таймаут) даёт False, исключения наружу не
    пробрасываются.
    """

    async def _run() -> bool:
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True

    try:
        return await asyncio.wait_for(_run(), timeout=PING_TIMEOUT_SECONDS)
    except Exception:
        return False


def _date_key_to_iso(date_key: int | None) -> str | None:
    """Преобразовать date_key (int YYYYMMDD) в строку YYYY-MM-DD."""

    if date_key is None:
        return None
    digits = f"{date_key:08d}"
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"


async def load_freshness() -> dict:
    """Собрать сведения о свежести данных (только SELECT).

    Возвращает словарь:
    * ``last_load_at`` значение max(finished_at) по успешным загрузкам meta.load_run;
    * ``last_data_date`` максимальный date_key из mart.stock_returns (YYYY-MM-DD);
    * ``layers`` последний успешный запуск по каждому target_table.
    """

    last_load_at: datetime | None = None
    last_data_date: str | None = None
    layers: dict[str, str] = {}

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        result = await session.execute(
            text(
                "SELECT max(finished_at) AS last_load_at "
                "FROM meta.load_run WHERE status = 'success'"
            )
        )
        row = result.first()
        if row is not None:
            last_load_at = row.last_load_at

        result = await session.execute(
            text(
                "SELECT target_table, max(finished_at) AS last_finished_at "
                "FROM meta.load_run WHERE status = 'success' "
                "GROUP BY target_table"
            )
        )
        for layer_row in result.all():
            finished_at = layer_row.last_finished_at
            if finished_at is not None:
                layers[layer_row.target_table] = _to_utc_iso(finished_at)

        result = await session.execute(
            text("SELECT max(date_key) AS last_date_key FROM mart.stock_returns")
        )
        row = result.first()
        if row is not None:
            last_data_date = _date_key_to_iso(row.last_date_key)

    return {
        "last_load_at": _to_utc_iso(last_load_at) if last_load_at is not None else None,
        "last_data_date": last_data_date,
        "layers": layers,
    }


def _to_utc_iso(value: datetime) -> str:
    """Привести timestamp к UTC и вернуть в ISO-8601."""

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()
