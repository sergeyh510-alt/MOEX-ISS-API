# MOEX-ISS API

[English](README.md) | Русский

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-compose-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/sergeyh510-alt/MOEX-ISS-API/actions/workflows/ci.yml/badge.svg)](https://github.com/sergeyh510-alt/MOEX-ISS-API/actions/workflows/ci.yml)

**Статус: этап 7/9**

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
| GET | `/api/v1/securities/{secid}/prices` | OHLCV за период | done |
| GET | `/api/v1/securities/{secid}/returns` | метрики доходности за период | done |
| GET | `/api/v1/securities/{secid}/summary` | агрегат: доходность, волатильность, min/max | done |
| GET | `/api/v1/indices` | список индексов с покрытием | done |
| GET | `/api/v1/indices/{code}` | история индекса за период | done |
| GET | `/api/v1/compare` | бумага против индекса (`secid`, `index`, период) | done |
| GET | `/api/v1/movers` | топ лучших и худших за дату или период | done |
| GET | `/api/v1/ranking` | рейтинг бумаг за период | done |

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

Дневные цены OHLCV за период:

```bash
curl "http://localhost:8000/api/v1/securities/SBER/prices?from=2024-01-03&to=2024-01-10&order=asc"
```

Метрики доходности за период:

```bash
curl "http://localhost:8000/api/v1/securities/SBER/returns?from=2024-01-03&to=2024-01-10"
```

Сводка за период (доходность, волатильность, лучший и худший день, просадка):

```bash
curl "http://localhost:8000/api/v1/securities/SBER/summary?from=2024-01-03&to=2024-01-10"
```

Список индексов с покрытием:

```bash
curl "http://localhost:8000/api/v1/indices"
```

История индекса за период:

```bash
curl "http://localhost:8000/api/v1/indices/IMOEX?from=2024-01-03&to=2024-01-10&order=asc"
```

Сравнение бумаги с индексом:

```bash
curl "http://localhost:8000/api/v1/compare?secid=SBER&index=IMOEX&from=2024-01-03&to=2024-01-10"
```

Лучшие и худшие за один день (без `date` берётся самый поздний день):

```bash
curl "http://localhost:8000/api/v1/movers?date=2024-01-10&limit=5"
```

Лучшие и худшие дни по всем бумагам за период:

```bash
curl "http://localhost:8000/api/v1/movers?from=2024-01-04&to=2024-01-10&limit=5"
```

Рейтинг бумаг за период по доходности (также `metric=volatility`, `avg_daily_return`, `cumulative_return`):

```bash
curl "http://localhost:8000/api/v1/ranking?from=2024-01-03&to=2024-01-10&metric=period_return&order=desc&limit=10"
```

Списочные эндпоинты отдают конверт `{"items": [...], "total": N, "limit": L, "offset": O}`
и заголовки `X-Total-Count`, `X-Limit`, `X-Offset`.

## Сквозные механизмы

- **Единый формат ошибок.** Любая ошибка отвечает одним телом с машинным кодом и идентификатором запроса: `{"error": {"code": "not_found", "message": "...", "details": null, "request_id": "..."}}`. Коды: `not_found`, `unauthorized`, `validation_error`, `rate_limited`, `internal_error`. Единственное исключение это `/health`, его тело читает healthcheck в compose.
- **Идентификатор запроса.** `X-Request-ID` возвращается в каждом ответе. Передайте свой заголовок, и вернётся то же значение, иначе сервер сгенерирует его, запишет в логи и положит в тело ошибки.
- **Логи.** Одна строка access-лога на запрос (метод, путь, статус, длительность, идентификатор запроса) плюс логи приложения, все с идентификатором. Секреты в логи не попадают.
- **Ограничение частоты.** Скользящее окно на клиента, `RATE_LIMIT_PER_MINUTE` (по умолчанию 600) действует на `/api/v1/*` и отвечает 429 с `Retry-After`. `/health` не ограничивается. Счётчик живёт в памяти процесса, поэтому несколько реплик считали бы его отдельно.
- **CORS.** `CORS_ORIGINS` это список через запятую, `*` это dev-значение по умолчанию. Вместе с `*` браузеры запрещают запросы с учётными данными, поэтому в этом режиме они выключены, а не делают вид, что работают.
- **API-ключ.** По умолчанию API публичный. Задайте `API_KEY`, и каждый запрос к `/api/v1/*` должен присылать `X-API-Key`, а `/health`, `/`, `/docs` и `/openapi.json` остаются открытыми. Сравнение делается в постоянном времени.

```bash
# без ключа запрос открыт, при заданном ключе нужен заголовок
curl -s http://localhost:8000/api/v1/meta/version
curl -s -H "X-API-Key: $MOEX_API_KEY" http://localhost:8000/api/v1/meta/version
```

## Тесты и CI

Юнит-тесты (`tests/unit`) работают без базы данных: они покрывают чистые
хелперы (конвертация дат и date_key, клампы пагинации, математика доходности и
ранжирования, настройки, ошибки и лимит частоты). Интеграционные тесты
(`tests/integration`) требуют живого PostgreSQL с загруженным слепком и
включаются переменной `TEST_DB=1`.

Запустить юнит-тесты локально:

```bash
python -m pytest tests/unit -q
```

Запустить весь набор (юнит плюс интеграционные) против базы из compose, где
`api` это образ API, а `api_postgres` хранит загруженный слепок:

```bash
docker compose run --rm -e TEST_DB=1 --no-deps api pytest -q
```

CI (`.github/workflows/ci.yml`) гоняет три задачи на каждый push в `master` и
на каждый pull request:

- **lint**: ставит ruff и запускает `ruff check .`.
- **tests**: поднимает сервис `postgres:17-alpine`, ставит `requirements.txt`,
  загружает `db/seed/00_schemas.sql` и `db/seed/01_seed.sql` через `psql`, затем
  запускает `pytest -q --cov=app --cov-report=term-missing` с `TEST_DB=1`.
- **docker**: проверяет сборку образа через `docker build` (без запуска).

## План работ

- [x] Этап 0: скелет проекта, FastAPI-приложение и docker-compose
- [x] Этап 1: слой доступа к данным, read-only роль и слепок данных
- [x] Этап 2: справочники (dates, securities, meta)
- [x] Этап 3: цены и доходность
- [x] Этап 4: индексы и сравнение с индексом
- [x] Этап 5: лидеры роста и падения, рейтинг
- [x] Этап 6: сквозные механизмы, ошибки, логи, api key
- [x] Этап 7: юнит и интеграционные тесты, CI
- [ ] Этап 8: ClickHouse как аналитический источник за флагом
- [ ] Этап 9: Redis-кэш и портфолио-полировка

## Ограничения

- Данные обновляются раз в день (не real-time).
- Dev-порты: PostgreSQL на `5438`, Redis на `6380` (DWH использует `5433`).
- Redis-кэш и ClickHouse по умолчанию выключены (включаются на этапах 8 и 9).
- CORS открыт (`*`) только для dev; в продакшене такая конфигурация недопустима.

## Лицензия

MIT, см. [LICENSE](LICENSE).
