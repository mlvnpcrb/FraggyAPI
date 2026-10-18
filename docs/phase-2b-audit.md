# Phase 2B verification audit

Date: 2026-10-18. Scope: merge approved Phase 2A, then implement a read-only,
rights-aware catalog and Next.js integration. No Phase 3, collection, production
hosting, paid resource or cloud Supabase change is included.

## Phase 2A baseline and merge

PR [#1](https://github.com/mlvnpcrb/FraggyAPI/pull/1) was OPEN, MERGEABLE and unchanged
at `36921fb1c5a614886aae91325d92b3597a693c81`; its two final checks were SUCCESS:
[PR workflow](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39108606213) and
[branch workflow](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39108604395).
It was merged normally using `gh pr merge --merge --match-head-commit`; no force
push was used. Merge commit: `2944ebdf5f0d342a13540dcf071837f022e3c761`.
`git switch main` and `git pull --ff-only` brought the checkout to that commit.

Revisions `0002_catalog`, `0003_search` and `0004_quality` were present. Before the
new branch, healthy Compose plus `RUN_DB_TESTS=1 pnpm test` passed 52 backend,
3 frontend and 3 ingestion tests. `pnpm build` passed (valid baseline cache reuse).
The new work is on `feat/phase-2b-catalog-api`. Phase 2B must remain unmerged until
separately approved.

## Implementation review

- Seven GET routes under `/api/v1`: brands list/detail by slug, fragrance list/detail
  by UUID, search, notes and accords. Explicit page/item/error schemas document
  bounds, ranked FTS, deterministic tie-breakers and same-release filter semantics.
- Public field checks require current-value approved claims plus record and source
  permissions. Selection alone never authorizes publication. Filters use the same
  checks, preventing private-field count inference. Restrictions fail closed.
- No source payload, descriptions, reviews, credentials, licensing evidence,
  media, ingestion runs or review work appear in public DTOs. Synthetic grants
  require an explicit non-production setting. Real publication checks are tested
  with invented test-only licensing evidence, never third-party content.
- SQL-bound parameters and escaped LIKE patterns; validated input sizes and bounded
  pages/nested summaries. Five SQL statements per nonempty catalog page are verified
  at both page sizes 1 and 50. No lazy relationship access. Statements have a
  configurable PostgreSQL timeout; Next.js requests time out in 5 seconds.
- Typed Next.js server requests replace all frontend fixtures. URL GET forms provide
  search/brand/concentration/year/note/accord/sort controls and pagination. Original
  bottle illustrations remain. Demo labels, empty/error/retry/loading and UUID 404
  handling are preserved. Server-side API base URL has no privileged credentials.
- No dependency/lockfile changes or new schema migrations. Existing migration
  fingerprints/round trips remain tested. Seven adapters remain disabled/pending.
  Existing free-tier hosting ADR is preserved; local tools remain free.

## Validation evidence

The following are current local results; remote GitHub evidence is separate below.

| Command                                                                      | Result and supporting output                                                                                                    |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `docker compose up -d --wait`                                                | PASS — `fraggyapi-db-1 Healthy`                                                                                                 |
| `pnpm lint`                                                                  | PASS — API/web lint and ingestion/scripts Ruff `All checks passed!`                                                             |
| `pnpm typecheck`                                                             | PASS — mypy `Success: no issues found in 12 source files`; Next route generation and strict tsc exit 0                          |
| `RUN_DB_TESTS=1 pnpm test`                                                   | PASS — 94 backend, 15 frontend, 3 ingestion tests; 112 total, no skipped tests                                                  |
| `pnpm build`                                                                 | PASS — Next.js production compilation/typecheck; API compileall; four dynamic catalog pages                                     |
| `pnpm format:check`                                                          | PASS — `All matched files use Prettier code style!`                                                                             |
| `alembic -c apps/api/alembic.ini upgrade head`                               | PASS — exit 0; no Phase 2B DDL                                                                                                  |
| `alembic -c apps/api/alembic.ini current`                                    | PASS — `0004_quality (head)`                                                                                                    |
| `alembic -c apps/api/alembic.ini check`                                      | PASS — `No new upgrade operations detected.`                                                                                    |
| `python scripts/smoke.py --manage-services --check-db-outage --demo-catalog` | PASS — API/docs/catalog/web/search/detail, empty search, HTTP 404, readiness 200→503→200; health 200 during outage; DB restored |
| `python scripts/check_secrets.py`                                            | PASS — working-tree/history scan, `0 findings`                                                                                  |
| `git diff --check`                                                           | PASS — no whitespace errors                                                                                                     |

Backend coverage adds public endpoint shapes, ranking/exact match, filter conjunction,
lookup paging, pagination bounds, malformed/unknown IDs, invalid enums/extra input,
empty catalogs, source/record/link/field revocation, stale values, production demo
exclusion, mixed licensed/synthetic field labeling, current-value identity permission,
nested release bounds, sanitized 500,
OpenAPI, no-store and fixed query counts. Existing schema/deletion/migration tests
remain intact. Frontend tests cover real client request construction, server pages,
UUID detail/null fields, API failures, synthetic labels, forms and pagination.

Runtime verification found and fixed a real defect: the old global loading boundary
caused unknown dynamic details to stream HTTP 200 before rendering not-found.
Directory/brand loading boundaries are now scoped away from the detail page;
unknown malformed and valid UUID details return actual HTTP 404. Smoke port probes
now tolerate TIME_WAIT from a prior owned run while rejecting active listeners.

Manual Chromium verification also passed at 1440px desktop and 390px mobile:
API-backed filter submission, stable UUID detail navigation, synthetic labeling,
no horizontal overflow, empty/reset flow, actual missing-UUID 404 and API-outage
error/retry UI. There were no client exceptions. Screenshots stayed in `/tmp` and
are not project artifacts. Source status checks confirmed 7/7 configuration and
7/7 database candidate sources disabled and pending review. A static browser-bundle
search found no database credential literals or server API configuration names.

Reusable cloud `start_skill` instructions were updated and saved as a draft for
review, covering UUID routes, no-store API client, optional synthetic grants and
current smoke commands. Installation/network/credential settings were preserved.
Saving this draft does not publish an environment or deploy production.

Existing ingestion Python files were also normalized with Ruff formatting only;
no adapter logic or source activation behavior changed. `ruff format --check
apps/api scripts workers` reports `39 files already formatted`.

## GitHub CI

The workflow runs frozen setup/dependency installation, Compose, backend/frontend
checks/tests, production build, migration integrity, explicitly opted-in demo HTTP
smoke and database outage recovery, and secret scanning. Branch push and PR checks
are configured for this feature branch.

Actual GitHub Actions passed for implementation commit
`5a57ea41368876abf524a4cce77ae18b7b04f4be`:

- [PR workflow 39110262638](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39110262638): SUCCESS.
- [Branch workflow 39110242557](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39110242557): SUCCESS.

The follow-up strengthens synthetic labels for mixed licensed/demo fields and
relationships, with a regression assertion that production hides the synthetic
scalar while retaining the licensed identity. All 112 local tests still pass.
The [Phase 2B PR #2](https://github.com/mlvnpcrb/FraggyAPI/pull/2) checks panel is the
authoritative result for subsequent/final feature heads; completion requires a
successful actual workflow on that exact head, reported separately in the PR and
completion report. Earlier successful runs alone never validate a newer commit.
The Phase 2B PR remains open and unmerged.

## Limitations and next approval boundary

- Real sources have no approved evidence; all seven remain pending/disabled. The
  production catalog therefore has no licensed imported dataset yet. Operator
  review of actual legal evidence is still required; status strings do not prove law.
- No real media, descriptions, variants/perfumers DTOs, writes, ingestion, automatic
  matching, subscriptions, API keys, rate-limit gateway or separate PWA edits.
- Full-text search has no typo tolerance/accent folding/aliases. `pg_trgm` is deferred.
  Large-data latency/plans/load, hosted PostgreSQL and deployment are not tested.
- Offset results are live rather than snapshot-consistent and stop at 10000.
  Release summaries stop at 20 (flagged); note/accord summaries stop at 50.
  UI filter menus show the first 50 taxonomy/brand rows, with one note/accord per
  form; API clients can use paginated lookup and repeat note/accord UUIDs.
- No public caching/offline redistribution contract: no-store is intentional for
  rights revocation. Stable UUID user references must tolerate later 404s.
- The previously documented unpatched development-only `braces` advisory remains;
  no dependencies changed or advisory suppressions were added in Phase 2B.

Ready for Phase 2B code review after actual GitHub checks pass. No automatic merge,
production deployment or Phase 3 work is authorized by this completion report.
