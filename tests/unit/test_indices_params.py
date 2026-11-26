"""Юнит-тесты параметров индексов и сравнения (этап 4)."""

from datetime import date

import pytest

from app.services.indices import normalize_index_code, validate_period_range


def test_normalize_index_code() -> None:
    """Код индекса приводится к верхнему регистру без пробелов."""

    assert normalize_index_code("imoex") == "IMOEX"
    assert normalize_index_code(" IMoex ") == "IMOEX"
    assert normalize_index_code("IMOEX") == "IMOEX"


def test_validate_period_range_ok() -> None:
    """Корректный период не поднимает ошибку."""

    validate_period_range(date(2024, 1, 1), date(2024, 1, 31))
    validate_period_range(date(2024, 1, 1), date(2024, 1, 1))
    validate_period_range(None, date(2024, 1, 31))
    validate_period_range(date(2024, 1, 1), None)
    validate_period_range(None, None)


def test_validate_period_range_invalid() -> None:
    """from > to даёт ошибку."""

    with pytest.raises(ValueError):
        validate_period_range(date(2024, 2, 1), date(2024, 1, 1))
