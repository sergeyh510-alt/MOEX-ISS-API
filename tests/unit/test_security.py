"""Юнит-тесты авторизации по X-API-Key (этап 6)."""

from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from app.config import get_settings
from app.core.errors import register_exception_handlers
from app.security import require_api_key

TEST_KEY = "unit-test-secret-key"


def _build_app() -> FastAPI:
    """Мини-приложение с той же зависимостью, что и настоящий роутер v1."""

    app = FastAPI()
    # Обработчики нужны, чтобы AppError превращался в 401, а не в 500.
    register_exception_handlers(app)

    router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])

    @router.get("/ping")
    async def ping() -> dict:
        return {"ok": True}

    app.include_router(router)
    return app


def test_key_disabled_allows_request(monkeypatch) -> None:
    """Пустой API_KEY означает открытый доступ."""

    monkeypatch.setattr(get_settings(), "API_KEY", "")
    client = TestClient(_build_app())

    response = client.get("/api/v1/ping")
    assert response.status_code == 200


def test_missing_header_gives_401(monkeypatch) -> None:
    """При заданном ключе запрос без заголовка отклоняется."""

    monkeypatch.setattr(get_settings(), "API_KEY", TEST_KEY)
    client = TestClient(_build_app())

    response = client.get("/api/v1/ping")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_wrong_header_gives_401(monkeypatch) -> None:
    """Неверный ключ отклоняется."""

    monkeypatch.setattr(get_settings(), "API_KEY", TEST_KEY)
    client = TestClient(_build_app())

    response = client.get("/api/v1/ping", headers={"X-API-Key": "not-the-key"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_correct_header_passes(monkeypatch) -> None:
    """Верный ключ пропускает запрос."""

    monkeypatch.setattr(get_settings(), "API_KEY", TEST_KEY)
    client = TestClient(_build_app())

    response = client.get("/api/v1/ping", headers={"X-API-Key": TEST_KEY})
    assert response.status_code == 200
    assert response.json() == {"ok": True}
