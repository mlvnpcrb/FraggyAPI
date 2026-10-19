# Phase 2K — multi-source offline collection foundation

Revised 2026-10-19 (Asia/Manila). This supersedes the single-source **direction**
of [the earlier 25-record proposal](phase-2k-pilot.md); that workflow remains an
unapproved example for one possible source. Wikidata is not mandatory. No live
access, import, scheduling, images or publication is approved in this phase.

## Architecture and reuse

```text
Per-source legal/access/field review + separately approved activity
       ↓ (future live gate; currently closed)
Existing CollectionSource/Grant → HTTPTransport → Collector jobs/leases
       ↓ official API / JSON or CSV feed / individually permitted HTML
Independent source mapping → existing Record schema → normalization/quality
       ↓
Source snapshots + links + per-field provenance → staged/manual review
       ↓ duplicate candidates / separate releases / conflicts / deferred records
Separate source + record + field rights checks → canonical PostgreSQL → public API
```

The Phase 2F engine already provides request throttling, bounded timeouts/retries,
backoff/Retry-After, checkpoints, leases, cancellation, duplicate-run prevention,
change hashes, run/error reporting and disabled schedules. Phase 2C–2G provide
staging, canonical matching, per-field provenance, source attribution, manual
publication and revocation. This phase does not build a second scheduler, HTTP
client, canonical database or licensing gate. Future approved source mappers plug
into those systems after their real contracts and rights are independently tested.

### Implemented now

- `collection/offline_sources.py`: independent `FragranticaFixture`,
  `ParfumoFixture`, `OfficialBrandFixture` and `WikidataFixture` classes behind a
  common parse interface and explicit allowlist. Every `collect()` raises.
- The Fragrantica/Parfumo fixtures use **invented distinct JSON contracts**, not
  downloaded data or asserted live HTML selectors. Their schemas must not be
  represented as validated website support. No page is scraped to build them.
- Official brand fixtures reuse the existing JSON feed extractor and public
  `Record` mapping; Wikidata fixtures reuse its existing SPARQL parser. Invented
  Wikidata references are rewritten to reserved fixture URLs and never sent out.
- `collection/multisource.py`: bounded original-only observations, resumable
  fixture state, per-source identity/hash changes, cross-source review candidates,
  source disagreements, release/variant distinctions and completeness reports.
- `catalog:rehearse`: local-file driver. It has no HTTP transport, DB connection,
  import, review approval, scheduling or publication operation. Original fixtures
  live under `data/examples/multisource/`; no real exports belong there.

Existing seven website skeletons, source registry and runtime grants remain
unchanged/disabled. No new offline adapter is registered as a live `Endpoint`
transport. Extending the fixture allowlist/schema is a code review operation,
not arbitrary module loading from configuration.

## Mapping and product identity

| Field                          | Handling                                                                                                                                               |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Source/dataset/record identity | Independent tuple; opaque digest avoids delimiter collisions. Source record ID never replaces canonical UUID                                           |
| Fragrance and brand            | Original labels retained; NFKC/lowercase/whitespace comparison keys reuse existing helpers. Equal labels do not prove equal products or brand entities |
| Concentration                  | Existing alias normalizer, e.g. EDP/eau_de_parfum, used for comparison; originals retained. Unknown stays null                                         |
| Launch year                    | Only explicitly provided fixture year; unknown stays null. Different known years require separate release/reformulation review                         |
| Perfumers                      | Names retained; normalized comparison does not infer missing authors                                                                                   |
| Top/heart/base notes           | Fragrantica-shaped fixture preserves positions; unpositioned Parfumo-shaped notes use `unknown`. No pyramid inferred                                   |
| Accords/family/collection      | Explicit supplied attributes; no derivation from note similarity                                                                                       |
| Version/flanker                | Distinct-version/related-name review labels from existing duplicate classifier; no collapse based on similar titles                                    |
| Bottle sizes/GTIN              | Existing validation; differing sizes/identifiers flag variant review, never prove shared release identity                                              |
| Additional source attributes   | Explicit fixture-only gender-positioning/longevity/sillage strings stay in `source_metadata`, not invented canonical/public fields                     |
| Descriptions/reviews/images    | No acquisition. Unsupported website fixture fields, including image URLs, fail. Real rights never inferred from presence in payload                    |

The official-brand contract can carry existing `Record` fields, including
structured notes, aliases and identifiers. It cannot supply arbitrary public
columns or rights. The Wikidata mapping remains deliberately sparse: reviewed
item/brand labels/IDs; concentration, year, notes, accords and perfumers unknown.
A generic `Record.source_url` is accepted only on the reserved fixture domain in
this rehearsal; no returned reference is fetched or hotlinked.

## Reconciliation, conflict and quality semantics

Candidate blocks use normalized brand and first fragrance-name token. The existing
classifier distinguishes possible duplicates, incomplete identity, distinct
concentrations, distinct years, distinct versions and related-name candidates.
All pairs require review and `automatic_merge=false`. Cross-source equality is
not a verified identity match; homonymous brands, translations and aliases need
manual/source-identifier review. No global source priority overwrites facts.

For plausible same-product candidates, nonempty differing perfumer, note, accord,
family and identifier claims are reported separately. Case/whitespace and simple
list ordering are normalized for comparison; note positions remain meaningful.
A disagreement flag is a review signal, not proof one source is wrong. Different
known concentrations/years/versions describe release candidates, not fields to
silently overwrite. Bottle differences have a separate variant-review flag.

Every observation retains source/dataset, source record reference, collected-at,
fixture URL, parser version, raw validated attributes, transformation labels and
`fixture_only` rights. Fixture reports are not legal evidence. Durable real
revision/field provenance continues to use the existing database model. Offline
state retains latest source observations; save previous reports if original
fixture revision history is needed. A changed hash requests review, not a merge.

The **completeness score** is exactly 100 × present fields / 10 (integer floor):
brand, name, concentration, year, perfumers, notes, accords, family, sizes and GTIN.
It measures attribute presence only. It is not truth, legal eligibility, matching
confidence or public-publication permission. Sparse official/open metadata is not
rejected merely for scoring below a rich fictional website example. No arbitrary
percentage is labeled a measured identity probability.

## Batching, resume and scale limits

Each fixture file is at most 2 MiB with at most 50 rows (Wikidata 25), sequential
page numbers and a declared next page. Streams are independent per source/dataset.
A continuation must start at its checkpoint's next page; a completed scan may
restart at page zero for incremental/hash comparison. Stable source identities
are compared against prior hashes: new/changed/unchanged are separate counts.
Missing records are **not** interpreted as deletion or revocation. A real source
must specify complete-scan/tombstone semantics before implementing withdrawal.

The runner copies its input state. A malformed/incomplete page, duplicate identity,
checkpoint mismatch, unsupported schema or exceeded limit returns no successful
updated state. Save a complete successful report before the next chunk. Retry
only corrected/local inputs; remote retries remain the existing authorized engine's
responsibility. It does not silently skip invalid rows and advance a checkpoint.

Bounds: 100 pages/run, 100 streams, 5,000 retained source observations, 8 MiB input
batch and checkpoint state, 16 MiB CLI resume-report input, 1,000 comparison pairs.
Pair overflow sets `comparison.complete=false` explicitly; no complete-match claim
may be made from that report. Other overflows fail closed. A CLI report is a
caller-owned unsigned fixture artifact, never an authorization token. It must be
kept out of source control; do not treat a hand-edited checkpoint as audited evidence.

These are **rehearsal limits**, not a proposed cap of 5,000 canonical perfumes.
A 1,000-observation/20-page stream and replay are regression tested. Growing a
real catalog to thousands uses bounded jobs and indexed PostgreSQL snapshots,
not a single ever-growing JSON checkpoint or all-pairs comparison. Before scale
approval: measure actual authorized field coverage, migration/storage growth,
lookup indexes, conservative candidate-recall/false-match rates, concurrency,
backups, retention, revocation and provider quotas. No production throughput or
catalog-coverage claim is made from offline fixture tests.

## Run safely now

```bash
pnpm catalog:rehearse > data/reports/multisource-first.json
pnpm catalog:rehearse --resume-report data/reports/multisource-first.json > data/reports/multisource-second.json
```

The first run produces seven source observations from four original fixture
pages. The second reports seven unchanged observations. To resume a partial
stream, pass only its next fixture files after the prior successful report:

```bash
pnpm catalog:rehearse path/to/next-original-page.json --resume-report data/reports/previous.json
```

Never redirect onto the input report; retain the last valid report if an attempt
fails. Commands emit static failure codes and a nonzero exit; they do not write
files themselves. Default examples and all referenced images/IDs are original
fictional fixtures. No live command or `--allow-external` option exists here.

## Future source activation gate

For **each source separately**, verify current terms/license, intended fields,
automated access and endpoint/robot restrictions, database storage, commercial
reuse, API redistribution, attribution, rates/auth, retention/withdrawal and costs.
A robots allowance or public web page is not a data license. Obtain separate
user approval for that source and exact activity/quantity, then use the existing
operator-reviewed manifest/Grant and manual source/record/field publication gates.
Actual live schema/selectors need authorized fixtures and tests before activation.
Never bypass denial, CAPTCHA, login, IP controls or rate limits. No paid resources,
images, scheduled scraping or mass collection is authorized by this implementation.

See [source coverage and access assessment](phase-2k-source-coverage.md).
