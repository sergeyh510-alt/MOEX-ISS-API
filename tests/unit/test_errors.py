"""Юнит-тесты единого формата ошибок (этап 6)."""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.errors import bad_request, not_found, register_exception_handlers


def _build_app() -> FastAPI:
    """Мини-приложение со всеми ветками ошибок."""

    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/not-found")
    async def raise_not_found() -> dict:
        raise not_found("Бумага не найдена.")

    @app.get("/bad-request")
    async def raise_bad_request() -> dict:
        raise bad_request("Период задан неверно.", details={"from": "2026-01-01"})

    @app.get("/http-exception")
    async def raise_http_exception() -> dict:
        raise HTTPException(status_code=404, detail="Нет такой записи.")

    @app.get("/validate")
    async def validate(limit: int) -> dict:
        return {"limit": limit}

    @app.get("/boom")
    async def raise_unexpected() -> dict:
        raise RuntimeError("внутренняя деталь, которую нельзя показывать наружу")

    return app


def _error_body(response) -> dict:
    body = response.json()
    assert set(body.keys()) == {"error"}
    error = body["error"]
    assert set(error.keys()) == {"code", "message", "details", "request_id"}
    return error


def test_app_error_envelope() -> None:
    """AppError превращается в конверт с кодом и сообщением."""

    client = TestClient(_build_app())
    response = client.get("/not-found")

    assert response.status_code == 404
    error = _error_body(response)
    assert error["code"] == "not_found"
    assert error["message"] == "Бумага не найдена."


def test_details_are_kept() -> None:
    """Подробности передаются в details как есть."""

    client = TestClient(_build_app())
    response = client.get("/bad-request")

    assert response.status_code == 400
    error = _error_body(response)
    assert error["code"] == "bad_request"
    assert error["details"] == {"from": "2026-01-01"}


def test_http_exception_is_mapped() -> None:
    """Обычный HTTPException тоже отдаётся в едином формате."""

    client = TestClient(_build_app())
    response = client.get("/http-exception")

    assert response.status_code == 404
    error = _error_body(response)
    assert error["code"] == "not_found"
    assert error["message"] == "Нет такой записи."


def test_validation_error_is_422() -> None:
    """Ошибка валидации параметров: 422 и code validation_error."""

    client = TestClient(_build_app())
    response = client.get("/validate", params={"limit": "не-число"})

    assert response.status_code == 422
    error = _error_body(response)
    assert error["code"] == "validation_error"
    assert isinstance(error["details"], list)
    assert "loc" in error["details"][0]


def test_unhandled_error_hides_details() -> None:
    """Необработанное исключение: 500, без трассировки и внутренних деталей."""

    client = TestClient(_build_app(), raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500
    error = _error_body(response)
    assert error["code"] == "internal_error"
    text = response.text
    assert "Traceback" not in text
    assert "RuntimeError" not in text
    assert "внутренняя деталь" not in text
