"""Юнит-тесты пагинации и разбора order (этап 2)."""

import pytest

from app.api.deps import (
    MAX_LIMIT,
    MIN_LIMIT,
    clamp_limit,
    clamp_offset,
    get_pagination,
    resolve_order,
)
from app.schemas.common import Order, parse_order


def test_pagination_defaults() -> None:
    """По умолчанию limit 100 и offset 0."""

    page = get_pagination(limit=100, offset=0)
    assert page.limit == 100
    assert page.offset == 0


def test_pagination_accepts_values() -> None:
    """Валидные значения проходят без изменений."""

    page = get_pagination(limit=1000, offset=50)
    assert page.limit == MAX_LIMIT
    assert page.offset == 50


def test_clamp_limit_upper() -> None:
    """limit больше максимума клампится в 1000."""

    assert clamp_limit(5000) == MAX_LIMIT
    assert get_pagination(limit=99999, offset=0).limit == MAX_LIMIT


def test_clamp_limit_lower() -> None:
    """limit меньше минимума клампится в 1."""

    assert clamp_limit(0) == MIN_LIMIT
    assert clamp_limit(-10) == MIN_LIMIT
    assert get_pagination(limit=0, offset=0).limit == MIN_LIMIT


def test_clamp_offset() -> None:
    """offset меньше нуля клампится в 0."""

    assert clamp_offset(-5) == 0
    assert clamp_offset(10) == 10
    assert get_pagination(limit=10, offset=-1).offset == 0


def test_parse_order_ok() -> None:
    """Разбор допустимых значений order."""

    assert parse_order("asc") == Order.asc
    assert parse_order("desc") == Order.desc
    assert resolve_order("asc") == Order.asc


def test_parse_order_invalid() -> None:
    """Невалидный order даёт ошибку."""

    with pytest.raises(ValueError):
        parse_order("up")
    with pytest.raises(ValueError):
        resolve_order("random")
