"""Бизнес-логика метаданных: свежесть и проверки качества."""

from datetime import datetime, timezone

from app.models.audit import DqRun
from app.schemas.meta import (
    DqCheck,
    DqInfo,
    DqRunInfo,
    DqSummary,
    FreshnessInfo,
    FreshnessLayer,
)
from app.services.dates import date_key_to_date


def to_utc_iso(value: datetime | None) -> str | None:
    """Привести timestamp к UTC и вернуть ISO-8601 (или None)."""

    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def build_freshness(
    *,
    last_load_at: datetime | None,
    last_data_date_key: int | None,
    layers: list[tuple[str, datetime | None, int | None]],
) -> FreshnessInfo:
    """Собрать сводку свежести данных."""

    return FreshnessInfo(
        generated_at=datetime.now(timezone.utc).isoformat(),
        last_load_at=to_utc_iso(last_load_at),
        last_data_date=date_key_to_date(last_data_date_key),
        layers=[
            FreshnessLayer(
                target_table=target_table,
                last_success_at=to_utc_iso(finished_at),
                rows_loaded=rows_loaded,
            )
            for target_table, finished_at, rows_loaded in layers
        ],
    )


def build_dq(run: DqRun | None, checks: list, status_counts: dict[str, int]) -> DqInfo:
    """Собрать сводку проверок качества за последний запуск."""

    last_run = None
    if run is not None:
        last_run = DqRunInfo(
            dq_run_id=run.dq_run_id,
            status=run.status,
            date_from=run.date_from,
            date_to=run.date_to,
            checks_total=run.checks_total,
            checks_passed=run.checks_passed,
            checks_failed=run.checks_failed,
            started_at=to_utc_iso(run.started_at) or "",
            finished_at=to_utc_iso(run.finished_at),
        )

    summary = DqSummary(
        passed=status_counts.get("passed", 0),
        failed=status_counts.get("failed", 0),
        error=status_counts.get("error", 0),
    )
    return DqInfo(
        last_run=last_run,
        summary=summary,
        checks=[
            DqCheck(
                check_name=check.check_name,
                layer=check.layer,
                target_table=check.target_table,
                status=check.status,
                issues_count=check.issues_count,
            )
            for check in checks
        ],
    )
