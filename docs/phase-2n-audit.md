# Phase 2N local validation and measurements

2026-10-20 (Asia/Manila). Branch: `feat/phase-2n-multisource-pilot`, based on
Phase 2M `32821aa761c98a84d0179ba6c473c3e70c11fefa`.

## Scope and controls

Working additions: bounded missing/stale-field planning; explicit local admission
through existing deduplicated intents; per-field original/normalized evidence,
missing/conflicting claims and manual review explanations. Durable review keeps
references/states rather than duplicating raw values; current rights checks precede
reconstruction of richer reports. No canonical writes, automatic claim selection,
provider activation, schedule or public enqueue route. Source counts denote distinct
supplied source identities, not proof of independent ownership or corroboration.

No website, demo bundle, Vercel config, source registry, Open Beauty Facts parser,
dependency or lockfile changes. PRs #8–#13 were observed open through read-only
GitHub inspection. No push/PR/deployment/merge occurred. No real data was requested,
imported or published; no images acquired and no paid resources provisioned.

## Reproducible commands

```bash
RUN_DB_TESTS=1 pnpm exec turbo run test --force
.venv/bin/python -m unittest discover -v
pnpm lint
.venv/bin/ruff format --check apps/api scripts workers
pnpm typecheck
pnpm format:check
pnpm exec turbo run build --force
.venv/bin/alembic -c apps/api/alembic.ini upgrade head
.venv/bin/alembic -c apps/api/alembic.ini current
.venv/bin/alembic -c apps/api/alembic.ini check
.venv/bin/python scripts/check_secrets.py
.venv/bin/python scripts/smoke.py --manage-services --check-db-outage --demo-catalog
.venv/bin/python scripts/benchmark_preview.py --search-records 10000 --repeats 10 --warmup 1 --output data/reports/phase2n-validation/search-planning-benchmark.json
```

Check output stays ignored in `data/reports/phase2n-validation/`. Tests and
benchmarks use existing UUID-owned disposable database helpers, never reset the
application database, and remove owned databases. Smoke restores PostgreSQL healthy
and stops only owned application processes.

## Search and planning measured separately

Final checks passed:

| Check                                   | Actual outcome                                                                                                           |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Forced full tests with PostgreSQL       | 460 backend passed in 124.72 seconds; 63 frontend passed                                                                 |
| Ingestion unittest suite                | 3 passed; total 526, preserving all 517 predecessor tests                                                                |
| Lint and Python formatting              | All checks passed; 113 Python files formatted                                                                            |
| Types                                   | Strict mypy passed on 54 source files; TypeScript passed                                                                 |
| Prettier and forced production build    | Passed                                                                                                                   |
| Alembic upgrade/current/check           | Head `0008_search_typos`; no new upgrade operations detected                                                             |
| Migration upgrade/downgrade regressions | Passed within full PostgreSQL suite                                                                                      |
| Runtime/outage/recovery smoke           | Website routes and unknown 404s passed; `/ready` 200 → 503 → 200, `/health` 200 during outage; database restored healthy |
| Heuristic secret scan                   | 258 working files / 42 commits / 437 historical blobs, zero findings before local commit                                 |
| Whitespace / protected-file review      | Passed; no changes to website, Vercel settings/config, registry, dependency locks or preserved OBF parser                |
| Phase 2N GitHub CI                      | NOT RUN: no push or PR authorized                                                                                        |

Nine new focused tests cover per-field independent sources, conflicting note
positions, concentrations, flankers/reformulations, partial fields, invalid input
bounds, future/stale verification, no-op fresh records, intent deduplication,
transaction rollback/replay and no canonical writes. Existing provider failure,
rate-limit/retry, rights/revocation, resumability and idempotency tests remain in
the full suite. A first-source private pilot is not declared ready to activate
solely because fictional tests pass.

Isolated development-host measurement after tests/build completed. Original-only
dataset: 10,000 fragrances, 100 brands, 21,000 releases, 42,000 variants, 235,100
provenance claims and 100 reviewed aliases. Search includes ASGI routing, real
PostgreSQL and rights-aware projections; excludes browser/socket/CDN time.

| Search scenario         | Median ms |  p95 ms |
| ----------------------- | --------: | ------: |
| Exact                   |   195.607 | 268.625 |
| Typo and brand          |   196.851 | 304.742 |
| Reviewed alias          |   176.936 | 298.748 |
| Concentration           |   348.154 | 435.348 |
| Lattafa Khamrah, absent |    39.023 |  43.783 |

Ten timed searches plus one warmup per scenario, 55 requests, zero errors. With ten
samples p95 is simply the largest timed observation, not a production SLA.
Concentration remains the slowest case; no performance improvement is claimed from
host/sample variation. Future plan/index/rights/count profiling is described in
[Phase 2M delivery notes](phase-2m-delivery-gate.md).

Pure planning for a missing-record snapshot with ten providers: **1,000 iterations,
0.0028 ms median / 0.0032 ms p95**, excluding file/JSON parsing and database access.
A separate ten-provider enqueue transaction measured **25.144 ms** once; this is
one observation, not a latency distribution or throughput result. Subsequent
explicit dispatch returned ten blocked intents and zero external requests. Search
never ran providers or waited for admission. No production/tens-of-thousands
throughput claim follows from this bounded test.

## Operational versus blocked

Publisher-documented OBF contract and existing reviewed-ID Wikidata parser are
operational offline; external endpoint compatibility/current rights remain
unverified. Fragrantica and Parfumo contracts are fictional fixtures. Official
brand providers require an actual named permitted feed. Other providers retain
unverified skeletons. All real collection remains disabled.

The local “Lattafa Khamrah” search returns zero because no genuine records have
been imported. Planning then reports missing fields and separate disabled provider
intents. With approved future collection, existing transport/leases/checkpoints
would stage each source independently, preserve conflicts, require identity/field
review and then separately authorized publication. This report does not pretend
that future genuine data or publication was demonstrated.

The [pilot approval package](phase-2n-pilot.md) defines proposed requests, limits,
private destination, 30-day content/90-day non-content retention and ownership-bound
rollback. Genuine coverage, overlap and the final 25 identities remain unverified.
No source has current verified permission for activation in this phase. Image and
gender fields are explicitly outside the new comparison contract. The previously
documented development-only `braces` advisory remains unresolved; secret/lint/build
passes are not full security clearance. GitHub CI is NOT RUN for Phase 2N because
no push or PR is authorized. The Vercel skip for Phase 2M does not cover Phase 2N.
