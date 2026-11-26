"""Общие схемы: конверт списка и порядок сортировки."""

from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Order(str, Enum):
    """Направление сортировки."""

    asc = "asc"
    desc = "desc"


def parse_order(value: str) -> Order:
    """Разобрать строку порядка сортировки, ошибка для невалидного значения."""

    try:
        return Order(value)
    except ValueError as exc:
        raise ValueError(f"недопустимое значение order: {value!r}, ожидается asc или desc") from exc


class Page(BaseModel, Generic[T]):
    """Конверт списка: элементы плюс общее число записей и границы выборки."""

    items: list[T]
    total: int
    limit: int
    offset: int


class ErrorBody(BaseModel):
    """Тело ошибки в едином формате."""

    code: str
    message: str
    details: str | None = None


class ErrorResponse(BaseModel):
    """Конверт ошибки: {"error": {...}}."""

    error: ErrorBody
