# Phase 2A database verification

Date: 2026-10-18. Baseline: `9f79482f1e44ebfe9d6eca76d530339f249cec71`.
Branch: `feat/phase-2a-database`. Scope: local database foundation only.

## Implementation evidence

| Requirement                  | Result                            | Evidence                                                                                                                                                                                                                                                                                                                                |
| ---------------------------- | --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Normalized catalog           | PASS                              | Twenty SQLAlchemy tables; UUID identities, lines/releases/variants, composition, rights and provenance separated                                                                                                                                                                                                                        |
| Migration ordering           | PASS                              | Unchanged 0001 → 0002_catalog → 0003_search → 0004_quality; no startup create_all                                                                                                                                                                                                                                                       |
| Constraints                  | PASS                              | Actual PostgreSQL inspection: 30 foreign keys, 57 check constraints, 92 indexes excluding Alembic; RESTRICT policies and unique semantic keys tested                                                                                                                                                                                    |
| Search preparation           | PASS                              | Brand/name/FK/year/concentration indexes, native name TSVECTOR/GIN, source sync windows; pg_trgm evaluated and deferred, no external engine                                                                                                                                                                                             |
| Synthetic seed               | PASS                              | Explicit opt-in, 52 deterministic fixture IDs across 20 tables, idempotency and edited-row preservation tested; production CLI refused                                                                                                                                                                                                  |
| Unknown/conflicting values   | PASS                              | Null concentration/year, unknown note placement, conflicting 2020/2021 claims retained; no canonical source winner                                                                                                                                                                                                                      |
| Source/media rights          | PASS                              | Payload retention and approved redistribution require separate declared evidence; media paths gated; no image downloaded                                                                                                                                                                                                                |
| Real PostgreSQL tests        | PASS                              | 52 API/backend tests including constraints, FK deletion, migration round trips and normalization-collision atomic rollback                                                                                                                                                                                                              |
| Existing tests               | PASS                              | 14 original API tests preserved within the 52; 3 web + 3 ingestion tests also passed; 58 total, no skips with RUN_DB_TESTS=1                                                                                                                                                                                                            |
| Lint/types/build             | PASS                              | pnpm lint/typecheck/build/format:check passed; strict mypy checks 10 application files                                                                                                                                                                                                                                                  |
| Application compatibility    | PASS                              | Existing API/version metadata unchanged, frontend mocks unchanged, real HTTP route/content smoke and outage/recovery passed                                                                                                                                                                                                             |
| Disabled sources             | PASS                              | Seven candidate policy rows pending/disabled in demo; all seven adapters retain unconditional live-collection block                                                                                                                                                                                                                     |
| Secret/generated file checks | PASS                              | No secret-pattern matches; only intended source/docs/config files prepared for Git; dependency lockfiles unchanged                                                                                                                                                                                                                      |
| GitHub CI / PR               | PASS (implementation CI); PR open | [Branch CI passed](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39108389256) and [PR CI passed](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39108419433) on `d21814604f2541c51a21d6926c3c5df15be64e27`; [PR #1](https://github.com/mlvnpcrb/FraggyAPI/pull/1) remains unmerged. Final head checks are verified separately. |

The implementation workflow was independently checked through GitHub Actions: status
`completed`, conclusion `success`, matching the implementation SHA above. This
documentation update records that evidence; its final PR/head checks are verified
separately before task completion. Live branch CI is available at:
https://github.com/mlvnpcrb/FraggyAPI/actions?query=branch%3Afeat%2Fphase-2a-database

## Commands and output

All commands run from `/workspace/FraggyAPI` unless otherwise noted.

```text
$ pnpm install --frozen-lockfile
Already up to date
$ docker compose up -d --wait
Container fraggyapi-db-1 Healthy
$ .venv/bin/alembic -c apps/api/alembic.ini upgrade head
(exit 0)
$ .venv/bin/alembic -c apps/api/alembic.ini current
0004_quality (head)
$ .venv/bin/alembic -c apps/api/alembic.ini check
No new upgrade operations detected.
$ .venv/bin/python -m fraggy_api.seed --allow-demo-data
Synthetic fixtures prepared (52 stable IDs); existing rows preserved
$ .venv/bin/python -m fraggy_api.seed --allow-demo-data
Synthetic fixtures prepared (52 stable IDs); existing rows preserved
```

```text
$ pnpm lint
API Ruff: All checks passed!
ESLint: exit 0
Workers/scripts Ruff: All checks passed!
$ pnpm typecheck
Web: Types generated successfully; tsc --noEmit exit 0
API: Success: no issues found in 10 source files
$ RUN_DB_TESTS=1 pnpm test
API collected 52 items: 52 passed in 15.69s
Web: Tests 3 passed (3)
Ingestion: Ran 3 tests; OK
$ pnpm build
Next.js 16.4.2: Compiled successfully
Generated 11 static pages; required dynamic routes built
Tasks: 2 successful, 2 total
$ pnpm format:check
All matched files use Prettier code style!
```

The integration fixtures create random `fraggy_test_*` local databases, migrate
them to head, and roll back individual tests. Migration tests create a separate
random database, upgrade from 0001 through head, downgrade 0004 to 0003 and back,
downgrade the catalog to 0001 and re-upgrade, then compare schema fingerprints and
run Alembic check. No destructive round trip targets the application database.

The historical 0003 collision test inserts two distinct names whose keys collide
under corrected 0004 whitespace normalization. Upgrade must fail transactionally:
both original names, the old schema and the 0003 version remain intact. This proves
that the corrective migration does not silently merge or remove existing entities.

Read-only inspection of the prepared local application database:

```text
catalog_tables 20
foreign_keys 30
check_constraints 57
indexes 92
candidate_sources_disabled 7
test_databases_remaining 0
```

```text
$ .venv/bin/python scripts/smoke.py --manage-services --check-db-outage
/health 200; /ready 200; /api/v1 200; /docs 200
Frontend /, /fragrances, two details, /brands, empty search: 200 with expected content
Unknown fragrance: 404
Compose db stopped: /ready 503, /health 200
Compose db restarted healthy: /ready 200
(exit 0; temporary API/web processes stopped)
$ .venv/bin/python scripts/check_secrets.py
0 findings
```

## Reviewed limitations

- No Phase 2B catalog endpoints, public export filter, PWA client, automatic matching,
  ingestion job execution or live collection is implemented. Existing version metadata
  remains unchanged for compatibility. Database tables do not grant commercial rights.
- Permission/evidence strings are declared metadata; trusted writers must verify
  actual terms, storage/reuse grants, expiry and revocation. The DB cannot prove a
  legal agreement is valid. Future retention/export logic must check rights per field.
- Native FTS is implemented; typo-tolerant pg_trgm search is deferred. Index performance
  was not benchmarked at production scale; review index/write overhead with real data.
- Multi-hop reformulation-cycle prevention, GTIN checksum verification and a complete
  ISO country taxonomy belong to later validated write services; current DB enforces
  same-line/non-self references, GTIN format and two-letter country shape.
- UUIDs are generated by application writers; direct SQL must supply them. ORM updates
  maintain updated_at; direct SQL writers must do so explicitly.
- Supabase/PostgreSQL 15+ compatibility is documented but not tested on a cloud project.
  Only local Docker PostgreSQL 17 was used. No extension or paid service was installed.
- Migration downgrades remove added data/columns; do not use them as a production reset.
  0004 rebuilds derived keys/indexes under transactional locks; large populated tables
  need a separate operational plan. Fresh key collisions intentionally stop upgrade.
- The prior development-only braces advisory remains as documented in the Phase 1C
  review. No dependency or lockfile changes were needed for Phase 2A.

## Phase 2B recommendation

After PR review/approval, implement rights-aware read-only versioned catalog/search
endpoints with explicit Pydantic allowlists, stable UUID/slug lookup, bounded paging,
query-plan tests and a separate Fraggy PWA client. Do not expose payloads, claim
licensed images, automatically merge entities, activate collectors or deploy merely
because the schema exists. This task does not start Phase 2B or merge the PR.
