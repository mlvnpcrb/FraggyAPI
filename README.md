# FraggyAPI

Phase 2C adds trusted licensed-file import and catalog review to the Next.js fragrance discovery site to a read-only, rights-aware
FastAPI catalog on PostgreSQL. The Phase 2A schema and seven disabled ingestion
adapters are preserved. Live scraping, paid services and deployments remain disabled.

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
Use `/` to explore, `/fragrances` to search/filter, `/fragrances/{uuid}` for a
detail and `/brands` for houses. These are local route descriptions, not cloud
preview links. The public catalog is empty until licensed fields are reviewed or
local synthetic publication is explicitly enabled. Bottle illustrations are original CSS.

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
Compose also reads the root `.env`. Next.js uses the server-only `API_BASE_URL`
(default `http://127.0.0.1:8000/api/v1`); export it before `pnpm dev` or set it in
`apps/web/.env.local`. It is not a browser credential. Never copy root database
settings into frontend env files. Root `.env` is not automatically loaded by Next.js.

| Variable                                                             | Purpose                                                                   |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `DATABASE_URL`                                                       | SQLAlchemy `postgresql+asyncpg` URL; localhost default works with Compose |
| `MIGRATION_DATABASE_URL`                                             | Optional separate direct/session connection for Alembic                   |
| `APP_ENV`                                                            | `development`, `test`, or `production`                                    |
| `CORS_ORIGINS`                                                       | JSON array of explicit origins (no wildcard/path/credentials)             |
| `DATABASE_TIMEOUT_SECONDS`                                           | Positive readiness timeout, at most 30 seconds; default 3                 |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` | Compose initialization and exposed local port                             |
| `API_BASE_URL`                                                       | Server-side public API base including `/api/v1`                           |
| `CATALOG_INCLUDE_SYNTHETIC`                                          | API demo grants opt-in; false by default, always false in production      |
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
Actual GitHub workflow evidence is recorded in the phase audit and PR.

Alembic's initial revision establishes history; revisions through `0004_quality`
now add the catalog/provenance schema and native search indexes.
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

## Phase 2A catalog database

```sh
# No demo data is inserted by migration or startup.
docker compose up -d --wait
.venv/bin/alembic -c apps/api/alembic.ini upgrade head
.venv/bin/alembic -c apps/api/alembic.ini current
# Explicit, optional, invented local data only; safe to repeat, preserves edits.
.venv/bin/python -m fraggy_api.seed --allow-demo-data
# Requires CREATEDB on the disposable localhost PostgreSQL role.
RUN_DB_TESTS=1 pnpm test
```

Twenty tables separate brands/fragrance lines from concentration/version-specific
releases, bottle variants, composition, source records, field claims and media rights.
UUIDs remain stable when display names change. All foreign keys use RESTRICT; no
catalog/provenance records cascade away. Unknown concentration/year values remain
null. Conflicting synthetic source years stay as claims for manual review.

The test fixture creates randomly named `fraggy_test_*` databases on loopback,
migrates them, rolls back each test, and drops only databases it created. Migration
round trips use another disposable database; never run catalog downgrades against
valuable data. Non-local/production test targets are refused. The application role
used for an eventual deployment should not have CREATEDB; use a separate local/CI
test role. No Supabase project is required or modified.

Seed data includes 2 invented houses, 4 lines, 6 releases, EDT/EDP/reformulation
examples, 4 variants, notes/accords/perfumers, two fictional archives, conflicting
claims, review work and reference-only media. It also copies the seven candidate
source definitions as disabled/pending rows. All source adapters remain disabled.
Synthetic UUIDv5 fixture keys are fixed and never derived from display names.

## Phase 2B public catalog

Seven GET routes expose brands, fragrance UUID details, ranked search, notes and
accords under `/api/v1`. See [public API](docs/public-api.md) and the separate
[Fraggy integration contract](docs/fraggy-integration.md). Browser pages use actual
API data; failures show error states, never fixture fallbacks. Operational metadata
now identifies phase `2B`; `/health` and `/ready` contracts are unchanged.

To view **invented local demo data**, explicitly publish fixture grants and start
with the development-only opt-in (never use this against production):

```sh
.venv/bin/python -m fraggy_api.seed --allow-demo-data --publish-demo-catalog
CATALOG_INCLUDE_SYNTHETIC=true pnpm dev
# Optional end-to-end fixture + outage verification; owns temporary servers:
.venv/bin/python scripts/smoke.py --manage-services --check-db-outage --demo-catalog
```

The original seed command does not publish anything. Both commands preserve
existing rows and edits. The 120-ID public fixture includes explicit grants for
original invented names/relationships only; edited fields fail closed until reviewed.
Every production field requires a selected, known, current-value claim, field
redistribution evidence, approved record rights and reviewed source policy. Raw
records, licensing evidence, descriptions, reviews and media have no public DTO fields.
No migration was added or rewritten in Phase 2B.

- [Phase 2B audit](docs/phase-2b-audit.md)

- [Database schema and ER diagram](docs/database-schema.md)
- [Data dictionary and contracts](docs/data-dictionary.md)
- [Phase 2A verification audit](docs/phase-2a-audit.md)

## Phase 2C licensed file import

CSV, JSON and JSONL are supported through a trusted local CLI, not an HTTP upload.
File-declared approval is never authority. Reviewed storage, canonical decisions
and field publication are separate; unverified files retain only quarantine hashes.
Synthetic examples always stay excluded in production. No migrations or new
infrastructure/dependencies were required; seven website adapters remain disabled.

```sh
pnpm catalog:import -- --file data/examples/fragrances.csv --manifest data/examples/source-manifest.json --dry-run
pnpm catalog:manage pending --source fictional-workshop-import
RUN_DB_TESTS=1 .venv/bin/python -m pytest apps/api/tests/test_import_cli.py -v
```

- [File schemas, limits, counters and safe batch resumption](docs/data-import.md)
- [Trusted source authorization and revocation](docs/source-authorization.md)
- [Operator decisions and complete fictional example](docs/catalog-review-workflow.md)
- [Phase 2C audit](docs/phase-2c-audit.md)

The operator CLI refuses production/non-loopback targets. Real files/manifests and
reports belong outside Git or under ignored `data/private`, `data/imports` or
`data/reports`. Public API v1/operational contracts remain unchanged; the API phase
metadata still describes the Phase 2B public interface. There is no Phase 2D,
subscription, deployment, separate PWA change or live scraping in this phase.
