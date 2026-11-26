"""Схемы лидеров роста и падения (mart.daily_movers)."""

from datetime import date as date_type
from typing import Literal

from pydantic import BaseModel, Field


class MoverRow(BaseModel):
    """Одна строка лидеров дня."""

    date: date_type
    date_key: int
    security_key: int
    secid: str
    daily_return_pct: float
    return_rank: int
    is_best_of_day: bool
    is_worst_of_day: bool


class MoversDay(BaseModel):
    """Ответ режима дня: лучшие и худшие бумаги одного торгового дня.

    Тип даты импортирован как date_type: поле с именем date и типом date | None
    с дефолтом ломается из-за отложенных аннотаций Python 3.14, когда значение
    по умолчанию затеняет одноимённый тип. Квалифицированный тип это обходит.
    """

    mode: Literal["day"] = "day"
    date: date_type | None = None
    best: list[MoverRow] = []
    worst: list[MoverRow] = []


class MoversPeriod(BaseModel):
    """Ответ режима периода: лучшие и худшие дни внутри окна.

    Поле from выводится алиасом "from" (зарезервированное слово Python), а
    populate_by_name позволяет принять значение и по имени from_.
    """

    model_config = {"populate_by_name": True}

    mode: Literal["period"] = "period"
    from_: date_type | None = Field(default=None, alias="from")
    to: date_type | None = None
    best: list[MoverRow] = []
    worst: list[MoverRow] = []
