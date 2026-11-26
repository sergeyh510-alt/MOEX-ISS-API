"""Схемы справочника бумаг (core.dim_security) и карточки с покрытием."""

from datetime import date

from pydantic import BaseModel


class Security(BaseModel):
    """Элемент списка бумаг."""

    security_key: int
    secid: str
    boardid: str
    shortname: str | None
    first_tradedate: date | None
    last_tradedate: date | None


class SecurityCoverage(BaseModel):
    """Покрытие бумаги в витрине mart.stock_returns."""

    data_from: date | None
    data_to: date | None
    price_rows: int


class SecurityDetail(BaseModel):
    """Карточка бумаги плюс покрытие в витрине."""

    security_key: int
    secid: str
    boardid: str
    shortname: str | None
    first_tradedate: date | None
    last_tradedate: date | None
    coverage: SecurityCoverage

