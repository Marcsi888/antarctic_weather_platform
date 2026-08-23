# Antarctic Weather Platform

Full-stack application for retrieving, caching, aggregating, and visualizing
historical Antarctic meteorological observations from AEMET OpenData.

**Status:** in active development. This README reflects what is actually
implemented as of each commit; sections for work not yet started are
omitted rather than stubbed out.

## Business Context

The application supports evaluation of a hypothetical wind-farm project in
Antarctica by making historical weather data from Spain's two Antarctic
research stations queryable, aggregatable, and inspectable through a web
interface: temperature, atmospheric pressure, and wind speed, over
arbitrary date ranges, at hourly/daily/monthly resolution.

## Data Source

Observations come from the AEMET OpenData REST API, specifically:

```
GET /api/antartida/datos/fechaini/{fechaIniStr}/fechafin/{fechaFinStr}/estacion/{identificacion}
```

This endpoint returns raw ~10-minute-interval observations recorded at
Spain's two Antarctic bases. AEMET updates this dataset annually, not in
real time — recent date ranges (the last several months) may legitimately
return no data.

### Supported stations

| Station | AEMET identifier |
|---|---|
| Gabriel de Castilla (meteorological) | `89070` |
| Juan Carlos I (meteorological) | `89064` |

These identifiers were confirmed against AEMET's official OpenAPI
specification (`https://opendata.aemet.es/AEMET_OpenData_specification.json`)
and verified with live requests. The radiometric station variants
(`89064R`, `89064RA`) exist in AEMET's system but are out of scope for this
application.

## Architecture

Layered backend, framework-independent domain logic:

```
API / Routes            FastAPI routers: request validation, response shaping
       |
Application / Service   Orchestration: cache check -> AEMET fetch -> aggregate
       |
Domain                  Pure functions: timezone conversion, aggregation,
       |                quality filtering (no FastAPI/SQLAlchemy dependency)
       |
Repositories             AEMET client, SQLite repository (independently mockable)
       |
SQLite / AEMET          External systems
```

Domain logic is deliberately kept free of framework dependencies so it can
be unit tested in isolation, particularly the timezone/DST pipeline and
aggregation functions, which are the parts of this system most sensitive to
subtle correctness bugs.

## Technology Stack

**Backend:** Python 3.12, FastAPI, Pydantic v2, pydantic-settings,
SQLAlchemy 2.x, SQLite, httpx, pytest, mypy (strict mode), ruff.

`httpx2` (Pydantic's actively maintained continuation of `httpx`, since
Starlette's `TestClient` deprecated the original) is a dev-only dependency
used solely by the test client. The AEMET integration itself uses `httpx`,
per the project's chosen HTTP client — see Assumptions below.

**Frontend:** not yet implemented.

## Repository Structure

```
antarctic_weather_platform/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory, health check
│   │   └── core/
│   │       ├── config.py        # environment-driven application settings
│   │       ├── logging.py       # root logger configuration
│   │       └── exceptions.py    # application exception hierarchy
│   ├── tests/
│   │   └── unit/
│   │       ├── test_config.py
│   │       ├── test_exceptions.py
│   │       ├── test_logging.py
│   │       └── test_main.py
│   └── pyproject.toml
├── docs/
│   └── development-plan.md
└── README.md
```

This will grow as domain, API, persistence, and frontend layers are added.

## Setup

### Backend

Requires Python 3.12+.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Environment Variables

Copy `.env.example` to `.env` at the project root and fill in your AEMET
API key. Never commit `.env` — it is already covered by `.gitignore`.

An AEMET OpenData API key is free and self-service:
`https://opendata.aemet.es/centrodedescargas/altaUsuario`.

| Variable | Required | Description |
|---|---|---|
| `AEMET_API_KEY` | yes | Sent as the `api_key` header on every AEMET request |
| `AEMET_BASE_URL` | no | Defaults to `https://opendata.aemet.es/opendata` |
| `AEMET_REQUEST_TIMEOUT_SECONDS` | no | Defaults to `10.0` |
| `DATABASE_PATH` | no | Defaults to `backend/data/weather.db` |
| `LOG_LEVEL` | no | Defaults to `INFO` |
| `CORS_ALLOW_ORIGINS` | no | Defaults to `["http://localhost:5173"]` |

Configuration is validated at startup (`backend/app/core/config.py`): a
missing or invalid required value fails immediately with a clear error
rather than surfacing later inside a request.

### Running tests

```bash
cd backend
pytest
```

## Design Decisions and Assumptions

These are stated here for reference; full reasoning for each is in the
technical report (`docs/report/`, written once the implementation is
complete).

- **Default input timezone.** If the caller omits a timezone, inputs are
  interpreted as `Europe/Madrid`. This matches the fixed output timezone
  (see below), so an unspecified date range corresponds to the same
  calendar day a user would see in the response, rather than shifting by
  the UTC offset.
- **Output timezone.** All returned datetimes are expressed in
  `Europe/Madrid` with an explicit UTC offset, regardless of the input
  timezone supplied. This is a fixed requirement, not a default.
- **Aggregation boundaries.** Hourly/daily/monthly buckets are drawn using
  `Europe/Madrid` calendar boundaries, consistent with the output timezone.
- **Browser timezone convenience default.** The frontend will pre-fill the
  timezone field using the browser's local timezone
  (`Intl.DateTimeFormat().resolvedOptions().timeZone`) as an editable
  starting value. This is a client-side convenience only — no IP-based
  geolocation or server-side location tracking is performed anywhere in
  this system.
- **Data quality filtering.** AEMET flags each observation with `qdato`
  (0 = good, 1 = bad quality), a field discovered during live API
  verification rather than specified in the original requirements.
  Observations with `qdato = 1` are excluded from aggregated (hourly/
  daily/monthly) results but retained in storage and in unaggregated
  responses, since a flagged-bad reading is not a trustworthy input to a
  mean.
- **Missing-value sentinel.** AEMET represents inapplicable/missing fields
  as the literal string `"NaN"` rather than JSON `null` or an omitted key.
  This is handled explicitly before type coercion in the AEMET response
  mapping layer.

## Trade-offs

- **httpx vs. httpx2.** `httpx` has had no release since December 2024,
  and its maintainers have begun stewarding `httpx2` as its continuation
  (used internally by Starlette's own `TestClient` as of the current
  version). We chose to keep `httpx` for the actual AEMET client, since it
  shows no deprecation notice on its own PyPI listing and is what this
  project's requirements specify; `httpx2` is used only as a dev
  dependency, to satisfy `TestClient`. This trades a small amount of
  forward-risk (building on a library with a long release gap) for
  avoiding an unverified migration onto a very recently released
  successor package under real project time constraints.

## Assumptions Requiring Future Verification

- The exact behavior of AEMET's 429 (rate limit) response under sustained
  load has not been empirically tested, only confirmed as a documented
  status code in the OpenAPI specification.
- Field availability differs between station types (confirmed: Juan Carlos
  I's live response included `radKjM2`, `rec`, `tsb`, and `altNieve` fields
  that Gabriel de Castilla's did not). The AEMET response mapping treats
  every field outside the five required ones as optional, but this has
  only been verified against these two specific stations.

## AI-Assisted Development Disclosure

AI-assisted tools were used as an engineering accelerator for design exploration, implementation support, code review, documentation, and test-case ideation.

All architectural decisions, trade-offs, verification of AEMET API behavior, and final validation of the submitted solution were reviewed and owned by the developer.
