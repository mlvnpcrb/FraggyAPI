# Phase 2N — multi-source pilot preparation

Prepared 2026-10-20 (Asia/Manila). Local branch descends from Phase 2M commit
`32821aa761c98a84d0179ba6c473c3e70c11fefa`. PRs #8–#13 remain unmerged.
No push, PR, Vercel configuration/demo/PWA change, genuine request/import,
image acquisition, publication or paid provisioning is authorized in this phase.

## Operational implementation

The public PostgreSQL search remains read-only and independent of transport.
After it returns, a trusted operator can provide a private local snapshot:

```bash
pnpm catalog:collect enrich-plan data/examples/enrichment-search-snapshot.json
# Optional local-only intent admission, never network dispatch:
pnpm catalog:collect enrich-plan data/examples/enrichment-search-snapshot.json --enqueue
```

The supplied query is real text, not a claim that the catalog contains that perfume.
No fictional representation of Lattafa Khamrah is inserted. The snapshot has no
record: planning reports missing fields and independent provider candidates. With
an actual reviewed local result, supply its UUID, concentration, supported Record
values and actual per-field verification dates. Missing, never-verified, future
verification dates or verification older than 90 days request enrichment. This
90-day planning threshold is not a source license expiry or factual accuracy score.
A fresh complete snapshot produces no intents. Snapshots are trusted operator
inputs, not an anonymous/public enqueue endpoint or a storage authorization.

`--enqueue` uses Phase 2M's provider/digest uniqueness, transaction boundaries and
cooldowns. It creates existing EnrichmentIntent rows only, not collection runs.
Unknown providers/fields fail closed. All real dispatch stays blocked. Repeated
queries deduplicate; each source gets an independent intent. Existing Collector
leases, checkpoints, cancellation, retry/backoff, source budgets, staging and
review are reused, not replaced with another queue or engine.

Two or more private observations can be compared by the bounded
`compare_observations` function (maximum ten). The existing rights-checked
`enrich-compare` command now returns richer field evidence after current rights
checks. Its existing review item retains references/states, without another copy
of raw/normalized values; re-running reconstructs those from authorized snapshots.
Pairwise comparisons can accumulate multiple sources in that queue.
No new canonical tables or migration are required.

For each supported field the report preserves original and normalized values,
source and record references, source URL, collection date, reviewed verification
date if known, reliability assessment/evidence if supplied, and conflicts/missing
values. Note position is part of normalization, so top Cedar and base Cedar
conflict. EDP and eau_de_parfum normalize together. Identity heuristics remain
separate from completeness, reliability and factual confidence. Unassessed facts
remain explicitly unassessed, not numeric probabilities. Imported source metadata
cannot grant itself reliability or storage rights.

Reliability is per field, never a universal provider ranking. A trusted review
caller may attach a named reviewer, evidence reference, date and brand_authored,
corroborated, limited or unknown assessment. A brand-authored claim merits human
attention for its own product, not automatic acceptance. Assessments dated before
collection or in the future do not contribute verified evidence. The durable
comparison defaults to unknown assessments rather than inventing them. Conflicts
retain all observations, with no preferred claim or automatic merge. A reviewer
must select claims through existing catalog/provenance tools, and publication
still requires independent current rights. Later publication is a separately
approved activity, not part of this private pilot.

Existing Record mapping covers names, concentration, year, notes/pyramid, accords,
perfumers, families, sizes, GTINs and version labels. Gender positioning and image
rights are explicitly unsupported in this new comparison contract; they are not
inferred. The existing media approval pipeline remains separate and no image
requests are proposed. Separate concentrations/flankers/reformulations must pass
existing identity review; equal names never collapse their identities.

## Source candidates and authorization status

This phase does not refresh source legal evidence through live requests. The
prior [source decision and pinned official schema references](first-25-source-decision.md),
[Phase 2J review](phase-2j-sources.md) and
[multi-source coverage assessment](phase-2k-source-coverage.md) remain the evidence
record. Prior proxy denials and stale/incomplete evidence are blockers, not implied
permission. No source is currently verified eligible for live activity here.

| Candidate                                 | Technical contract / useful fields                                                                                                                 | Access, reuse and outstanding requirements                                                                                                                                                                                                                                                                                               |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Open Beauty Facts                         | Offline parser for publisher-documented structured search: barcode, title, brand, category, quantity, modification time; raw observations separate | Pending: refresh OBF-specific endpoint rules, ODbL/DbCL storage/derived-database/commercial API terms, attribution and monitored User-Agent/usage requirements. Shared-server rate guidance is not verified OBF policy. Publisher's 100,000+ cosmetics statistic is not perfume coverage. No notes, concentration or perfumers invented. |
| Wikidata                                  | Existing reviewed-ID SPARQL parser: English product/brand labels and entity IDs                                                                    | Structured data CC0 evidence exists historically; current endpoint rules, contact, discovery scope, genuine product identity and exact IDs still need review. Sparse fragrance coverage unverified; no images or label-derived concentrations.                                                                                           |
| Official brand catalogs/feeds             | Existing separate fixture feed/HTML contract; potential authoritative product names, concentrations, launch claims and notes                       | No named reusable brand feed or contract verified. Direct permission for automation, retention and redistribution required; public page access alone insufficient. Lattafa is a desired coverage candidate, not an authorized provider or coverage claim.                                                                                |
| Fragrantica                               | Separate fictional fixture adapter; potentially rich notes, accords, years, perfumers                                                              | Permission required/unverified. No working live parser claimed. No requests until explicit access/storage/reuse evidence; never bypass anti-bot or access denials.                                                                                                                                                                       |
| Parfumo                                   | Separate fictional fixture adapter; potentially rich notes, perfumers and release information                                                      | Permission required/unverified, same independent licensing/access gates; not cleared by other providers' grants.                                                                                                                                                                                                                         |
| Other fragrance datasets/distributor APIs | Existing independent skeletons and future provider registration                                                                                    | No live schema/coverage/reuse grant assumed. Basenotes, Wikiparfum, Perfume Society, PerfumeMaster and ScentBase stay disabled. Free-tier/code licenses do not establish database rights.                                                                                                                                                |

## Proposed 25-fragrance multi-source pilot — NOT authorized

Goal: at most 25 distinct reviewed genuine fragrance identities, with multiple
independent sources contributing where evidence permits. Target overlap is not
promised. Brand/SKU/product identities and concentrations need manual review.
Include Lattafa Khamrah only if an eligible source actually supplies it. If fewer
than 25 qualify or no cross-source overlaps exist, report the shortfall; do not
expand collection or invent data. All sources may ultimately be unsuitable.

Proposed requests, not executed and not executable grants:

1. Open Beauty Facts: GET the following URL for pages 1–4 only. Page size 25 means
   up to 100 candidate SKU observations, not 100 canonical fragrances.

```text
https://world.openbeautyfacts.org/api/v2/search?categories_tags_en=perfumes&page=1&page_size=25&fields=code,product_name,brands,brands_tags,categories_tags,quantity,product_type,last_modified_t
```

Only `page` may vary from 1 to 4. Maximum four attempts total including retries,
one connection, at least ten seconds between starts, ten-second timeout, 2 MiB
response ceiling, maximum one retry subject to the total budget. Honor stricter
verified endpoint requirements and Retry-After or stop. Existing parser bound is
25 products/page. Exact fields and raw keys need reviewed manifest permissions.

2. Wikidata: proposed bounded discovery GET for the desired example, not a query
   proving fragrance classification:

```text
https://www.wikidata.org/w/api.php?action=wbsearchentities&search=Lattafa%20Khamrah&language=en&type=item&limit=5&format=json
```

At most one discovery request plus one retry. Search can return brands or other
entities; a human must inspect references and product identity. This search API
contract is not wired to a live collector; source-specific discovery authorization
and mapping tests are prerequisites. No other names/queries are implicitly
approved. No fictional Q IDs may be substituted.

After manual candidate review, existing `collection.wikidata.query` generates
exact SPARQL from a frozen list of at most 25 approved genuine Q IDs for
`https://query.wikidata.org/sparql`, requesting item/itemLabel/brand/brandLabel via
P1716. One page plus one retry, one connection, at least one second between starts,
ten-second timeout, 2 MiB response bound. The exact final SPARQL cannot be frozen
until IDs are reviewed; submit it separately before execution. Brand relation alone
does not prove fragrance identity. All unsupported fields remain missing.

These are at most eight HTTP attempts across two separately approved sources:
four OBF, two discovery and two reviewed-ID attempts. Retry limits consume these
budgets; there is no automatic crawl or periodic refresh. Each reviewed source
config must enforce its own budget; this document does not activate it. The
existing four-attempt/day enrichment cap is not raised by this proposal. Stricter
policy wins. No third brand request exists until a named free authorized feed and
exact endpoint/body/budget are approved; Fragrantica/Parfumo receive zero requests.

## Storage, review, rollback and approvals

Destination proposal: existing development host, dedicated UUID-owned loopback
PostgreSQL database and private 0700 directory / 0600 files, using existing staging,
SourceRecord revisions, review and audit. No database is provisioned by this plan.
No application catalog, Vercel bundle, public API or PWA imports. Estimated added
service cost ₱0, conditional on existing local compute/storage; no purchase or
cloud provisioning. Respect underlying licenses even for private combined data.

Proposed retention: raw/staged content 30 days, non-content audit hashes/counts and
rights decisions 90 days. Verify source-specific retention/withdrawal constraints
before approval; no automatic cleanup scheduler is activated. Rollback cancels only
owned runs, revokes their collection permission, removes only ownership-verified
pilot DB/files, preserves a non-content audit and does not touch existing catalog
or shared sources. Keep source revocation distinct from deleting the entire pilot.
Tests cover transaction rollback and replay, existing import/revocation tests cover
rights and canonical safeguards. Real end-to-end rollback remains a pilot gate.

Required before genuine requests: fresh source-specific licensing/access/robots
and attribution evidence; exact discovery scope and final record IDs/queries;
verified monitored contact supplied through secure environment configuration (not
chat or Git); approved storage destination/retention; exact fields and independent
storage/reuse/publication decisions; parser/live schema compatibility; explicit
user approval for each activity. No image or public publication approval is sought.
GitHub delivery also needs separate approval: Phase 2M's branch-specific Vercel
skip rule does not cover this Phase 2N branch. No push is safe to assume.
