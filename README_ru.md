# MOEX-ISS API

[English](README.md) | Русский

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-compose-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Статус: этап 0/9**

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

## Эндпоинты

Все прикладные эндпоинты находятся под `/api/v1`. Служебные эндпоинты в корне.

| Метод | Путь | Назначение | Статус |
|---|---|---|---|
| GET | `/health` | живость (пинг БД и свежесть на этапе 1) | done |
| GET | `/api/v1/meta/version` | версия API, версия схемы DWH | planned |
| GET | `/api/v1/meta/freshness` | когда обновлялся каждый слой | planned |
| GET | `/api/v1/meta/dq` | статус проверок качества данных | planned |
| GET | `/api/v1/dates` | торговый календарь (`trading_only=true`) | planned |
| GET | `/api/v1/securities` | список бумаг (поиск `q`, `boardid`, сортировка, пагинация) | planned |
| GET | `/api/v1/securities/{secid}` | карточка бумаги | planned |
| GET | `/api/v1/securities/{secid}/prices` | OHLCV за период | planned |
| GET | `/api/v1/securities/{secid}/returns` | метрики доходности за период | planned |
| GET | `/api/v1/securities/{secid}/summary` | агрегат: доходность, волатильность, min/max | planned |
| GET | `/api/v1/indices` | список индексов | planned |
| GET | `/api/v1/indices/{code}` | история индекса за период | planned |
| GET | `/api/v1/compare` | бумага против индекса (`secid`, `index`, период) | planned |
| GET | `/api/v1/movers` | топ лучших и худших за дату или период | planned |
| GET | `/api/v1/ranking` | рейтинг бумаг за период | planned |

## План работ

- [x] Этап 0: скелет проекта, FastAPI-приложение и docker-compose
- [ ] Этап 1: слой доступа к данным, read-only роль и слепок данных
- [ ] Этап 2: справочники (dates, securities, meta)
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
