"""Чистые хелперы индексов и сравнения: нормализация кода и валидация периода.

Функции не зависят от БД, чтобы их можно было покрыть юнит-тестами.
"""

from datetime import date


def normalize_index_code(code: str) -> str:
    """Нормализовать код индекса для поиска: убрать пробелы и привести к верхнему.

    В БД коды индексов хранятся в верхнем регистре (например IMOEX), поэтому
    сравнение без учёта регистра делаем через верхний регистр.
    """

    return code.strip().upper()


def validate_period_range(from_date: date | None, to_date: date | None) -> None:
    """Проверить период: начало не должно быть позже конца.

    Ошибка ValueError, если from_date > to_date. Пустые границы допустимы.
    """

    if from_date is not None and to_date is not None and from_date > to_date:
        raise ValueError(
            f"начало периода {from_date.isoformat()} позже конца {to_date.isoformat()}"
        )
