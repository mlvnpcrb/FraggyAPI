# Catalog quality checks

Phase 2E adds `fraggy_api.quality`, a local operator diagnostic layer over the
existing schema/import/publication architecture. It never corrects, merges,
invents fields, approves rights, changes source status or enables collection.

```bash
pnpm catalog:quality -- --format json
pnpm catalog:quality -- --format text
pnpm catalog:quality -- --format json --fail-on error
```

The CLI rejects production and non-loopback databases before checkout. PostgreSQL
executes a **REPEATABLE READ, READ ONLY** transaction; reports reflect one snapshot
and attempted writes are rejected by PostgreSQL. Sessions roll back and engines
close. Output goes to stdout only. No admin endpoint, upload or scheduler exists.
Exit 0 means report generated, 1 means command failure, and 2 means an explicitly
requested error/warning gate failed or the report was incomplete. Default `none`
does not hide findings; it permits an operator to inspect a partial report.

## Checks and severity

| Check                            | Interpretation                                                                                                                                                                                  |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Missing house/fragrance identity | Error for missing/blank required names or brand link. Schema normally prevents persistence; diagnostics independently query stored data                                                         |
| Concentrations                   | Invalid enum is an error; null is an informational unknown. EDT/EDP/Parfum are separate, never inferred from name                                                                               |
| Years                            | Warning outside 1700 through current UTC year + 2; this heuristic is intentionally stricter than the schema's 1000–2999 envelope, not a universal historical truth                              |
| Brands/aliases                   | Normalized duplicate house names, aliases ambiguous across owners and aliases shadowing another canonical name are warnings; no automatic renaming                                              |
| Duplicate candidates             | Same normalized house/name release blocks; matching known concentration/year gives only `possible_duplicate`, never identity proof                                                              |
| Versions/flankers                | Version/reformulation observations are informational; name-prefix candidates require manual review and never collapse separate fragrance lines                                                  |
| Source conflicts                 | Conflicting field claims are warnings, retained independently of canonical selection                                                                                                            |
| Provenance                       | Warn when a canonical house/fragrance/release/variant/note/accord/perfumer/family lacks a source link with a claim; existence is not licensing approval                                         |
| Relationships/notes              | Check every modeled FK with NOT EXISTS, same-line reformulation identity, allowed note positions; unknown position is informational                                                             |
| URLs                             | Warn about source/media references unsafe for the public HTTPS attribution contract. Private HTTP references may remain stored; no URLs are fetched or echoed                                   |
| Credits                          | Missing, expired, unsupported or unaccepted required source attribution is an error; private legal evidence is never printed                                                                    |
| Publication                      | Selected known claims lacking approved link/record/source/field permissions are warnings. Stale scalar claims are warnings; exact public identity predicates determine visible fragrance counts |

Constraints are not disabled to fabricate corrupt rows for tests. Existing
PostgreSQL tests already exercise constraint rejection. The independent integrity
queries are useful for restored/legacy databases as well as current constrained
ones. Nulls remain unknown; conflicting values are not silently resolved.

`selected_claims_with_rights` counts selected claims meeting rights conditions;
it is **not** a count of all currently publishable values. Stale values are reported
separately. `fragrances_development` and `fragrances_production` use the same current
name/slug/brand relationship grants as the API, including its production synthetic
exclusion. They do not assert that every release/optional field is publishable.
Source attribution coverage measures policy completeness, not legal correctness or
an approval of each contributing record. Zero blockers does not establish clearance.

## Bounded analysis and privacy

SQL computes totals, percentages and issue counts. Finding samples contain at most
25 UUIDs, sorted deterministically. Counts can overlap (one record can have several
issues); severity totals are observations, not unique affected records. Alias
comparisons use existing normalized keys; stable UUIDs remain independent of names.

Exact-name release blocks examine at most 21 releases each, then at most 1,000
candidate pairs. Related-name analysis uses the first normalized token within a
house, at most 21 fragrance lines per block, and shares that pair budget. This
heuristic deliberately produces review candidates, not a comprehensive flanker
ontology. GTIN/bottle-level identity remains the existing import matcher's job.
Two same-name/same-year/same-concentration rows still require manual review of
flankers, versions and variants. Cross-brand names are not merged.

Source details are capped at 1,000 entries; URL checking streams at most 100,000
non-null references per field. Any source/URL/candidate cap makes `complete=false`;
never interpret clipped samples as a clean full-catalog audit. Field/table totals
remain SQL aggregates. Statement timeouts still apply; command failure is not a
passing report. No query count is claimed constant across evolving schema checks.

Reports expose counts, canonical/finding UUIDs, source UUID/type/status and category
codes—not raw names, source URLs, snapshots, claim values, source keys, agreements,
reviewer identities, reasons or transformation logs. Exception output contains
safe categories/type names only. Human output includes the same aggregate sections,
source coverage and duplicate categories. Treat operational reports as private and
keep them in ignored storage. This is a quality diagnostic, not a replacement for
human data/license review.

## Starter import gate

The existing bounded parser supports an explicitly authorized 100–300-record
CSV/JSON/JSONL starter. Verify supplier authority and storage/redistribution/credit
scope first, dry-run, stage, review exact/ambiguous matches, approve distinct
canonical records, run this report, resolve relevant blockers, explicitly publish
fields and inspect API/frontend credits. Re-run after revisions and withdrawals.
No genuine starter dataset is approved in this phase. Use original fictional
fixtures; do not copy real perfumes into synthetic fixtures.

See [report contract](catalog-quality-report.md), [source assessment](phase-2e-source-assessment.md)
and [pilot workflow](pilot-import-workflow.md). Phase 2F collection remains future
work requiring review and merge of Phase 2E plus verified source authorization.

Publication claim counts are limited to the currently public target/field contract;
private family/collection/variant/perfumer claims are not publication blockers.
Attribution coverage considers active approved/synthetic publication policies and
only the latest source review. Revoked/storage-only sources do not falsely become
missing-credit errors merely because older policy history required attribution.
