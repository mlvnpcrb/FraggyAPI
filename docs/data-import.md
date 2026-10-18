# Licensed local data import

> Phase 2D extends this Phase 2C baseline with explicitly reviewed structured
> attribution. Follow [the attribution contract](attribution-contract.md) and
> [the pilot workflow](pilot-import-workflow.md) for attributed sources; old
> unattributed manifests retain their digest and behavior.

Phase 2C adds trusted **local CLI** imports, not a public upload endpoint or a
website scraper. Parsing, authorization, normalization/matching, transactional
staging, canonical writing and publication are separate modules under
`apps/api/fraggy_api/importing`. The existing 20-table schema is sufficient; there
is no new migration. All seven website adapters remain disabled and pending review.

## Commands and stages

Run from the repository root after `bash scripts/setup.sh`, healthy Docker Compose
and Alembic upgrade. No new dependencies are required. Commands refuse production
and non-loopback databases in this phase; no cloud database is modified.

```sh
pnpm catalog:import -- --file data/examples/fragrances.csv --manifest data/examples/source-manifest.json --dry-run
pnpm catalog:import -- --file data/examples/fragrances.json --manifest data/examples/source-manifest.json --batch-size 100
pnpm catalog:manage pending --source fictional-workshop-import
pnpm catalog:manage results --run-id RUN_UUID
pnpm catalog:manage inspect --record-id RECORD_UUID
pnpm catalog:manage source-status --source fictional-workshop-import
pnpm catalog:manage provenance --fragrance-id FRAGRANCE_UUID --limit 50 --offset 0
```

UUID placeholders must be replaced with actual output values. `catalog:manage`
also supports `source-review`, `review`, `publish`, and `revoke`; see the source
and catalog-review documents. The equivalent Python entry point is
`.venv/bin/python -m fraggy_api.importing.cli COMMAND ...`.

The stages are: select file → bounded parse/validation → verify trusted source
review → normalize for matching → candidate detection → read-only preview → stage
snapshot/review item → explicit canonical decision → separate field publication.
Nothing automatically merges or publishes. Even an exact candidate requires an
operator decision. Ordinary import stores source snapshots and queues, not
canonical fragrance rows. `--dry-run` runs SELECTs only and rolls back its session;
it never creates sources, runs, snapshots, queues or temporary database tables.

## File schema

CSV is UTF-8 (optional BOM) with a header, standard quoted values/newlines and
optional columns. Array-valued cells contain JSON arrays, including notes as an
array of objects. JSON is a top-level array of records. JSONL contains one record
per nonblank line. Equivalent fictional files are in `data/examples`.

| Field                                   | Required / type                                                                            |
| --------------------------------------- | ------------------------------------------------------------------------------------------ |
| `source_record_id`                      | Required nonblank string, at most 160 characters; stable provider identity                 |
| `brand_name`, `fragrance_name`          | Required nonblank Unicode strings, at most 200 characters                                  |
| `source_url`                            | Optional HTTP(S) reference up to 2048 characters, no user/password; never fetched          |
| `brand_aliases`                         | Optional array of names, at most 20                                                        |
| `family`, `collection`, `version_label` | Optional names, at most 200 characters each                                                |
| `concentration`                         | Optional label, at most 80 characters; EDP/EDT/EDC/Parfum/Extrait and canonical enum forms |
| `release_year`                          | Optional integer 1000–2999; missing remains null                                           |
| `perfumers`                             | Optional array of up to 10 names                                                           |
| `notes`                                 | Up to 40 `{name, aliases?, position?}` objects; up to 20 aliases per note                  |
| `notes[].position`                      | `top`, `heart`, `base`, `unknown` (default); never inferred                                |
| `accords`                               | Optional array of up to 20 names                                                           |
| `bottle_sizes_ml`                       | Optional positive finite milliliter values, up to 20, maximum 999999, at most 3 decimals   |
| `gtin`                                  | Optional digits string, length 8/12/13/14 and valid check digit; leading zeros preserved   |

A GTIN with multiple bottle sizes is rejected: one identifier cannot be silently
assigned to different packages. Check digits validate structure, not allocation or
real product identity. This importer never invents missing identifiers. Unknown
concentrations stay null; unsupported labels fail validation rather than being
guessed. Families are normalized taxonomy identities; collection is preserved as
a private fragrance claim/snapshot attribute because the schema has no collection
entity. Perfumers are not merged on name alone. Review-created variants preserve
explicit milliliter originals. Public DTOs still omit variants, perfumers,
collection and licensed descriptive/media content.

Limits are 2 MiB actual read, 1–1000 rows, nesting depth 6, at most 50 object/header
fields, and 4096 characters per generic string before stricter typed limits.
Duplicate JSON keys, duplicate provider IDs in a file, invalid encodings, malformed
CSV/JSON, unknown fields, controls such as NUL, non-finite numbers and ambiguous
GTIN/size assignments fail safely. Errors identify row/categories without echoing
payloads, database URLs or exception text. File paths are local and never resolved
as network URLs. No format evaluates code, formulas, HTML or YAML tags.

Original validated values are stored only with verified storage rights. Matching
keys use NFKC, lowercase and whitespace cleanup, consistent with database keys.
Canonical display names use NFKC/whitespace cleanup; original source strings remain
in snapshots. Concentration synonyms map to the existing controlled vocabulary.
Field provenance records transformation version, original field reference, source
snapshot, collection time, selected/conflicting/unknown state and separate rights.
Note positions, aliases, size and identifier claims are retained privately.

## Transactions, counters and resumption

Each batch (default 100, configurable 1–200) is one transaction, including its run,
snapshots and review items. A late error rolls back the whole current batch. Prior
successful batches remain committed and are returned in a safe partial-failure
report. Re-running the same file resumes safely: unchanged source/provider IDs,
manifest digests and record content digests reuse their existing snapshot UUIDs.
No completed decision is reapplied. Changed content creates a new source revision
and new pending review, preserving earlier claims and canonical UUIDs.

Import summaries include `inserted` snapshots, `skipped` unchanged snapshots,
`linked`/`rejected` previously resolved snapshots and `review_required` pending
snapshots, plus `quarantined` new hash-only entries. State counters overlap with
`skipped`; they are not a partition to sum into a row count. Canonical review
commands separately report inserted releases or explicit existing-release links.
`results` reports each batch's seen/accepted counts and paginated record states.

A transaction advisory lock serializes these trusted writers across sources;
review items also lock their row. Public SELECTs continue through MVCC. SQL
statement timeouts remain bounded by the existing settings; lock contention fails
safely and can be retried. This is a bounded local batch workflow, not a distributed
queue. Split larger datasets into files with stable provider IDs and the same
reviewed manifest, then resume using the same commands. No paid workers or search
services are required.

All generated reports are JSON, with strings escaped for terminals. There is no
CSV export/report writer, so spreadsheet formula values are never emitted as
executable CSV cells. CSV imports preserve original data as data; do not convert
private JSON values into spreadsheet cells without a separately reviewed escaping
policy. Real datasets, private manifests and reports belong outside Git or under
ignored `data/private`, `data/imports`, and `data/reports`. Only invented examples
are committed; never put source credentials or agreement text in manifests.
