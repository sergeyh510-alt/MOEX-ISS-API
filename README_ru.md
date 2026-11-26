# MOEX-ISS API

[English](README.md) | Русский

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-compose-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Статус: этап 2/9**

REST API на FastAPI поверх мини-DWH Московской биржи (MOEX). Сервис ничего не
считает сам: он только читает готовые слои `mart` и `core` и отдаёт их в виде
документированных JSON-ответов (Swagger / OpenAPI).

## Источник данных

Данные приходят из отдельного проекта мини-DWH Московской биржи:
[sergeyh510-alt/MOEX-ISS-mini-DWH](https://github.com/sergeyh510-alt/MOEX-ISS-mini-DWH).
Тот проект грузит данные MOEX ISS через Airflow в PostgreSQL со слоями
`raw -> stg -> core -> mart`, плюс `meta` (свежесть) и `audit` (качество данных).
Данный API это read-only слой доступа поверх него.

## Быстрый старт

```bash
cp .env.example .env
docker compose up -d
```

Затем откройте http://localhost:8000/docs для интерактивной документации Swagger.

## Проверка живости (health)

`GET /health` проверяет сервис и базу данных. Он пингует PostgreSQL с коротким
таймаутом и отдаёт свежесть данных: последняя успешная загрузка из
`meta.load_run` плюс `max(date_key)` по `mart.stock_returns` (последняя дата
данных).

```json
{
  "status": "ok",
  "version": "0.1.0",
  "time_utc": "2026-11-26T10:00:00+00:00",
  "db": { "status": "ok", "latency_ms": 3.41 },
  "data": { "last_load_at": "2026-10-09T15:02:05+00:00", "last_data_date": "2026-10-10" }
}
```

Если база недоступна, эндпоинт возвращает HTTP 503 со `"status": "degraded"` и
`"db": {"status": "unavailable", "latency_ms": null}`.

## Слепок данных

Каталог `db/seed/` содержит слепок витрин DWH, чтобы API запускался с чистого
клона без живого DWH:

- `db/seed/00_schemas.sql`: создаёт схемы `mart`, `core`, `meta`, `audit`.
- `db/seed/01_seed.sql`: полный DDL плюс данные (`pg_dump --inserts`) витрин.

Контейнер `api_postgres` монтирует `db/seed` в
`/seed`, а `db/init/99_load_seed.sh` применяет файлы
по алфавиту при первом старте и затем повторно выдаёт `SELECT` read-only роли
`api_ro`.

Перегенерировать слепок из живого DWH (поправьте параметры подключения):

```bash
pg_dump --no-owner --no-privileges --inserts \
  --schema=mart --schema=core --schema=meta --schema=audit \
  "postgresql://dwh:dwh@localhost:5433/moex_dwh" > db/seed/01_seed.sql
```

## Эндпоинты

Все прикладные эндпоинты находятся под `/api/v1`. Служебные эндпоинты в корне.

| Метод | Путь | Назначение | Статус |
|---|---|---|---|
| GET | `/health` | живость, пинг БД и свежесть данных | done |
| GET | `/api/v1/meta/version` | версия API, версия схемы DWH | done |
| GET | `/api/v1/meta/freshness` | когда обновлялся каждый слой | done |
| GET | `/api/v1/meta/dq` | статус проверок качества данных | done |
| GET | `/api/v1/dates` | торговый календарь (`trading_only=true`) | done |
| GET | `/api/v1/securities` | список бумаг (поиск `q`, `boardid`, сортировка, пагинация) | done |
| GET | `/api/v1/securities/{secid}` | карточка бумаги с покрытием | done |
| GET | `/api/v1/securities/{secid}/prices` | OHLCV за период | planned |
| GET | `/api/v1/securities/{secid}/returns` | метрики доходности за период | planned |
| GET | `/api/v1/securities/{secid}/summary` | агрегат: доходность, волатильность, min/max | planned |
| GET | `/api/v1/indices` | список индексов | planned |
| GET | `/api/v1/indices/{code}` | история индекса за период | planned |
| GET | `/api/v1/compare` | бумага против индекса (`secid`, `index`, период) | planned |
| GET | `/api/v1/movers` | топ лучших и худших за дату или период | planned |
| GET | `/api/v1/ranking` | рейтинг бумаг за период | planned |

## Примеры

Список бумаг с поиском, сортировкой и пагинацией:

```bash
curl "http://localhost:8000/api/v1/securities?q=sber&sort=secid&order=asc&limit=10"
```

Карточка бумаги с покрытием в mart.stock_returns:

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

Списочные эндпоинты отдают конверт `{"items": [...], "total": N, "limit": L, "offset": O}`
и заголовки `X-Total-Count`, `X-Limit`, `X-Offset`.

## План работ

- [x] Этап 0: скелет проекта, FastAPI-приложение и docker-compose
- [x] Этап 1: слой доступа к данным, read-only роль и слепок данных
- [x] Этап 2: справочники (dates, securities, meta)
- [ ] Этап 3: цены и доходность
- [ ] Этап 4: индексы и сравнение с индексом
- [ ] Этап 5: лидеры роста и падения, рейтинг
- [ ] Этап 6: сквозные механизмы, ошибки, логи, api key
- [ ] Этап 7: юнит и интеграционные тесты, CI
- [ ] Этап 8: ClickHouse как аналитический источник за флагом
- [ ] Этап 9: Redis-кэш и портфолио-полировка

## Ограничения

- Данные обновляются раз в день (не real-time).
- Dev-порты: PostgreSQL на `5438`, Redis на `6380` (DWH использует `5433`).
- Redis-кэш и ClickHouse по умолчанию выключены (включаются на этапах 8 и 9).
- CORS открыт (`*`) только для dev; в продакшене такая конфигурация недопустима.

## Лицензия

MIT, см. [LICENSE](LICENSE).
