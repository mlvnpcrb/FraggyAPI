# Ingestion architecture

## Phase boundary and current implementation

The initial repository had no application or phase plan. This addition establishes
Phase 1: source registry, independent adapter skeletons, shared source-record
interface, configuration, and fixture tests. It adds no HTTP clients, scheduler,
database, canonical merger, or public API. Live collection always raises
`LiveIngestionDisabled`, independently of registry flags. The registry loader also
rejects Phase 1 activation. Production pipeline behavior below is a design contract
for future implementation, not a claim of completed ingestion.

Adapters implement `SourceAdapter.parse_fixture` and inherit the disabled `collect`
entry point. Each has its own module so later authorized parsers remain isolated.
Fixtures represent invented standardized input, not captured HTML or validated site
layouts. They cannot establish compatibility with current websites.

## Proposed later-phase flow

Reviewed source configuration → authorization gate → rate-limited collection →
immutable source record → normalization → candidate matching → manual review or
canonical linkage → rights-aware field selection → licensed API projection.

Separate normalization/, matching/, provenance/, and jobs/ modules will be introduced
when their phases begin. Keep adapters concerned with source extraction; do not put
cross-source identity or public export policy in parsers.

## Normalization contract

Preserve raw source information in a source-record store separate from canonical
entities. The fixture payload sketches these nullable/optional normalized fields:

| Field                                | Proposed representation                                                                   |
| ------------------------------------ | ----------------------------------------------------------------------------------------- |
| brand_name, perfume_name             | Display strings, plus derived matching keys                                               |
| concentration                        | Controlled vocabulary with original label retained                                        |
| release_year                         | Integer or null; preserve uncertain source claims                                         |
| perfumers                            | List of names; later link stable person identifiers                                       |
| gender_positioning, fragrance_family | Normalized labels with raw values retained                                                |
| notes                                | Object containing top, heart, base lists; unknown pyramid placement stays source-specific |
| main_accords                         | List of normalized labels with original ordering retained                                 |
| bottle_sizes_ml                      | List of positive numbers; keep original units in source record                            |
| product_identifiers                  | List of scheme/value pairs, e.g. GTIN; distinguish bottle SKU from fragrance identity     |
| image_references                     | Reference metadata only, subject to rights filtering                                      |
| longevity, sillage                   | Licensed metric with scale, population, timestamp; otherwise null                         |
| last_verified_at                     | Timezone-aware timestamp or null; never substitute collection time                        |
| source_specific                      | Unmapped source attributes, isolated from public canonical fields                         |

`SourceRecord` carries source_id, source_record_id, source_url, collected_at, payload,
and usage_rights_status. Source URLs identify records; they are not fetch instructions.
Missing values are unknown, not empty claims. Preserve original spelling and Unicode;
derive Unicode-normalized, case-folded whitespace-normalized matching keys separately.
Version transformations, units, vocabularies and schema. Invalid records should be
quarantined with actionable errors rather than silently coerced.

## Matching and review design (not implemented in Phase 1)

Generate candidates by normalized brand/name and reliable identifiers. Concentration
conflicts are a hard exclusion, including when an identifier conflicts. Track flankers,
editions and reformulations explicitly; never strip distinguishing names for merging.
Unknown concentration, edition or conflicting years require review rather than guessing.
Bottle-level identifiers must resolve their parent identity before comparison.

An initial proposed score is brand 0.25 + fragrance name 0.35 + concentration 0.25 +
release year 0.15, using exact normalized comparisons. Do not renormalize missing
components to inflate confidence. Exact verified identifiers may prioritize candidates
but cannot override concentration, flanker or reformulation conflicts. Similar names
only retrieve candidates; they never authorize merging.

Provisional policy: score >= 0.95 is eligible for automatic linkage only with all identity
fields known, no conflicts, and a unique candidate; 0.70–0.95 or any ambiguity goes to
manual review; lower scores remain separate. These thresholds need calibration against
labeled fixtures before automatic matching is enabled. A reviewer records candidate IDs,
evidence, decision, time and reason. Make links reversible and keep audit history.

## Field provenance and public distribution design

Each later imported field must have its own provenance record, including nested notes
and individual list elements: canonical entity/field path, source identifier, original
record reference, collection timestamp, ordered transformations with versions and
inputs, usage rights status and evidence reference, confidence in [0,1], and verification
time. Confidence is evidence-based and independent of rights status. Preserve competing
claims; do not silently overwrite disagreements with the most recent source.

Public projections must check commercial reuse permissions at field level, apply required
attribution, and exclude unreviewed/restricted descriptions, reviews and images. Source
records must not be returned wholesale by the public API. Rights revocation needs export
suppression, cache invalidation, and retention/deletion handling without losing the
minimum permitted audit record. Synthetic fixtures carry `fixture_only` rights and must
never become production catalog content.

## Future operational requirements

Use idempotent jobs keyed by source, source record and content/version; durable checkpoints;
per-source concurrency and request budgets; bounded retry/backoff respecting Retry-After;
quarantine and dead-letter handling; sanitized structured errors; metrics and alerting.
Validate licenses before each job and public export. Never log credentials. Source failures
must not take down other sources or promote incomplete records. Database constraints,
transactions, retention policy and migrations belong to the later persistence phase.

## Local validation

Requires Python 3.10+ and no third-party packages or credentials. From `/workspace/FraggyAPI`:

```sh
python -m unittest discover -s workers/ingestion/tests -v
```

Tests exercise all seven adapters, local record preservation, invalid fixture rejection,
network blocking, registry activation rejection, and duplicate-source rejection. No live
service needs starting in Phase 1. Use the existing checkout; do not create a worktree
for ordinary cloud tasks.

## Phase 1B application foundation

The repository now also contains `apps/web`, `apps/api`, local Compose PostgreSQL,
and Alembic history initialization. These do not activate ingestion: no catalog
models, HTTP source clients, canonical merger, or ingestion scheduler were added.
See the root README for the complete setup and `docs/phase-1-audit.md` for current
application verification. The Phase 1 contracts above remain the boundary for the
source adapters; later pipeline behavior remains design-only.

## Phase 2A persistence

The twenty-table catalog/provenance schema now implements the persistence boundary
outlined above. See `database-schema.md`, `data-dictionary.md` and the Phase 2A audit.
Source records, candidate links and field claims are separate from canonical entities;
storage rights do not imply commercial reuse rights. Synthetic fixture records and
review examples are explicit opt-in only. This adds no live collectors, matcher,
merger, public catalog API or PWA data client. All seven source adapters remain disabled.
