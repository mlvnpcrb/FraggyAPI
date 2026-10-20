# Phase 2M — local search and provider-independent enrichment

Implementation review: 2026-10-19 (Asia/Manila). Local only; no push, PR, deployment,
Vercel setting changes, genuine records, image acquisition or paid services.

## Preserved work and ancestry

Checkpoint `59b3b03` preserves the unchanged Open Beauty Facts parser/tests,
first-real-source research and Vercel investigation. Phase 2M branch
`feat/phase-2m-search-enrichment` descends from that checkpoint and Phase 2L
`99737e199d4b4e8b1f8243d06e2febb9640a88cf`. PRs #8–#12 stay unmerged. No separate
PWA or website/Vercel demo source files are changed.

## Working search

The existing public catalog/search routes and rights-aware DTO projection are
reused. PostgreSQL `pg_trgm` GIN indexes select candidates; a bounded
`fuzzystrmatch` edit-distance recheck rejects weak trigram similarities. These are
bundled PostgreSQL extensions, not paid services/Python dependencies. Migrations
0007/0008 add reviewed aliases, indexes, intents and the helper function. An owner
must have permission to install both extensions; no weaker fallback is silently
enabled. Downgrades retain shared extensions but remove owned schema/function.

Brand and fragrance terms can match across their respective labels and aliases.
Aliases require current selected field claims, source/record rights and entity
links; a private alias cannot make a record discoverable. Alias text and evidence
are not added to public responses. Candidate intersections narrow numeric/longer
terms first, then public rights remain authoritative. Search never merges IDs.
Numeric identifiers and short terms remain exact words; longer words allow one or
two edits behind an indexed trigram prefilter. This is conservative typo tolerance,
not exhaustive edit-distance recall or translation inference.

EDP/EDT/EDC and explicit eau-de-* phrases are recognized as concentration filters;
Elixir is not invented as a canonical concentration. Conflicting explicit filters
return 400. Concentration/year and optional `size_ml`/`gtin` criteria must hold on
the same release, with size and GTIN on the same rights-approved variant. Releases,
flankers and reformulations retain their separate existing identities. Responses
preserve the existing public fields and release projection. A window count avoids
evaluating search twice; empty offset pages retain accurate totals via fallback.

GET search is read-only and imports no collector code. No intent is implicitly
created. External delays, access failures and source availability cannot delay a
search response. Explicit opt-in background admission is an independent operator
action, not a hidden side effect of arbitrary visitor queries.

## Working enrichment and evidence review

- `EnrichmentIntent` stores private bounded query/target metadata, a normalized
  request digest, provider identity, status, cooldown and linked CollectionRun.
  Unique provider/digest keys deduplicate concurrent requests. Different providers
  may enrich the same fragrance independently; concentration/variant distinctions
  participate in request identity. A variant cannot target an unrelated fragrance.
- `providers.py` overlays independent contract/capability metadata over existing
  adapters. Open Beauty Facts uses its official documented contract; Fragrantica
  and Parfumo retain explicitly fictional fixture contracts, not live parsers.
  Wikidata, official brand feeds and the seven original candidates remain distinct.
  A future provider needs its own reviewed contract/permissions; an unknown key
  never gains collection rights by being requested.
- Trusted `catalog:collect enrich-*` commands reuse the existing nonproduction,
  loopback database guard. `enrich-run` has no external-access switch. It reuses
  Collector claim/execute/finish, source authorization, leases, cancellation,
  retries, checkpoints, idempotent staging and run history. No new execution queue,
  daemon, paid service or recurring schedule is introduced. Intents are admission
  metadata, not a second leasing system. Expired collector leases can resume the
  same intent; abandoned run links are marked failed.
- Dispatch rechecks source-specific grants/expiry/revocation and source identity.
  A one-hour per-intent cooldown, existing source cooldown, one run/source and a
  four-attempt rolling daily source budget apply. Worst-case pages times retries
  are reserved conservatively; source-row locking prevents concurrent overspend.
  Every real dispatch is explicitly blocked in Phase 2M, even if another grant
  exists. Only already-reviewed original loopback fixtures may run. Query strings
  are never substituted into arbitrary provider URLs: the reviewed collector
  configuration fixes endpoint/scope. Source-specific search dispatch mapping
  remains an activation prerequisite, not an implemented live capability.
- `stage_provider_page` calls the existing staging pipeline. Trusted storage
  permission must cover normalized fields, observation-hash metadata and each raw
  `source_observation.FIELD`. Raw observations/provenance remain in SourceRecord,
  separate from canonical tables. A raw hash participates in revision identity;
  repeated data is idempotent and changed raw facts create a new revision.
  Unmappable observations are counted explicitly, not fabricated into records.
- `enrich-compare LEFT_UUID RIGHT_UUID` compares privately authorized observations
  per field and attaches idempotent reports to existing pending DataReviewQueue
  items. Values remain in their original source snapshots; missing/agreement/
  conflict states and Phase 2L identity evidence remain separate. Reports retain
  multiple source comparisons (bounded to 20, fail rather than truncate).
  Storage withdrawal blocks comparison; publication restrictions do not falsely
  prohibit authorized private review. No claim is automatically selected, no
  canonical field is overwritten, and nothing is published.

Private intent queries are operator data, not source records or routine logs.
Use an approved private retention/cleanup policy before exposing an enqueue flow
to users. No public enqueue/admin endpoint was introduced in this phase.

## Reproducible demonstration and measurement

```bash
.venv/bin/python scripts/benchmark_preview.py --search-records 10000 --repeats 10 --warmup 1 --output data/reports/phase2m-search.json
```

This extends the existing owned preview benchmark and load generator; it does not
create a competing fixture/benchmark engine. It creates, migrates, analyzes and
removes only its randomly named disposable local database. Original data: 10,000
fragrances, 100 brands, 21,000 releases, 42,000 variants, 100 reviewed aliases and
235,100 provenance claims. No imported genuine records/images.

Five scenarios cover exact, typo+brand, alias, concentration and the user-provided
“Lattafa Khamrah” query. The latter truthfully returns no local result; the demo
does not fabricate a genuine product. Separate background intents are then stored
for all provider candidates and blocked because no real collection is configured.
Tests additionally execute actual approved local HTTP fixture enrichment through
Collector, demonstrating concurrent deduplication, interruption recovery and manual
review staging with zero canonical writes.

Latency includes ASGI routing, real PostgreSQL, publication checks, credits/media
projection and serialization. It excludes browser/network/CDN latency. Ten timed
requests per scenario follow one warmup; the report records median, nearest-rank
p95, SQL counts, failures and cleanup. Final measured results and local check
outcomes are recorded below after validation. No production SLA is claimed.

Measured on the local development host, Python 3.12.14, after the full suite
finished (no concurrent test load):

| Search                             |     Median |        p95 |
| ---------------------------------- | ---------: | ---------: |
| Exact                              | 195.434 ms | 235.765 ms |
| Typo + brand                       | 225.485 ms | 320.940 ms |
| Reviewed alias                     | 208.713 ms | 282.961 ms |
| Concentration                      | 347.030 ms | 536.665 ms |
| Lattafa Khamrah, absent local data |  40.960 ms |  45.039 ms |

Zero errors across 55 requests including warmups. Positive results used eight
bounded SQL reads; the empty-result query used three. p95 is the largest of ten
timed samples, not a statistically established production tail. No internet or
database-throughput-at-scale claim follows from this fixture measurement. Search
still incurs rights/projection work; broader queries and larger real catalogs need
representative measurement before a production latency target can be promised.

The initial shared-load measurement was slower (exact median 352.846 ms,
concentration 400.838 ms). The isolated measurements above are the final benchmark
run; the difference is not evidence of a further algorithm change.

## Source coverage and rights remain independent of architecture

The [official Open Beauty Facts README at the reviewed revision](https://github.com/openfoodfacts/openbeautyfacts/blob/89fcee881b0fd205dc17e3e58b34228a1f0a6238/README.md)
publishes **100,000+ cosmetic products from 170 countries**. That is a publisher
claim about all cosmetics, not a verified perfume count or current live statistic.
Its taxonomy includes perfumes; the schema exposes identity/brand/quantity fields,
not a rich fragrance note/accord/perfumer catalog. No perfume-specific published
count was established from this evidence, and no discovery/product request was
made to manufacture a coverage claim. Twenty-five distinct usable perfumes remain
unverified. Open Beauty Facts is one candidate, never the canonical record owner.

OBF-specific terms/access/robots, precise ODbL/DbCL applicability, attribution and
derived-database/commercial API obligations remain unresolved. Other sources need
their own permissions, not inherited OBF/Wikidata rights. The preserved
[optional 25-record pilot](first-25-source-decision.md) remains separate; fresh
rights/access verification, monitored contact where required, exact approved
scope/budget/destination/retention and explicit activity approval precede any live
request. Images and publication need independent approval.

No remote CI is triggered: pushing could invoke the existing Vercel integration.
Before any push/PR, obtain explicit approval for delivery with a verified safe
deployment-control path. This task changes no Vercel settings and activates no
source, schedule, import of genuine data or production deployment.

## Final local validation

Completed on 2026-10-19; output artifacts remain ignored under
`data/reports/phase2m-validation/`.

| Check                                                                 | Actual result                                                                                                                    |
| --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `RUN_DB_TESTS=1 pnpm exec turbo run test --force`                     | PASS: 451 backend tests (128.41 seconds), 63 frontend tests; no cached tasks                                                     |
| `.venv/bin/python -m unittest discover -v`                            | PASS: 3 ingestion tests; total 517, including all 498 predecessor tests and 19 Phase 2M tests                                    |
| `pnpm lint` and Ruff format check                                     | PASS: all checks, 111 Python files formatted                                                                                     |
| `pnpm typecheck`                                                      | PASS: strict Python checks on 53 source files and TypeScript checks                                                              |
| `pnpm format:check`                                                   | PASS: Prettier                                                                                                                   |
| `pnpm exec turbo run build --force`                                   | PASS: API compilation and Next.js production build, no cached tasks                                                              |
| Alembic upgrade/current/check                                         | PASS: `0008_search_typos (head)`; `No new upgrade operations detected.`                                                          |
| Migration regression tests                                            | PASS: disposable-database upgrade/downgrade tests within the full suite                                                          |
| `scripts/smoke.py --manage-services --check-db-outage --demo-catalog` | PASS: website routes, search, unknown-slug/UUID 404s; `/ready` 200 → 503 → 200, `/health` stays 200; PostgreSQL restored healthy |
| `scripts/check_secrets.py`                                            | PASS: 252 working files, 40 commits, 414 historical blobs, zero heuristic findings before final commit                           |
| `git diff --check` and checkpoint preservation                        | PASS: no whitespace errors; all four checkpoint files unchanged                                                                  |
| GitHub CI                                                             | NOT RUN: no push or PR authorized; local success does not establish remote CI success                                            |

No dependency or lockfile changes were made. The previously documented high
development-tooling `braces` advisory (GHSA-vfj7-8cjw-p6xm) remains unresolved;
passing lint/build/secret checks do not constitute full dependency security
clearance. Real provider activation, genuine coverage validation and public
enrichment enqueue/retention operations remain outside this local implementation.
