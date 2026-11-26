"""Read-only модели витрин слоя mart.

Схема колонок и типов повторяет ``db/seed/01_seed.sql`` (авторитетный слепок).
bigint отражён как BigInteger, integer как Integer, numeric как Numeric.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StockReturn(Base):
    """mart.stock_returns: доходность бумаг и производные метрики."""

    __tablename__ = "stock_returns"
    __table_args__ = {"schema": "mart"}

    security_key: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    date_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    secid: Mapped[str] = mapped_column(Text, nullable=False)
    boardid: Mapped[str] = mapped_column(Text, nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    prev_close: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    daily_return_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    gap_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    amplitude_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    ma_5: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    ma_20: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    volatility_5_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    volatility_20_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    cumulative_return_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IndexCompare(Base):
    """mart.index_compare: сравнение доходности бумаги и индекса."""

    __tablename__ = "index_compare"
    __table_args__ = {"schema": "mart"}

    index_code: Mapped[str] = mapped_column(Text, primary_key=True)
    security_key: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    date_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    secid: Mapped[str] = mapped_column(Text, nullable=False)
    stock_return_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    index_return_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    excess_return_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DailyMover(Base):
    """mart.daily_movers: лидеры роста и падения за день."""

    __tablename__ = "daily_movers"
    __table_args__ = {"schema": "mart"}

    date_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    security_key: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    secid: Mapped[str] = mapped_column(Text, nullable=False)
    daily_return_pct: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    return_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    is_best_of_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_worst_of_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

