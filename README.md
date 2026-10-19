# FraggyAPI

Phase 2G prepares the first source-specific metadata integration and a rights-aware
fragrance media pipeline on the existing Next.js, FastAPI and PostgreSQL foundation.
Wikidata integration is validated with fictional offline records; genuine collection
requires separate approval. Approved local bottle images support primary, gallery,
release and variant selection, with independent storage/publication reviews and
revocation. All seven website adapters, live scraping, paid services and deployments
remain disabled. The separate Fraggy PWA is unchanged.

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
local synthetic publication is explicitly enabled. Missing images use original CSS bottle placeholders; approved images are delivered through rights-checked local API routes.

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
metadata still describes the Phase 2B public interface. Phase 2D extends that baseline below. No subscription, deployment, separate PWA
change or live scraping is included.

## Phase 2D — reviewed attribution and fictional pilot

The local file-import foundation now supports explicit operator acceptance of
structured, public-only attribution, field-level credit paths, multiple providers,
source/field withdrawal and safe credits in the catalog UI. All seven website
adapters remain disabled; no external dataset is cleared, downloaded or imported.
No production deployment or paid infrastructure is introduced (₱0/month local
operating target).

- [Attribution API/PWA contract](docs/attribution-contract.md)
- [Source readiness and unresolved permissions](docs/licensed-source-readiness.md)
- [End-to-end fictional pilot commands](docs/pilot-import-workflow.md)
- [Phase 2D verification report](docs/phase-2d-audit.md)

Use `pnpm catalog:manage -- source-review ... --accept-attribution` only after a
human reviews storage, commercial redistribution, public fields and supported
obligations. `publish` remains a separate record decision. `unpublish --record-id
UUID --fields release_year ...` withdraws individual field grants; `revoke`
withdraws a source's publication. License labels and URLs never authorize use.

## Phase 2E — dataset discovery and catalog readiness

Read-only catalog quality reports, conservative duplicate analysis and disposable
PostgreSQL benchmarks extend the existing architecture. No real starter dataset
is cleared. All seven website adapters remain disabled/pending review; automated
collection is reserved for Phase 2F after Phase 2E review and merge.

```bash
pnpm catalog:quality -- --format json
pnpm catalog:quality -- --format text --fail-on error
.venv/bin/python scripts/benchmark_catalog.py --sizes 100,1000,10000 \
  --repeats 5 --warmup 1 --output data/reports/benchmark.json
```

Quality reads a PostgreSQL-enforced read-only snapshot, never changes data, and
reports missing percentages, candidates, provenance/rights/credit blockers and
publication eligibility. Benchmarks create and drop their own UUID-named local
databases; they never reset the application DB. Keep operational outputs private
and ignored. No paid search or hosted services are introduced; development remains
₱0/month.

- [Source evidence and future collection suitability](docs/phase-2e-source-assessment.md)
- [Quality checks and limits](docs/catalog-quality.md)
- [JSON/text report contract](docs/catalog-quality-report.md)
- [Local performance methodology/results](docs/phase-2e-performance.md)
- [Phase 2E verification](docs/phase-2e-audit.md)

## Phase 2F local collection

The authorized collector integrates with existing import, manual review, provenance,
attribution and quality commands. Collection/schedules and external network are off
by default; all seven website skeletons remain disabled. No real source was approved.

```bash
pnpm catalog:collect -- list
pnpm catalog:collect -- quality
.venv/bin/python scripts/demo_collection.py
```

The explicit demo uses only original fictional local HTTP metadata and a UUID-owned
disposable database. See [architecture](docs/phase-2f-architecture.md),
[authorization](docs/collector-authorization.md), [operations](docs/collector-operations.md)
and [audit](docs/phase-2f-audit.md). Never install a real-source schedule or supply
external-network opt-in without a separately approved source-specific pilot.

## Phase 2G — source and media readiness

- [Source selection and verified research](docs/phase-2g-source-selection.md)
- [Offline source integration](docs/phase-2g-integration.md)
- [Real-data pilot approval package — not authorized](docs/first-real-data-pilot.md)
- [Media architecture and operator commands](docs/fragrance-media-architecture.md)
- [Independent image licensing assessment](docs/image-rights-and-sources.md)
- [Phase 2G audit and measurements](docs/phase-2g-audit.md)

Run the original-only integrated demonstration with
`.venv/bin/python scripts/demo_collection.py --first-source --records 100`.
It creates and removes only its owned disposable database and image directory;
no genuine data or photo is acquired. Local media operations use
`pnpm catalog:media -- --help`; `MEDIA_ROOT` is server-only and defaults to ignored
`data/private/media`. Keep it private and outside all static mounts. No storage
provider/CDN is required for the ₱0/month development workflow.

## Phase 2H — verified local preview

With Node 24, pnpm 11.25.0, Python 3.12+ and Docker/Compose available:

```bash
bash scripts/setup.sh
docker compose up -d --wait
pnpm preview:local
```

This explicitly starts an original-only synthetic preview in its own disposable
PostgreSQL database, with 100 fictional fragrances and four original approved
image fixtures. It safely applies migrations there and starts loopback FastAPI
and Next development servers. The existing application DB is not reset or loaded.
No genuine fragrance record, photo, live source or paid service is used.

On the **same computer** open `http://127.0.0.1:3000/`. API docs are
`http://127.0.0.1:8000/docs`, health `/health`, readiness `/ready` on port 8000.
All were actually tested. In the Codex cloud environment these are internal
loopback addresses, not publicly accessible preview URLs; no forwarded URL is
available through the current tools. Use platform forwarding if separately
available, or run these commands on your own computer. Do not call localhost a
public deployment. Ports 3000 and 8000 must be free; use
`pnpm preview:local --web-port 3001 --api-port 8001` for alternatives.

Keep the supervisor terminal running. Ctrl-C normally stops owned processes and
removes its own fixture DB/media; when a managed cloud terminal detaches a child,
send SIGTERM only to the verified supervisor PID in ignored
`data/reports/local-preview.json` and confirm `running=false`. It must not stop
unrelated servers or delete other databases. Interrupted hosts may require an
operator to inspect and explicitly clean their known owned fixture DB.

Offline pilot readiness: `pnpm pilot:check -- config/wikidata-pilot-proposal.json`.
The template keeps `CONTACT_EMAIL` unchanged and live discovery/collection disabled.
A real monitored address, actual ID qualification, endpoint review and separate
explicit user approval are still required. No genuine candidate IDs are invented.

- [Readiness scorecard, counts, preview URLs and blockers](docs/phase-2h-readiness-report.md)
- [Exact pilot scope, budget, methodology and approval gates](docs/phase-2h-pilot-preparation.md)
- [Local search/filter/page/detail/media measurements](docs/phase-2h-performance.md)
- [Engineering, security and browser audit evidence](docs/phase-2h-audit.md)

Optional original-only browser QA (Chromium installed) while the owned preview is
running: `node scripts/browser_qa.mjs data/reports/local-preview.json --outage`.
It blocks external origins, inspects desktop/tablet/mobile and pauses/resumes only
the verified owned API to test error recovery. Outputs stay under ignored
`data/reports/browser-qa/`. Benchmarks use `scripts/benchmark_preview.py` and remove
only their own fixture DB/files. Run database outage tests only after all other
DB-dependent tests/benchmarks finish; restore PostgreSQL healthy afterward.

## Proposed Vercel fictional preview

The website can run without FastAPI/PostgreSQL when explicitly configured with
`FRAGGY_DEMO_MODE=synthetic`. It bundles the existing 100 fictional fragrances
and four original image fixtures, labels every page as a read-only demo, and
preserves the normal backend path when unset. API outages never activate it.

See [the Vercel preview configuration and deployment instructions](docs/vercel-demo.md).
Set Vercel Root Directory to `apps/web`; do not run the root Python-inclusive
build. **No public deployment is authorized yet.** The reviewed configuration
and access policy need approval before creating a `*.vercel.app` preview.

## Phase 2J — first real-data pilot preparation

`pnpm pilot:prepare` reports the disabled 25-record proposal.
`pnpm pilot:prepare --dry-run` exercises original local SPARQL fixtures through
the existing adapter/quality rules, with no network, database writes, imports,
images or publication. Quantities are bounded to 20–50. Genuine collection is
blocked pending fresh source evidence, a monitored contact, reviewed genuine IDs
and separate explicit activity approval.

See [source comparison](docs/phase-2j-sources.md) and
[Phase 2K's proposed workflow and rollback](docs/phase-2k-pilot.md).
