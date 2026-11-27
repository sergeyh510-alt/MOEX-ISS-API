"""SQL для ClickHouse: те же строки витрин, что и у PostgreSQL-репозиториев.

Здесь намеренно нет агрегатов уровня SQL. Мы отдаём сырые строки витрин, а
математику (доходность за период, среднее, волатильность, просадка, агрегаты
рейтинга) считают те же функции из app.services.returns и app.services.ranking,
что и для PostgreSQL. Поэтому результаты двух источников совпадают по
построению, а не по совпадению.

Таблицы лежат в базе из CLICKHOUSE_DATABASE и имеют имена stock_returns,
daily_movers, index_compare. Строки возвращаются лёгкими объектами с доступом
по атрибутам, как у ORM-строк PostgreSQL.
"""

from types import SimpleNamespace
from typing import Any

from app import analytics_ch

# Колонки, которые нужны сборке сводки и рейтинга (совпадают с PostgreSQL).
_RETURN_COLUMNS = (
    "security_key",
    "date_key",
    "secid",
    "boardid",
    "close",
    "daily_return_pct",
    "cumulative_return_pct",
)

_SELECT_RETURNS = ", ".join(_RETURN_COLUMNS)


def _to_rows(records: list[dict[str, Any]]) -> list[SimpleNamespace]:
    """Обернуть словари строк в объекты с доступом по атрибутам."""

    return [SimpleNamespace(**record) for record in records]


def fetch_stock_return_series(
    *,
    security_key: int,
    from_date_key: int,
    to_date_key: int,
) -> list[SimpleNamespace]:
    """Ряд витрины одной бумаги за период, по возрастанию date_key.

    Аналог PostgreSQL-репозитория list_returns_in_period.
    """

    sql = (
        f"SELECT {_SELECT_RETURNS} FROM stock_returns "
        "WHERE security_key = {security_key:Int64} "
        "AND date_key >= {from_date_key:Int32} "
        "AND date_key <= {to_date_key:Int32} "
        "ORDER BY date_key ASC"
    )
    params = {
        "security_key": security_key,
        "from_date_key": from_date_key,
        "to_date_key": to_date_key,
    }
    return _to_rows(analytics_ch.query_rows(sql, params))


def fetch_returns_window(
    *,
    from_date_key: int,
    to_date_key: int,
) -> list[SimpleNamespace]:
    """Ряд всей витрины за окно, по возрастанию (security_key, date_key).

    Аналог PostgreSQL-репозитория list_returns_window.
    """

    sql = (
        f"SELECT {_SELECT_RETURNS} FROM stock_returns "
        "WHERE date_key >= {from_date_key:Int32} "
        "AND date_key <= {to_date_key:Int32} "
        "ORDER BY security_key ASC, date_key ASC"
    )
    params = {"from_date_key": from_date_key, "to_date_key": to_date_key}
    return _to_rows(analytics_ch.query_rows(sql, params))


def fetch_leadership_counts(
    *,
    from_date_key: int,
    to_date_key: int,
) -> dict[int, tuple[int, int]]:
    """Число дней-лидеров и дней-аутсайдеров по каждой бумаге за окно.

    Аналог PostgreSQL-репозитория count_leadership. Возвращает отображение
    security_key -> (times_best_of_day, times_worst_of_day).
    """

    sql = (
        "SELECT security_key, "
        "countIf(is_best_of_day) AS times_best_of_day, "
        "countIf(is_worst_of_day) AS times_worst_of_day "
        "FROM daily_movers "
        "WHERE date_key >= {from_date_key:Int32} "
        "AND date_key <= {to_date_key:Int32} "
        "GROUP BY security_key"
    )
    params = {"from_date_key": from_date_key, "to_date_key": to_date_key}
    rows = analytics_ch.query_rows(sql, params)
    return {
        int(row["security_key"]): (
            int(row["times_best_of_day"] or 0),
            int(row["times_worst_of_day"] or 0),
        )
        for row in rows
    }


def fetch_returns_bounds() -> tuple[int | None, int | None]:
    """Границы доступного периода витрины: (min date_key, max date_key).

    Аналог PostgreSQL-репозитория get_returns_bounds.
    """

    sql = "SELECT min(date_key) AS min_key, max(date_key) AS max_key FROM stock_returns"
    rows = analytics_ch.query_rows(sql)
    if not rows:
        return None, None
    return rows[0]["min_key"], rows[0]["max_key"]
