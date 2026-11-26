"""Read-only модели слоя meta (свежесть и источники).

Схема колонок и типов повторяет ``db/seed/01_seed.sql``. Вида meta.freshness
в слепке нет (это view в DWH), поэтому свежесть считаем из meta.load_run.
"""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LoadRun(Base):
    """meta.load_run: журнал запусков загрузки."""

    __tablename__ = "load_run"
    __table_args__ = {"schema": "meta"}

    load_run_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    dag_id: Mapped[str | None] = mapped_column(Text)
    task_id: Mapped[str | None] = mapped_column(Text)
    run_id: Mapped[str | None] = mapped_column(Text)
    target_table: Mapped[str] = mapped_column(Text, nullable=False)
    date_from: Mapped[date | None] = mapped_column(Date)
    date_to: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    rows_loaded: Mapped[int] = mapped_column(BigInteger, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    rows_rejected: Mapped[int] = mapped_column(BigInteger, nullable=False)


class Source(Base):
    """meta.source: справочник источников."""

    __tablename__ = "source"
    __table_args__ = {"schema": "meta"}

    source_code: Mapped[str] = mapped_column(Text, primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

