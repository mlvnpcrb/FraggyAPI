# Database data dictionary

This describes the Phase 2A head (`0004_quality`). UUIDs identify entities independently
of names. All times are PostgreSQL TIMESTAMPTZ; collection/verification times describe
source events, not the row creation time. Nullable means unknown/not applicable, not
zero, an empty string, a guessed year or an invented concentration.

## Shared fields and lookup conventions

Every table has `id` (UUID, application UUIDv4 unless a deterministic demo UUIDv5 is
explicitly supplied), `created_at` (server now) and `updated_at` (server now initially;
ORM writes refresh it). Direct SQL writers must set update time themselves. SQL-only
inserts must supply UUIDs; no pgcrypto/uuid-ossp extension is needed.

Named catalog tables additionally have `name` and a stored generated `name_key`:
Unicode NFKC → collapse POSIX whitespace → trim → lowercase. Display names are not
rewritten. Slugs are explicit unique lowercase ASCII route handles and do not change
automatically on a name edit. All foreign keys below use RESTRICT; no delete cascades.
`UUID` references are mandatory unless the nullable column says yes.

## Internal data contracts

- `BrandRead`, `FragranceRead`, `ReleaseRead` are internal Pydantic v2 projections,
  with ORM validation. Brand descriptions/source payloads are not public fields.
- `SourceRecordInput` requires aware collection timestamps, a source UUID, nonblank
  external record ID, positive revision/schema version, and an object payload only
  when storage rights are approved/synthetic. Approved storage and redistribution
  need separate nonblank evidence references.
- `FieldClaimInput` requires an aware time, field path, rights, confidence in [0,1]
  when known, and transformations with explicit name/version. Unknown values are
  null; known/conflicting values preserve a non-null candidate claim.
- `selection_status=candidate` is the default. Selected is an internal editorial
  decision, not commercial permission. No automatic source preference exists.

Rights states are `pending_review`, `approved`, `restricted`, `synthetic`. Each
permission is independently scoped: retention does not grant redistribution.
Synthetic means invented test/demo data, never a real-source permission grant.

Concentrations are `parfum`, `extrait_de_parfum`, `eau_de_parfum`, `eau_de_toilette`,
`eau_de_cologne`, `eau_fraiche`, `oil`, `other`, or null. Preserve the original label
in `original_concentration`; `other` is a known unclassified label, not unknown.
Note positions are top/heart/base/unknown. Unknown position is not inferred as base.

Ingestion states are queued/running/succeeded/failed/cancelled/synthetic. Record
processing is pending_review/validated/rejected/linked. Link review is
pending_review/approved/rejected. Claims are known/unknown/conflicting and
candidate/selected/rejected. Review queue status is pending/resolved/dismissed;
resolved/dismissed rows need a reviewer, decision and resolution time.

Snapshot identity is `(source_id, source_record_id, revision)`, not a mutable URL.
`schema_version` refers to payload interpretation; revision identifies a new
snapshot. Payloads/transformations must be versioned and sanitized by trusted writers.
No field-level rights or license status can be verified simply by a database insert;
external review evidence must be validated before claiming approved rights.

## Table purposes

| Table                         | Purpose                                                               |
| ----------------------------- | --------------------------------------------------------------------- |
| brands / brand_aliases        | Canonical houses and alternate spelling keys                          |
| fragrance_families            | Optional controlled family taxonomy                                   |
| fragrances                    | Fragrance lines with optional family, year and positioning            |
| fragrance_releases            | Distinct concentrations, versions and reformulations                  |
| fragrance_variants            | Bottle/packaging choices and claimed product identifiers              |
| notes / note_aliases          | Canonical note terms and alternate labels                             |
| release_notes                 | Ordered note credits with known or unknown pyramid position           |
| accords / release_accords     | Canonical accord vocabulary and optional strength/order               |
| perfumers / release_perfumers | Distinct people and per-release credits                               |
| data_sources                  | Source policy, review evidence, limits and disabled registry metadata |
| ingestion_runs                | Source-scoped operational history; no scheduler implementation        |
| source_records                | Rights-gated structured snapshots, revisions and processing state     |
| source_entity_links           | Real-FK candidate links to exactly one canonical target               |
| field_provenance              | Multiple field claims with attribution, transformations and rights    |
| data_review_queue             | Pending/resolved review work, including cross-source conflicts        |
| media_assets                  | Rights-aware URL/attribution/license/path metadata only               |

## Columns

Shared `id`, `created_at`, `updated_at` are omitted below to avoid repeating their
contract. `generated key` refers to the normalization above; `generated FTS` is a
stored `simple`-configuration vector of the fragrance display name. Neither is
editable client data. Defaults are schema defaults, not guesses about real perfumes.

### `accords`

| Column     | PostgreSQL type | Nullable | Default / derivation | References |
| ---------- | --------------- | -------- | -------------------- | ---------- |
| `name`     | `TEXT`          | no       | —                    | —          |
| `name_key` | `TEXT`          | no       | generated key        | —          |
| `slug`     | `VARCHAR(160)`  | no       | —                    | —          |

### `brands`

| Column        | PostgreSQL type | Nullable | Default / derivation | References |
| ------------- | --------------- | -------- | -------------------- | ---------- |
| `country`     | `VARCHAR(2)`    | yes      | —                    | —          |
| `description` | `TEXT`          | yes      | —                    | —          |
| `name`        | `TEXT`          | no       | —                    | —          |
| `name_key`    | `TEXT`          | no       | generated key        | —          |
| `slug`        | `VARCHAR(160)`  | no       | —                    | —          |

### `data_sources`

| Column                       | PostgreSQL type            | Nullable | Default / derivation | References |
| ---------------------------- | -------------------------- | -------- | -------------------- | ---------- |
| `key`                        | `VARCHAR(100)`             | no       | —                    | —          |
| `name`                       | `TEXT`                     | no       | —                    | —          |
| `website`                    | `TEXT`                     | no       | —                    | —          |
| `adapter_identifier`         | `VARCHAR(100)`             | yes      | —                    | —          |
| `source_type`                | `VARCHAR(40)`              | no       | —                    | —          |
| `authorization_status`       | `VARCHAR(24)`              | no       | pending_review       | —          |
| `licensing_status`           | `VARCHAR(24)`              | no       | pending_review       | —          |
| `enabled`                    | `BOOLEAN`                  | no       | false                | —          |
| `allowed_collection_methods` | `JSONB`                    | no       | '[]'::jsonb          | —          |
| `permitted_fields`           | `JSONB`                    | no       | '[]'::jsonb          | —          |
| `reuse_restrictions`         | `JSONB`                    | no       | '[]'::jsonb          | —          |
| `evidence`                   | `JSONB`                    | no       | '[]'::jsonb          | —          |
| `error_history`              | `JSONB`                    | no       | '[]'::jsonb          | —          |
| `rate_limit`                 | `JSONB`                    | no       | '{}'::jsonb          | —          |
| `reviewed_at`                | `TIMESTAMP WITH TIME ZONE` | yes      | —                    | —          |
| `last_successful_sync`       | `TIMESTAMP WITH TIME ZONE` | yes      | —                    | —          |
| `adapter_status`             | `VARCHAR(32)`              | no       | skeleton             | —          |

### `fragrance_families`

| Column        | PostgreSQL type | Nullable | Default / derivation | References |
| ------------- | --------------- | -------- | -------------------- | ---------- |
| `description` | `TEXT`          | yes      | —                    | —          |
| `name`        | `TEXT`          | no       | —                    | —          |
| `name_key`    | `TEXT`          | no       | generated key        | —          |
| `slug`        | `VARCHAR(160)`  | no       | —                    | —          |

### `notes`

| Column     | PostgreSQL type | Nullable | Default / derivation | References |
| ---------- | --------------- | -------- | -------------------- | ---------- |
| `name`     | `TEXT`          | no       | —                    | —          |
| `name_key` | `TEXT`          | no       | generated key        | —          |
| `slug`     | `VARCHAR(160)`  | no       | —                    | —          |

### `perfumers`

| Column     | PostgreSQL type | Nullable | Default / derivation | References |
| ---------- | --------------- | -------- | -------------------- | ---------- |
| `name`     | `TEXT`          | no       | —                    | —          |
| `name_key` | `TEXT`          | no       | generated key        | —          |
| `slug`     | `VARCHAR(160)`  | no       | —                    | —          |

### `brand_aliases`

| Column     | PostgreSQL type | Nullable | Default / derivation | References |
| ---------- | --------------- | -------- | -------------------- | ---------- |
| `brand_id` | `UUID`          | no       | —                    | brands.id  |
| `name`     | `TEXT`          | no       | —                    | —          |
| `name_key` | `TEXT`          | no       | generated key        | —          |

### `fragrances`

| Column               | PostgreSQL type | Nullable | Default / derivation | References            |
| -------------------- | --------------- | -------- | -------------------- | --------------------- |
| `search_vector`      | `TSVECTOR`      | no       | generated FTS        | —                     |
| `brand_id`           | `UUID`          | no       | —                    | brands.id             |
| `family_id`          | `UUID`          | yes      | —                    | fragrance_families.id |
| `release_year`       | `INTEGER`       | yes      | —                    | —                     |
| `gender_positioning` | `VARCHAR(80)`   | yes      | —                    | —                     |
| `name`               | `TEXT`          | no       | —                    | —                     |
| `name_key`           | `TEXT`          | no       | generated key        | —                     |
| `slug`               | `VARCHAR(160)`  | no       | —                    | —                     |

### `ingestion_runs`

| Column             | PostgreSQL type            | Nullable | Default / derivation | References      |
| ------------------ | -------------------------- | -------- | -------------------- | --------------- |
| `source_id`        | `UUID`                     | no       | —                    | data_sources.id |
| `status`           | `VARCHAR(24)`              | no       | queued               | —               |
| `started_at`       | `TIMESTAMP WITH TIME ZONE` | yes      | —                    | —               |
| `completed_at`     | `TIMESTAMP WITH TIME ZONE` | yes      | —                    | —               |
| `records_seen`     | `INTEGER`                  | no       | 0                    | —               |
| `records_accepted` | `INTEGER`                  | no       | 0                    | —               |
| `sanitized_errors` | `JSONB`                    | no       | '[]'::jsonb          | —               |

### `note_aliases`

| Column     | PostgreSQL type | Nullable | Default / derivation | References |
| ---------- | --------------- | -------- | -------------------- | ---------- |
| `note_id`  | `UUID`          | no       | —                    | notes.id   |
| `name`     | `TEXT`          | no       | —                    | —          |
| `name_key` | `TEXT`          | no       | generated key        | —          |

### `fragrance_releases`

| Column                   | PostgreSQL type | Nullable | Default / derivation | References                                     |
| ------------------------ | --------------- | -------- | -------------------- | ---------------------------------------------- |
| `fragrance_id`           | `UUID`          | no       | —                    | fragrance_releases.fragrance_id, fragrances.id |
| `concentration`          | `VARCHAR(40)`   | yes      | —                    | —                                              |
| `original_concentration` | `TEXT`          | yes      | —                    | —                                              |
| `release_year`           | `INTEGER`       | yes      | —                    | —                                              |
| `version_label`          | `TEXT`          | yes      | —                    | —                                              |
| `reformulation_of_id`    | `UUID`          | yes      | —                    | fragrance_releases.id                          |
| `version_metadata`       | `TEXT`          | yes      | —                    | —                                              |

### `source_records`

| Column                    | PostgreSQL type            | Nullable | Default / derivation | References                                |
| ------------------------- | -------------------------- | -------- | -------------------- | ----------------------------------------- |
| `source_id`               | `UUID`                     | no       | —                    | data_sources.id, ingestion_runs.source_id |
| `ingestion_run_id`        | `UUID`                     | yes      | —                    | ingestion_runs.id                         |
| `source_record_id`        | `TEXT`                     | no       | —                    | —                                         |
| `source_url`              | `TEXT`                     | yes      | —                    | —                                         |
| `revision`                | `INTEGER`                  | no       | 1                    | —                                         |
| `schema_version`          | `INTEGER`                  | no       | 1                    | —                                         |
| `collected_at`            | `TIMESTAMP WITH TIME ZONE` | no       | —                    | —                                         |
| `last_verified_at`        | `TIMESTAMP WITH TIME ZONE` | yes      | —                    | —                                         |
| `payload`                 | `JSONB`                    | yes      | —                    | —                                         |
| `storage_status`          | `VARCHAR(24)`              | no       | pending_review       | —                                         |
| `redistribution_status`   | `VARCHAR(24)`              | no       | pending_review       | —                                         |
| `storage_evidence`        | `TEXT`                     | yes      | —                    | —                                         |
| `redistribution_evidence` | `TEXT`                     | yes      | —                    | —                                         |
| `processing_state`        | `VARCHAR(24)`              | no       | pending_review       | —                                         |

### `fragrance_variants`

| Column            | PostgreSQL type  | Nullable | Default / derivation | References            |
| ----------------- | ---------------- | -------- | -------------------- | --------------------- |
| `release_id`      | `UUID`           | no       | —                    | fragrance_releases.id |
| `bottle_size_ml`  | `NUMERIC(10, 3)` | yes      | —                    | —                     |
| `original_size`   | `NUMERIC(10, 3)` | yes      | —                    | —                     |
| `original_unit`   | `VARCHAR(24)`    | yes      | —                    | —                     |
| `gtin`            | `VARCHAR(14)`    | yes      | —                    | —                     |
| `packaging_label` | `TEXT`           | yes      | —                    | —                     |

### `release_accords`

| Column          | PostgreSQL type | Nullable | Default / derivation | References            |
| --------------- | --------------- | -------- | -------------------- | --------------------- |
| `release_id`    | `UUID`          | no       | —                    | fragrance_releases.id |
| `accord_id`     | `UUID`          | no       | —                    | accords.id            |
| `strength`      | `NUMERIC(5, 4)` | yes      | —                    | —                     |
| `display_order` | `INTEGER`       | yes      | —                    | —                     |

### `release_notes`

| Column          | PostgreSQL type | Nullable | Default / derivation | References            |
| --------------- | --------------- | -------- | -------------------- | --------------------- |
| `release_id`    | `UUID`          | no       | —                    | fragrance_releases.id |
| `note_id`       | `UUID`          | no       | —                    | notes.id              |
| `position`      | `VARCHAR(16)`   | no       | unknown              | —                     |
| `display_order` | `INTEGER`       | yes      | —                    | —                     |

### `release_perfumers`

| Column          | PostgreSQL type | Nullable | Default / derivation | References            |
| --------------- | --------------- | -------- | -------------------- | --------------------- |
| `release_id`    | `UUID`          | no       | —                    | fragrance_releases.id |
| `perfumer_id`   | `UUID`          | no       | —                    | perfumers.id          |
| `credited_role` | `VARCHAR(80)`   | yes      | —                    | —                     |

### `source_entity_links`

| Column             | PostgreSQL type | Nullable | Default / derivation | References            |
| ------------------ | --------------- | -------- | -------------------- | --------------------- |
| `source_record_id` | `UUID`          | no       | —                    | source_records.id     |
| `brand_id`         | `UUID`          | yes      | —                    | brands.id             |
| `fragrance_id`     | `UUID`          | yes      | —                    | fragrances.id         |
| `release_id`       | `UUID`          | yes      | —                    | fragrance_releases.id |
| `variant_id`       | `UUID`          | yes      | —                    | fragrance_variants.id |
| `note_id`          | `UUID`          | yes      | —                    | notes.id              |
| `accord_id`        | `UUID`          | yes      | —                    | accords.id            |
| `perfumer_id`      | `UUID`          | yes      | —                    | perfumers.id          |
| `family_id`        | `UUID`          | yes      | —                    | fragrance_families.id |
| `confidence`       | `NUMERIC(5, 4)` | yes      | —                    | —                     |
| `review_status`    | `VARCHAR(24)`   | no       | pending_review       | —                     |

### `field_provenance`

| Column                | PostgreSQL type            | Nullable | Default / derivation | References             |
| --------------------- | -------------------------- | -------- | -------------------- | ---------------------- |
| `entity_link_id`      | `UUID`                     | no       | —                    | source_entity_links.id |
| `field_path`          | `TEXT`                     | no       | —                    | —                      |
| `value`               | `JSONB`                    | yes      | —                    | —                      |
| `value_state`         | `VARCHAR(24)`              | no       | —                    | —                      |
| `selection_status`    | `VARCHAR(24)`              | no       | candidate            | —                      |
| `collected_at`        | `TIMESTAMP WITH TIME ZONE` | no       | —                    | —                      |
| `transformations`     | `JSONB`                    | no       | '[]'::jsonb          | —                      |
| `usage_rights_status` | `VARCHAR(24)`              | no       | pending_review       | —                      |
| `rights_evidence`     | `TEXT`                     | yes      | —                    | —                      |
| `confidence`          | `NUMERIC(5, 4)`            | yes      | —                    | —                      |

### `media_assets`

| Column               | PostgreSQL type | Nullable | Default / derivation | References             |
| -------------------- | --------------- | -------- | -------------------- | ---------------------- |
| `entity_link_id`     | `UUID`          | no       | —                    | source_entity_links.id |
| `source_url`         | `TEXT`          | no       | —                    | —                      |
| `attribution`        | `TEXT`          | yes      | —                    | —                      |
| `license_identifier` | `TEXT`          | yes      | —                    | —                      |
| `license_url`        | `TEXT`          | yes      | —                    | —                      |
| `rights_evidence`    | `TEXT`          | yes      | —                    | —                      |
| `usage_status`       | `VARCHAR(24)`   | no       | pending_review       | —                      |
| `storage_status`     | `VARCHAR(24)`   | no       | pending_review       | —                      |
| `storage_path`       | `TEXT`          | yes      | —                    | —                      |

### `data_review_queue`

| Column                | PostgreSQL type            | Nullable | Default / derivation | References            |
| --------------------- | -------------------------- | -------- | -------------------- | --------------------- |
| `source_record_id`    | `UUID`                     | no       | —                    | source_records.id     |
| `field_provenance_id` | `UUID`                     | yes      | —                    | field_provenance.id   |
| `release_id`          | `UUID`                     | yes      | —                    | fragrance_releases.id |
| `reason`              | `TEXT`                     | no       | —                    | —                     |
| `status`              | `VARCHAR(24)`              | no       | pending              | —                     |
| `context`             | `JSONB`                    | no       | '{}'::jsonb          | —                     |
| `reviewer`            | `TEXT`                     | yes      | —                    | —                     |
| `resolution`          | `TEXT`                     | yes      | —                    | —                     |
| `resolved_at`         | `TIMESTAMP WITH TIME ZONE` | yes      | —                    | —                     |

## Operational and legal boundaries

`ingestion_runs.sanitized_errors` and `data_sources.error_history` must contain only
bounded sanitized diagnostics, never tokens, raw HTTP bodies or private agreement
contents. `rate_limit` and evidence are structured policy metadata, not proof that
access is enabled. All seven candidate adapters remain unconditionally disabled.

Media `source_url`/`license_url` are untrusted references, not download instructions.
A storage path requires approved storage rights/evidence; public usage needs its
own reviewed license. No image is downloaded by the seed or this database layer.
Revocation must suppress future exports and purge retained payloads/paths as required
by the agreement; no public export/retention job is implemented in Phase 2A.

Source links intentionally use explicit target FKs instead of an arbitrary target
UUID. Extending them to a new canonical entity type requires a migration and XOR
check update. Aliases can be ambiguous across owners; review, never silently merge.
Original source-specific data belongs only in permitted payloads and field claims.

See `database-schema.md` for constraint/index details, deletion behavior, migration
operational risks and future versioned API/PWA mapping. There are no new public
catalog endpoints or automatic merger in this phase.
