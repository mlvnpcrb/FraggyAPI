# Phase 2G audit — first authorized-source readiness and media

Phase: **2G, offline implementation only**. Date: 2026-10-19 (Asia/Manila).
Branch: `feat/phase-2g-first-source`. Phase 2G must remain unmerged for review.

## Authorized predecessor merge

PR [#6](https://github.com/mlvnpcrb/FraggyAPI/pull/6) was OPEN/MERGEABLE;
head exactly `f54073545f0c5c88fe299875802a2ca8641082bd`; both required
Foundation checks were SUCCESS:
[PR check](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39138440194),
[push check](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39138437688).
Normal merge with `--match-head-commit` produced
`0472cd57f1783cbf427143dda59315b31a75d5c2`.
Local main was updated with `git pull --ff-only origin main`. The merged baseline
passed **278 backend + 26 web + 3 ingestion = 307 tests**, and `pnpm build`
succeeded using valid Turborepo outputs. The requested G branch was created only
then; it is based on the merged main, not an unmerged F branch.

## Source research and genuine data readiness

See [source selection](phase-2g-source-selection.md) for actual evidence,
HTTP limitations, separate rights decisions and classification of every candidate.
Wikidata is selected for the bounded adapter; official CC0 structured-data
licensing and API access documentation were verified. Its live endpoint/robots,
actual fragrance ID list, monitored operator contact and user pilot approval are
still outstanding. No real metadata/image policy has been activated in PostgreSQL.

Parfumo, The Perfume Society and ScentBase require permission for intended reuse;
other website candidates remain pending. Prior incompatible dataset licensing
remains incompatible. Image rights have not been inherited from metadata licenses.

**Genuine records imported/published: 0. Genuine photos acquired/published: 0.**
The seven website adapters remain disabled and pending review. No paid services,
production deployment, billing or separate Fraggy PWA modifications.

## Synthetic demonstration and quality

Command:

```bash
.venv/bin/python scripts/demo_collection.py --first-source --records 100
```

Observed final standalone run: **2.260 seconds** total including migration and full
ASGI review/publication/media/revocation flow, excluding final resource teardown;
4 source pages / 100 staged records, then 4 repeat pages / 100 unchanged / 0 new.
98 remained pending manual review; 0 public before review, 2 after explicit
publication, 0 after revocation. One original image was hidden (404), separately
approved (200 WebP, 1538 bytes, two renditions), then hidden (404); both orphan
renditions removed. Zero external collection requests. Owned server, temporary
image directory and UUID-owned database were cleaned up.

Pre-staging quality correctly reported 100 missing-note and 100 unknown-year
records, with no fabricated values. Canonical quality after the two explicit
reviews was complete: 0 errors, 0 warnings, 2 informational findings. These are
synthetic results and do not establish coverage or quality of actual Wikidata.

## Performance measurements

Command:

```bash
.venv/bin/python scripts/benchmark_catalog.py --sizes 100,1000 --repeats 5 --warmup 1 --output /tmp/phase2g-benchmark.json
```

Local Python 3.12.14, warm PostgreSQL, five timed repetitions after one warmup,
original synthetic catalogs with approved attribution but **no media assets**.
Measures in-process API query/projection/DTO serialization, not browser/network
latency, cold starts, image encoding throughput or a production SLA. All runs
completed with no failures; bounded **8 reads** (the extra media batch included).

| Catalog | Query      | Median ms | p95 ms  |
| ------- | ---------- | --------- | ------- |
| 100     | Search     | 72.458    | 119.406 |
| 100     | Filter     | 78.995    | 138.090 |
| 100     | Pagination | 88.811    | 165.265 |
| 1000    | Search     | 139.907   | 197.597 |
| 1000    | Filter     | 98.016    | 179.567 |
| 1000    | Pagination | 148.895   | 235.182 |

## Completion checks

The following local results were executed against the Phase 2G implementation.
Remote CI must additionally pass on the final pushed head; local success does
not substitute for GitHub results. The existing 307 tests are retained;
DTO/count assertions were extended for additive image fields and one bounded read,
not removed or weakened. Applied migration history is unchanged.

| Check                                                           | Result / supporting output                                                                                                                                                                                                                                                                                                                              |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bash scripts/setup.sh`                                         | PASS; frozen pnpm lockfile installation and locked Python installation, editable API installed successfully; `pip check`: no broken requirements                                                                                                                                                                                                        |
| `RUN_DB_TESTS=1 pnpm test`                                      | PASS; **333 backend + 44 web + 3 ingestion = 380 passing**, no skipped/failed tests. All 307 original tests retained, 73 added. Backend 77.68 seconds; frontend 996 ms; worker suite 0.003 seconds                                                                                                                                                      |
| Source regression after strengthening malformed-page assertions | PASS; `pytest apps/api/tests/test_wikidata.py -q`: **20 passed**; full requested-ID pages prevent unrelated incompleteness masking malformed-field failures                                                                                                                                                                                             |
| `pnpm lint`                                                     | PASS; Ruff API/scripts/workers and web ESLint: all checks passed                                                                                                                                                                                                                                                                                        |
| `pnpm typecheck`                                                | PASS; strict mypy: no issues in 41 source files; Next route generation and `tsc --noEmit` succeeded                                                                                                                                                                                                                                                     |
| `pnpm format:check` / Ruff format                               | PASS; all matched Prettier files conform; 82 Python files already formatted                                                                                                                                                                                                                                                                             |
| `pnpm build`                                                    | PASS; API compile and Next production build succeeded; dynamic same-origin `/media/[id]/[preset]` route included                                                                                                                                                                                                                                        |
| Alembic upgrade/current/check                                   | PASS; `0006_media (head)`; `No new upgrade operations detected.` Disposable upgrade/downgrade/migration tests included above; no applied migration edited                                                                                                                                                                                               |
| Default F demonstration                                         | PASS; original 2 staged, repeat 2 unchanged, public 0 → 2 → 0; collection refused after revocation; no external requests                                                                                                                                                                                                                                |
| 100-record G demonstration                                      | PASS; four-page source mapping, idempotent staging, manual publication, separate image approval/bytes, source revocation and blob cleanup as above                                                                                                                                                                                                      |
| Runtime/outage/recovery smoke                                   | PASS; real API health/readiness, catalog/search/filter/lookup/web routes and unknown UUID/slug 404s. PostgreSQL stopped: `/ready` 503, `/health` 200. Restored: `/ready` 200. Compose returned healthy; owned servers stopped                                                                                                                           |
| Real Chromium desktop/mobile                                    | PASS; production web + owned disposable API/database; approved image and credit rendered on desktop cards (1440 px) and mobile detail (**390 px**, document width 390); no horizontal overflow or image/credit overlap; card placeholder retained for missing image. Browser inspection found and fixed image sizing/long-name overflow before delivery |
| Secret/generated-file review                                    | PASS; working-tree/history pattern scan: **0 findings**. Only `.env.example` is tracked as an environment file; no private image store, real datasets, build outputs, test reports, credentials or browser artifacts staged                                                                                                                             |
| Disabled-source database check                                  | PASS; seven website candidates all `pending_review/pending_review/enabled=false`; **0 collector configurations, 0 approved media assets** in the application database                                                                                                                                                                                   |
| Scope/free-first review                                         | PASS; private local PostgreSQL/files only; no genuine collection, paid resource, CDN, deployment, billing, PWA change or Phase 2G merge                                                                                                                                                                                                                 |

The first-source fixture uses `example.invalid` contact/rights text and invented
Q identifiers; these are never live source approvals. Source/asset conditions
that cannot be represented by the supported policy fail closed. The safe local
implementation is ready for code review; **real pilot readiness remains blocked**
by the source/ID/endpoint/contact/image-rights items in the approval package.

## Remote delivery acceptance

The PR must remain open and unmerged. Its Checks tab and
[branch workflow runs](https://github.com/mlvnpcrb/FraggyAPI/actions?query=branch%3Afeat%2Fphase-2g-first-source)
are authoritative for the pushed head. The final delivery report records the
exact commit SHA, PR URL and actual successful GitHub run links after verification;
this audit does not claim a remote result solely from local outputs.
