# Phase 2E local PostgreSQL performance

Measured 2026-10-18 (Philippine calendar date). These are local development
observations, **not production latency/capacity guarantees** or an API SLA.
No paid search infrastructure, database reset, external record or hosted service
was used. The application database was not benchmark-loaded.

## Reproduce

```bash
docker compose up -d --wait
.venv/bin/python scripts/benchmark_catalog.py --sizes 100,1000,10000 \
  --repeats 5 --warmup 1 --output data/reports/benchmark.json
```

The CLI refuses production/non-loopback targets, creates one UUID-named
`fraggy_bench_*` database per size, applies existing migrations, explicitly loads
original fictional fixtures, runs ANALYZE and finally drops only the databases it
created. It requires CREATEDB on local PostgreSQL. The underlying fixture writer
also refuses ordinary application database names or nonempty house catalogs.
No fixtures, raw EXPLAIN output or generated operational files are committed.
The raw local artifact for this run is `data/reports/phase2e-benchmark-release.json`;
reproduction generates a new artifact with timestamps, actual samples and plans.

Environment: Python 3.12.14; Linux 6.18.55 x86_64/glibc 2.41; 5 CPUs reported by
`os.cpu_count()` (not a dedicated CPU reservation); PostgreSQL 17.11 Alpine 64-bit
under existing Docker Compose. PostgreSQL reports shared_buffers=16384 8-KiB pages
(128 MiB), work_mem=4096 KiB (4 MiB), max_connections=100. Existing statement timeout
remained **3 seconds per statement**; no timeout/rights checks were disabled.
Application connections explicitly set `jit=off`; the artifact records this
effective setting. Database-wide configuration is unchanged.
No test/build jobs intentionally ran concurrently with this final timed run. The
development machine remains shared; CPU allocation, caches and run-to-run
variation are practical limitations.

## Fixture and method

| Fragrances | Houses | Releases | Bottle variants | Selected/unknown claim rows |
| ---------- | ------ | -------- | --------------- | --------------------------- |
| 100        | 10     | 210      | 420             | 2,350                       |
| 1,000      | 100    | 2,100    | 4,200           | 23,500                      |
| 10,000     | 100    | 21,000   | 42,000          | 235,000                     |

Each catalog has 24 shared fictional notes, 8 accords, 4 families and 20 invented
perfumers. Each line has EDP/EDT releases; every tenth has a separate EDP
reformulation linked to its prior EDP. Names vary and include a fictional Night
suffix; some years deliberately remain unknown. Releases have top/heart/base
notes, accord, perfumer and 50/100 mL bottle variants. Public fields have synthetic
source records, approved links/claims and explicitly reviewed supported attribution.
Additional private bottle/perfumer/family shape is not a claim of complete public
provenance for every private fixture field. All fixtures remain excluded from
production. The bulk fixture writer stresses the public query graph; its load time
is **not** a measurement of the manually reviewed import CLI's throughput.

Each scenario runs one warm-up and five measured sequential requests with fresh
request sessions using the real public `catalog()` query, rights policy, projection
and DTO JSON conversion. This is **in-process application/database time**, excluding
HTTP transport, middleware, browser rendering and internet latency. Cache is warm;
PostgreSQL/session/SQLAlchemy caches are not forcibly flushed. Memory tracing uses
a separate untimed request because tracing materially inflated latency in an
initial trial. Reported p95 is nearest-rank over five observations (therefore the
maximum); it is not a reliable production tail estimate. No concurrency/load or
cold-cache conclusions are supported.

- Search: `q=Cedar`, limit 20, default relevance sort; about half the fictional
  names match. The test checks returned synthetic labels and nonempty credits.
- Filter: EDP + year 2020 + one published note UUID, limit 20, **same-release**
  semantics, no brand narrowing. Unknown years cannot match.
- Pagination: name sort, limit 20, offset `min(size - 20, 500)` (80/500/500).
  This does not test the maximum 10,000 offset or keyset pagination.

## Final observed latency (milliseconds)

| Fragrances | Search median / p95   | Filter median / p95 | Pagination median / p95 | SELECTs per request |
| ---------- | --------------------- | ------------------- | ----------------------- | ------------------- |
| 100        | 153.765 / 199.136     | 176.562 / 241.142   | 189.459 / 244.824       | 7 / 7 / 7           |
| 1,000      | 273.034 / 312.807     | 211.837 / 293.160   | 273.872 / 394.846       | 7 / 7 / 7           |
| 10,000     | 1,489.604 / 1,551.479 | 560.622 / 657.415   | 1,613.872 / 1,675.858   | 7 / 7 / 7           |

All 45 final timed requests completed without failures/timeouts, plus warm-ups and
separate memory/plan requests. Seven SELECTs cover source policy, total, root rows,
bounded releases, notes, accords and credits. Transaction/isolation driver commands
are outside that SELECT count. Fixed query count does **not** imply fixed work.
The 3-second statement timeout is per statement, not the entire request.

Separate Python allocation peaks: approximately 2.10–2.57 MiB per request across
these scenarios. Process maximum RSS after each size was 85.3 / 101.4 / 348.5 MiB;
that high-water mark includes fixture generation, interpreter/driver buffers and
prior scenarios, not just one request. PostgreSQL/container memory was not profiled.
Fixture generation + inserts + ANALYZE took about 0.89 / 6.92 / 66.91 seconds.

## Actual EXPLAIN observations

The script captures the seven SELECTs and executes
`EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` separately after timing. It retains each
complete plan in the local artifact without connection strings or query parameter
dumps. These are diagnostic executions, not the measured latency samples.

Observed at 10,000 fragrances:

| Scenario / statement    | Top node  | Execution ms | Shared hits / reads | Temp read / written blocks |
| ----------------------- | --------- | ------------ | ------------------- | -------------------------- |
| Search count (#2)       | Aggregate | 149.926      | 192402 / 0          | 0 / 0                      |
| Search credits (#7)     | Limit     | 917.635      | 1163635 / 0         | 658 / 659                  |
| Filter count (#2)       | Aggregate | 125.699      | 129039 / 0          | 0 / 0                      |
| Filter credits (#7)     | Limit     | 131.229      | 50962 / 0           | 0 / 0                      |
| Pagination count (#2)   | Aggregate | 275.416      | 372402 / 0          | 0 / 0                      |
| Pagination credits (#7) | Limit     | 929.427      | 1163635 / 0         | 658 / 659                  |

Plans include bitmap/index/index-only scans using source-entity target indexes,
`ix_provenance_link_field`, source-record/source primary keys, release-fragrance
and note/accord association indexes, plus joins, sorts, windows, materialized eligible-release CTE scans and some
sequential scans. The broad search did **not** use `ix_fragrances_search` in these observed
plans; the broad term and combined brand search can favor scans. No index was
forced and no unobserved index benefit is claimed. Credit sorts spilled at the
existing work_mem setting. Buffer hits are repeated accesses, not distinct pages.
The relatively small DTO allocation does not make these SQL operations cheap.

## Defects found and corrected

The original credit projection read many repeated house/note claims, built ORM
objects and revalidated the same credit for every path. In the same workload,
1,000-record search/filter/pagination medians were about 7275/7127/6697 ms; 10,000
search/pagination hit the credit safety cap and the broad filter timed out. These
were measured failures, not successful capacity results.

Phase 2E now deduplicates **authorized** source/entity/field/value contributions
in SQL before the cap and unions paths before DTO construction. Distinct providers,
values and fields remain separate; revocation is applied before deduplication.
A genuinely excessive distinct credit set still fails closed. Raw private
provenance remains intact. An additional query change evaluates a requested
note/accord's independent visibility outside the correlated release test, keeping
membership and its grant on the same release. The eligible-release UUID set is
materialized once per SQL statement to stabilize the plan on un-analyzed imports. Regression tests preserve taxonomy
rights, concentrations/years and cross-release filtering. No API DTO/route or
migration was changed by these corrections.

Intermittent final CI failures also reproduced locally in release and note
projection under the un-analyzed shared test catalog. Those projections now read
directly from page-scoped materialized rows without rejoining the full entity
table. Rights checks and window limits remain unchanged. The full local suite and
both implementation workflows passed afterward, but later final-head runs exposed
another timeout. An after-failure EXPLAIN captured the filter-count rights checks
flattened into twelve semi-joins with underestimated cardinalities, without JIT.
The shared grant query now retains a correlated per-entity existence check using
an `OFFSET 0` planner boundary. Permission predicates and timeouts are unchanged.
The measurements above were rerun on this corrected query implementation,
including all 63 complete plans.

After preserving per-entity grants, a measured 10,000-record note plan spent
2374.184 ms compiling JIT code out of 2388.634 ms execution. A later pagination
warm-up timed out under the unchanged 3-second statement budget. Application
connections now disable JIT to avoid compiler-cost thresholds dominating these
bounded queries. The final measurements above use that setting; this earlier
failed run is retained locally as `phase2e-benchmark-grant-jit-before.json`.
The direct un-analyzed regression fixture does not disable JIT or raise its guard.

## Remaining performance limits

A 100–300-record pilot is the next controlled data target, not a readiness claim
for public production traffic. At 10,000 fictional records, search/pagination latency,
credit sort spills and rights-join work remain material. Synthetic regularity,
single-source provenance, warm caches and sequential local requests do not model
heterogeneous production rights graphs, network/pooler overhead, concurrent writes,
source-policy churn or realistic skew. More samples, cold/concurrent workloads,
selective search cases, deeper pages, alternate licensed graphs and production-like
hardware are needed before an SLA. Investigate query plans/indexes and credit
aggregation first; do not add paid search automatically or weaken rights/timeouts.
