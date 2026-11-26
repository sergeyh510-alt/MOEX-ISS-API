"""Запросы к core.dim_security и mart.stock_returns. Только SELECT."""

from datetime import date
from enum import Enum

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import DimSecurity
from app.models.mart import StockReturn
from app.schemas.common import Order

# Допустимые для сортировки колонки dim_security.
SORT_COLUMNS = {
    "secid": DimSecurity.secid,
    "shortname": DimSecurity.shortname,
    "first_tradedate": DimSecurity.first_tradedate,
    "last_tradedate": DimSecurity.last_tradedate,
}

# Enum для Swagger: допустимые поля сортировки (валидируется FastAPI).
# Имя уникально, чтобы не конфликтовать со схемой сортировки других роутеров.
SecuritySortField = Enum("SecuritySortField", {name: name for name in SORT_COLUMNS}, type=str)

DEFAULT_SORT = "secid"


def _order_by(sort: str, order: Order):
    """Построить выражение ORDER BY с вторичным ключом boardid."""

    column = SORT_COLUMNS[sort]
    expression = column.asc() if order == Order.asc else column.desc()
    return [expression, DimSecurity.boardid.asc()]


async def list_securities(
    session: AsyncSession,
    *,
    q: str | None,
    boardid: str | None,
    sort: str,
    order: Order,
    limit: int,
    offset: int,
) -> tuple[list[DimSecurity], int]:
    """Вернуть страницу справочника бумаг и общее число строк по фильтру."""

    conditions = []
    if q:
        pattern = f"%{q}%"
        conditions.append(
            or_(
                DimSecurity.secid.ilike(pattern),
                DimSecurity.shortname.ilike(pattern),
            )
        )
    if boardid:
        conditions.append(DimSecurity.boardid == boardid)

    total_stmt = select(func.count()).select_from(DimSecurity)
    rows_stmt = select(DimSecurity)
    if conditions:
        total_stmt = total_stmt.where(*conditions)
        rows_stmt = rows_stmt.where(*conditions)

    total = (await session.execute(total_stmt)).scalar_one()
    rows_stmt = rows_stmt.order_by(*_order_by(sort, order)).limit(limit).offset(offset)
    rows = list((await session.execute(rows_stmt)).scalars().all())
    return rows, int(total)


async def get_security(
    session: AsyncSession,
    *,
    secid: str,
    boardid: str | None,
) -> DimSecurity | None:
    """Найти карточку бумаги: по boardid либо с самым поздним last_tradedate."""

    stmt = select(DimSecurity).where(DimSecurity.secid == secid)
    if boardid:
        stmt = stmt.where(DimSecurity.boardid == boardid)
    stmt = stmt.order_by(
        DimSecurity.last_tradedate.desc().nullslast(),
        DimSecurity.boardid.asc(),
    ).limit(1)
    return (await session.execute(stmt)).scalars().first()


async def get_coverage(
    session: AsyncSession,
    *,
    security_key: int,
) -> tuple[date | None, date | None, int]:
    """Покрытие бумаги в mart.stock_returns: (min date_key, max date_key, число строк)."""

    stmt = select(
        func.min(StockReturn.date_key),
        func.max(StockReturn.date_key),
        func.count(),
    ).where(StockReturn.security_key == security_key)
    row = (await session.execute(stmt)).one()
    return row[0], row[1], int(row[2])
