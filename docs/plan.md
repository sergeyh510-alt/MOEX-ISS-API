# MOEX-ISS-API: план проекта

REST API на FastAPI поверх мини-DWH Московской биржи (проект `MOEX_ISS`).
API ничего не считает сам: он только читает готовые слои `mart` / `core` и отдаёт
их по HTTP в виде документированных JSON-ответов (Swagger / OpenAPI).

Объём подтверждён 2026-11-26: PostgreSQL (основной источник), ClickHouse (этап 8),
Redis-кэш (этап 9), опциональный API-ключ, документация на двух языках.

---

## 0. Контекст и цель

Уже есть (сделан ранее, отдельный репозиторий):

* `C:\IntelliJ IDEA_PROJECT\MOEX_ISS`: мини-DWH на Airflow + PostgreSQL,
  слои `raw` -> `stg` -> `core` -> `mart`, плюс `meta` (свежесть) и `audit`
  (проверки качества данных). Опубликован на GitHub, есть данные за
  2024-01-01 .. 2026-10-10 (2118 строк истории по акциям, 706 по индексам).
* `C:\IntelliJ IDEA_PROJECT\Sql_qwery`: отдельный учебный проект NL-to-SQL
  поверх той же витрины `mart` (к API отношения не имеет, это другой кейс).

Задача этого репозитория: **отдельный сервис-слой**, HTTP API, через который
витрину DWH может читать любой клиент (браузер, мобильное приложение, BI,
другой сервис). Это классическая связка «хранилище -> слой доступа по API» и
хороший портфолио-кейс на стыке Data Engineering и backend.

Репозиторий: https://github.com/sergeyh510-alt/MOEX-ISS-API (public, MIT, ветка `master`).

---

## 1. Источник данных (что именно доступно)

Существующий DWH, PostgreSQL 17 внутри Docker. Параметры подключения
(из `MOEX_ISS/.env.example`):

| Параметр | Значение |
|---|---|
| host (снаружи) | `localhost` (или `host.docker.internal` из контейнера) |
| host port | `5433` (внутри стека 5432; порт занят DWH, менять нельзя) |
| database | `moex_dwh` |
| user / password | `dwh` / `dwh` (dev-заглушки) |

Таблицы, которые API будет отдавать (реальные, проверены в `MOEX_ISS/sql`):

**Витрины `mart`** (денормализованы, читаются без джойнов):

* `mart.stock_returns`: `security_key, date_key, secid, boardid, close, prev_close,
  daily_return_pct, gap_pct, amplitude_pct, ma_5, ma_20, volatility_5_pct,
  volatility_20_pct, cumulative_return_pct`, PK `(security_key, date_key)`.
* `mart.index_compare`: `index_code, security_key, date_key, secid,
  stock_return_pct, index_return_pct, excess_return_pct`, PK `(index_code, security_key, date_key)`.
* `mart.daily_movers`: `date_key, security_key, secid, daily_return_pct,
  return_rank, is_best_of_day, is_worst_of_day`, PK `(date_key, security_key)`.

**Измерения и факты `core`** (для справочников и «сырых» цен):

* `core.dim_security`: `security_key, secid, boardid, shortname, first_tradedate, last_tradedate`.
* `core.dim_date`: `date_key` (int `YYYYMMDD`), `calendar_date, year, quarter, month,
  day, iso_week, day_of_week, day_name, is_weekend, is_trading_day`.
* `core.fact_daily_prices`: OHLCV, `open, low, high, close, waprice, value,
  volume, numtrades, prev_close, close_change, close_change_pct`.
* `core.fact_daily_index`: `index_code, date_key, open, low, high, close, value,
  prev_close, close_change, close_change_pct`.

**Служебные слои** (бонусом, для «здоровья» сервиса):

* `meta.load_run` / `meta.freshness`: когда последний раз грузились данные.
* `audit.dq_run` / `audit.dq_check`: результаты проверок качества данных.

Важные особенности, которые учитываем в контракте:

* Дата в витринах это **целое** `date_key` (`YYYYMMDD`), а не `date`. В API наружу
  отдаём нормальную дату `YYYY-MM-DD`, а `date_key` принимаем как удобный
  альтернативный параметр и конвертируем внутри.
* Цены и проценты это `numeric`, наружу отдаём числа с фиксированной точностью
  (не строки) и документируем точность в описании схемы.
* `ma_20` / `volatility_20_pct` равны `NULL`, если истории меньше 20 торговых дней;
  отсутствие метрики это норма, а не ошибка.
* Витрины идемпотентны, но обновляются DAG'ом раз в день, поэтому данные «вчерашние».

---

## 2. Ключевое архитектурное решение: как API видит DWH

Два независимых `docker compose` стека должны сосуществовать. Варианты:

* **A. External network (рекомендуемый для «боевого» режима).** API подключается
  к сети DWH-стека как к внешней (`moex_iss_moex_net`) и ходит в `dwh_postgres`
  по имени сервиса. Ничего в DWH не меняется, API получает живые данные.
* **B. Через хост-порт.** API идёт на `host.docker.internal:5433`. Проще, но
  зависит от того, что DWH-стек поднят на этой машине.
* **C. Самодостаточный dev-режим (рекомендуемый для ревьюера портфолио).**
  Репозиторий API поднимает свой `api_postgres`, куда заливается **небольшой
  слепок** витрин (дамп в `db/seed/`). Порт API-БД: `5438` (свободен от
  DWH 5433 и Airflow 5434/5436). Тогда `docker compose up` работает с чистого
  клона, без проекта DWH.

**Решение:** реализуем C (для воспроизводимости и портфолио) и одновременно
поддерживаем A/B через переменные окружения (`DWH_DB_HOST`, `DWH_DB_PORT`):
один и тот же код, разные конфиги. Слепок в `db/seed/` генерируется скриптом из
живого DWH и коммитится (это учебные данные Мосбиржи, не секрет).

Доступ к БД API получает **read-only ролью** (`api_ro`): `SELECT` на `mart`,
`core`, `meta`, `audit` и больше ничего. Это защищает DWH от случайной записи
и красиво смотрится в README.

---

## 3. Технологический стек

| Слой | Выбор | Почему |
|---|---|---|
| Web | FastAPI + Uvicorn | async, автогенерация OpenAPI/Swagger |
| Валидация | Pydantic v2 + pydantic-settings | модели ответов + конфиг из env |
| ORM | SQLAlchemy 2.0 (async, `asyncpg`) | типизированные запросы, пул соединений |
| БД | PostgreSQL 17 (существующий DWH) | основной источник данных |
| ClickHouse | второй источник для тяжёлой аналитики, этап 8 | включается флагом `USE_CLICKHOUSE` |
| Кэш | Redis, этап 9 | снятие нагрузки с БД на повторных чтениях |
| Авторизация | опциональный `X-API-Key` | публично по умолчанию, ключ за флагом |
| Миграции | не нужны (API только читает) | схема принадлежит DWH |
| Тесты | pytest + pytest-asyncio + httpx | unit + integration |
| Линт/типы | ruff (+ mypy опционально) | чистота кода |
| CI | GitHub Actions | lint + tests + сборка образа |
| Контейнер | python:3.12-slim (не 3.14: нужны колёса под asyncpg/psycopg) | |
| Логи | structlog или stdlib logging + request-id | наблюдаемость |

---

## 4. Контракт API (v1)

Все прикладные эндпоинты под префиксом `/api/v1`. Служебные в корне.

| Метод | Путь | Назначение | Источник |
|---|---|---|---|
| GET | `/health` | живость + пинг БД + свежесть данных | `meta.freshness` |
| GET | `/api/v1/meta/version` | версия API, версия схемы DWH | конфиг |
| GET | `/api/v1/meta/freshness` | когда обновлялся каждый слой | `meta.freshness` |
| GET | `/api/v1/meta/dq` | статус проверок качества | `audit.dq_run`, `audit.dq_check` |
| GET | `/api/v1/dates` | торговый календарь (можно `trading_only=true`) | `core.dim_date` |
| GET | `/api/v1/securities` | список бумаг (поиск `q`, `boardid`, сортировка, пагинация) | `core.dim_security` |
| GET | `/api/v1/securities/{secid}` | карточка бумаги | `core.dim_security` |
| GET | `/api/v1/securities/{secid}/prices` | OHLCV за период | `core.fact_daily_prices` |
| GET | `/api/v1/securities/{secid}/returns` | метрики доходности за период | `mart.stock_returns` |
| GET | `/api/v1/securities/{secid}/summary` | агрегат: доходность за период, волатильность, min/max | `mart.stock_returns` |
| GET | `/api/v1/indices` | список индексов | `core.fact_daily_index` |
| GET | `/api/v1/indices/{code}` | история индекса за период | `core.fact_daily_index` |
| GET | `/api/v1/compare` | бумага против индекса (`secid`, `index`, период) | `mart.index_compare` |
| GET | `/api/v1/movers` | топ лучших/худших за дату или период | `mart.daily_movers` |
| GET | `/api/v1/ranking` | рейтинг бумаг за период | `mart.stock_returns` |

Сквозные правила (одинаковые для всех списочных эндпоинтов):

* **Пагинация:** `limit` (по умолчанию 100, максимум 1000) + `offset`, в ответе
  `X-Total-Count`, `X-Limit`, `X-Offset`; тело: конверт
  `{ "items": [...], "total": N, "limit": L, "offset": O }`.
* **Даты:** `from` / `to` в формате `YYYY-MM-DD`; алиасы `from_date` / `to_date`
  (чтобы не конфликтовать с `from` в Python); если не заданы, берём разумный
  дефолт (например, последние 30 торговых дней).
* **Сортировка:** `sort` = имя поля, `order` = `asc|desc`; допустимые поля
  перечислены в Swagger как `enum`.
* **Ошибки:** единый формат `{ "error": { "code", "message", "details" } }`
  со статусами 400/404/422/500; 404 когда бумаги/индекса нет.
* **Авторизация:** по умолчанию API публичный; если задан env `API_KEY`, все
  `/api/v1/*` требуют заголовок `X-API-Key` (кроме `/health`), иначе 401.
* **Кэш:** при включённом Redis ответы списочных эндпоинтов кэшируются по ключу
  из пути и параметров (TTL настраивается), заголовок `X-Cache: HIT|MISS`.
* **Время:** всё наружу в UTC (ISO-8601), `timestamptz` из БД приводим к UTC.
* **Десятичные:** отдаём `number` (float), точность документируем в описании поля.
* **Теги Swagger:** Health, Meta, Calendar, Securities, Prices, Returns, Indices,
  Compare, Movers, Analytics, у каждого тега описание на русском и английском.

---

## 5. Структура репозитория

```
MOEX-ISS-API/
├─ app/
│  ├─ main.py                 # создание FastAPI, роутеры, middleware, lifespan
│  ├─ config.py               # pydantic-settings: читает .env
│  ├─ db.py                   # async engine + session factory + pool
│  ├─ cache.py                # Redis-клиент и декоратор кэширования (этап 9)
│  ├─ security.py             # проверка X-API-Key (этап 6)
│  ├─ analytics_ch.py         # клиент ClickHouse (этап 8)
│  ├─ models/                 # SQLAlchemy-модели (read-only, mapped на mart/core)
│  ├─ schemas/                # Pydantic-схемы запросов и ответов
│  ├─ repositories/           # SQLAlchemy-запросы по сущностям
│  ├─ services/               # бизнес-логика (агрегаты, приведение дат)
│  ├─ api/
│  │  ├─ deps.py              # зависимости (сессия, пагинация, период)
│  │  └─ v1/                  # роутеры по разделам
│  ├─ core/                   # ошибки, логирование, пагинация, константы
│  └─ __init__.py
├─ db/
│  ├─ init/                   # SQL: создание read-only роли и грантов
│  └─ seed/                   # дамп-слепок витрин для dev-режима
├─ scripts/
│  ├─ dump_seed.py            # снять слепок с живого DWH в db/seed/
│  └─ ch_load.py              # заливка витрин в ClickHouse (этап 8)
├─ tests/
│  ├─ unit/                   # чистые функции, парсеры, пагинация
│  └─ integration/            # httpx против тестовой БД
├─ docs/
│  ├─ plan.md                 # этот файл
│  ├─ architecture.md         # схема решения, поток данных
│  ├─ api.md                  # описание эндпоинтов + примеры curl
│  └─ queries.md              # сами SQL-запросы с пояснениями
├─ .github/workflows/ci.yml   # lint + tests + build
├─ docker-compose.yml         # api + api_postgres + redis (dev-слепок)
├─ docker-compose.ch.yml      # override: ClickHouse (этап 8)
├─ docker-compose.dwh.yml     # override: подключение к живому DWH (вариант A/B)
├─ Dockerfile
├─ requirements.txt (или pyproject.toml + uv/pip)
├─ .env.example
├─ .gitignore
├─ LICENSE                    # уже есть (MIT)
├─ README.md                  # EN (основной портфолио-документ)
└─ README_ru.md               # RU (взаимные ссылки с README.md)
```

---

## 6. Этапы работ

Правило по каждому этапу: **останавливаемся, отчитываемся** (что сделано,
какие тесты зелёные, что не проверено), **ждём подтверждения**, затем коммит и
push в GitHub. Коммит на каждом шаге = история проекта.
README ведём **сразу на двух языках** (`README.md` + `README_ru.md`), начиная с этапа 0.

### Этап 0. Скелет и инфраструктура

* Структура каталогов, `.gitignore`, `.env.example`, `requirements.txt`,
  `pyproject.toml` (конфиг ruff и pytest).
* `app/main.py` с приложением, `/health`, тегами Swagger, описанием.
* `Dockerfile` (python:3.12-slim + uvicorn), `docker-compose.yml`
  (api + api_postgres на порту 5438 + redis), healthcheck, зависимость api от БД.
* `README.md` (EN, основной) и `README_ru.md` (RU), взаимные ссылки, статус
  этапа, как запустить, скриншот Swagger.

**Критерий приёмки:** `docker compose up -d` поднимает api; `GET /health` и
`GET /docs` отвечают 200; тест `tests/unit/test_health.py` зелёный.
**Коммит:** `feat(stage0): project skeleton, FastAPI app and docker-compose`.

### Этап 1. Слой доступа к данным (done, выполнен 2026-11-26)

* Read-only роль `api_ro` + гранты (`db/init/`).
* SQLAlchemy-модели на `mart` / `core` (read-only), `app/db.py` (async pool).
* `scripts/dump_seed.py`: слепок витрин из живого DWH в `db/seed/`.
* `/health` расширен реальным пингом БД и свежестью из `meta.freshness`.

**Коммит:** `feat(stage1): db layer, read-only role and data snapshot`.
**Критерий приёмки:** API стартует, `/health` показывает «БД доступна» и дату
последней загрузки; запись через `api_ro` запрещена (проверено тестом).

### Этап 2. Справочники (done, выполнен 2026-11-26)

* `/api/v1/dates`, `/api/v1/securities`, `/api/v1/securities/{secid}`,
  `/api/v1/meta/*`.
* Пагинация, поиск `q`, сортировка, 404.

**Коммит:** `feat(stage2): dictionaries endpoints (dates, securities, meta)`.
**Критерий приёмки:** на слепке из DWH список бумаг и календарь отдаются
корректно, пагинация и поиск покрыты тестами.

### Этап 3. Цены и доходность (done, выполнен 2026-11-26)

* `/securities/{secid}/prices`, `/returns`, `/summary`.

**Коммит:** `feat(stage3): prices and returns endpoints`.
**Критерий приёмки:** данные совпадают с ручным SQL-запросом к DWH (сверка
контрольных значений), NULL-метрики отдаются корректно.

### Этап 4. Индексы и сравнение (done, выполнен 2026-11-26)

* `/indices`, `/indices/{code}`, `/compare`.

**Коммит:** `feat(stage4): indices and index comparison endpoints`.
**Критерий приёмки:** сравнение бумаги с IMOEX совпадает с `mart.index_compare`.

### Этап 5. Ранжирование (done, выполнен 2026-11-26)

* `/movers` (за дату и за период), `/ranking`.

**Коммит:** `feat(stage5): movers and ranking endpoints`.
**Критерий приёмки:** топ-1 лучший/худший совпадает с `mart.daily_movers`.

### Этап 6. Сквозные механизмы и авторизация (done, выполнен 2026-11-26)

* Единый конверт списков, единый формат ошибок, request-id, структурные логи,
  CORS, ограничение частоты (простое), аккуратные описания и примеры в OpenAPI,
  экспорт `openapi.json` в артефакт.
* Опциональный `X-API-Key`: при заданном env `API_KEY` эндпоинты `/api/v1/*`
  требуют заголовок, иначе 401; `/health` остаётся открытым.

**Коммит:** `feat(stage6): cross-cutting concerns, errors, logging, api key`.
**Критерий приёмки:** Swagger без предупреждений, во всех списках единый формат,
валидация параметров даёт 422 в едином виде, при включённом ключе запрос без
заголовка даёт 401.

### Этап 7. Тесты и CI (done, выполнен 2026-11-26)

* `tests/unit` (парсинг дат, пагинация, конфликты параметров), `tests/integration`
  (httpx против тестовой БД со слепком).
* `.github/workflows/ci.yml`: ruff + pytest + сборка образа.

**Коммит:** `test(stage7): unit and integration tests plus CI`.
**Критерий приёмки:** CI зелёный на push, покрытие ключевых веток есть,
README содержит бейдж.

### Этап 8. ClickHouse (done, выполнен 2026-11-27)

* Сервис ClickHouse в `docker-compose.ch.yml`, заливка витрин
  (`scripts/ch_load.py`), клиент `app/analytics_ch.py`.
* Тяжёлые агрегаты (`/ranking`, `/summary` по всему периоду) читают ClickHouse.
* Включается флагом `USE_CLICKHOUSE=false` по умолчанию, PostgreSQL остаётся
  основным источником.

**Коммит:** `feat(stage8): ClickHouse analytics source behind a flag`.
**Критерий приёмки:** при флаге off поведение не меняется; при флаге on
аналитические эндпоинты читают ClickHouse; результаты сверены с PostgreSQL.

### Этап 9. Redis-кэш и портфолио-полировка (done, выполнен 2026-11-27)

* Redis-кэш ответов (`app/cache.py`), заголовок `X-Cache`, настройка TTL,
  инвалидация по расписанию.
* README EN + RU, схема архитектуры (mermaid), скриншоты Swagger, раздел
  «что сломалось и как починил», раздел «ограничения».

**Коммит:** `feat(stage9): redis cache and portfolio polish`.
**Критерий приёмки:** второй одинаковый запрос отдаётся из кэша (`X-Cache: HIT`),
репозиторий читается как готовый кейс, `docker compose up` работает с чистого клона.

**Итог проекта:** все девять этапов выполнены. Сервис отдаёт документированный
REST поверх мини-DWH Мосбиржи, работает с чистого клона на слепке данных,
имеет единый формат ошибок, идентификатор запроса, лимит частоты, опциональный
API-ключ, опциональный ClickHouse для тяжёлой аналитики, опциональный Redis-кэш,
двуязычный README и схему архитектуры. CI гоняет линтер, тесты и сборку образа.

---

## 7. Тестирование

* **Unit:** парсинг `date_key` <-> `YYYY-MM-DD`, пагинация, валидация периода
  (`from > to`), построение фильтров, формат ошибок, проверка ключа.
* **Integration:** поднимаем тестовую БД со слепком, гоняем httpx-клиент по всем
  эндпоинтам, сверяем контрольные значения с прямым SQL к DWH.
* **Контрактные:** проверка, что `openapi.json` генерируется и не ломается
  (snapshot-тест).

Команда: `docker compose run --rm api pytest -q` (и `ruff check .`).

**Важно (из опыта RateCompass):** `docker compose run` использует уже собранный
образ, поэтому после правок кода нужно `docker compose build api`.

---

## 8. Документация

* `README.md` (EN) / `README_ru.md` (RU): что это, как запустить (с DWH и без),
  примеры запросов, скриншот Swagger, ограничения.
* `docs/architecture.md`: поток данных DWH -> API -> клиент, схема стека.
* `docs/api.md`: таблица эндпоинтов, примеры `curl`, коды ошибок.
* `docs/queries.md`: ключевые SQL-запросы с объяснением (план запроса, индексы).

---

## 9. Риски и подводные камни (реестр)

1. **Сосуществование стеков:** порт DWH `5433` занят, поэтому у API своя БД на
   `5438`; в override-файле имя внешней сети, это реальное имя сети DWH
   (`moex_iss_moex_net`), его нужно перепроверить на живой машине.
2. **Docker Desktop должен быть запущен** (`start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"`),
   а в командах нужен префикс `set "PATH=C:\Program Files\Docker\Docker\resources\bin;%PATH%" &&`,
   иначе ломаются credential helpers.
3. **Порты:** API 8000, api_postgres 5438, Redis 6380 (6379 занят другими
   стеками), ClickHouse 8124 (HTTP) и 9001 (native) на этапе 8.
4. **Слепок данных:** слепок в `db/seed/` должен быть небольшим (мегабайты),
   иначе репозиторий распухнет; ограничиваемся, например, 3-5 бумагами и IMOEX.
5. **Read-only:** без роли `api_ro` и грантов есть риск случайной записи. В коде
   дополнительно запрещаем `session.commit()` в репозиториях (только `SELECT`).
6. **`date_key` как int:** не забыть конвертацию и валидацию диапазона
   (`YYYYMMDD`), иначе получим странные пустые ответы.
7. **`numeric` -> JSON:** отдаём числа, а не строки; при больших значениях
   следим за точностью (Pydantic `Decimal` -> `float` в схеме).
8. **CORS/кэш/ключ:** для портфолио включаем CORS `*` в dev, в README помечаем,
   что в прод так нельзя. Ключ и Redis выключены по умолчанию.
9. **Python 3.12, а не 3.14:** на 3.14 нет колёс части драйверов; в контейнере
   фиксируем 3.12.
10. **Секреты:** в репозиторий попадает только `.env.example`, реальные значения
    в `.env` (в `.gitignore`). Проверка секретов перед push.
11. **Ничего не меняем в DWH:** API исключительно читает; миграции в этом
    репозитории не пишем.

---

## 10. Правила работы

* Работаем **этапами с остановкой** после каждого: отчёт -> подтверждение -> коммит.
* **Коммит и push в GitHub на каждом этапе** (`https://github.com/sergeyh510-alt/MOEX-ISS-API`),
  история = журнал работ. Сообщения коммитов в стиле Conventional Commits.
* Всё, что можно проверить, проверяем на живых данных DWH (сверка с ручным SQL),
  а не «на словах». Что не удалось проверить, так и пишем.
* Реализацию кода ведёт Codex (как принято в наших проектах), проверку и коммиты
  делает Rowboat.
* В любом тексте (README, docstring, комментарии) не используем длинное тире.

---

## 11. Решения по объёму (зафиксировано 2026-11-26)

1. **ClickHouse:** да, вторым источником (этап 8), за флагом `USE_CLICKHOUSE`,
   PostgreSQL остаётся основным.
2. **Способ доступа к данным:** вариант C (свой слепок, работает с чистого
   клона) плюс переменные для живого DWH.
3. **Авторизация:** опциональный `X-API-Key` (этап 6), по умолчанию публично.
4. **Redis-кэш:** да (этап 9), выключен по умолчанию.
5. **README:** на двух языках, `README.md` (EN) и `README_ru.md` (RU), с
   взаимными ссылками, начиная с этапа 0.
