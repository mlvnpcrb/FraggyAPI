# Phase 2D audit

Audit date: 2026-10-18 (UTC). Repository: mlvnpcrb/FraggyAPI.
Branch: `feat/phase-2d-attribution`. No Phase 2D merge is authorized.

## Phase 2C baseline and merge

PR #3 was OPEN/MERGEABLE at the approved head
`f79ba42fbba913529cecbdbf128e93566848bbaa`. Both required `checks` runs were
COMPLETED/SUCCESS:

- [PR checks](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39119055556)
- [Branch checks](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39119052776)

`gh pr merge 3 --merge --match-head-commit f79ba42fbba913529cecbdbf128e93566848bbaa`
merged normally as `ea597de77c7d66aebc1c3984c47ba29dae51849f`.
`git switch main && git pull --ff-only` fast-forwarded to that SHA.
Baseline `RUN_DB_TESTS=1 pnpm test` passed 162 backend + 15 frontend + 3 ingestion
= 180 tests. `pnpm build` passed. The feature branch was created afterward.

## Implemented boundaries

- Structured attribution lives in the existing trusted source-review JSON history;
  no new schema is necessary. Optional empty manifest additions are omitted from
  serialization so existing Phase 2C policy digests remain valid.
- Untrusted manifests still cannot authorize themselves. Human review separately
  approves storage, commercial redistribution, fields and supported attribution;
  record review and explicit field publication remain separate actions.
- All seven public endpoints add `attributions` to named/release DTOs. Credits
  contain public provider/license/text/links/copyright/disclosure/verification
  metadata and deduplicated relative field pointers, never private evidence.
- Multiple sources may contribute to one record without overwriting claims.
  Required credits accompany currently displayed matching grants; unsupported or
  incomplete obligations block publication. No images/descriptions/reviews added.
- Whole-source revocation, individual `unpublish`, re-review/license changes and
  stale canonical claims withdraw affected fields and credit paths. Re-review
  alone never resurrects grants. Production always excludes synthetic imports.
- Public request sessions use lazy REPEATABLE READ snapshots across policy/value/
  credit queries. CLI writers retain their previous isolation. No eager database
  checkout occurs before readiness's bounded query/error handler.
- Frontend credits appear beside home/catalog cards, details, brand cards and
  lookup/filter values. Plain-text escaping, safe separate external links,
  accessible sections and mobile wrapping preserve existing design.

## Verification evidence

The final uninterrupted local run passed all 232 tests with no skips (203 backend,
26 frontend, 3 ingestion). GitHub checks/PR links are recorded after actual remote
success.

| Check                          | Command/evidence                                                                                                         | Result                                                                                                                                                                     |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Full PostgreSQL test suite     | `RUN_DB_TESTS=1 pnpm test`                                                                                               | PASS; 203 backend + 26 frontend + 3 ingestion = 232; zero skipped                                                                                                          |
| Ruff / ESLint                  | `pnpm lint`                                                                                                              | PASS; both workspace tasks and workers/scripts                                                                                                                             |
| Python / TypeScript            | `pnpm typecheck`                                                                                                         | PASS; mypy 22 source files; Next typegen + tsc                                                                                                                             |
| Build                          | `pnpm build`                                                                                                             | PASS; Python compile and Next production routes                                                                                                                            |
| Formatting                     | `pnpm format:check`; `.venv/bin/ruff format --check apps/api scripts workers`                                            | PASS; Prettier and 54 Python files                                                                                                                                         |
| Migration integrity            | `alembic -c apps/api/alembic.ini upgrade head`, `current`, `check` using `.venv/bin/alembic`                             | PASS; `0004_quality (head)`; `No new upgrade operations detected.`                                                                                                         |
| Operational recovery           | `.venv/bin/python scripts/smoke.py --manage-services --check-db-outage --demo-catalog`                                   | PASS after the lazy isolation fix; ready 200 → 503 → 200; health 200 during outage; Compose restored healthy                                                               |
| Browser pilot                  | Owned local API + production Next server, original fictional data in a disposable migrated database, Chromium 1440/390px | PASS; home/directory/UUID detail/brands; visible provider/license/disclosure, safe links, no nested links/overflow/client exceptions; withdrawal reflected on new requests |
| Source safety                  | Registry assertion and PostgreSQL `WHERE source_type = 'website'`                                                        | PASS; seven rows, all `enabled=f`, authorization/licensing `pending_review`                                                                                                |
| Secrets                        | `.venv/bin/python scripts/check_secrets.py`                                                                              | PASS; zero findings in working files and reachable history                                                                                                                 |
| Diff / generated files         | `git diff --check`; intended-file review                                                                                 | PASS; private manifests/reports, DB volumes, `.env`, caches and build outputs excluded                                                                                     |
| Dependencies / migration scope | Lockfiles, dependency manifests, applied migrations, registry and adapters unchanged                                     | PASS; no new dependency/service/paid resource                                                                                                                              |
| GitHub checks                  | Actual remote runs, linked below after completion                                                                        | Pending                                                                                                                                                                    |

An initial frontend test expected an isolated text node where markup intentionally
combines provider and credit text; assertions now check accessible region content
and still verify escaping/safe links. The initial outage run caught eager session
checkout returning 500 rather than readiness 503; lazy factory isolation fixed it.
An overlapping outage interrupted one migration test with ConnectionResetError;
the complete suite is rerun with PostgreSQL continuously available. No assertion
was disabled. The only existing test changes add the new DTO property and update
the fixed query budget from five to six; all prior 180 test cases remain.

New tests exercise attributed publication, seven endpoints/privacy, multiple
providers, field tracing, deduplication, missing metadata, unsafe URLs, unsupported
obligations, human acceptance, source/field revocation, changed licenses, stale
claims, expired/future verification, synthetic production exclusion, old manifest
digest compatibility, constant query counts and fail-closed credit overflow.
Actual CLI tests cover all three input formats, authorization → stage → canonical
review → public fields → API → withdrawal; a separate real PostgreSQL test proves
request snapshot consistency. Frontend tests exercise credits through pages/cards/
filters, empty arrays, multiple entries and hostile markup/links.

## Source and operating limitations

All seven candidates remain pending_review/disabled. Manufacturer/open dataset/
partnership categories have no verified source grant. The readiness document
records questions, not legal clearance; no current external terms/robots/license
was independently verified and no third-party data was fetched/imported.

The operator is trusted via local OS/database access; there is no authenticated
admin UI/HTTP write API or production operator workflow. Human review must establish
supplier authority and actual legal coverage. Supported obligations are adjacent
plain-text credits with safe HTTPS links and modification disclosure. Other
placements/conditions are blocked; the 365-day verification policy requires renewed
review. Requests cap active file policies at 1,000 and candidate credit claims at
20,000; overflow fails closed. Limits are suitable for this bounded pilot, not a
claim of large-catalog capacity testing. Already delivered client copies cannot be
recalled; consumers must refresh and preserve credits.

No separate Fraggy PWA code, subscriptions, deployment, paid service, live scraping,
automatic licensing approval or Phase 3 functionality was added. Local operating
target remains ₱0/month. Existing free-first hosting decisions remain unchanged.
The prior documented unpatched dev-only `braces` advisory is unchanged; no new
dependency was introduced and it was not suppressed by this phase.

See [attribution contract](attribution-contract.md),
[source readiness](licensed-source-readiness.md) and
[pilot workflow](pilot-import-workflow.md) before an explicitly authorized real
pilot. Phase 2D must remain an unmerged review PR until separately approved.
