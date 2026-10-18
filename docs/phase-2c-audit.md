# Phase 2C verification audit

Date: 2026-10-18. Scope: trusted local licensed CSV/JSON/JSONL import, canonical
review and separate publication on the existing catalog schema. No website
collection, unauthorized dataset download, public administration, paid services,
cloud database changes, production deployment, separate PWA edits or later phase.

## Approved Phase 2B merge

PR [#2](https://github.com/mlvnpcrb/FraggyAPI/pull/2) was OPEN, MERGEABLE and unchanged
at `6f30a7edfb40dbcdd59a7c8129ffe824927450f4`. Its final
[PR CI](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39110466340) and
[branch CI](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39110463849) were SUCCESS.
It was merged normally with a matching-head guard. Merge SHA:
`a2178a545bf5f20db2db57177507463895df9b51`.

The main checkout was pulled with `--ff-only`. Baseline validation passed 94 backend,
15 frontend and 3 ingestion tests (112 total), plus the existing build. The new
branch is `feat/phase-2c-data-import`. No force push/reset or unrelated work removal.

## Architecture and security review

- Separate format validation, operator authorization, deterministic matching,
  transactional staging, canonical writing/review and local CLI modules.
- Existing source/run/snapshot/link/field-provenance/review tables reused. No new
  tables, schema revisions, startup DDL or migrations changed. Head is `0004_quality`.
- File flags/license references alone cannot authorize storage. Only a trusted
  operator DB review event with matching manifest digest grants it. Publication is
  a further record/field decision. The OS/operator DB credentials are the trust
  boundary; reviewer strings alone are not authentication.
- Unverified input stores only hashes and minimal quarantine/run/review metadata;
  no payload, original external ID, source URL or canonical values. Withdrawal of
  raw storage requires explicit `--deny-storage` and clears snapshot payloads. Independently verified historical audit
  metadata is retained privately for review, not automatically published.
- Field/record/source publication revocation is immediate. Source re-review cannot
  silently restore prior grants. Source policy changes require new snapshot review.
  Mandatory attribution is stored but publication fails closed until a suitable
  public attribution contract exists. No copyrighted media/descriptions/reviews or
  raw claims enter the public DTOs.
- Fictional manifests use `synthetic_file_import` and synthetic rights; they require
  explicit development visibility and remain hidden in production. Existing
  Phase 2A synthetic fixtures and all Phase 2B boundaries remain tested.
- Bounded UTF-8 local files; strict shapes, safe parse errors, row/field/depth/size
  limits, concentration synonyms, explicit note positions and GTIN check digits.
  No parsing executes code or formulas. Reports are escaped JSON, not CSV exports.
- Candidates provide reasons and confidence only. Exact matches still require
  operator choice. EDT/EDP, editions/years/flankers and ambiguous aliases cannot be
  silently merged. Existing canonical values are not overwritten by links. New
  revisions retain old source claims. Perfumers are not merged solely on names.
- Batched transactions, shared advisory writer lock, final review row locks,
  stable UUIDs, digest/revision idempotence and resumable committed batches. A late
  failure rolls back the current batch and reports earlier successful batches.
- No dependency changes; pnpm/Python locks remain unchanged. No public routes,
  frontend admin panel, service credentials or network fetches added. Real datasets,
  private manifests and generated reports have documented ignored storage paths.

## Validation

| Command/check                                                         | Result and evidence                                                                       |
| --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `docker compose up -d --wait`                                         | PASS — local PostgreSQL healthy                                                           |
| `pnpm lint`                                                           | PASS — API/web and worker/script lint                                                     |
| `pnpm typecheck`                                                      | PASS — mypy checks 19 application files; strict TypeScript/Next type generation           |
| `RUN_DB_TESTS=1 pnpm test`                                            | PASS — 162 backend, 15 frontend, 3 ingestion tests (180 total), no skips                  |
| `pnpm format:check`                                                   | PASS — Prettier                                                                           |
| `ruff format --check apps/api scripts workers`                        | PASS — Python formatting                                                                  |
| `pnpm build`                                                          | PASS — API compile and Next.js production build                                           |
| Alembic `upgrade head`, `current`, `check`                            | PASS — `0004_quality (head)`; no new upgrade operations                                   |
| `scripts/smoke.py --manage-services --check-db-outage --demo-catalog` | PASS — API/web/routes/search/404 and readiness 200→503→200; health stays 200; DB restored |
| `scripts/check_secrets.py`                                            | PASS — working tree/history scan, zero findings                                           |
| `git diff --check`                                                    | PASS — no whitespace errors                                                               |

The import suite adds 68 tests. Parsing covers all formats, quoted CSV, Unicode,
missing/unknown fields, normalization, corrupt encodings, JSON duplicate keys,
CSV shape problems, file/row/string/nesting limits, GTIN and source URL validation.
Real PostgreSQL tests cover unverified quarantine, dry-run non-mutation,
record/batch rollback, candidate classes and identity distinctions, alias reuse,
conflicting claims, new revisions, idempotence, every manual decision, publication
boundaries, source/field revocation, storage withdrawal and synthetic production
exclusion. Existing Phase 2A migration/deletion tests and Phase 2B tests are preserved.

The CLI smoke uses a randomly named disposable localhost PostgreSQL database and
actual subprocess commands: preview → operator source review → import → list/
inspect/results → approve new → explicitly publish → public API → provenance →
reimport → revoke. A second smoke proves failure after an earlier committed batch,
then safe resume. Only test-owned databases are dropped; no application reset.

Direct root `pnpm catalog:import -- ... --dry-run` and
`pnpm catalog:manage -- pending ...` invocations also passed; the fictional source
had no trusted review in the application DB and the preview reported only hashes
and `rights_review_required`, with zero canonical writes. Explicit registry/DB
checks confirmed all seven website sources remain disabled and pending review.

Cloud `start_skill` instructions were updated and saved as a draft, including
operator trust boundaries, non-production CLI scope, safe startup and disposable
CLI smoke guidance. Install/network/credential settings were preserved. Draft
persistence is not environment publication or a production deployment.

## GitHub verification

CI is configured for the feature branch and PR, with frozen dependency setup,
PostgreSQL-backed tests (including CLI smoke), lint/types/format, production build,
migration integrity, HTTP outage/recovery and secret scanning. Actual GitHub Actions passed on implementation head
`3ba48ad2705410750842353315a2f102a570188a`:

- [PR workflow 39118761209](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39118761209): SUCCESS.
- [Branch workflow 39118718353](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39118718353): SUCCESS.

The [Phase 2C PR #3](https://github.com/mlvnpcrb/FraggyAPI/pull/3) checks panel is the
authoritative result for final/subsequent documentation heads. Completion requires
an actual successful workflow on the reported final SHA; earlier/local results
alone cannot validate a newer commit. Phase 2C remains unmerged pending approval.

## Limitations

- Human operators must actually verify provider/ownership/storage/redistribution
  evidence. There is no automatic legal verification or tamper-proof external audit.
  DB administrators remain trusted. Commands are deliberately local/non-production;
  production access/deployment is not part of this phase.
- Attribution-required datasets can be stored privately when authorized but cannot
  be published with the current DTO. No real third-party dataset was imported or
  website approved. The seven website sources remain disabled/pending review.
- 2 MiB/1000-row files, 1–200-row transactions and bounded candidates are intentional
  free-tier limits. Larger datasets must be split/resumed. No background scheduler,
  distributed jobs or production-scale performance benchmark is included.
- Linking preserves incoming enrichment claims privately; it does not modify
  existing notes, variants or scalar values. Ambiguous aliases require trusted
  curation/corrected input, not an automatic merge. Separate releases do not infer
  reformulation chains. GTIN checksums do not prove identifier allocation/identity.
- Collection stays source-specific rather than adding a new taxonomy. Public v1
  omits variants/perfumers/collections/media and retains the Phase 2B contract.
- Raw storage withdrawal purges snapshots while retaining minimal historical audit
  metadata for review; provider-specific retention/deletion obligations need actual
  legal/operator evaluation. No universal data-retention rule is claimed.
- The previously documented unpatched development-only braces advisory remains;
  no dependencies or suppressions were changed.

Ready for Phase 2C review after successful actual CI on the final head. No Phase 2D,
Phase 3, automatic merge, website collection or production action is authorized.
