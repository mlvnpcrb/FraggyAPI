# Phase 1B completion audit (historical local baseline)

This report records Phase 1B before committing. See `phase-1c-review.md` for the
subsequent finalization review; current Git status and remote CI supersede its
pre-commit observations.

Date: 2026-10-17. Repository: `/workspace/FraggyAPI`.

## Completion decision

**Phase 1B is complete for local development.** The previously missing application
foundation is implemented and verified. No Phase 2 catalog models or live scraping
were added. All seven source candidates remain disabled and pending review.

Recommend reviewing this working tree and running the added CI on GitHub before
accepting the baseline and beginning Phase 2. There are no diagnosed local failures
remaining. A remote CI run, hosted Supabase/Cloudflare/ASGI deployment and restoration
in a new cloud task are NOT VERIFIED. Nothing was deployed, committed or pushed;
no paid resource or account was created. The checkout still has no commits and all
implementation files are untracked, so this report describes working-tree behavior.

The earlier audit correctly found only an ingestion skeleton. Phase 1B resolves
those local application gaps; that earlier report was not evidence of a working app.

## Requirement results

| # | Requirement | Status | Supporting evidence |
| --- | --- | --- | --- |
| 1 | pnpm/Turborepo monorepo | PASS | `pnpm install --frozen-lockfile`: `Already up to date`; `pnpm peers check`: `No peer dependency issues found`. Turbo lists `@fraggy/api`, `@fraggy/web`; all root commands execute. |
| 2 | Next.js starts and builds | PASS | `pnpm dev`: Next `Ready in 328ms`; `pnpm build`: `Compiled successfully`, `2 successful, 2 total`. Production HTTP checks cover required routes. |
| 3 | FastAPI starts, `/health` | PASS | `pnpm dev`: `Application startup complete`; managed production HTTP smoke: `/health -> 200`, body `{"status":"ok"}`; `/api/v1` and `/docs -> 200`. |
| 4 | `/ready` queries PostgreSQL | PASS | Real `SELECT 1` through injected async session. Live outage check: 200 with DB, 503 after Compose stop, health stays 200, readiness recovers to 200 after restart. Unit tests cover timeout, bad result and sanitized failure. |
| 5 | Alembic | PASS | Upgrade/current/check and downgrade/upgrade succeeded; `0001_foundation (head)`, `No new upgrade operations detected.` Only `alembic_version` exists in public schema. |
| 6 | Local PostgreSQL via Compose | PASS | `docker compose up -d --wait`: `Healthy`; `docker compose ps`: `postgres:17-alpine`, healthy, loopback port 5432. Persistent named volume retained. |
| 7 | Seven adapters disabled | PASS | Registry output shows seven `False pending_review`; existing tests invoke every adapter and require `LiveIngestionDisabled`. Source permission/license review is still pending, not approved. |
| 8 | Backend/frontend tests | PASS | `RUN_DB_TESTS=1 pnpm test`: 14 API tests, 3 frontend tests, 3 ingestion tests passed; zero skips in this run. |
| 9 | Python lint / TypeScript | PASS | `pnpm lint`: Ruff passes API/workers/scripts, ESLint has no warnings/errors. `pnpm typecheck`: strict mypy passes 4 API files, TypeScript exits 0. Prettier check passes. |
| 10 | Secrets not committed | PASS, limited guarantee | `git ls-files` count 0, commit count 0. Secret scanner: 83 nonignored files, zero findings; environment files ignored. Disposable local defaults explicitly documented. Heuristic scanning is not a guarantee for all credential formats. |
| 11 | AGENTS.md rules | PASS | Created and reviewed boundaries, conventions, migrations, collection/security, tests/docs/phase completion rules. `rg '^##' AGENTS.md` output below. |
| 12 | GitHub Actions CI | PASS (configuration); NOT VERIFIED (remote run) | PR/main workflow includes frozen setup, Compose, lint/types/format/tests/build, migrations, runtime outage checks and secret scan. `actionlint` exits 0. No pushed commit/remote execution. |
| 13 | Free-tier hosting documented | PASS (decision record); NOT VERIFIED (deployment) | `docs/adr/001-free-tier-hosting.md` exists; official provider source docs were read for quotas/limitations. It preserves FastAPI and explains Workers dependency limitations, candidate ASGI hosting, pooling, suspension, commercial review and upgrades. |

## Actual command evidence

Commands run from the repository root unless shown otherwise. Output excerpts omit
installation progress and repeated per-file listings, not failures or skipped tests.

### Installation and toolchain

```text
$ node --version
v24.19.0
$ pnpm --version
11.25.0
$ python --version
Python 3.12.14
$ docker compose version
Docker Compose version v2.40.3
$ pnpm install --frozen-lockfile
Scope: all 3 workspace projects
Already up to date
Done in 440ms using pnpm v11.25.0
$ pnpm peers check
No peer dependency issues found
$ bash scripts/setup.sh
Already up to date
... pinned Python requirements already satisfied ...
Successfully installed fraggy-api-0.1.0
$ .venv/bin/pip check
No broken requirements found.
```

Setup was repeated. A separate fresh virtual environment additionally validated the
Python lock without relying on the existing environment:

```sh
python -m venv /tmp/fraggy-clean-python
/tmp/fraggy-clean-python/bin/pip install -r apps/api/requirements-dev.lock
/tmp/fraggy-clean-python/bin/pip install --no-deps --no-build-isolation -e apps/api
/tmp/fraggy-clean-python/bin/pip check
RUN_DB_TESTS=1 /tmp/fraggy-clean-python/bin/python -m pytest apps/api/tests -q
```

```text
No broken requirements found.
.............. [100%]
14 passed in 0.66s
```

Initial pnpm attempts encountered an unwritable home store, unsupported peers and
an unapproved resolver postinstall. Corrections: project-local store/cache paths,
compatible ESLint 9.39.5/TypeScript 5.9.3, and explicit approval for the single
`unrs-resolver` dependency script. No signature/checksum/TLS verification was disabled.
The first pytest run warned that the newer Starlette expects httpx2; the dev
manifest/lock now use httpx2, and the final suite has no warnings. An initial import
lint warning and a button text-color defect were also fixed and revalidated.

### Build, lint, types, formatting and tests

```text
$ pnpm build
Next.js 16.4.2 (Turbopack)
Compiled successfully
Finished TypeScript
Generating static pages using 4 workers (11/11)
Route (app)
  /                          static
  /brands                    static
  /fragrances                dynamic
  /fragrances/[slug]         six generated synthetic detail pages
Tasks: 2 successful, 2 total
(exit 0)
$ pnpm lint
@fraggy/api:lint: All checks passed!
Tasks: 2 successful, 2 total
All checks passed!  [workers and scripts]
(exit 0; ESLint no warnings/errors)
$ pnpm typecheck
@fraggy/api:typecheck: Success: no issues found in 4 source files
Tasks: 2 successful, 2 total
(exit 0; web tsc --noEmit)
$ pnpm format:check
All matched files use Prettier code style!
$ RUN_DB_TESTS=1 pnpm test
API: collected 14 items; 14 passed in 0.55s
Web: Test Files 1 passed (1); Tests 3 passed (3)
Ingestion: Ran 3 tests in 0.008s; OK
```

`pnpm test` was also run without the DB opt-in: the real PostgreSQL test was
explicitly skipped in that offline run. The final opt-in run above has no skips.
API tests cover docs visibility, version/liveness, query-backed readiness, timeouts,
invalid results, error sanitization, explicit CORS and actual DB readiness. Frontend
tests cover combined search/filters, empty/reset behavior and detail links. Existing
ingestion tests remain intact.

### Development startup and production HTTP smoke

```text
$ pnpm dev
Turbo packages: @fraggy/api, @fraggy/web
API: Application startup complete.
Web: Next.js 16.4.2; Ready in 328ms
GET / 200
GET /fragrances 200
GET /fragrances/santal-no-04 200
GET /brands 200
```

This persistent development command was intentionally interrupted after browser
verification; its resulting termination status is not a build/test failure. During
the first transition from dev to smoke, an old server was still shutting down and
a request reset. After confirming ports were free, the smoke passed. The helper now
checks port availability before starting managed servers.

```text
$ .venv/bin/python scripts/smoke.py --manage-services --check-db-outage
PASS http://127.0.0.1:8000/health -> 200
PASS http://127.0.0.1:8000/ready -> 200
PASS http://127.0.0.1:8000/api/v1 -> 200
PASS http://127.0.0.1:8000/docs -> 200
PASS http://127.0.0.1:3000/ -> 200
PASS http://127.0.0.1:3000/fragrances -> 200
PASS http://127.0.0.1:3000/fragrances/santal-no-04 -> 200
PASS http://127.0.0.1:3000/fragrances/figue-sauvage -> 200
PASS http://127.0.0.1:3000/brands -> 200
PASS http://127.0.0.1:3000/fragrances?q=not-a-real-scent -> 200
PASS http://127.0.0.1:3000/fragrances/unknown-scent -> 404
Container fraggyapi-db-1 Stopped
PASS http://127.0.0.1:8000/ready -> 503
PASS http://127.0.0.1:8000/health -> 200
Container fraggyapi-db-1 Healthy
PASS http://127.0.0.1:8000/ready -> 200
(exit 0)
```

The managed smoke starts native Uvicorn and `next start` after `pnpm build`, checks
response content as well as HTTP status, and stops its own web/API processes. It
restores the local DB in a finally block during outage checks. The final helper
port guard was also verified with a subsequent successful managed HTTP smoke.

### Browser checks

A temporary Playwright script used installed Chromium at desktop 1440×1000 and
mobile 390×844. It checked client-side filters, empty/reset state, detail navigation,
light/dark switching, mobile navigation, absence of horizontal overflow, and absence
of browser page errors. Screenshots were visually inspected; original CSS artwork
uses no third-party perfume images or remote fonts.

```text
PASS browser: desktop/mobile layouts, theme switch, filters, empty/reset,
details, navigation; no page errors
PASS primary link button contrast:
{'text': 'rgb(250, 249, 246)', 'bg': 'rgb(41, 46, 40)'}
```

This manual browser script was temporary; CI runs the retained unit and HTTP smoke
checks, not a claimed Playwright suite. Loading/error/not-found boundaries are
implemented; a real catalog/API-client failure is outside the synthetic UI phase.

### PostgreSQL and migrations

```text
$ docker compose up -d --wait
Container fraggyapi-db-1 Healthy
$ docker compose ps
fraggyapi-db-1 postgres:17-alpine Up (healthy) 127.0.0.1:5432->5432/tcp
$ .venv/bin/alembic -c apps/api/alembic.ini downgrade base
(exit 0; disposable project database)
$ .venv/bin/alembic -c apps/api/alembic.ini upgrade head
(exit 0)
$ .venv/bin/alembic -c apps/api/alembic.ini current
0001_foundation (head)
$ .venv/bin/alembic -c apps/api/alembic.ini check
No new upgrade operations detected.
$ docker compose exec -T db psql -U fraggy -d fraggy -Atc "SELECT tablename FROM pg_tables WHERE schemaname='public';"
alembic_version
```

Only migration history is created. Database credentials never enter frontend code.
Supabase-style connection settings, TLS guidance and a separate migration URL are
provided; no live Supabase credential or hosted connection was used.

### Ingestion, secrets, engineering rules and CI

```text
$ .venv/bin/python -c 'from workers.ingestion.registry import load_registry; [print(s["id"], s["enabled"], s["authorization_status"]) for s in load_registry()["sources"]]'
fragrantica False pending_review
parfumo False pending_review
basenotes False pending_review
wikiparfum False pending_review
perfume_society False pending_review
perfumemaster False pending_review
scentbase False pending_review
$ .venv/bin/python scripts/check_secrets.py
Scanned 83 working-tree files, 0 commits, 0 historical blobs; 0 findings
$ git ls-files | wc -l
0
$ git rev-list --all --count
0
$ git check-ignore .env .env.local apps/web/.env.local
.env
.env.local
apps/web/.env.local
$ rg '^##' AGENTS.md
## Boundaries and phase
## Conventions
## Migrations
## Collection and security
## Tests, documentation and completion
$ /tmp/fraggy-actionlint .github/workflows/ci.yml
(no output; exit 0)
$ test -s docs/adr/001-free-tier-hosting.md
(exit 0)
```

Actionlint 1.7.7 was downloaded from its official GitHub release and verified against
the release SHA-256 checksum file before execution. It found no workflow problems.
Local checks exercised the CI commands; GitHub-hosted execution remains unverified.
The secret scanner checks nonignored working-tree files and all reachable committed
blobs, printing only paths/counts. Default localhost credentials are documented and
explicitly allowed; this is heuristic scanning plus review, not a comprehensive
credential certification.

## Reusable cloud setup and remaining limits

Saved configuration draft fields: `install_script` runs `bash scripts/setup.sh` from
`/workspace/FraggyAPI`; `start_skill` captures Docker startup, Alembic upgrade, dev
startup, readiness checks and validation commands. Save confirmed `status: saved`.
The draft does not execute scripts, publish an environment snapshot or deploy an
application. Review/save the draft in environment settings, then publish the cloud
environment when desired. New-task restoration has not been independently tested.

Local database is healthy and retained. Temporary web/API smoke servers were stopped;
use `pnpm dev` to restart. No extra secrets are needed for local development.
The hosting ADR distinguishes verified documentation from untested deployment and
unverified provider eligibility. GitHub raw official sources were accessible after
public documentation hosts were blocked. Nothing grants commercial source rights:
all seven candidates remain pending review.
