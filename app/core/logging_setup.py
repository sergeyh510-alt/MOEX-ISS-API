"""Настройка логирования и идентификатор запроса.

Идентификатор запроса живёт в contextvar: его выставляет middleware и читает
логгер. Модуль называется ``logging_setup``, чтобы не путаться со стандартным
модулем ``logging`` при абсолютных импортах.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar, Token

_REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")

_CONFIGURED = False

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s [request_id=%(request_id)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def set_request_id(value: str) -> Token[str]:
    """Положить идентификатор запроса в контекст текущей задачи."""

    return _REQUEST_ID.set(value)


def get_request_id() -> str:
    """Вернуть идентификатор текущего запроса (или "-" вне запроса)."""

    return _REQUEST_ID.get()


class RequestIdFilter(logging.Filter):
    """Подставляет request_id в каждую запись лога."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _REQUEST_ID.get()
        return True


def setup_logging(level: str = "INFO") -> None:
    """Настроить корневой логгер один раз на процесс.

    Формат строки: время, уровень, логгер, request_id, сообщение. Секреты в
    логи не попадают: сам логгер их не добавляет, а код их не логирует.
    """

    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper() or "INFO")

    _CONFIGURED = True
