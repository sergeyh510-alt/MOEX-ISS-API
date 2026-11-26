"""Read-only модели слоя core (измерения и факты).

Схема колонок и типов повторяет ``db/seed/01_seed.sql`` (авторитетный слепок).
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, Numeric, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DimSecurity(Base):
    """core.dim_security: справочник бумаг."""

    __tablename__ = "dim_security"
    __table_args__ = {"schema": "core"}

    security_key: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    secid: Mapped[str] = mapped_column(Text, nullable=False)
    boardid: Mapped[str] = mapped_column(Text, nullable=False)
    shortname: Mapped[str | None] = mapped_column(Text)
    first_tradedate: Mapped[date | None] = mapped_column(Date)
    last_tradedate: Mapped[date | None] = mapped_column(Date)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DimDate(Base):
    """core.dim_date: торговый календарь."""

    __tablename__ = "dim_date"
    __table_args__ = {"schema": "core"}

    date_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    calendar_date: Mapped[date] = mapped_column(Date, nullable=False)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    quarter: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    iso_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    day_name: Mapped[str] = mapped_column(Text, nullable=False)
    is_weekend: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_trading_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FactDailyPrice(Base):
    """core.fact_daily_prices: дневные цены OHLCV по бумагам."""

    __tablename__ = "fact_daily_prices"
    __table_args__ = {"schema": "core"}

    security_key: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    date_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    waprice: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    volume: Mapped[int | None] = mapped_column(BigInteger)
    numtrades: Mapped[int | None] = mapped_column(BigInteger)
    prev_close: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    close_change: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    close_change_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FactDailyIndex(Base):
    """core.fact_daily_index: дневные значения индексов."""

    __tablename__ = "fact_daily_index"
    __table_args__ = {"schema": "core"}

    index_code: Mapped[str] = mapped_column(Text, primary_key=True)
    date_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    prev_close: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    close_change: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    close_change_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

