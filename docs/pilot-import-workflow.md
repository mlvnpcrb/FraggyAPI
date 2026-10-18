# Local attributed pilot import

This process uses only original fictional fixtures. It does not approve any real
source. Do not download/import an external dataset in Phase 2D without separate
user authorization and documented rights. No website collection or public upload
endpoint exists. Use the existing checkout, Compose PostgreSQL and trusted local
CLI; operating cost remains ₱0/month. Nothing runs on startup automatically.

## 1. Register and review the manifest

Read [the attribution contract](attribution-contract.md) and
[source readiness questions](licensed-source-readiness.md). The fictional manifest
is `data/examples/attributed-source-manifest.json`; the equivalent records are
`data/examples/fragrances.csv`, `.json` and `.jsonl`. Provider/license links use
`example.invalid` and are deliberately not evidence of a real license.

For a genuinely authorized dataset, first obtain the user's explicit approval of
that dataset/use, then put files/manifests in ignored `data/private/` or
`data/imports/`. Put private agreement references only in
`license_evidence_references`; author a separate public-only `attribution` object.
Record supplier authority, collection/storage/redistribution scopes, fields,
expiry and withdrawal terms. Set unresolved `redistribution_conditions` rather
than pretending they are supported. Keep copyrighted descriptions, reviews and
images out of these bounded metadata imports.

Review required text and placement manually. Confirm that adjacent-record credits
satisfy every free-text requirement, that public HTTPS links are safe, and that
modification disclosure accurately describes normalization/matching. A compatible
license label alone proves nothing. Set the genuine review date; do not refresh
it merely to evade expiration. The checked-in fictional example is valid only
within 365 days of its stated date; after that, perform a new fictional review in
an ignored local copy. Automated tests generate today's date independently.

```bash
docker compose up -d --wait
.venv/bin/alembic -c apps/api/alembic.ini upgrade head
pnpm catalog:manage -- source-review \
  --manifest data/examples/attributed-source-manifest.json \
  --allow-storage --accept-attribution \
  --publish-fields name,slug,brand_id,fragrance_id,concentration,release_year,notes,accords \
  --reviewer local-pilot-operator \
  --reason "Reviewed original fictional policy and supported public credit"
pnpm catalog:manage -- source-status --source fictional-attribution-pilot
```

This explicit review registers the source, records the digest, operator, reason,
time, accepted obligations and public-field scope in PostgreSQL. It never enables
an adapter or publishes a record. `--accept-attribution` is a human attestation,
not automatic legal verification. For storage-only review, omit public fields;
unsupported obligations still prevent later publication. `--deny-storage` is an
explicit destructive withdrawal of stored raw snapshot payloads, not a dry run.

## 2. Dry-run and stage

```bash
pnpm catalog:import -- --file data/examples/fragrances.csv \
  --manifest data/examples/attributed-source-manifest.json --dry-run
pnpm catalog:import -- --file data/examples/fragrances.csv \
  --manifest data/examples/attributed-source-manifest.json --batch-size 100
pnpm catalog:manage -- pending --source fictional-attribution-pilot
```

Dry run is read-only. Inspect candidate reasons and UUIDs before making decisions.
Staging writes immutable source snapshots and pending queue entries, never public
canonical records. Unreviewed files produce hash-only quarantine. JSON/JSONL use
the same record schema and can replace CSV. Existing size/row/depth/batch limits,
transaction rollback and resumable provider-ID/content-hash behavior remain.
Use `results --run-id RUN_UUID` and `inspect --record-id RECORD_UUID` privately.
Do not commit their output.

## 3. Review identities and conflicts

Replace uppercase UUID placeholders with actual returned UUIDs. Review any existing
canonical candidates, concentrations, years, versions and GTINs. Select
`approve_new` only after confirming the fictional record is new:

```bash
pnpm catalog:manage -- review --review-id REVIEW_UUID \
  --decision approve_new --reviewer local-pilot-operator \
  --reason "Confirmed distinct fictional identity and preserved unknown values"
```

Use `link_existing --target-release RELEASE_UUID` only with verified identity;
it does not overwrite existing composition/variants. `separate_release` keeps a
separate version on an existing line. `defer` and `reject` remain available.
No name-only automatic merge occurs. Decisions retain reviewer/time/reason/history.
Inspect `provenance --fragrance-id FRAGRANCE_UUID` privately if needed.

## 4. Publish individually reviewed fields

```bash
pnpm catalog:manage -- publish --record-id RECORD_UUID \
  --fields name,slug,brand_id,fragrance_id,concentration,release_year,notes,accords \
  --reviewer local-pilot-publisher \
  --reason "Verified exact selected values, public field scope and complete credits"
```

Only selected, known matching claims become public. Unknown/conflicting claims
stay private. Source review, canonical review and record field publication are
three separate approvals. Stale known selected claims reject the transaction.
Missing permissions, digest changes, incomplete credits, unaccepted obligations,
expired verification dates and unsupported conditions fail closed.

## 5. Verify API and frontend

For these synthetic fixtures, start the API with explicit demo visibility and the
web with the existing `pnpm dev` workflow. For example, from the root:

```bash
CATALOG_INCLUDE_SYNTHETIC=true pnpm dev
```

Do not set demo visibility in production; the API ignores it there anyway. Use
internal local HTTP requests to `/api/v1/fragrances`, fragrance UUID details,
brand slug details, search, brands, notes and accords. Check required credits and
field pointers, multiple provider behavior, safe links and absence of private
legal/reviewer/snapshot information. Public response examples live in
[attribution-contract.md](attribution-contract.md).

Inspect the local web home, directory, details, brand listing and filter credits
at desktop and mobile sizes. Credits must be readable beside the record, with
provider/license/copyright/disclosure text and safe separate links. An empty
credit array renders no panel. No preview/production deployment is required.

## 6. Withdraw fields and source publication

```bash
pnpm catalog:manage -- unpublish --record-id RECORD_UUID --fields release_year \
  --reviewer local-pilot-publisher --reason "Withdraw year only"
pnpm catalog:manage -- revoke --source fictional-attribution-pilot \
  --reviewer local-pilot-publisher --reason "End fictional pilot publication"
```

After commit, repeat API requests and reload frontend pages. A withdrawn optional
field becomes null/absent and loses its credit paths, while independently granted
fields remain. Whole-source withdrawal removes grants and credits; a record
without another complete set of identity grants disappears. Health remains
available. Historical audit/storage remain according to storage permission.
Clients must refresh: already delivered data cannot be recalled.

A source/attribution/license change requires a new explicit source review, which
restricts all old publication grants. Reimport under the new digest, manually
link/review the new snapshot and publish fields again. Source review alone never
resurrects prior grants. Same-policy renewal also requires explicit record
publication approval. Withdrawing storage separately purges raw snapshots.

## Reproducible automated pilot

```bash
RUN_DB_TESTS=1 .venv/bin/pytest apps/api/tests/test_attribution.py \
  apps/api/tests/test_attribution_cli.py
pnpm --filter @fraggy/web test
```

The real CLI test creates a random disposable PostgreSQL database, migrates it,
reviews original fictional permissions, validates all three dry-run formats,
stages/reviews/publishes, verifies the real API, withdraws a field and revokes the
source, then drops only its owned database. Frontend tests exercise API DTO credits
through pages/components. The phase audit records the separate real-browser
API-to-frontend pilot. No private dataset, production database or paid service is
needed.
