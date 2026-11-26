"""Бизнес-логика справочника бумаг: сборка карточки с покрытием."""

from app.models.core import DimSecurity
from app.schemas.securities import Security, SecurityCoverage, SecurityDetail
from app.services.dates import date_key_to_date


def to_security(row: DimSecurity) -> Security:
    """Преобразовать строку dim_security в схему списка."""

    return Security(
        security_key=row.security_key,
        secid=row.secid,
        boardid=row.boardid,
        shortname=row.shortname,
        first_tradedate=row.first_tradedate,
        last_tradedate=row.last_tradedate,
    )


def to_security_detail(
    row: DimSecurity,
    min_date_key: int | None,
    max_date_key: int | None,
    price_rows: int,
) -> SecurityDetail:
    """Собрать карточку бумаги с покрытием витрины mart.stock_returns."""

    coverage = SecurityCoverage(
        data_from=date_key_to_date(min_date_key),
        data_to=date_key_to_date(max_date_key),
        price_rows=price_rows,
    )
    return SecurityDetail(
        security_key=row.security_key,
        secid=row.secid,
        boardid=row.boardid,
        shortname=row.shortname,
        first_tradedate=row.first_tradedate,
        last_tradedate=row.last_tradedate,
        coverage=coverage,
    )

