# MOEX-ISS API

English | [Русский](README_ru.md)

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-compose-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Status: Stage 5/9**

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

## Health

`GET /health` checks the service and the database. It pings PostgreSQL with a
short timeout and reports data freshness read from `meta.load_run` (last
successful load) plus `max(date_key)` over `mart.stock_returns` (last data date).

```json
{
  "status": "ok",
  "version": "0.1.0",
  "time_utc": "2026-11-26T10:00:00+00:00",
  "db": { "status": "ok", "latency_ms": 3.41 },
  "data": { "last_load_at": "2026-10-09T15:02:05+00:00", "last_data_date": "2026-10-10" }
}
```

If the database is unavailable the endpoint returns HTTP 503 with
`"status": "degraded"` and `"db": {"status": "unavailable", "latency_ms": null}`.

## Data snapshot

`db/seed/` holds a snapshot of the DWH marts so the API runs from a clean clone
without the live DWH:

- `db/seed/00_schemas.sql`: creates the `mart`, `core`, `meta`, `audit` schemas.
- `db/seed/01_seed.sql`: full DDL plus data (`pg_dump --inserts`) of the marts.

The `api_postgres` container mounts `db/seed` into
`/seed`, and `db/init/99_load_seed.sh` applies the
files in alphabetical order on first start, then re-grants `SELECT` to the
read-only role `api_ro`.

To regenerate the snapshot from a running DWH (adjust connection params):

```bash
pg_dump --no-owner --no-privileges --inserts \
  --schema=mart --schema=core --schema=meta --schema=audit \
  "postgresql://dwh:dwh@localhost:5433/moex_dwh" > db/seed/01_seed.sql
```

## Endpoints

All application endpoints live under `/api/v1`. Service endpoints live at the root.

| Method | Path | Purpose | Status |
|---|---|---|---|
| GET | `/health` | liveness + db ping + data freshness | done |
| GET | `/api/v1/meta/version` | API version, DWH schema version | done |
| GET | `/api/v1/meta/freshness` | when each layer was last updated | done |
| GET | `/api/v1/meta/dq` | data quality checks status | done |
| GET | `/api/v1/dates` | trading calendar (`trading_only=true`) | done |
| GET | `/api/v1/securities` | securities list (search `q`, `boardid`, sort, paging) | done |
| GET | `/api/v1/securities/{secid}` | single security card with coverage | done |
| GET | `/api/v1/securities/{secid}/prices` | OHLCV over a period | done |
| GET | `/api/v1/securities/{secid}/returns` | return metrics over a period | done |
| GET | `/api/v1/securities/{secid}/summary` | aggregate: return, volatility, min/max | done |
| GET | `/api/v1/indices` | indices list with coverage | done |
| GET | `/api/v1/indices/{code}` | index history over a period | done |
| GET | `/api/v1/compare` | stock vs index (`secid`, `index`, period) | done |
| GET | `/api/v1/movers` | top gainers / losers for a date or period | done |
| GET | `/api/v1/ranking` | securities rating over a period | done |

## Examples

List securities with search, sorting and paging:

```bash
curl "http://localhost:8000/api/v1/securities?q=sber&sort=secid&order=asc&limit=10"
```

Security card with data coverage in `mart.stock_returns`:

```bash
curl "http://localhost:8000/api/v1/securities/SBER"
```

Trading calendar for a period, trading days only:

```bash
curl "http://localhost:8000/api/v1/dates?from=2026-01-01&to=2026-01-31&trading_only=true"
```

Data freshness by layer:

```bash
curl "http://localhost:8000/api/v1/meta/freshness"
```

Daily OHLCV prices for a period:

```bash
curl "http://localhost:8000/api/v1/securities/SBER/prices?from=2024-01-03&to=2024-01-10&order=asc"
```

Return metrics for a period:

```bash
curl "http://localhost:8000/api/v1/securities/SBER/returns?from=2024-01-03&to=2024-01-10"
```

Period summary (return, volatility, best/worst day, max drawdown):

```bash
curl "http://localhost:8000/api/v1/securities/SBER/summary?from=2024-01-03&to=2024-01-10"
```

Indices list with coverage:

```bash
curl "http://localhost:8000/api/v1/indices"
```

Index history for a period:

```bash
curl "http://localhost:8000/api/v1/indices/IMOEX?from=2024-01-03&to=2024-01-10&order=asc"
```

Stock vs index comparison:

```bash
curl "http://localhost:8000/api/v1/compare?secid=SBER&index=IMOEX&from=2024-01-03&to=2024-01-10"
```

Top gainers and losers for a single day (omit `date` for the latest day):

```bash
curl "http://localhost:8000/api/v1/movers?date=2024-01-10&limit=5"
```

Best and worst days across all securities for a period:

```bash
curl "http://localhost:8000/api/v1/movers?from=2024-01-04&to=2024-01-10&limit=5"
```

Securities rating over a period by return (also `metric=volatility`, `avg_daily_return`, `cumulative_return`):

```bash
curl "http://localhost:8000/api/v1/ranking?from=2024-01-03&to=2024-01-10&metric=period_return&order=desc&limit=10"
```

List endpoints return the envelope `{"items": [...], "total": N, "limit": L, "offset": O}`
plus the headers `X-Total-Count`, `X-Limit`, `X-Offset`.

## Roadmap

- [x] Stage 0: project skeleton, FastAPI app and docker-compose
- [x] Stage 1: db layer, read-only role and data snapshot
- [x] Stage 2: dictionaries endpoints (dates, securities, meta)
- [x] Stage 3: prices and returns endpoints
- [x] Stage 4: indices and index comparison endpoints
- [x] Stage 5: movers and ranking endpoints
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
