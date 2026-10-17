# FraggyAPI

Phase 1B application foundation: a Next.js synthetic fragrance directory, FastAPI
operational endpoints, local PostgreSQL, Alembic, and seven disabled ingestion
adapters. No real fragrance catalog, live scraping, or deployment is included.

## Requirements

- Node.js 24 (`.node-version` / `.nvmrc`), pnpm 11.25.0 (`packageManager`).
- Python 3.12+ with venv/pip; Docker Engine and Docker Compose v2.
- Free/open-source local tools only. No Supabase account or API keys required.

## Setup and run

From the repository root:

```sh
# If pnpm is not available, install the pinned version using your Node tool manager.
pnpm install --frozen-lockfile
bash scripts/setup.sh
# Optional: cp .env.example .env (only if .env does not already exist).
docker compose up -d --wait
.venv/bin/alembic -c apps/api/alembic.ini upgrade head
pnpm dev
```

`scripts/setup.sh` installs frozen JavaScript dependencies, creates `.venv`, installs
pinned Python development dependencies from `apps/api/requirements-dev.lock`, and
installs the API editable without changing the dependency lock. Run it before root
commands that invoke Python. It is safe to repeat. To refresh Python dependencies,
intentionally resolve `apps/api[dev]` in a clean venv and review both manifest and
lock changes. Do not replace locks as a troubleshooting shortcut.

`pnpm dev` runs web on port 3000 and API on port 8000, both bound to loopback.
Use `/` to explore, `/fragrances` to search/filter, `/fragrances/santal-no-04` for a
sample detail and `/brands` for houses. These are local route descriptions, not
cloud preview links. Web content is explicitly synthetic; bottle illustrations are
original CSS and require no external image service.

The API serves `/health` (200 independent of PostgreSQL), `/ready` (200 after a real
`SELECT 1`, 503 on database failure), `/api/v1` metadata and development `/docs`.
`APP_ENV=production` disables OpenAPI/docs. Liveness must not be used as database
readiness. API sessions are request-scoped and the engine is disposed on shutdown.

Stop development with Ctrl-C. `docker compose stop db` preserves local data;
`docker compose up -d --wait db` restarts it. Never use `down -v` against data you
need. Database ports are exposed on loopback only; default credentials are public,
disposable **local development only**, and must be replaced for hosting.

## Configuration and Supabase compatibility

API settings load environment variables and the root `.env`; exported values win.
Compose also reads the root `.env`. The optional Next.js public API URL is reserved
for a later API client; the current UI reads only `src/lib/mock-data.ts`. If needed
for frontend development, put only the non-secret `NEXT_PUBLIC_API_URL` in
`apps/web/.env.local`. Never copy the root database settings into frontend env files.

| Variable                                                             | Purpose                                                                   |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `DATABASE_URL`                                                       | SQLAlchemy `postgresql+asyncpg` URL; localhost default works with Compose |
| `MIGRATION_DATABASE_URL`                                             | Optional separate direct/session connection for Alembic                   |
| `APP_ENV`                                                            | `development`, `test`, or `production`                                    |
| `CORS_ORIGINS`                                                       | JSON array of explicit origins (no wildcard/path/credentials)             |
| `DATABASE_TIMEOUT_SECONDS`                                           | Positive readiness timeout, at most 30 seconds; default 3                 |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` | Compose initialization and exposed local port                             |
| `RUN_DB_TESTS`                                                       | Set to `1` to include the real PostgreSQL pytest check                    |

For Supabase, securely supply the Dashboard's direct or session-pooler URL, retain
its exact host, port and username, and change the URL scheme to
`postgresql+asyncpg`. Percent-encode special characters in passwords. Use verified
TLS (asyncpg supports `?ssl=verify-full` with the appropriate trust chain). Do not
copy libpq-only query parameters such as `sslmode` unchanged into an asyncpg URL.
Direct endpoints can require IPv6; session pooling is an alternative for IPv4-only
networks. Live Supabase connectivity was not tested and is not required locally.

Use direct/session mode for this persistent API and migrations. A transaction
pooler is not the validated default. Both asyncpg statement caches are disabled,
but that alone does not prove transaction-pooler compatibility. The API caps each
worker at three pooled connections plus two overflow connections. Multiply this by
replicas/workers when budgeting the database connection limit; Alembic uses NullPool.
Never place `DATABASE_URL` or a service-role credential in `NEXT_PUBLIC_*`.

## Checks

```sh
pnpm build
pnpm lint
pnpm typecheck
pnpm test                         # offline suite; DB test explicitly skipped
RUN_DB_TESTS=1 pnpm test          # includes PostgreSQL; start Compose first
pnpm format:check
.venv/bin/python scripts/check_secrets.py
.venv/bin/alembic -c apps/api/alembic.ini current
.venv/bin/alembic -c apps/api/alembic.ini check
# Requires production build and free ports 3000/8000; stops its own servers.
# Stops/restarts this project's local database; do not run against shared services.
.venv/bin/python scripts/smoke.py --manage-services --check-db-outage
```

Root tasks use Turborepo to dispatch API and web checks. Python lint covers API,
ingestion and helper scripts; mypy checks the API and strict TypeScript checks web.
Pytest covers the API, Vitest/Testing Library cover filtering and navigation links,
and unittest covers all seven ingestion adapters. Database tests are not cached.
CI runs PR/main checks plus migrations and runtime outage/recovery against Compose.
An actual GitHub-hosted run remains unverified until the files are pushed.

Alembic's initial revision establishes version history only, with no catalog tables.
For a future approved schema task, work from `apps/api`, generate a revision using
`../../.venv/bin/alembic revision --autogenerate -m "description"`, review it, and
validate upgrade/downgrade on disposable data. See `AGENTS.md` for permanent rules.

## Architecture and decisions

- `apps/web`: Next.js App Router, strict TypeScript, Tailwind v4, shadcn/ui
  source-owned Button using Radix Slot/CVA and `components.json` configuration.
- `apps/api`: FastAPI, Pydantic v2, SQLAlchemy 2 asyncpg, Alembic and structured logs.
- `workers/ingestion`: existing disabled source skeletons and synthetic fixtures.
- `config/sources.json`: all seven candidates disabled and `pending_review`.
- [Ingestion architecture](docs/ingestion-architecture.md)
- [Source permissions](docs/data-sources.md)
- [Free-tier hosting ADR](docs/adr/001-free-tier-hosting.md)
- [Phase 1 audit and verification evidence](docs/phase-1-audit.md)

Dependencies are pinned in the pnpm and Python locks. ESLint 9 and TypeScript 5.9
are deliberately selected because the current Next.js plugin peers do not support
ESLint 10/TypeScript 7 together. Upgrade those tools only when peers support them.
No deployment runtime has been silently substituted for Next.js or FastAPI.
