# Phase 2H — reproducible local performance

Measured 2026-10-19 (Asia/Manila), Python 3.12.14, local PostgreSQL, original
synthetic fixtures. These are local development measurements, not production
latency, scalability, uptime or an external network/CDN SLA.

```bash
.venv/bin/python scripts/benchmark_preview.py --repeats 5 --warmup 1 --output data/reports/phase-2h-performance.json
```

The command refuses production/remote PostgreSQL, creates/migrates only its own
UUID-named disposable database, builds 100 fictional fragrances and four original
approved raster assets, and removes that database/directory in `finally`. It
never fills/resets the application database or contacts external perfume sources.
No real data/image rights are inferred from fixture permissions.

Each scenario has one warmup plus five timed requests. p95 is the nearest-rank
sample (`ceil(0.95*n)`). Captures real FastAPI ASGI routing, rights-aware database
queries, DTO/JSON serialization; image timing includes byte read/hash verification.
No socket, browser, DNS, CDN, cold boot or production traffic timing. Read counts
include SELECT and WITH statements. The environment also ran local QA tooling;
CPU contention, small sample count and warm caches limit generalization.

| Scenario                                            | Median ms | p95 ms  | SQL reads / request | Failures |
| --------------------------------------------------- | --------- | ------- | ------------------- | -------- |
| Search                                              | 246.403   | 371.651 | 8                   | 0        |
| Brand + concentration filter                        | 172.181   | 226.924 | 8                   | 0        |
| Pagination                                          | 176.186   | 245.855 | 8                   | 0        |
| Fragrance detail, including approved image metadata | 99.582    | 100.526 | 7                   | 0        |
| Approved primary image byte delivery                | 23.432    | 27.099  | 2                   | 0        |

**0/30 failed requests, error rate 0%** including warmups; 25 timed requests.
Bounded reads do not imply constant SQL work or unlimited catalog/media capacity.
These samples exercise a single local process and small fixture corpus. They do
not include parallel-load/resource exhaustion, large real datasets, long-running
collection or multi-host storage tests.

[Phase 2G measurements](phase-2g-audit.md) also cover 100/1000-record catalog
queries with no images. Their narrower query/DTO timing is a different method;
do not present direct timing differences as a measured regression or improvement.
A public beta requires representative authorized data, a deployment environment,
concurrency/load/error-budget targets and measurements under those conditions.
