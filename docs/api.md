# API: эндпоинты, примеры, ошибки

Базовый URL: `http://localhost:8000`. Прикладные эндпоинты живут под
`/api/v1`, служебные (`/`, `/health`, `/docs`, `/openapi.json`) в корне.

## Таблица эндпоинтов

| Метод | Путь | Что отдаёт | Источник |
|---|---|---|---|
| GET | `/` | краткая информация о сервисе | нет (статика) |
| GET | `/health` | живость, пинг БД, свежесть данных | `meta.load_run`, `mart.stock_returns` |
| GET | `/api/v1/meta/version` | версия API, источник данных, список схем | настройки |
| GET | `/api/v1/meta/freshness` | когда обновлялся каждый слой, последняя дата | `meta.load_run`, `mart.stock_returns` |
| GET | `/api/v1/meta/dq` | статус проверок качества за последний запуск | `audit.dq_run`, `audit.dq_check` |
| GET | `/api/v1/dates` | торговый календарь с фильтром `trading_only` | `core.dim_date` |
| GET | `/api/v1/securities` | справочник бумаг (поиск `q`, `boardid`, сортировка) | `core.dim_security` |
| GET | `/api/v1/securities/{secid}` | карточка бумаги и покрытие витрины | `core.dim_security`, `mart.stock_returns` |
| GET | `/api/v1/securities/{secid}/prices` | дневные цены OHLCV за период | `core.fact_daily_prices` |
| GET | `/api/v1/securities/{secid}/returns` | метрики доходности за период | `mart.stock_returns` |
| GET | `/api/v1/securities/{secid}/summary` | сводка: доходность, волатильность, просадка | `mart.stock_returns` |
| GET | `/api/v1/indices` | список индексов с покрытием | `core.fact_daily_index` |
| GET | `/api/v1/indices/{code}` | история индекса за период | `core.fact_daily_index` |
| GET | `/api/v1/compare` | сравнение доходности бумаги и индекса | `mart.index_compare` |
| GET | `/api/v1/movers` | лидеры роста и падения за день или период | `mart.daily_movers` |
| GET | `/api/v1/ranking` | рейтинг бумаг за период | `mart.stock_returns`, `mart.daily_movers` |

## Примеры curl

Список бумаг с поиском и сортировкой:

```bash
curl "http://localhost:8000/api/v1/securities?q=sber&sort=secid&order=asc&limit=10"
```

Карточка бумаги с покрытием:

```bash
curl "http://localhost:8000/api/v1/securities/SBER"
```

Торговый календарь за период, только торговые дни:

```bash
curl "http://localhost:8000/api/v1/dates?from=2026-01-01&to=2026-01-31&trading_only=true"
```

Свежесть данных по слоям:

```bash
curl "http://localhost:8000/api/v1/meta/freshness"
```

Дневные цены за период:

```bash
curl "http://localhost:8000/api/v1/securities/SBER/prices?from=2024-01-03&to=2024-01-10&order=asc"
```

Метрики доходности за период:

```bash
curl "http://localhost:8000/api/v1/securities/SBER/returns?from=2024-01-03&to=2024-01-10"
```

Сводка по бумаге (доходность, волатильность, просадка, лучший и худший день):

```bash
curl "http://localhost:8000/api/v1/securities/SBER/summary?from=2024-01-03&to=2024-01-10"
```

Индексы и история индекса:

```bash
curl "http://localhost:8000/api/v1/indices"
curl "http://localhost:8000/api/v1/indices/IMOEX?from=2024-01-03&to=2024-01-10&order=asc"
```

Сравнение бумаги с индексом:

```bash
curl "http://localhost:8000/api/v1/compare?secid=SBER&index=IMOEX&from=2024-01-03&to=2024-01-10"
```

Лидеры за день (без `date` берётся самый поздний день витрины) и за период:

```bash
curl "http://localhost:8000/api/v1/movers?date=2024-01-10&limit=5"
curl "http://localhost:8000/api/v1/movers?from=2024-01-04&to=2024-01-10&limit=5"
```

Рейтинг бумаг за период по доходности (ещё метрики: `volatility`,
`avg_daily_return`, `cumulative_return`):

```bash
curl "http://localhost:8000/api/v1/ranking?from=2024-01-03&to=2024-01-10&metric=period_return&order=desc&limit=10"
```

## Формат ответа списков

Списочные эндпоинты отдают конверт:

```json
{"items": [], "total": 0, "limit": 100, "offset": 0}
```

## Заголовки

| Заголовок | Где | Смысл |
|---|---|---|
| `X-Request-ID` | все ответы | идентификатор запроса (ваш или сгенерированный) |
| `X-Total-Count` | списочные | всего строк по фильтру |
| `X-Limit` | списочные | размер страницы |
| `X-Offset` | списочные | смещение страницы |
| `X-Cache` | `/api/v1/*` при `CACHE_ENABLED=true` | `HIT` или `MISS` |
| `Retry-After` | 429 | через сколько секунд повторить |

## Формат ошибок

Любая ошибка отвечает единым телом с машинным кодом и идентификатором запроса:

```json
{
  "error": {
    "code": "not_found",
    "message": "Бумага не найдена.",
    "details": null,
    "request_id": "5f1c2a3b4d5e6f70"
  }
}
```

Коды: `bad_request`, `unauthorized`, `forbidden`, `not_found`,
`method_not_allowed`, `validation_error`, `rate_limited`, `internal_error`,
`service_unavailable`. Исключение одно: `/health` отвечает своим телом, его
читает healthcheck в docker-compose.

## Авторизация

По умолчанию API публичный. Если задан `API_KEY`, каждый запрос к `/api/v1/*`
требует заголовок `X-API-Key`, а `/health`, `/`, `/docs` и `/openapi.json`
остаются открытыми.
