# Catalog operator review workflow

Only a trusted local operator may review/import/publish. There is no public admin
panel, upload route or automatic matching/merging. See source authorization before
using actual data. The committed examples are wholly fictional.

## Candidate decisions

Candidate detection compares normalized brand identity/known aliases, fragrance
name, concentration, release year, bottle sizes and supplied identifiers. Brand
alias ambiguity fails closed. Exact identity requires known agreeing concentration
and year, compatible supplied variants and no unresolved version label. Multiple
exact candidates remain possible duplicates. Related names generate review reasons,
not an identity. GTIN conflicts do not override brand/name/release distinctions.

Candidates are classified `exact_identity_match`, `possible_duplicate`,
`new_fragrance`, or `conflict_requiring_review`, with deterministic IDs/reasons and
confidence indicators used only for prioritization. Candidate output is bounded;
truncation requires further inspection. No confidence authorizes a merge. Matching
fetches bounded variants in one query, not one query per candidate.

```sh
pnpm catalog:manage pending --source fictional-workshop-import --limit 50
pnpm catalog:manage inspect --record-id RECORD_UUID
pnpm catalog:manage review --review-id REVIEW_UUID --decision approve_new \
  --reviewer catalog-editor --reason 'Confirmed this original fictional identity'
```

Review choices:

| Decision           | Effect                                                                                                                 |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| `approve_new`      | Explicitly creates a new fragrance line/release, reusing only unambiguous reviewed brand/taxonomy identities           |
| `link_existing`    | Requires `--target-release UUID`; links provenance without modifying existing canonical values or composition/variants |
| `separate_release` | Requires `--target-release UUID`; creates a distinct release on that fragrance line; preserves the target              |
| `reject`           | Marks the source snapshot rejected; no canonical writes                                                                |
| `defer`            | Keeps the review pending and appends reviewer/time/reason to its history                                               |

Link/separate targets must have the same normalized brand/fragrance identity;
flankers cannot be linked on a similar name. Known concentration/year conflicts or
version distinctions require a separate release, not overwrite. Identifier
conflicts with another release cannot be silently linked. Brand/note alias
ambiguity must be corrected by trusted curation or a corrected input revision;
this phase does not provide a general-purpose taxonomy editor. Perfumers are never
merged solely by name. Unknowns remain unknown; no missing years/notes/perfumers
are filled from a candidate.

Linking does not enrich or mutate an existing canonical release. Incoming
composition/variants are retained as private incoming claims for review, while
conflicting scalar values stay candidate/conflicting claims. A new revision or
explicit separate release can preserve distinct editions. Review-created releases
keep all specified note positions, variants and provenance. `separate_release`
creates a distinct version identity but does not invent a reformulation-of chain.
Resolved/rejected decisions cannot be overwritten. Deferrals append history;
canonical writes and final queue state commit atomically. Targets cannot be passed
to unrelated decisions. CLI review actions are scoped to file-import review items.

## Complete fictional example

Start the local database and migrations. The first import preview needs no writes:

```sh
docker compose up -d --wait
.venv/bin/alembic -c apps/api/alembic.ini upgrade head
pnpm catalog:import -- --file data/examples/fragrances.csv \
  --manifest data/examples/source-manifest.json --dry-run
```

It reports `rights_review_required` until a trusted review is recorded. For the
original fictional example only, record that review:

```sh
pnpm catalog:manage source-review --manifest data/examples/source-manifest.json \
  --allow-storage \
  --publish-fields name,slug,brand_id,fragrance_id,concentration,release_year,notes,accords \
  --reviewer example-operator --reason 'Reviewed original fictional example metadata'
pnpm catalog:import -- --file data/examples/fragrances.csv \
  --manifest data/examples/source-manifest.json --dry-run
pnpm catalog:import -- --file data/examples/fragrances.csv \
  --manifest data/examples/source-manifest.json
pnpm catalog:manage pending --source fictional-workshop-import
```

Read the returned `records` UUID and corresponding `reviews[].id`. Substitute them
below. These are intentionally stable references obtained from the actual run,
not guessed IDs based on display names:

```sh
pnpm catalog:manage inspect --record-id RECORD_UUID
pnpm catalog:manage review --review-id REVIEW_UUID --decision approve_new \
  --reviewer example-editor --reason 'Verified the fictional row as a new fragrance'
# Canonical data is still private at this point.
pnpm catalog:manage publish --record-id RECORD_UUID \
  --fields name,slug,brand_id,fragrance_id,concentration,release_year,notes,accords \
  --reviewer example-publisher --reason 'Explicit fictional demonstration publication'
CATALOG_INCLUDE_SYNTHETIC=true pnpm dev
```

Verify internally that `GET /api/v1/fragrances` returns the synthetic record with a
stable fragrance UUID and a distinct release UUID. Use the returned fragrance UUID:

```sh
pnpm catalog:manage provenance --fragrance-id FRAGRANCE_UUID
pnpm catalog:manage source-status --source fictional-workshop-import
pnpm catalog:import -- --file data/examples/fragrances.csv \
  --manifest data/examples/source-manifest.json
# This reimport skips the unchanged snapshot and preserves canonical IDs.
pnpm catalog:manage revoke --source fictional-workshop-import \
  --reviewer example-publisher --reason 'Withdraw the fictional publication grant'
```

The public record disappears unless another independently permitted source grants
its fields. Imported snapshots and review history remain private. Production never
shows this synthetic example, even if the demo setting is accidentally enabled.
The real end-to-end CLI test executes these steps against an isolated disposable
PostgreSQL database; it also checks resumed batches after a late failure:

```sh
RUN_DB_TESTS=1 .venv/bin/python -m pytest apps/api/tests/test_import_cli.py -v
```

Private licensed real-data manifests must use actual reviewed evidence and
`synthetic: false`. No real data, permissions or cloud deployment is implied by
running the fictional example. All seven website adapters stay disabled.
