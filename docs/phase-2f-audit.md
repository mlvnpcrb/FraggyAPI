# Phase 2F audit

Review date: 2026-10-18. Branch: `feat/phase-2f-collection`.
Phase 2F remains unmerged pending review. No external collection was activated.

## Baseline verification and merge

PR #5 was OPEN/MERGEABLE at exactly
`3251d202deaafcb910b9745835c991cff3ac4003`, with both required GitHub workflows
successful: [PR](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39134900211)
and [branch](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39134895932).
`gh pr merge 5 --merge --match-head-commit 3251d202deaafcb910b9745835c991cff3ac4003`
created normal merge `5349179b0933e375f456fcfd528987b89fc7528a`.
`git switch main && git pull --ff-only origin main` fast-forwarded the existing
checkout. All 256 baseline tests passed before creating the Phase 2F branch.
No force push, unrelated-history overwrite or separate PWA change occurred.

## Delivered implementation

See [architecture](phase-2f-architecture.md),
[authorization](collector-authorization.md) and [operations](collector-operations.md).
Collector code implements strict source-policy/digest/expiry gates, exact endpoint
REST/JSON/CSV/embedded-JSON HTML adapters, pinned TLS/public-DNS validation, explicit
external opt-in, bounded responses/records/timeouts, durable request spacing,
transient retries/backoff/Retry-After, incremental pagination/watermarks/ETags,
page-atomic existing importer staging, content-digest change detection/idempotency,
disabled schedules, fencing leases, unique active-run prevention, recovery,
cancellation, bounded monitoring and pre-staging Phase 2E quality classifications.
Manual decisions and field publication remain independent existing commands.

Migration `0005_collection` adds the two collector control/history tables with
restricting foreign keys, status/count constraints, due index and partial unique
running index. Run audit data binds reviewed configuration, page response hashes,
existing ingestion-run UUIDs and committed checkpoints; source evidence retains
private collection approvals. No applied migration or dependency lockfile changed.
The original catalog seed remains opt-in and leaves collector tables empty.
Schema inventory tests are updated for the two additional tables/head while
preserving their original catalog, foreign-key, idempotency and round-trip checks.

## Synthetic demonstration and performance

`./.venv/bin/python scripts/demo_collection.py [--records 100|1000]` uses original
fictional metadata in UUID-owned disposable databases, a real loopback HTTP server
and real FastAPI ASGI routes. No external site or fragrance data is requested.

| Fictional records | HTTP pages, first run | HTTP requests, first + idempotent run | Total local seconds | Manually published | Left pending |
| ----------------- | --------------------: | ------------------------------------: | ------------------: | -----------------: | -----------: |
| 2                 |                     2 |                                     4 |               2.600 |                  2 |            0 |
| 100               |                     1 |                                     2 |               3.720 |                  2 |           98 |
| 1,000             |                    10 |                                    20 |              16.119 |                  2 |          998 |

All three demonstrations succeeded: scheduled run staged the original records;
rerun skipped every unchanged record; public catalog was empty before review;
explicit approval/publication exposed only two synthetic credited records; source
and collection revocation removed them and denied further collection. Two-record
canonical quality was complete with 0 errors, 1 warning and 4 informational
observations. Warnings are reported, not automatically corrected or suppressed.

Times are single local sequential runs, measured from database creation through
collection, idempotency, manual review/publication, API/quality checks and withdrawal,
excluding final database/server cleanup. They include migrations and do not measure
pure collector throughput, HTTP/browser API latency, concurrency, p95 or production
capacity. PostgreSQL 17 Compose, Python 3.12, unchanged 3-second SQL statement budget;
no local test/build job intentionally ran concurrently with these measurements.
No SLA or real-source performance claim follows. Generated JSON/logs remain ignored
or outside the checkout, and every demonstration database/server was removed.

## Validation status

All 307 tests passed locally: 278 backend, 26 frontend and 3 ingestion, preserving
all 256 baseline cases and adding 51 collector cases. The only original assertions
changed are schema inventories/head and the seed table inventory: both new collector
tables must remain empty after normal demo seeding. No assertion or permission
check was disabled. New tests cover all requested authorization, network denial,
rate/retry, pagination, malformed data, checkpoints, interruption, idempotency,
revocation, scheduling, concurrent-run and publication boundaries.

| Check                 | Command / observed output                                                                      | Result                                                                            |
| --------------------- | ---------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Full PostgreSQL tests | `RUN_DB_TESTS=1 pnpm test`; 278 + 26 + 3 passing                                               | PASS, no skips                                                                    |
| Lint                  | `pnpm lint`; Ruff and ESLint                                                                   | PASS                                                                              |
| Strict types          | `pnpm typecheck`; mypy 35 source files and TypeScript                                          | PASS                                                                              |
| Formatting            | `pnpm format:check`; Ruff format check, 73 Python files                                        | PASS                                                                              |
| Production build      | `pnpm build`; Python compile and Next production routes                                        | PASS                                                                              |
| Migrations            | Alembic upgrade/current/check; `0005_collection (head)`; `No new upgrade operations detected.` | PASS                                                                              |
| Operator startup      | `catalog:collect list` returned `[]`; quality command completed read-only                      | PASS, no collectors activated                                                     |
| Synthetic demos       | 2 / 100 / 1,000 records as measured above                                                      | PASS, zero external collection requests                                           |
| Runtime/outage        | Existing owned service smoke, after DB-dependent checks                                        | PASS: ready 200 → 503 → 200, health 200 throughout; Compose restored healthy      |
| Secrets/diff          | `scripts/check_secrets.py`, `git diff --check`                                                 | PASS: zero findings, clean diff; only intended project files                      |
| GitHub CI             | Actual final-head workflows and PR Checks tab                                                  | PASS on implementation head; final documentation-head checks remain authoritative |

The initial full run found two catalog inventory assumptions that needed to
account for new, deliberately empty collector tables; the final rerun passed.
The standalone demonstration initially assumed two records in a one-record input
fixture; it now creates explicit original fictional variations and passed all
three sizes. These were corrected failures, not skipped checks.

## Remaining boundaries

All seven website adapters remain disabled/pending, with no runtime registry edits.
No genuine source/dataset is approved. Phase 2E's blocked website/Wikidata policy
research and observed incompatible dataset terms remain unresolved. Grant review
records a human decision, not automatic legal verification; real collection needs
source-specific evidence, separately approved pilot activation, supported auth,
network/TLS validation and conservative frequency/field mapping.

HTML support is explicit embedded JSON, not arbitrary rendered-page extraction.
REST supports the documented cursor/since envelope; custom protocols need their own
reviewed adapter. Scheduling is local sequential polling with bounded due/history
lists; no hosted queue, paid scheduler, cron installation, deployment or production
load validation. In-flight requests can finish during cancellation but cannot stage
late pages after token/permission checks. Already distributed API copies require
client refresh after revocation. The separate Fraggy PWA is untouched.

## GitHub implementation verification

Implementation head `7bbf4affce3bf370283f7d7ffe269431480ac7bd` passed both actual
[PR workflow](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39138147325) and
[branch workflow](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39138095918).
The workflows verified dependency installation, PostgreSQL tests, lint, strict
Python/TypeScript checks, formatting, production build, Alembic integrity,
the standalone scheduled synthetic demonstration, runtime outage/recovery and
secret scanning. Only the failure-only diagnostics step was intentionally skipped.

The following documentation commit records those completed results. The PR Checks
tab and completion report identify the exact final head and its workflows; the
implementation run is not substituted for final-head validation. PR #6 remains
open/unmerged until explicitly approved. The saved environment startup instructions
also preserve disabled collection defaults; saving did not publish an environment,
activate network access, start a scheduler or install cron.
