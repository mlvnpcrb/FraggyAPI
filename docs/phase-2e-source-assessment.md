# Phase 2E source assessment and collection readiness

Reviewed 2026-10-18 UTC. This is a research register, not a licensing approval.
No catalog, review, sample CSV/parquet, product image or other third-party fragrance
record was downloaded, stored or imported. Only repository metadata and public
license documents were retrieved. No source was contacted or purchased.

## Evidence and limitations

The environment proxy denied CONNECT to the seven source websites and Wikidata
before an origin response was received (`curl: (56) CONNECT tunnel failed,
response 403`). Requests were limited to policy/documentation URLs. This is an
**environment access failure**, not a website prohibition, a robots instruction,
or evidence that an API does not exist. A network draft preserves existing access
and adds the research domains, but saving it does not activate network access.
Unobserved facts below remain unknown. No access controls were bypassed.

GitHub REST repository/license metadata was accessible. Evidence was checked on
2026-10-18; commit-pinned links below preserve the reviewed policy version.
GitHub search results, repository descriptions, availability and license badges
alone do not prove original collection rights or data redistribution rights.
Robots permission alone never supplies storage/commercial redistribution rights.

Classification meanings:

- **Verified eligible:** verified applicable access, storage and commercial API
  redistribution rights, including supported obligations. None established.
- **Requires permission:** an agreement or clarification is needed for the proposed
  scope; this does not assert that all possible future uses are legally prohibited.
- **Incompatible:** observed terms conflict with the intended commercial database
  API. A separately negotiated grant could change this assessment.
- **Pending verification:** evidence is missing, inaccessible or ambiguous.

The earlier project vocabulary maps verified eligible → approved, incompatible →
prohibited for the stated use, and pending/requires permission → pending
verification. Research classifications do not update runtime authorization flags.

## Seven existing website candidates

For **each row**, official API availability, structured downloads, authentication,
automated access permission, current terms, database storage, commercial reuse,
public API redistribution, required attribution and documented rate limits are
**unknown/unverified**. Neither absence of an API nor permission to scrape is
inferred. Cost and data quality/coverage are also unknown because no current
contract or fragrance records were inspected. Direct permission must be obtained
unless independently verified applicable terms explicitly cover the intended use.

| Source              | Candidate website (not fetched)           | Robots evidence                                                                      | Official API / structured download / auth | Automation / storage / commercial reuse / API redistribution | Attribution / rate limits | Coverage / cost      | Direct permission                       | Classification       |
| ------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------- | ------------------------------------------------------------ | ------------------------- | -------------------- | --------------------------------------- | -------------------- |
| Fragrantica         | [website](https://www.fragrantica.com/)   | [robots](https://www.fragrantica.com/robots.txt): proxy denied; directives unknown   | unknown / unknown / unknown               | unknown / unknown / unknown / unknown                        | unknown / unknown         | unassessed / unknown | obtain grant or verify applicable terms | pending verification |
| Parfumo             | [website](https://www.parfumo.com/)       | [robots](https://www.parfumo.com/robots.txt): proxy denied; directives unknown       | unknown / unknown / unknown               | unknown / unknown / unknown / unknown                        | unknown / unknown         | unassessed / unknown | obtain grant or verify applicable terms | pending verification |
| Basenotes           | [website](https://basenotes.com/)         | [robots](https://basenotes.com/robots.txt): proxy denied; directives unknown         | unknown / unknown / unknown               | unknown / unknown / unknown / unknown                        | unknown / unknown         | unassessed / unknown | obtain grant or verify applicable terms | pending verification |
| Wikiparfum          | [website](https://www.wikiparfum.com/)    | [robots](https://www.wikiparfum.com/robots.txt): proxy denied; directives unknown    | unknown / unknown / unknown               | unknown / unknown / unknown / unknown                        | unknown / unknown         | unassessed / unknown | obtain grant or verify applicable terms | pending verification |
| The Perfume Society | [website](https://perfumesociety.org/)    | [robots](https://perfumesociety.org/robots.txt): proxy denied; directives unknown    | unknown / unknown / unknown               | unknown / unknown / unknown / unknown                        | unknown / unknown         | unassessed / unknown | obtain grant or verify applicable terms | pending verification |
| PerfumeMaster       | [website](https://www.perfumemaster.com/) | [robots](https://www.perfumemaster.com/robots.txt): proxy denied; directives unknown | unknown / unknown / unknown               | unknown / unknown / unknown / unknown                        | unknown / unknown         | unassessed / unknown | obtain grant or verify applicable terms | pending verification |
| ScentBase           | [website](https://www.scentbase.com/)     | [robots](https://www.scentbase.com/robots.txt): proxy denied; directives unknown     | unknown / unknown / unknown               | unknown / unknown / unknown / unknown                        | unknown / unknown         | unassessed / unknown | obtain grant or verify applicable terms | pending verification |

All seven registry/adapter configurations remain disabled with authorization and
licensing `pending_review`. No `verified eligible` source was added to PostgreSQL.
Terms pages/API documentation must be located and reviewed after network access
is available; guessed terms paths are not presented as evidence.

## Other candidate sources and actual dataset discovery

### Wikidata — pending verification

Evidence URLs attempted: [licensing](https://www.wikidata.org/wiki/Wikidata:Licensing)
and [data access](https://www.wikidata.org/wiki/Wikidata:Data_access); both were
proxy-blocked on the review date. Official API details, structured dumps, auth,
permitted automation, robots, current terms, storage/commercial/API redistribution,
attribution and rate limits are unverified in this run. Fragrance coverage,
completeness, freshness and concentration/reformulation distinctions were not
measured. Cost is unverified. Direct permission may be unnecessary if an
applicable verified open license suffices, but no clearance is asserted here.
Review separate terms for structured data, text and media; do not transfer a
structured-data license to images or narrative content automatically.

### FragDB/fragrance-database — incompatible with proposed commercial API

Observed evidence:
[LICENSE.md at 548d908](https://github.com/FragDB/fragrance-database/blob/548d908d5e49b8ae6d05166b468da2398054c952/LICENSE.md),
Git blob `3771bf00eae1befe9f56e5c04cc6063eaf80390a`, reviewed 2026-10-18.
The repository description advertises a large multilingual fragrance database;
those volume claims were not independently validated.

- **API / structured files / auth:** no official fragrance API verified. The license
  identifies CSV/parquet samples and commercial downloads; catalog files were not
  fetched. Authentication/delivery controls for paid products are unknown.
- **Automation / robots / terms:** GitHub policy metadata was readable through the
  existing authenticated tooling. This does not establish permission to automate
  collection from upstream websites. Upstream robots/access terms were not verified.
- **Storage / commercial reuse / API redistribution:** samples explicitly use
  CC-BY-NC-4.0. Commercial tiers permit application integration but explicitly
  prohibit “Redistribution of the full database”, “Reselling the data to third
  parties” and “Creating derivative databases for sale”. These terms do not support
  FraggyAPI's intended commercial independent database/developer API.
- **Attribution:** sample terms require appropriate credit, a fragdb.net link and
  change disclosure. MIT terms apply separately to code examples, not the samples.
- **Rate limits:** no collection/API rate limits verified. The license describes
  download counts/access windows, which are not scraping permission.
- **Coverage / quality:** advertised scale only; originality, upstream rights,
  completeness and field accuracy unverified. No sample record inspection.
- **Cost:** license lists Core USD 200, Full USD 400, Annual USD 1,000 and Lifetime
  USD 2,000. Nothing was purchased; paid options are outside this phase's ₱0 scope.
- **Permission:** would require an explicit compatible negotiated redistribution
  grant plus verified upstream authority; do not assume payment alone supplies it.

### SentimentDrivenCommunityDetection — pending verification

Observed [repository metadata](https://github.com/Kalashi-Saed-Collaborations/SentimentDrivenCommunityDetection)
describes perfume attributes and user-review data derived from Atrafshan.
[LICENSE at 3d668cf](https://github.com/Kalashi-Saed-Collaborations/SentimentDrivenCommunityDetection/blob/3d668cf482443136cd4da0a2db7a5a84b8cb8bee/LICENSE)
(blob `dcdf98dde8b5b275488fb5a1ee547ac649707f45`) is an MIT **Software** license.
Both documents were checked 2026-10-18; no dataset files were downloaded.

No official fragrance API, download schema, automation permission, auth conditions,
robots policy or rate limit was verified. A repository software license does not
by itself establish the contributors' authority over upstream reviews/database
rights or permission for storage, commercial reuse and public API redistribution
of those records. MIT requires retention of its copyright/permission notice for
covered software; data-specific attribution obligations remain unknown.
Coverage/quality/cost are unverified. Request explicit data scope, upstream rights
and commercial redistribution clarification before considering a starter import.
User reviews remain outside the current metadata/publication contract.

### Other public perfume repositories — pending verification

[0xdidi/PerfumeDataset](https://github.com/0xdidi/PerfumeDataset) and
[harry-jooyoung-kim/perfume_dataset](https://github.com/harry-jooyoung-kim/perfume_dataset)
were discovered through GitHub repository metadata on 2026-10-18; the API reported
no detected license. That means permission is **not established**, not that a
particular license violation was proven. No records were downloaded. Official APIs,
structured-file schemas, authentication, automation, robots, terms, storage,
commercial/API redistribution, attribution, limits, coverage, freshness and cost
remain unverified. Obtain explicit rights/authority evidence from maintainers;
“public repository” is not a redistribution license.

### Official manufacturer catalogs — requires permission

No specific manufacturer dataset or agreement was supplied. Official catalog/API,
structured feed/download availability, auth, robots, automation, rate limits,
terms, storage and commercial/API redistribution are unknown per manufacturer.
Catalog publication and brand ownership do not automatically grant API resale
rights for supplied assets. Exact attribution, permitted factual fields, derived
identifiers and withdrawal obligations require review. Coverage/quality/cost are
unassessed. Prefer a brand-supplied 100–300-record file with written scope and
supplier authority before considering website extraction. No evidence URL exists
for an agreement that has not been supplied.

### Authorized distributors — requires permission

No distributor feed or agreement supplied. APIs/downloads/auth/robots/automation/
rate limits/terms are unknown. Distributor status does not prove authority to
license a brand's catalog for database storage, commercial reuse or API resale.
Require explicit field scope, sublicensing authority, attribution, expiry and
withdrawal procedures. Coverage/quality/cost remain unassessed. A direct written
grant or independently verified applicable license is required before import.

### Direct manufacturer/distributor partnerships — requires permission

No partner contacted and no agreement supplied. Negotiate local CSV/JSON/JSONL
first; API/feed/auth/automation/robots/limits remain source-specific and unverified.
The written scope must cover access, retention/storage, commercial redistribution,
derived/matched fields, exact credit placement, change disclosure, update cadence,
revocation and permitted public endpoints. Coverage, quality and cost are unknown;
no commitment or spending is authorized. Terms/permission URLs are unavailable
until the parties provide them.

## Starter dataset readiness and Phase 2F gate

**No genuine 100–300-record starter dataset is cleared.** The import pipeline
accepts bounded CSV/JSON/JSONL, preserves snapshots/UUIDs/release versions/bottle
variants, and requires reviewed storage, independent canonical review and explicit
field publication. Use original synthetic fixtures until the user separately
supplies an authorized dataset and explicitly approves its use. Run quality checks
and inspect duplicates/conflicts, nulls, provenance and credits before publication.
A research finding never invokes source-review or activates an adapter.

After Phase 2E review and merge, Phase 2F may implement a modular collection engine
only for verified methods/scopes: official APIs or authorized feeds/downloads
first; HTML extraction only with verified permission. Require source-specific
adapters, auth through secure settings, robots checks in addition to licensing,
rate limits, bounded retry/backoff, schedules, incremental cursors, idempotency,
normalization, duplicate candidates, provenance, validation/manual review,
license-aware publication, monitoring/error reports and prompt revocation.
Recheck terms/license versions and dates before scheduling. Unsupported obligations
or revoked/unknown authorization must stop collection/publication. No CAPTCHA,
login circumvention, proxy evasion, billing or production deployment is included.
