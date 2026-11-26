"""Эндпоинты метаданных: версия, свежесть данных, проверки качества."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.repositories import meta as meta_repo
from app.schemas.meta import DqInfo, FreshnessInfo, VersionInfo
from app.services.meta import build_dq, build_freshness

router = APIRouter(prefix="/meta", tags=["Meta"])


@router.get("/version", response_model=VersionInfo, summary="Версия API и источник")
async def get_version() -> VersionInfo:
    """Версия API, имя сервиса, источник данных и список схем DWH."""

    settings = get_settings()
    return VersionInfo(
        api_version=settings.APP_VERSION,
        name="MOEX-ISS API",
        data_source="MOEX-ISS mini-DWH (Airflow + PostgreSQL)",
        schemas=["mart", "core", "meta", "audit"],
    )


@router.get("/freshness", response_model=FreshnessInfo, summary="Свежесть данных")
async def get_freshness(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FreshnessInfo:
    """Когда обновлялся каждый слой (meta.load_run) и последняя дата витрины."""

    last_load_at = await meta_repo.get_last_load_at(session)
    last_data_date_key = await meta_repo.get_last_data_date(session)
    layers = await meta_repo.list_layers(session)
    return build_freshness(
        last_load_at=last_load_at,
        last_data_date_key=last_data_date_key,
        layers=layers,
    )


@router.get("/dq", response_model=DqInfo, summary="Проверки качества данных")
async def get_dq(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DqInfo:
    """Статус проверок качества (audit.dq_run, audit.dq_check) за последний запуск."""

    run = await meta_repo.get_last_dq_run(session)
    checks = []
    status_counts: dict[str, int] = {}
    if run is not None:
        checks = await meta_repo.list_dq_checks(session, dq_run_id=run.dq_run_id)
        status_counts = await meta_repo.count_dq_statuses(session, dq_run_id=run.dq_run_id)
    return build_dq(run, checks, status_counts)
