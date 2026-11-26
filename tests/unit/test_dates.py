"""Юнит-тесты конвертации date_key <-> date (этап 2)."""

from datetime import date

import pytest

from app.services.dates import (
    date_key_to_date,
    date_to_date_key,
    parse_iso_date,
)


def test_date_key_to_date_ok() -> None:
    """Корректный date_key превращается в дату."""

    assert date_key_to_date(20241124) == date(2024, 11, 24)
    assert date_key_to_date(20260101) == date(2026, 1, 1)


def test_date_key_to_date_none() -> None:
    """Пустое значение даёт None."""

    assert date_key_to_date(None) is None


def test_date_key_to_date_invalid_day() -> None:
    """Февраль 30 не существует: должна быть ошибка."""

    with pytest.raises(ValueError):
        date_key_to_date(20260230)


def test_date_key_to_date_out_of_range() -> None:
    """date_key вне диапазона даёт ошибку."""

    with pytest.raises(ValueError):
        date_key_to_date(18991231)
    with pytest.raises(ValueError):
        date_key_to_date(0)


def test_date_key_to_date_wrong_type() -> None:
    """Не целое число даёт ошибку."""

    with pytest.raises(ValueError):
        date_key_to_date("20241124")  # type: ignore[arg-type]


def test_date_to_date_key_ok() -> None:
    """Дата превращается в int YYYYMMDD и обратно."""

    assert date_to_date_key(date(2026, 11, 24)) == 20261124
    assert date_to_date_key(None) is None
    assert date_key_to_date(date_to_date_key(date(2024, 1, 9))) == date(2024, 1, 9)


def test_parse_iso_date() -> None:
    """Разбор YYYY-MM-DD и ошибка для неверного формата."""

    assert parse_iso_date("2026-10-10") == date(2026, 10, 10)
    assert parse_iso_date(None) is None
    with pytest.raises(ValueError):
        parse_iso_date("10.10.2026")

