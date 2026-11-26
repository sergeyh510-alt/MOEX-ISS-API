"""Конфигурация приложения.

Настройки читаются из переменных окружения и/или файла ``.env`` через
``pydantic-settings``. Секреты (пароли, API-ключ) не логируем.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения.

    Значения по умолчанию рассчитаны на локальную dev-среду. Реальные
    значения задаются в ``.env`` (файл в ``.gitignore``).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Приложение
    APP_VERSION: str = "0.1.0"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Источник данных: PostgreSQL (мини-DWH Мосбиржи)
    DWH_DB_HOST: str = "localhost"
    DWH_DB_PORT: int = 5433
    DWH_DB_NAME: str = "moex_dwh"
    DWH_DB_USER: str = "dwh"
    DWH_DB_PASSWORD: str = "dwh"

    # Авторизация: пустой API_KEY означает, что авторизация выключена
    API_KEY: str = ""

    # CORS: список источников через запятую, "*" это dev-режим
    CORS_ORIGINS: str = "*"

    # Ограничение частоты запросов на клиента (скользящее окно в минуту)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 600

    # Дополнительные источники (этапы 8 и 9)
    USE_CLICKHOUSE: bool = False
    REDIS_URL: str = "redis://localhost:6380/0"

    @property
    def database_url(self) -> str:
        """DSN для SQLAlchemy async (asyncpg)."""

        return (
            "postgresql+asyncpg://"
            f"{self.DWH_DB_USER}:{self.DWH_DB_PASSWORD}"
            f"@{self.DWH_DB_HOST}:{self.DWH_DB_PORT}/{self.DWH_DB_NAME}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        """Список источников для CORS, разобранный из строки настроек."""

        raw = self.CORS_ORIGINS.strip()
        if not raw:
            return ["*"]
        if raw == "*":
            return ["*"]
        return [item.strip() for item in raw.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    """Вернуть единственный экземпляр настроек (кэш на процесс)."""

    return Settings()
