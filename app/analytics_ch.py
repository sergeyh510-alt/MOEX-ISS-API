"""Обёртка над clickhouse-connect для необязательного источника аналитики.

ClickHouse включается флагом ``USE_CLICKHOUSE`` и используется только для
тяжёлых агрегатов (/summary и /ranking). PostgreSQL остаётся основным
источником и источником истины.

Клиент создаётся лениво. Модуль импортируется даже без установленного
clickhouse-connect: импорт драйвера делается внутри функций, поэтому юнит-тесты
и сам сервис поднимаются без этого пакета.
"""

from __future__ import annotations

from typing import Any

from app.config import get_settings

_client: Any | None = None


def get_client() -> Any:
    """Вернуть единственный клиент ClickHouse (создаётся при первом вызове)."""

    global _client
    if _client is None:
        import clickhouse_connect

        settings = get_settings()
        _client = clickhouse_connect.get_client(
            host=settings.CLICKHOUSE_HOST,
            port=settings.CLICKHOUSE_PORT,
            username=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD,
            database=settings.CLICKHOUSE_DATABASE,
            connect_timeout=settings.CLICKHOUSE_TIMEOUT_S,
            send_receive_timeout=settings.CLICKHOUSE_TIMEOUT_S,
        )
    return _client


def dispose_client() -> None:
    """Закрыть клиент и сбросить его (например при остановке приложения)."""

    global _client
    if _client is not None:
        try:
            _client.close()
        finally:
            _client = None


def available() -> bool:
    """Короткая проверка соединения с ClickHouse.

    Возвращает True/False и никогда не поднимает исключение: это именно
    проверка доступности. Реальные запросы идут через query_rows и там ошибки
    пробрасываются наверх.
    """

    try:
        return bool(get_client().ping())
    except Exception:
        return False


def query_rows(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Выполнить запрос и вернуть строки как список словарей.

    Параметры передаются серверным связыванием clickhouse-connect в формате
    ``{name:Type}``. Ошибки соединения не глотаем: пробрасываем наверх, чтобы
    вызывающий код сам решил, что делать (например отдать 503).
    """

    result = get_client().query(sql, parameters=params or {})
    columns = list(result.column_names)
    return [dict(zip(columns, row, strict=False)) for row in result.result_rows]
