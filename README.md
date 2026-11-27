# MOEX-ISS API

English | [Русский](README_ru.md)

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-compose-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/sergeyh510-alt/MOEX-ISS-API/actions/workflows/ci.yml/badge.svg)](https://github.com/sergeyh510-alt/MOEX-ISS-API/actions/workflows/ci.yml)

**Status: Stage 9/9**

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

## Architecture

```mermaid
flowchart LR
    client["Client: browser, BI, service"]
    api["FastAPI app.main"]
    services["Services app.services"]
    repo["Repositories: SELECT only"]
    pg[("PostgreSQL: mart, core, meta, audit")]
    ch[("ClickHouse: secondary copy")]
    cache[("Redis: response cache")]

    client -->|HTTP| api
    api --> cache
    api --> services
    services --> repo
    repo -->|primary source| pg
    services -.->|USE_CLICKHOUSE=true| ch
    api -.->|CACHE_ENABLED=true| cache
```

Request flow: the client calls `/api/v1/...`, the API layer validates the
parameters, the service layer computes derived metrics, and the repositories
read rows from PostgreSQL. Optional branches are switched by flags: ClickHouse
speeds up heavy analytics (`/summary`, `/ranking`), Redis caches successful
responses. PostgreSQL stays the source of truth.

More detail: [docs/architecture.md](docs/architecture.md) (data flow, layers),
[docs/api.md](docs/api.md) (endpoints, examples, errors and headers),
[docs/queries.md](docs/queries.md) (key SQL with explanations).

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

## ClickHouse (optional analytics source)

PostgreSQL is the primary source and the source of truth. ClickHouse is an
optional second source used only for the heavy analytics endpoints (`/summary`
and `/ranking`); enable it with `USE_CLICKHOUSE=true`. When the flag is off the
behavior is exactly the same as before. Both sources feed the same raw mart rows
into the same math functions (`app/services/returns.py`, `app/services/ranking.py`),
so results match by construction rather than by chance.

Start the stack with ClickHouse (the override file adds the `api_ch` service and
sets the API env):

```bash
docker compose -f docker-compose.yml -f docker-compose.ch.yml up -d
```

Load the mart tables from PostgreSQL into ClickHouse (idempotent: re-run to
refresh the secondary copy):

```bash
docker compose exec api python -m scripts.ch_load
```

Notes:

- ClickHouse data is a secondary copy. It is not updated automatically: re-run
  the loader (or the loading container) to refresh it.
- If `USE_CLICKHOUSE=true` and ClickHouse is unavailable, the analytics endpoints
  return HTTP 503 in the unified error format. There is no silent fallback to
  PostgreSQL.
- Enabled by `USE_CLICKHOUSE=true`, `CLICKHOUSE_HOST`, `CLICKHOUSE_PORT`,
  `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD`, `CLICKHOUSE_DATABASE`,
  `CLICKHOUSE_TIMEOUT_S`.
- CI does not run ClickHouse: the parity test is skipped unless `TEST_CH=1`.

## Redis cache (optional)

The cache is optional and off by default. It only speeds up responses; if it is
off or Redis is unreachable the API works as usual (a single warning is logged,
no 503 because of the cache).

Enable it with `CACHE_ENABLED=true`, then start the stack (Redis is already part
of `docker-compose.yml`) and set the env:

```bash
# in .env
CACHE_ENABLED=true
CACHE_TTL_SECONDS=60
CACHE_KEY_PREFIX=moex-api
REDIS_URL=redis://redis:6379/0
docker compose up -d
```

Only successful HTTP 200 GET responses under `/api/v1` are cached, keyed by
path and query parameters, with the TTL from `CACHE_TTL_SECONDS`. Every such
response carries `X-Cache: HIT` or `X-Cache: MISS`. Errors are never cached and
`/health` is never cached. The cache is invalidated only by TTL.

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

## Cross-cutting concerns

- **Unified error format.** Every error answers with the same body, carrying a machine readable code and the request id: `{"error": {"code": "not_found", "message": "...", "details": null, "request_id": "..."}}`. Codes: `not_found`, `unauthorized`, `validation_error`, `rate_limited`, `internal_error`. `/health` is the only exception, its body is read by the compose healthcheck.
- **Request id.** `X-Request-ID` comes back on every response. Send your own header and the same value is echoed, otherwise the server generates one, writes it to the logs and puts it into the error body.
- **Logging.** One access line per request (method, path, status, duration, request id) plus application logs, all with the request id. Secrets are never logged.
- **Rate limiting.** Sliding window per client, `RATE_LIMIT_PER_MINUTE` (600 by default) applies to `/api/v1/*` and answers 429 with `Retry-After`. `/health` is never limited. The counter lives in process memory, so several replicas would count separately.
- **CORS.** `CORS_ORIGINS` is a comma separated list, `*` is the dev default. With `*` browsers forbid credentialed requests, so credentials are switched off in that mode instead of pretending they work.
- **API key.** The API is public by default. Set `API_KEY` and every `/api/v1/*` request must send `X-API-Key`, while `/health`, `/`, `/docs` and `/openapi.json` stay open. The comparison is constant time.

```bash
# without a key the call is open, with a key set it must carry the header
curl -s http://localhost:8000/api/v1/meta/version
curl -s -H "X-API-Key: $MOEX_API_KEY" http://localhost:8000/api/v1/meta/version
```

## Tests and CI

Unit tests (`tests/unit`) run without any database: they cover the pure helpers
(date and date_key conversion, pagination clamps, returns and ranking math,
settings, error, rate limit and cache key helpers). Integration tests
(`tests/integration`) need a live PostgreSQL with the loaded snapshot and are
enabled by `TEST_DB=1`. The ClickHouse parity test needs `TEST_CH=1` and the
cache flow test needs `TEST_REDIS=1`; without those variables they are skipped.

Run the unit tests locally:

```bash
python -m pytest tests/unit -q
```

Run the full suite (unit plus integration) against the compose database, where
`api` is the API image and `api_postgres` holds the loaded snapshot:

```bash
docker compose run --rm -e TEST_DB=1 --no-deps api pytest -q
```

CI (`.github/workflows/ci.yml`) runs three jobs on every push to `master` and on
every pull request:

- **lint**: installs ruff and runs `ruff check .`.
- **tests**: starts a `postgres:17-alpine` service, installs `requirements.txt`,
  loads `db/seed/00_schemas.sql` and `db/seed/01_seed.sql` through `psql`, then
  runs `pytest -q --cov=app --cov-report=term-missing` with `TEST_DB=1`.
- **docker**: verifies the image builds with `docker build` (no run).

## What broke and how I fixed it

Real issues found while building this project and how they were fixed:

- **Snapshot volume mounted into a read-only init directory.** The `db/seed`
  volume was mounted inside `/docker-entrypoint-initdb.d`, which is mounted
  `:ro`. Docker could not create the mount point and the container failed with
  `mkdirat ... read-only file system`. Fixed by mounting the snapshot at a
  separate path `/seed` and reading the files from there.
- **ClickHouse healthcheck hit `localhost`, which is IPv6 in the container.**
  Inside the container `localhost` resolves to IPv6 `::1`, while ClickHouse
  listens on IPv4 only, so the probe always got "Connection refused" and the
  `api` service never started (it waits for `service_healthy`). Fixed by using
  `127.0.0.1` in the healthcheck.
- **A unit test patched a repository through `sys.modules`.** The test replaced
  `app.repositories.ranking` via `sys.modules`, but `analytics` imports the
  submodule with `from app.repositories import ranking`; once the submodule is
  already imported, the package attribute points at the real module, so the
  patch did nothing and the real function ran with `session=None`. The test
  only passed where `sqlalchemy` was absent. Fixed by patching the three
  functions on the real module with `monkeypatch.setattr` and guarding the test
  with `pytest.importorskip("sqlalchemy")`.
- **Pydantic fields named `date` with type `date | None = None` broke on Python
  3.14.** With lazy (postponed) annotations the default value shadows the
  same-named type, so `date | None` could not be evaluated. Fixed by importing
  the type as `date_type` and qualifying the field type (`date_type | None`).
- **`ORDER BY ... DESC` in psql puts `NULL` first.** The reference query for the
  best day returned `NULL` first because PostgreSQL sorts `NULL` as the largest
  value in `DESC` unless `NULLS LAST` is given. Fixed by handling `NULL`
  explicitly in the ordering/tie-break logic.

## Roadmap

- [x] Stage 0: project skeleton, FastAPI app and docker-compose
- [x] Stage 1: db layer, read-only role and data snapshot
- [x] Stage 2: dictionaries endpoints (dates, securities, meta)
- [x] Stage 3: prices and returns endpoints
- [x] Stage 4: indices and index comparison endpoints
- [x] Stage 5: movers and ranking endpoints
- [x] Stage 6: cross-cutting concerns, errors, logging, api key
- [x] Stage 7: unit and integration tests plus CI
- [x] Stage 8: ClickHouse analytics source behind a flag
- [x] Stage 9: redis cache and portfolio polish

## Limitations

- Data is updated once a day (not real-time).
- Dev ports: PostgreSQL on `5438`, Redis on `6380`, ClickHouse on `8124` (the DWH uses `5433`).
- No authorization by default; set `API_KEY` to require `X-API-Key`.
- Rate limiting counts in process memory, so several replicas count separately.
- ClickHouse is off by default and is a secondary copy that must be reloaded manually.
- There is no incremental refresh: the snapshot and ClickHouse are reloaded in full.
- The Redis cache is off by default and is invalidated only by TTL.
- The service is designed for a single instance.
- CORS is wide open (`*`) for dev only; do not use this configuration in production.

## License

MIT, see [LICENSE](LICENSE).
