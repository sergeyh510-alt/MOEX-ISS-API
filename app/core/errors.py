"""Единый формат ошибок приложения.

Любой ответ об ошибке выглядит так::

    {"error": {"code": "...", "message": "...", "details": ..., "request_id": "..."}}

Исключение одно: ``/health`` отвечает своим телом, потому что он проверяет
живость сервиса и используется healthcheck-ом в docker-compose.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging_setup import get_request_id
from app.core.middleware import REQUEST_ID_HEADER

logger = logging.getLogger(__name__)

# Соответствие HTTP-статуса машинному коду ошибки.
STATUS_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    502: "bad_gateway",
    503: "service_unavailable",
}


class AppError(Exception):
    """Ошибка приложения: машинный код, сообщение, статус и подробности."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def not_found(message: str, details: Any | None = None) -> AppError:
    """Ошибка "не найдено" (HTTP 404)."""

    return AppError(code="not_found", message=message, status_code=404, details=details)


def unauthorized(message: str = "Требуется корректный ключ доступа в заголовке X-API-Key.") -> AppError:
    """Ошибка авторизации (HTTP 401)."""

    return AppError(code="unauthorized", message=message, status_code=401)


def bad_request(message: str, details: Any | None = None) -> AppError:
    """Некорректный запрос (HTTP 400)."""

    return AppError(code="bad_request", message=message, status_code=400, details=details)


def error_payload(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    """Собрать тело ответа об ошибке с текущим request_id."""

    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": get_request_id(),
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Подключить обработчики, приводящие все ошибки к единому формату."""

    @app.exception_handler(AppError)
    async def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = STATUS_CODES.get(exc.status_code, "http_error")
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(code, str(exc.detail)),
            headers={REQUEST_ID_HEADER: get_request_id()},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "loc": ".".join(str(part) for part in error.get("loc", ())),
                "msg": str(error.get("msg", "")),
                "type": str(error.get("type", "")),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_payload(
                "validation_error",
                "Некорректные параметры запроса.",
                details,
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
        # Трассировку пишем только в лог, наружу отдаём общее сообщение.
        logger.exception("Необработанная ошибка: %s", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content=error_payload("internal_error", "Внутренняя ошибка сервиса."),
            headers={REQUEST_ID_HEADER: get_request_id()},
        )
