# Operator quality report contract

Run the report against local PostgreSQL after migrations:

```bash
mkdir -p data/reports
pnpm catalog:quality -- --format json > data/reports/catalog-quality.json
pnpm catalog:quality -- --format text > data/reports/catalog-quality.txt
```

`data/reports/` is ignored. Shell redirection is explicit operator file output;
the CLI itself only reads the database and prints stdout. Never commit real data,
private evidence or operational reports. Examples below describe invented fixtures.

## JSON sections (schema version 1)

- `generated_at`: UTC ISO timestamp for the report snapshot.
- `read_only`, `automatic_changes`: always true and zero on successful reports.
- `complete`: false if any bounded analysis is incomplete. Check this before using
  percentages/candidates for a release decision.
- `totals`: brands, fragrances, releases, notes, accords and `awaiting_review`
  (source records with pending-review/validated processing state, not queue-item
  count; a record can have multiple historical review events).
- `missing_fields`: per-field `{missing,total,percent}`; percentage is 0 for empty
  populations. Includes required identities, family, concentration, release year,
  and absent note/accord associations. Unknown is not automatically erroneous.
- `duplicate_candidates`: bounded `{left_id,right_id,classification,automatic_merge}`.
  Related-name entries identify fragrance UUIDs; exact-name entries identify release
  UUIDs. Classification distinguishes the two. Automatic merge is always false.
- `duplicate_analysis`: returned pair count, release/line block and pair bounds,
  overflow-release count, related-candidate truncation. No total-pair count is
  invented after a cap.
- `findings`: category code, error/warning/info, count, sampled UUIDs and truncation.
  A truncation finding counts one analysis event; `overflow_releases` separately
  counts rows outside the examined release blocks.
- `severity_counts`: sums of issue observations by severity, not unique rows.
- `source_coverage`: source UUID/type, retained snapshot count, authorization and
  licensing status, collection-enabled flag. Private evidence and keys excluded.
- `source_coverage_truncated`: identifies incomplete source details explicitly.
- `publication_eligibility`: current development/production fragrance counts,
  selected claim counts meeting rights, selected claim blockers. Rights-only claim
  counts do not certify current canonical value equality; stale claims are separate.
- `licensing_blockers`: sources without approved/synthetic licensing among the
  bounded source details, and selected-claim blockers. This is not a legal opinion.
- `attribution_coverage`: reviewed sources requiring credits and sources with
  complete supported credit metadata. This does not approve record publication.

Text output includes totals, severity counts, candidates, missing percentages,
source coverage, publication eligibility, blockers and attribution coverage.
It contains no raw legal evidence and uses the same meanings as JSON.

## Findings and action

Errors require investigation before release. Warnings require context: an old
historic perfume may legitimately predate the heuristic year boundary; an alias
may deliberately be ambiguous; a revoked claim should remain blocked. Informational
unknowns preserve incomplete knowledge and version distinctions. Neither absence
of findings nor an exit code of zero approves a dataset or enables collection.

A source change can restrict old grants without deleting canonical history. Field
withdrawal should increase blocked selected claims and remove that public value;
source withdrawal can remove the entire public record. An invalid/missing credit
policy hides affected public grants and creates a credit finding. Previously
served client copies still require refresh.

Automated tests cover empty reports, invalid/unknown metadata, conflicting claims,
alias ambiguities, scalar staleness, unsafe URLs, missing credits, source/field
withdrawal, distinction-preserving candidates, report truncation, JSON/text CLI
output, production/remote refusal and PostgreSQL enforcement of read-only mode.
Existing import/publication/browser regressions remain in place.

Publication claim counts are limited to the currently public target/field contract;
private family/collection/variant/perfumer claims are not publication blockers.
Attribution coverage considers active approved/synthetic publication policies and
only the latest source review. Revoked/storage-only sources do not falsely become
missing-credit errors merely because older policy history required attribution.
