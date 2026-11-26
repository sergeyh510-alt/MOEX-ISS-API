"""Схемы метаданных: версия, свежесть, проверки качества."""

from datetime import date

from pydantic import BaseModel


class VersionInfo(BaseModel):
    """Версия API и описание источника данных."""

    api_version: str
    name: str
    data_source: str
    schemas: list[str]


class FreshnessLayer(BaseModel):
    """Последняя успешная загрузка по одному целевому слою."""

    target_table: str
    last_success_at: str | None
    rows_loaded: int | None


class FreshnessInfo(BaseModel):
    """Сводка свежести данных."""

    generated_at: str
    last_load_at: str | None
    last_data_date: date | None
    layers: list[FreshnessLayer]


class DqRunInfo(BaseModel):
    """Последний запуск проверок качества данных."""

    dq_run_id: int
    status: str
    date_from: date | None
    date_to: date | None
    checks_total: int
    checks_passed: int
    checks_failed: int
    started_at: str
    finished_at: str | None


class DqSummary(BaseModel):
    """Сводка по статусам проверок последнего запуска."""

    passed: int
    failed: int
    error: int


class DqCheck(BaseModel):
    """Отдельная проверка качества данных."""

    check_name: str
    layer: str
    target_table: str
    status: str
    issues_count: int


class DqInfo(BaseModel):
    """Последний запуск проверок и его детализация."""

    last_run: DqRunInfo | None
    summary: DqSummary
    checks: list[DqCheck]

