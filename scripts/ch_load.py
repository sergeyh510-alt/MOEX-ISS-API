"""Загрузка витрин mart из PostgreSQL в ClickHouse (этап 8).

ClickHouse это необязательный второй источник для тяжёлой аналитики. Скрипт
копирует mart.stock_returns, mart.daily_movers и mart.index_compare из
PostgreSQL в ClickHouse (MergeTree) и идемпотентен: повторный запуск приводит
к тому же состоянию (таблицы пересоздаются и переливаются целиком).

Запуск:
    python -m scripts.ch_load
    python scripts/ch_load.py

Подключение к PostgreSQL берётся из существующих настроек (DWH_*), к ClickHouse
из новых (CLICKHOUSE_*).
"""

from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import asyncpg
import clickhouse_connect

if TYPE_CHECKING:
    from app.config import Settings


def _ensure_app_on_path() -> None:
    """Разрешить прямой запуск файла (python scripts/ch_load.py).

    При прямом запуске sys.path[0] это каталог scripts, поэтому корень проекта
    добавляем вручную, чтобы импортировался пакет app.
    """

    if __package__ in (None, ""):
        root = str(Path(__file__).resolve().parent.parent)
        if root not in sys.path:
            sys.path.insert(0, root)


def _get_settings() -> Settings:
    """Вернуть настройки, предварительно обеспечив импорт пакета app."""

    _ensure_app_on_path()
    from app.config import get_settings

    return get_settings()

TABLE_NAMES = ("stock_returns", "daily_movers", "index_compare")

# Явные списки колонок, чтобы порядок при чтении и вставке совпадал.
STOCK_RETURNS_COLUMNS = (
    "security_key",
    "date_key",
    "secid",
    "boardid",
    "close",
    "prev_close",
    "daily_return_pct",
    "gap_pct",
    "amplitude_pct",
    "ma_5",
    "ma_20",
    "volatility_5_pct",
    "volatility_20_pct",
    "cumulative_return_pct",
    "loaded_at",
    "updated_at",
)

DAILY_MOVERS_COLUMNS = (
    "date_key",
    "security_key",
    "secid",
    "daily_return_pct",
    "return_rank",
    "is_best_of_day",
    "is_worst_of_day",
    "loaded_at",
    "updated_at",
)

INDEX_COMPARE_COLUMNS = (
    "index_code",
    "security_key",
    "date_key",
    "secid",
    "stock_return_pct",
    "index_return_pct",
    "excess_return_pct",
    "loaded_at",
    "updated_at",
)

# DDL таблиц ClickHouse. MergeTree, порядок сортировки по ключам витрин.
STOCK_RETURNS_DDL = """
CREATE TABLE IF NOT EXISTS {db}.stock_returns (
    security_key Int64,
    date_key Int32,
    secid String,
    boardid String,
    close Float64,
    prev_close Nullable(Float64),
    daily_return_pct Nullable(Float64),
    gap_pct Nullable(Float64),
    amplitude_pct Nullable(Float64),
    ma_5 Nullable(Float64),
    ma_20 Nullable(Float64),
    volatility_5_pct Nullable(Float64),
    volatility_20_pct Nullable(Float64),
    cumulative_return_pct Nullable(Float64),
    loaded_at DateTime64(6, 'UTC'),
    updated_at DateTime64(6, 'UTC')
)
ENGINE = MergeTree
ORDER BY (security_key, date_key)
"""

DAILY_MOVERS_DDL = """
CREATE TABLE IF NOT EXISTS {db}.daily_movers (
    date_key Int32,
    security_key Int64,
    secid String,
    daily_return_pct Float64,
    return_rank Int32,
    is_best_of_day Bool,
    is_worst_of_day Bool,
    loaded_at DateTime64(6, 'UTC'),
    updated_at DateTime64(6, 'UTC')
)
ENGINE = MergeTree
ORDER BY (date_key, security_key)
"""

INDEX_COMPARE_DDL = """
CREATE TABLE IF NOT EXISTS {db}.index_compare (
    index_code String,
    security_key Int64,
    date_key Int32,
    secid String,
    stock_return_pct Nullable(Float64),
    index_return_pct Nullable(Float64),
    excess_return_pct Nullable(Float64),
    loaded_at DateTime64(6, 'UTC'),
    updated_at DateTime64(6, 'UTC')
)
ENGINE = MergeTree
ORDER BY (index_code, security_key, date_key)
"""

TABLES = {
    "stock_returns": (STOCK_RETURNS_COLUMNS, STOCK_RETURNS_DDL),
    "daily_movers": (DAILY_MOVERS_COLUMNS, DAILY_MOVERS_DDL),
    "index_compare": (INDEX_COMPARE_COLUMNS, INDEX_COMPARE_DDL),
}


def _convert(value: Any) -> Any:
    """Привести значение из asyncpg к типу, который поймёт clickhouse-connect."""

    if isinstance(value, Decimal):
        return float(value)
    return value


def _ch_client(settings: Settings, *, database: str | None) -> Any:
    """Создать клиент ClickHouse (с указанием или без указания базы)."""

    kwargs: dict[str, Any] = {
        "host": settings.CLICKHOUSE_HOST,
        "port": settings.CLICKHOUSE_PORT,
        "username": settings.CLICKHOUSE_USER,
        "password": settings.CLICKHOUSE_PASSWORD,
        "connect_timeout": settings.CLICKHOUSE_TIMEOUT_S,
        "send_receive_timeout": settings.CLICKHOUSE_TIMEOUT_S,
    }
    if database is not None:
        kwargs["database"] = database
    return clickhouse_connect.get_client(**kwargs)


async def _fetch_all_pg_rows(settings: Settings) -> dict[str, list[tuple]]:
    """Прочитать все таблицы mart из PostgreSQL за одно соединение.

    Возвращает отображение table -> список кортежей значений в порядке колонок
    из TABLES.
    """

    conn = await asyncpg.connect(
        host=settings.DWH_DB_HOST,
        port=settings.DWH_DB_PORT,
        user=settings.DWH_DB_USER,
        password=settings.DWH_DB_PASSWORD,
        database=settings.DWH_DB_NAME,
    )
    result: dict[str, list[tuple]] = {}
    try:
        for table, (columns, _ddl) in TABLES.items():
            column_sql = ", ".join(columns)
            records = await conn.fetch(f"SELECT {column_sql} FROM mart.{table}")
            result[table] = [tuple(_convert(value) for value in record) for record in records]
    finally:
        await conn.close()
    return result


def _ensure_database(settings: Settings) -> None:
    """Создать базу ClickHouse, если её ещё нет."""

    client = _ch_client(settings, database=None)
    try:
        client.command(f"CREATE DATABASE IF NOT EXISTS {settings.CLICKHOUSE_DATABASE}")
    finally:
        client.close()


def _load_tables(settings: Settings) -> dict[str, int]:
    """Создать таблицы и перелить данные, вернуть число строк по таблицам."""

    pg_rows = asyncio.run(_fetch_all_pg_rows(settings))
    client = _ch_client(settings, database=settings.CLICKHOUSE_DATABASE)
    counts: dict[str, int] = {}
    try:
        for table, (columns, ddl) in TABLES.items():
            client.command(ddl.format(db=settings.CLICKHOUSE_DATABASE))
            # Идемпотентность: полностью чистим таблицу перед заливкой.
            client.command(f"TRUNCATE TABLE {settings.CLICKHOUSE_DATABASE}.{table}")
            rows = pg_rows.get(table, [])
            if rows:
                client.insert(table, rows, column_names=list(columns))
            result = client.query(f"SELECT count() FROM {settings.CLICKHOUSE_DATABASE}.{table}")
            counts[table] = int(result.result_rows[0][0])
    finally:
        client.close()
    return counts


def main() -> None:
    """Создать базу и таблицы ClickHouse и залить витрины mart из PostgreSQL."""

    settings = _get_settings()
    _ensure_database(settings)
    counts = _load_tables(settings)
    print("Загрузка витрин mart в ClickHouse завершена:")
    for table in TABLE_NAMES:
        print(f"  {table}: {counts.get(table, 0)} строк")


if __name__ == "__main__":
    main()
