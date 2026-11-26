"""Юнит-тесты конфигурации (этап 1)."""

import pytest

from app.config import Settings, get_settings

FIELD_NAMES = [
    "APP_VERSION",
    "APP_HOST",
    "APP_PORT",
    "LOG_LEVEL",
    "DWH_DB_HOST",
    "DWH_DB_PORT",
    "DWH_DB_NAME",
    "DWH_DB_USER",
    "DWH_DB_PASSWORD",
    "API_KEY",
    "USE_CLICKHOUSE",
    "REDIS_URL",
]


@pytest.fixture
def clean_defaults(monkeypatch) -> Settings:
    """Настройки со значениями по умолчанию, без влияния env и .env.

    На машине и в контейнере уже может быть заполнен .env (или переменные
    окружения от docker compose), поэтому для проверки именно дефолтов
    очищаем переменные и отключаем чтение файла .env.
    """

    for name in FIELD_NAMES:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)
    return Settings(_env_file=None)


def test_defaults(clean_defaults: Settings) -> None:
    """Значения по умолчанию соответствуют dev-среде."""

    settings = clean_defaults
    assert settings.APP_VERSION == "0.1.0"
    assert settings.APP_HOST == "0.0.0.0"
    assert settings.APP_PORT == 8000
    assert settings.LOG_LEVEL == "INFO"
    assert settings.DWH_DB_HOST == "localhost"
    assert settings.DWH_DB_PORT == 5433
    assert settings.DWH_DB_NAME == "moex_dwh"
    assert settings.DWH_DB_USER == "dwh"
    assert settings.DWH_DB_PASSWORD == "dwh"
    assert settings.API_KEY == ""
    assert settings.USE_CLICKHOUSE is False
    assert settings.REDIS_URL == "redis://localhost:6380/0"


def test_database_url() -> None:
    """database_url собирается как postgresql+asyncpg DSN."""

    settings = Settings(
        _env_file=None,
        DWH_DB_HOST="db",
        DWH_DB_PORT=5432,
        DWH_DB_NAME="moex",
        DWH_DB_USER="user",
        DWH_DB_PASSWORD="secret",
    )
    assert settings.database_url == "postgresql+asyncpg://user:secret@db:5432/moex"


def test_get_settings_cached() -> None:
    """get_settings возвращает один и тот же объект (lru_cache)."""

    assert get_settings() is get_settings()

