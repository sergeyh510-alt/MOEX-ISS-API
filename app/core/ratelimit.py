"""Простое ограничение частоты запросов в памяти процесса.

Лимитер считает запросы по ключу клиента в скользящем окне. Состояние живёт в
памяти одного процесса, поэтому при нескольких репликах лимит будет считаться
для каждой отдельно; общий счётчик (например в Redis) это отдельная задача.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.errors import error_payload

RATE_LIMIT_HEADER = "X-RateLimit-Limit"

# Защита от неограниченного роста словаря при большом числе клиентов.
MAX_TRACKED_CLIENTS = 10000


class RateLimiter:
    """Скользящее окно: не больше ``per_minute`` запросов на ключ."""

    def __init__(self, per_minute: int, window_seconds: float = 60.0) -> None:
        self.per_minute = max(1, per_minute)
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, now: float | None = None) -> tuple[bool, float]:
        """Вернуть пару (запрос разрешён, секунд до освобождения слота)."""

        moment = time.monotonic() if now is None else now

        if len(self._hits) > MAX_TRACKED_CLIENTS:
            self._hits.clear()

        bucket = self._hits[key]
        while bucket and moment - bucket[0] > self.window:
            bucket.popleft()

        if len(bucket) >= self.per_minute:
            retry_after = max(0.0, self.window - (moment - bucket[0]))
            return False, retry_after

        bucket.append(moment)
        return True, 0.0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Ограничивает частоту запросов к прикладным эндпоинтам."""

    def __init__(
        self,
        app,
        *,
        per_minute: int = 600,
        enabled: bool = True,
        prefix: str = "/api/v1",
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.prefix = prefix
        self.limiter = RateLimiter(per_minute)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not self.enabled or not request.url.path.startswith(self.prefix):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        allowed, retry_after = self.limiter.check(client)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content=error_payload(
                    "rate_limited",
                    "Превышен лимит запросов, повторите попытку позже.",
                ),
                headers={
                    "Retry-After": str(int(retry_after) + 1),
                    RATE_LIMIT_HEADER: str(self.limiter.per_minute),
                },
            )

        return await call_next(request)
