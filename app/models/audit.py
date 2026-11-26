"""Read-only модели слоя audit (проверки качества данных).

Схема колонок и типов повторяет ``db/seed/01_seed.sql`` (авторитетный слепок).
"""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DqRun(Base):
    """audit.dq_run: запуск набора проверок качества данных."""

    __tablename__ = "dq_run"
    __table_args__ = {"schema": "audit"}

    dq_run_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    date_from: Mapped[date | None] = mapped_column(Date)
    date_to: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    checks_total: Mapped[int] = mapped_column(Integer, nullable=False)
    checks_passed: Mapped[int] = mapped_column(Integer, nullable=False)
    checks_failed: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DqCheck(Base):
    """audit.dq_check: отдельная проверка качества данных."""

    __tablename__ = "dq_check"
    __table_args__ = {"schema": "audit"}

    dq_check_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dq_run_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    check_name: Mapped[str] = mapped_column(Text, nullable=False)
    layer: Mapped[str] = mapped_column(Text, nullable=False)
    target_table: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    issues_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    max_allowed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
