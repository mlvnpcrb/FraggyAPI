# Phase 2H engineering audit

Date: 2026-10-19, Asia/Manila. Scope: offline pilot readiness, actual synthetic
local application, fixes and readiness assessment. No production deployment,
external fragrance query/import, real photograph, paid service or PWA changes.

## Predecessor merge evidence

PR [#7](https://github.com/mlvnpcrb/FraggyAPI/pull/7) was OPEN, MERGEABLE and CLEAN,
not draft, with no blocking reviews or conflicts. Exact head:
`4f73033726bbf1821d1064d937a81e00d58499a9`.
Both required Foundation checks remained successful:
[PR run](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39170747468),
[push run](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39170731760).
Normal merge with exact-head protection produced
`f7d391dbfafcce47064591e8f6bee826f804847a`.
Local main updated fast-forward only. All **380 baseline tests** passed (333 API,
44 web, 3 ingestion); production build passed. Only then was
`feat/phase-2h-pilot-readiness` created. No worktree or unrelated remote overwrite.

## Implemented and confirmed fixes

- Disabled offline candidate/proposal checker with the user-required
  `CONTACT_EMAIL` placeholder. No discovery/client/network operation. Live grant
  validation rejects placeholders/example addresses before source activation.
- Reproducible `preview:local` supervisor creates a fresh owned disposable database,
  100 original fictional fragrances and four original approved images, binds only
  loopback API/web, verifies actual responses and removes only its own resources
  on shutdown. It refuses production, remote databases and occupied/invalid ports.
  It reconnects its administration connection for cleanup after a PostgreSQL outage.
- Actual Chromium inspection found homepage source credits overlapping the
  positioned hero caption. Credits now flow below the artwork in its adjacent
  wrapper, with layout regression coverage.
- Installed Next 16.4.2 documentation/runtime shows `retry` refreshes server data,
  whereas legacy `reset` only clears boundary state. The error UI now uses `retry`;
  actual API pause → loading → error → resume → retry recovered the catalog.
- New synthetic preview/performance/browser tools preserve the shared collector,
  import/provenance/publication/image architecture. No schema migration is added.

## Full-suite database investigation

The first combined run reported one existing rights/filter regression timing out
(358 backend tests passed, 1 failed). The isolated regression then passed; its
plan cost was about 11,850 with JIT enabled but no JIT plan generated. A subsequent
instrumented full backend run passed all 359, with lower observed plan costs
(about 4,387); the original failing plan was not captured. Do not claim the exact
transient failure mechanism was proven or a production failure was reproduced.

A confirmed configuration mismatch remained: disposable test sessions enabled
PostgreSQL JIT, while the application explicitly disables it for bounded rights
queries. Test connections now match that application policy. The existing 10-second
regression timeout, authorization/filter assertions and un-analyzed import state
are unchanged; no test was removed, skipped or softened and no ANALYZE was added
to conceal the import state. The final standard full suite and remote CI are
required after this correction. SQL planning remains a performance consideration
for future larger/real datasets and deployment-specific tests.

## Executed functional evidence

Initial browser inspection covered homepage, brands, listing, search, brand/
concentration filtering, pagination, detail and empty states at 1440×1000,
768×1024 and 390×844. After fixes: **26 browser scenarios passed**, no overflow
or hero-credit overlap; all four detail/gallery/release/variant images loaded at
each width. Mobile navigation toggle worked. Source credits, alt text, labels,
single main landmark and lazy placeholders were checked. A real API pause verified
loading, generic error and retry recovery. Browser instrumentation blocked outside
hosts; **zero external origins requested**. Screenshots/results stay ignored under
`data/reports/browser-qa/`. This limited review is not WCAG certification.

Original-only baseline media tests additionally verify malformed MIME/files,
size/dimension/decompression limits, EXIF stripping, approval, shared-hash dedup,
revocation, missing/symlink/corrupt files and garbage collection. Existing F/G
synthetic demonstrations test scheduled collection, manual canonical review,
separate field/image publication, withdrawal and denied subsequent collection.

Catalog inventory was queried directly from PostgreSQL and cross-checked against
the running API; the report distinguishes owned preview from the application DB.
No source is authorized for real collection. The seven website rows remain
`pending_review/pending_review/enabled=false` in both inventories.

## Security findings

- `pip-audit==2.10.1` installed in a separate `/tmp` virtualenv; locked requirement
  scan, 40 Python dependencies, **0 known vulnerabilities**. Writable cache override
  was necessary; TLS/signature verification was not disabled. Tool is not added
  to application dependencies.
- `pnpm audit --prod --json`: **0 known production JavaScript vulnerabilities**.
- Full `pnpm audit --json`: **1 high development-only advisory**,
  [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm),
  `braces <=3.0.3`, through `eslint-config-next → @next/eslint-plugin-next →
fast-glob → micromatch → braces`. npm audit and GitHub advisory API agree that
  there is **no published patched version**. Keep lint patterns/configuration
  trusted; do not claim a clean full dependency audit. Monitor upstream, then
  review and test a frozen-lock update or a separately reviewed mitigation. Do
  not hide the finding by weakening checks or fabricating a patched version.
- Existing ORM bind parameters, typed/length-bounded inputs, reserved website IDs,
  denied external network defaults, independent image rights, safe local decoding,
  no public upload/static mount and private evidence projection were reviewed and
  exercised by regression tests. Managed image blobs use mode 0600; private store
  directories 0700. Secret scanning is a separate required check.
- This is not a penetration test, exhaustive vulnerability assessment, authentication
  audit, third-party license opinion or production hardening certification.

## Delivery verification

Full-suite/lint/types/format/build/migration/outage/secret checks and actual remote
CI are completion gates. Final results and the PR/CI references are recorded in
[the readiness report](phase-2h-readiness-report.md). Local measurements alone do
not prove GitHub CI success. The Phase 2H PR must remain open and unmerged.

`next dev` generated `apps/web/AGENTS.md`; it is intentionally retained as scoped
framework engineering guidance, reviewed against the installed Next documentation.
Build outputs, private preview state/media, audit artifacts, screenshots, real data,
credentials and `.env` files remain ignored and must not be committed.

Final standard local suite after alignment: **408 passing** (359 backend, 46 web,
3 ingestion), retaining all 380 G tests. Backend completed in 147.52 seconds,
frontend in 6.09 seconds; no failed/skipped tests in this accepted run. Initial
failure and its diagnostic limitations are retained above rather than erased.
Lint, strict types, Prettier/Ruff formatting and forced production build passed.
Alembic remains 0006_media with no drift. Final remote-head status is verified
separately through the PR; the security advisory remains disclosed regardless
of green application CI.

The owned preview itself was also tested across a PostgreSQL stop/restart:
health stayed 200, readiness became 503 then recovered to 200. SIGTERM to its
verified supervisor cleaned up its owned processes, files and database even after
the old administrative connection was lost; the preview-DB count returned to 0.
A fresh final preview was then started. This is separate from the existing runtime
smoke's independently owned API/web outage test.
