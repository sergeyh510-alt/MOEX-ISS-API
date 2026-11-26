"""Зависимости FastAPI: пагинация, период дат и заголовки пагинации."""

from dataclasses import dataclass
from datetime import date

from fastapi import Query
from fastapi.responses import Response

from app.schemas.common import Order, parse_order

DEFAULT_LIMIT = 100
MIN_LIMIT = 1
MAX_LIMIT = 1000


@dataclass
class Pagination:
    """Параметры пагинации с клампами."""

    limit: int
    offset: int


@dataclass
class PeriodDates:
    """Период дат (from_date/to_date с алиасами from/to)."""

    from_date: date | None
    to_date: date | None


def get_pagination(
    limit: int = Query(DEFAULT_LIMIT, description="Размер страницы, клампится в 1..1000"),
    offset: int = Query(0, description="Смещение, клампится в >= 0"),
) -> Pagination:
    """Зависимость пагинации: limit клампится в 1..1000 (по умолчанию 100), offset >= 0."""

    return Pagination(limit=clamp_limit(limit), offset=clamp_offset(offset))


def clamp_limit(limit: int) -> int:
    """Ограничить размер страницы диапазоном 1..1000."""

    return max(MIN_LIMIT, min(MAX_LIMIT, limit))


def clamp_offset(offset: int) -> int:
    """Ограничить смещение снизу нулём."""

    return max(0, offset)


def get_period(
    from_date: date | None = Query(
        None,
        alias="from",
        description="Начало периода, YYYY-MM-DD (алиас from_date)",
    ),
    to_date: date | None = Query(
        None,
        alias="to",
        description="Конец периода, YYYY-MM-DD (алиас to_date)",
    ),
) -> PeriodDates:
    """Зависимость периода дат: from/to, алиасы from_date/to_date."""

    return PeriodDates(from_date=from_date, to_date=to_date)


def resolve_order(order: str) -> Order:
    """Разобрать строку порядка сортировки в enum Order."""

    return parse_order(order)


def set_pagination_headers(response: Response, total: int, limit: int, offset: int) -> None:
    """Проставить заголовки пагинации в ответ."""

    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
