"""Запросы к meta.load_run, audit.dq_run и audit.dq_check. Только SELECT."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import DqCheck, DqRun
from app.models.mart import StockReturn
from app.models.meta import LoadRun


async def get_last_load_at(session: AsyncSession) -> datetime | None:
    """Время последней успешной загрузки (max finished_at по status success)."""

    stmt = select(func.max(LoadRun.finished_at)).where(LoadRun.status == "success")
    return (await session.execute(stmt)).scalar_one()


async def get_last_data_date(session: AsyncSession) -> int | None:
    """Максимальный date_key витрины mart.stock_returns."""

    stmt = select(func.max(StockReturn.date_key))
    return (await session.execute(stmt)).scalar_one()


async def list_layers(session: AsyncSession) -> list[tuple[str, datetime | None, int | None]]:
    """Последняя успешная загрузка по каждому target_table.

    Возвращает список (target_table, последний finished_at, rows_loaded этой
    загрузки). Используем DISTINCT ON по PostgreSQL, чтобы взять именно строку
    последнего успешного запуска слоя.
    """

    stmt = (
        select(LoadRun.target_table, LoadRun.finished_at, LoadRun.rows_loaded)
        .where(LoadRun.status == "success")
        .order_by(LoadRun.target_table.asc(), LoadRun.finished_at.desc().nullslast())
        .distinct(LoadRun.target_table)
    )
    rows = (await session.execute(stmt)).all()
    return [(row[0], row[1], row[2]) for row in rows]


async def get_last_dq_run(session: AsyncSession) -> DqRun | None:
    """Последний запуск проверок качества (по времени старта, затем по id)."""

    stmt = select(DqRun).order_by(DqRun.started_at.desc(), DqRun.dq_run_id.desc()).limit(1)
    return (await session.execute(stmt)).scalars().first()


async def list_dq_checks(session: AsyncSession, *, dq_run_id: int) -> list[DqCheck]:
    """Проверки указанного запуска качества."""

    stmt = (
        select(DqCheck)
        .where(DqCheck.dq_run_id == dq_run_id)
        .order_by(DqCheck.dq_check_id.asc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def count_dq_statuses(session: AsyncSession, *, dq_run_id: int) -> dict[str, int]:
    """Число проверок по статусам для указанного запуска."""

    stmt = (
        select(DqCheck.status, func.count())
        .where(DqCheck.dq_run_id == dq_run_id)
        .group_by(DqCheck.status)
    )
    rows = (await session.execute(stmt)).all()
    return {status: int(count) for status, count in rows}
