# Phase 2L — offline collection intelligence

Phase 2L builds on Phase 2K without activating any source. All examples are
original synthetic records. PRs #8–#11 remain unmerged; the Vercel demo, separate
PWA, production deployment and real collection are outside this change.

## Reused components and operational boundaries

The existing `Record`, independent fixture adapters, authorization grants,
pinned-address transport, retry budgets, leases, checkpoints, atomic staging,
quality checks and manual publication system remain authoritative. There is no
new database schema, paid dependency, canonical merge or automatic publication.

Operational collector changes are additive: terminal runs and transient retries
retain sanitized HTTP status/cause metadata; summaries explain failure categories
and health. Socket deadlines distinguish timeout failures. Authorization still
precedes transport; 401/403 stop, retries remain bounded and cannot bypass access
restrictions. Health reports do not grant rights or enable schedules.

The new matching/index, response inspector and priority planner run offline. The
multi-source rehearsal adds an `intelligence` report while retaining Phase 2K's
original comparison and checkpoint formats. The priority planner returns an
unsigned plan with `dispatch_allowed=false` and `schedule_enabled=false`; it is
not a durable queue or an operational scheduler replacement.

## Identification, claims and extraction

Unicode case, spacing, punctuation and diacritic normalization generate candidate
labels; original values remain untouched in source observations. Claimed aliases
can link candidate labels, including explicitly supplied translations, but never
establish verified identity. Manufacturer is retained separately from brand.
Missing information stays missing. Related-product references, flankers, release
years, editions/reformulations, concentrations, packaging, sizes and GTINs trigger
separate review guards rather than inferring a shared product.

The existing REST/JSON, CSV and embedded-JSON HTML extractors are exercised by
local contracts. Fixture mapping additionally preserves manufacturer, name alias
and related-fragrance claims. `middle` maps explicitly to `heart`, recording the
transformation; conflicting middle/heart lists fail validation. Elixir is retained
as a strength descriptor with unknown canonical concentration, never assumed to
mean Parfum. Notes, accords, perfumers, family, sizes and identifiers continue
through existing validation.

**Fragrantica-shaped and Parfumo-shaped fixture adapters are invented contracts,
not verified live parsers.** No current website compatibility is claimed. Live
adapters need reviewed authorized examples, schema contracts and activity approval.

## Explainable matching and review

`collection/intelligence.py` returns reasons, evidence points, caps, missing fields,
conflicts, variant flags and review status. Full observations retain each source's
values; pair field-provenance pointers identify both observations. A conflict does
not overwrite a claim or select a factual winner.

| Evidence                                                  |       Points |
| --------------------------------------------------------- | -----------: |
| Normalized brand agrees                                   |           30 |
| Brand orthographic variant / claimed alias                |      25 / 20 |
| Normalized fragrance name agrees                          |           30 |
| Name orthographic variant / explicit alias / related name | 25 / 20 / 10 |
| Known concentration agrees                                |           20 |
| Known release year agrees                                 |           10 |
| GTIN agrees                                               |           10 |

Scores are deterministic identity-evidence points, **not probabilities, factual
accuracy or completeness**. Existing completeness reporting remains separate;
factual accuracy cannot be established by this fixture exercise.

Review guards cap scores at 79; missing concentration/year caps at 69;
flanker/edition/year/strength uncertainty caps at 49; different brand/name/known
concentration or manufacturer-as-brand caps at 20. Unusable punctuation-only
identity labels require correction and score zero. GTIN agreement never overrides
these guards. Multiple candidate relationships cap scores at 69. Conflicting
notes, accords, perfumers and families remain explicitly reported even where
identity evidence is strong. Bottle/package differences require variant review.

Only unconflicted, single-candidate evidence scores of at least 80 are labelled
`ready_for_human_review`. Every outcome has `automatic_merge=false` and
`publication_authorized=false`. No model writes a canonical entity.

## Bounded candidate indexing

The standalone index accepts at most 50,000 observations and 100,000 evaluated
pairs; defaults are 1,000 pairs and 64 entries per bucket (maximum 128). It indexes
normalized brand/name and explicitly claimed aliases, then prefers a rare shared
name token. At most five brand aliases and ten tokens per name are indexed.
Same-stream pairs are skipped; duplicate observation IDs fail. Phase 2K's smaller
5,000-observation/100-page rehearsal bounds are unchanged.

This is deliberately non-exhaustive entity resolution. Token buckets, aliases and
pair caps can omit valid candidates. Overflow/truncation counts and
`complete_within_candidate_rules=false` expose this; false must never be interpreted
as proof that no duplicates exist. No approximate-name-only global scan is claimed.

## Diagnostics and scheduling simulation

`collection/diagnostics.py` inspects supplied bounded responses without HTTP. It
reports schema/format changes, safe missing-field paths, repeated page hashes and
incomplete pagination when an expected final count is supplied. It cannot infer
the true size of an undocumented upstream catalog. Access failures, rate limiting,
timeouts and upstream errors have distinct actions. Reports omit response bodies,
exception text, credentials and untrusted field names.

`collection/priority.py` simulates priority/due-date ordering, request fingerprints,
per-source rate-budget snapshots, blocked-source health, bounded retries and one
in-flight task per source. Exponential delay is bounded; Retry-After can extend it
within the simulation limit. It performs no requests or database writes. Actual
collection must still use existing authorization, leases, rate limits, persistent
checkpoints and cancellation. Existing rehearsal changed-record/resume behavior
and collector interrupted-run/idempotency tests are retained.

## Reproduce

```bash
pnpm catalog:intelligence
pnpm catalog:rehearse
pnpm catalog:intelligence --benchmark --size 10000
pnpm catalog:intelligence --benchmark --size 50000
pnpm catalog:intelligence --benchmark --size 10000 --hotspot
RUN_DB_TESTS=1 pnpm test
```

Benchmarks include generated records, indexing and scoring under `tracemalloc` in
one Python process. They exclude HTTP, PostgreSQL, persistent import and public
API serving; they are not production throughput measurements. See the audit for
measured timings, memory, candidate retrieval and limitations.
