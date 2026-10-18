# Phase 2E audit

Review date: 2026-10-18 (Philippine calendar date). Repository:
`mlvnpcrb/FraggyAPI`. Branch: `feat/phase-2e-catalog-data`.
Phase 2E must remain unmerged pending approval. No Phase 2F work is implemented.

## Approved baseline

Before merging PR #4, GitHub reported OPEN/MERGEABLE, exact approved head
`317d8c8d70cbf8326a64e14b77af7a388ce82a58`, and both required checks SUCCESS:
[PR run](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39121936149) and
[branch run](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39121932183).
`gh pr merge 4 --merge --match-head-commit 317d8c8d70cbf8326a64e14b77af7a388ce82a58`
created normal merge `e87ba1a1e1ebd43455ed719b0c0733da691a4b18`.
`git switch main && git pull --ff-only` updated the existing checkout. The merged
baseline passed all 232 tests and build before creating the Phase 2E branch.
No unmerged-branch development, force push or unrelated change discard occurred.

## Source/dataset findings

[Source assessment](phase-2e-source-assessment.md) records all requested access,
authentication, automation, robots, storage, commercial/API redistribution,
attribution, rate/download, quality, cost and direct-permission questions.
Seven websites and Wikidata policy requests were blocked by the environment proxy,
not by verified website policies. Those facts remain explicitly unverified.
Research network domains are saved in an environment draft; saving is not live
access or publication of the development environment.

Accessible GitHub metadata/license research found FragDB's noncommercial sample
terms and explicit commercial prohibitions on database redistribution/resale.
That candidate is incompatible with the intended commercial database API under
observed terms. A separate research repository's MIT Software license does not
prove upstream review-data rights. Other datasets remain pending verification;
manufacturer/distributor partnerships require an applicable verified grant.
Commit-pinned evidence and review date are in the assessment. No genuine starter
dataset is cleared. No samples/catalog/review records were downloaded or imported,
no source contacted, and no paid license bought. The existing parser/review/rights
workflow is ready for a separately authorized 100–300-record local starter pilot.
All seven adapters remain disabled/pending review in configuration and PostgreSQL.

## Implementation

`pnpm catalog:quality` reads a PostgreSQL-enforced REPEATABLE READ, READ ONLY
snapshot and emits JSON or text. It checks identities, concentrations, year
plausibility, aliases, duplicate candidates, versions/flankers, source conflicts,
provenance, note/foreign-key relationships, safe URLs, credits, rights and stale
scalar claims. It reports totals, missing percentages, source coverage, reviewed
credit coverage, publication eligibility and blockers. Samples and analysis caps
are explicit; incomplete analysis cannot masquerade as a clean gate.
No raw names, URLs, claim values, snapshots, agreements, reviewer identities or
legal evidence are exposed in reports. UUIDs/statuses/counts/categories suffice
for local operators; private detailed review remains in existing trusted commands.

The explicit synthetic benchmark creates/drops only UUID-owned local disposable
PostgreSQL databases, migrates them, generates mixed-concentration/version/bottle/
note/provenance fixtures and measures real catalog query/projection/serialization.
No app database reset or migration semantic edit is needed.

Benchmarks exposed duplicate-credit work/cap failures and a broad-filter statement
timeout (confirmed by PostgreSQL timeout logs). Authorized contributions are now
deduplicated in SQL and field paths unioned before DTO construction. Note/accord
visibility is checked independently while membership/grants remain on the
same release. A materialized UUID-only set evaluates eligible releases once per
SQL statement, avoiding a pathological repeated plan on un-analyzed imports. Distinct providers and rights checks remain intact. The full prior
232 tests are preserved; no public DTO/route or separate PWA code changed.

A quality-report false positive on a valid nullable composite FK was corrected:
checks now compare the full FK tuple and honor PostgreSQL MATCH SIMPLE null
semantics. The seed regression asserts zero relationship errors. No constraint
was disabled to create or hide a defect. A later full recheck exposed a slow filter
plan on an un-analyzed shared test catalog; its owned query was cancelled for
diagnosis, the eligible-release set was materialized and the full suite passed
again. The new fixture regression has a statement timeout guard, not an ANALYZE
that conceals this import state.

## Local results

| Check                 | Command/evidence                                                              | Result                                                                                                                                     |
| --------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Full PostgreSQL tests | `RUN_DB_TESTS=1 pnpm test`                                                    | PASS; 227 backend + 26 frontend + 3 ingestion = 256; no skips                                                                              |
| Python/frontend lint  | `pnpm lint`                                                                   | PASS; Ruff/ESLint and workers/scripts                                                                                                      |
| Strict types          | `pnpm typecheck`                                                              | PASS; mypy 27 source files; Next typegen/TypeScript                                                                                        |
| Build                 | `pnpm build`                                                                  | PASS; Python compile and existing Next production routes                                                                                   |
| Formatting            | `pnpm format:check`; `.venv/bin/ruff format --check apps/api scripts workers` | PASS                                                                                                                                       |
| Alembic               | upgrade head/current/check with `apps/api/alembic.ini`                        | PASS; `0004_quality (head)`; no new upgrade operations                                                                                     |
| Quality CLI           | JSON and text against original local demo data                                | PASS; complete report, no mutations; actual findings below                                                                                 |
| Benchmarks            | 100 / 1,000 / 10,000, three scenarios, five timed requests each               | PASS; all 45 final samples, seven SELECTs each, no failures/timeouts                                                                       |
| Browser end-to-end    | Owned CLI/import/API/Next pilot in disposable DB, Chromium 1440/390           | PASS; four routes, required credits, safe links, no nested links/overflow/client errors; field/source withdrawal reflected on new requests |
| Runtime recovery      | Owned API/frontend smoke with Compose outage/recovery                         | PASS; ready 200 → 503 → 200, independent health 200; PostgreSQL restored healthy                                                           |
| Secrets/diff          | `scripts/check_secrets.py`; `git diff --check`                                | PASS; zero findings; intended project files only                                                                                           |
| Scope/dependencies    | Applied migrations, dependencies/locks, adapter/registry files unchanged      | PASS; no paid/production/real-data/collection/billing/PWA changes                                                                          |
| GitHub CI             | Actual remote workflows, linked after success                                 | Pending remote verification                                                                                                                |

New tests cover quality categories, normalized duplicate distinctions, EDT/EDP/
Parfum/version/year/related-name cases, missing percentages, existing conflicts,
source/field withdrawal, stale claims, missing/unsafe credits, sanitized URLs,
PostgreSQL read-only rejection, bounded report truncation, real JSON/text CLI,
production/remote refusal and the attributed 100-record benchmark query graph.
A 300-record original fictional starter test dry-runs, stages three batches,
manually reviews/publishes three distinct concentrations, reports 297 pending
records, and verifies production exclusion. Existing import
authorization→dry-run→stage→manual review→publication→API regressions
remain; the separate actual browser pilot validates frontend and revocation.

The unchanged original local demo report is complete with 2 houses, 4 fragrances,
6 releases, 4 notes, 1 accord and 2 source records awaiting review. It reports
**0 errors, 9 warnings and 5 informational observations**: two conflicting source
claims, missing private variant/perfumer/family provenance, unknown concentrations/
note position and version information. These are honest fixture quality findings,
not disabled checks or fabricated corrections. Development public eligibility is
4; production is 0 because the data is synthetic. Seven website sources remain
pending; no source is legally cleared by a clean quality report.

## Performance and remaining limits

See [measured performance and EXPLAIN evidence](phase-2e-performance.md).
At 10,000 fictional fragrances, observed medians were 2212.763 ms search,
3645.450 ms combined filter and 2352.527 ms pagination. Each has seven SELECTs;
local warm sequential measurements exclude HTTP/browser overhead. The largest
fixture has 21,000 releases, 42,000 variants and 235,000 claim rows. Credit sorts
still spill and multi-second rights work remains material. This does not establish
production capacity or justify an SLA. Generated raw plans/reports stay ignored.

Quality analysis is bounded; prefix/name similarity does not prove identity.
Report counts can overlap and legal correctness requires human evidence review.
No approved genuine dataset is available; current website policies remain
unverified because of the proxy restriction. Existing dev-only braces advisory
is unchanged; no dependency was added or suppression introduced. No hosted/pooler,
concurrent production workload or public-client withdrawal rollout was tested.
Already delivered client copies require refresh after revocation.

Phase 2F should follow Phase 2E review/merge and start with one source whose exact
access/storage/commercial redistribution/credit rights are verified, preferably
an official API or supplied feed. Add modular adapters, schedules, secure auth,
rate limits, bounded retry/backoff, incremental checkpoints, idempotent ingestion,
manual review, provenance, rights-aware publication, monitoring and revocation.
Resolve the measured query/capacity limits before promising public scale. Do not
activate any of the seven website adapters based on robots or availability alone.
Local development remains ₱0/month; no production deployment or paid service.
