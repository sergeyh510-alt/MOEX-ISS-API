# MOEX-ISS API

English | [Русский](README_ru.md)

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-compose-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Status: Stage 0/9**

REST API on FastAPI over a mini-DWH of the Moscow Exchange (MOEX). The service
does not compute anything on its own: it only reads the ready-made `mart` and
`core` layers and serves them as documented JSON (Swagger / OpenAPI).

## Data source

The data comes from a separate mini-DWH project of the Moscow Exchange:
[sergeyh510-alt/MOEX-ISS-mini-DWH](https://github.com/sergeyh510-alt/MOEX-ISS-mini-DWH).
That project loads MOEX ISS data through Airflow into PostgreSQL with layers
`raw -> stg -> core -> mart` plus `meta` (freshness) and `audit` (data quality).
This API is the read-only access layer on top of it.

## Quick start

```bash
cp .env.example .env
docker compose up -d
```

Then open http://localhost:8000/docs for the interactive Swagger UI.

## Endpoints

All application endpoints live under `/api/v1`. Service endpoints live at the root.

| Method | Path | Purpose | Status |
|---|---|---|---|
| GET | `/health` | liveness (db ping + freshness on stage 1) | done |
| GET | `/api/v1/meta/version` | API version, DWH schema version | planned |
| GET | `/api/v1/meta/freshness` | when each layer was last updated | planned |
| GET | `/api/v1/meta/dq` | data quality checks status | planned |
| GET | `/api/v1/dates` | trading calendar (`trading_only=true`) | planned |
| GET | `/api/v1/securities` | securities list (search `q`, `boardid`, sort, paging) | planned |
| GET | `/api/v1/securities/{secid}` | single security card | planned |
| GET | `/api/v1/securities/{secid}/prices` | OHLCV over a period | planned |
| GET | `/api/v1/securities/{secid}/returns` | return metrics over a period | planned |
| GET | `/api/v1/securities/{secid}/summary` | aggregate: return, volatility, min/max | planned |
| GET | `/api/v1/indices` | indices list | planned |
| GET | `/api/v1/indices/{code}` | index history over a period | planned |
| GET | `/api/v1/compare` | stock vs index (`secid`, `index`, period) | planned |
| GET | `/api/v1/movers` | top gainers / losers for a date or period | planned |
| GET | `/api/v1/ranking` | securities rating over a period | planned |

## Roadmap

- [x] Stage 0: project skeleton, FastAPI app and docker-compose
- [ ] Stage 1: db layer, read-only role and data snapshot
- [ ] Stage 2: dictionaries endpoints (dates, securities, meta)
- [ ] Stage 3: prices and returns endpoints
- [ ] Stage 4: indices and index comparison endpoints
- [ ] Stage 5: movers and ranking endpoints
- [ ] Stage 6: cross-cutting concerns, errors, logging, api key
- [ ] Stage 7: unit and integration tests plus CI
- [ ] Stage 8: ClickHouse analytics source behind a flag
- [ ] Stage 9: redis cache and portfolio polish

## Limitations

- Data is updated once a day (not real-time).
- Dev ports: PostgreSQL on `5438`, Redis on `6380` (the DWH uses `5433`).
- Redis cache and ClickHouse are disabled by default (enabled on stages 8 and 9).
- CORS is wide open (`*`) for dev only; do not use this configuration in production.

## License

MIT, see [LICENSE](LICENSE).
