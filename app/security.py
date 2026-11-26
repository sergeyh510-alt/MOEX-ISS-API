"""Авторизация по API-ключу.

Ключ необязательный: если настройка ``API_KEY`` пустая, API открыт (это режим
портфолио-демо). Если ключ задан, прикладные эндпоинты ``/api/v1/*`` требуют
заголовок ``X-API-Key``. Служебные ``/health``, ``/``, ``/docs`` и
``/openapi.json`` остаются открытыми, иначе не работал бы healthcheck.
"""

from __future__ import annotations

import secrets

from fastapi import Header

from app.config import get_settings
from app.core.errors import unauthorized


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Проверить заголовок X-API-Key, если ключ включён в настройках."""

    expected = get_settings().API_KEY.strip()
    if not expected:
        return

    # Сравнение делаем в постоянном времени, чтобы не подсказывать ключ по времени ответа.
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise unauthorized()
