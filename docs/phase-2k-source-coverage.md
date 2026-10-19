# Multi-source field coverage and permission assessment

Prepared 2026-10-19 (Asia/Manila). **No live source approved by this phase.**
This distinguishes potential catalog coverage from verified API/schema support.
Names of major sites identify candidate providers, not endorsement or permission.
No genuine pages/data/images were downloaded to implement these parsers.

| Candidate                                         | Potential useful fields to evaluate                                                                                    | Preferred access                                                                         | Current access/reuse decision                                                                                                                                                         |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Fragrantica                                       | Product/brand, concentration, year, perfumers, note pyramid, accords, positioning and reported performance             | Official licensed API/export or direct agreement first; HTML only if expressly permitted | No verified current automated collection, storage and commercial API redistribution grant. Live adapter stays disabled; implemented shape is fictional JSON only                      |
| Parfumo                                           | Product/brand, releases, concentration, perfumers, notes/family, performance and variants                              | Official licensed feed/API/export or direct permission                                   | Prior terms assessment indicates permission needed; fresh review remains blocked. No approved API contract, bulk license or live parser                                               |
| Wikidata                                          | Entity/brand IDs and labels; other fields only after semantic verification                                             | Official APIs/SPARQL or approved scoped download                                         | Historical official CC0 structured-fact evidence; current access/policy/robot rechecks failed. Sparse fields and exact-product classification remain limitations; not the only target |
| Official brand/manufacturer catalogs              | Authoritative product identity, concentrations, sizes, identifiers; launch/perfumers/notes where provided and licensed | Negotiated JSON/CSV/PIM export or official API                                           | No named brand grant verified. Public product pages do not authorize copying or independent API resale. Fictional generic brand-feed adapter only                                     |
| Authorized distributor feeds                      | Product IDs/GTIN, size/concentration variants, stock-linked identities and licensed factual attributes                 | Provider API or structured feed                                                          | No approved provider/contract. Affiliate presentation rights may not allow a permanent fragrance database or public API. Actual fields/auth/rates/cost need review                    |
| Basenotes                                         | Directory/product/brand, notes, release/perfumer facts where licensed                                                  | Official export/API/licensing agreement                                                  | No verified grant; existing skeleton disabled; reviews/prose excluded                                                                                                                 |
| Wikiparfum                                        | Product identity, ingredients/families and factual attributes where licensed                                           | Official agreement/API/feed                                                              | No verified storage/commercial API grant; skeleton disabled                                                                                                                           |
| The Perfume Society                               | Families, ingredients and educational material where licensed                                                          | Direct permission/structured licensed export                                             | Permission required under prior review; education/prose not an open data license; skeleton disabled                                                                                   |
| PerfumeMaster                                     | Brand/product/release/notes metadata where licensed                                                                    | Licensed export/API or permitted extraction                                              | No verified grant; skeleton disabled                                                                                                                                                  |
| ScentBase                                         | Fragrance identities and collections metadata where licensed                                                           | Official export/API/agreement                                                            | Permission required under prior review; no active grant; skeleton disabled                                                                                                            |
| Community/open repositories and dataset platforms | Potentially broad names/notes catalogs                                                                                 | Download only after verifying actual dataset license and upstream rights                 | None approved. MIT scraping code or uploader claims do not license the underlying catalog. No unapproved downloads                                                                    |

All field lists above are **assessment targets**, not claims that a provider offers
a stable endpoint or every field. Copyrighted reviews/descriptions and images are
excluded. Image metadata/photography requires independently verified downloading,
storage, transformation, display/commercial/API/CDN/retention rights and approval.
No image acquisition is implemented.

## Evidence and unresolved requirements

[Phase 2J comparison](phase-2j-sources.md),
[Phase 2G source evidence](phase-2g-source-selection.md) and
[Phase 2H policy observations](phase-2h-pilot-preparation.md) preserve the evidence
URLs and historical findings. Recent official Wikidata Licensing/Data access/API/
User-Agent/query policy requests returned HTTP 403; WDQS robots failed proxy
CONNECT 403. Those observations are **access failures**, not licenses, origin
robot decisions or a reason to bypass restrictions. No fresh verification is
claimed here. Prior permission-required findings must be refreshed before use.

Candidate official locations: <https://www.fragrantica.com/>,
<https://www.parfumo.com/>, <https://www.wikidata.org/>,
<https://basenotes.com/>, <https://www.wikiparfum.com/>,
<https://perfumesociety.org/>, <https://www.perfumemaster.com/>,
<https://www.scentbase.com/>. Brand/distributor routes require a **named provider**,
exact export/API, current written scope and actual cost/rate/auth evidence before
they can become approved sources. Unknown means unverified, not permitted.

For each source, the review ledger must record evidence URL/private agreement,
verification date/reviewer, license/terms version, expiry, collection and storage
permissions separately from commercial/API reuse, permitted/forbidden fields,
attribution, documented request limits/backoff/auth, retention and source revocation.
Current rate limits and costs for website candidates are **unknown**. Do not
invent them or assume free access. The development budget remains ₱0; paid offers
are out of scope. Wikidata's earlier one-request/second proposal is our conservative
budget, not a verified current provider quota or universal rule for other sources.

## Source strategy for a large catalog

Support rich licensed brand/distributor/catalog sources alongside sparse open
metadata. Select the first real pilot only after source evidence and coverage are
verified; neither Wikidata nor a major site is automatically chosen. A first
approved 20–50-record run remains useful to validate mappings and manual review
before expansion. Thousands of products require separate measured batch, coverage,
quality, rate, rights and retention approval, not a blanket scraping instruction.

No login/CAPTCHA/anti-bot bypass, proxy evasion, request-budget escalation or
alternative-host workaround is allowed. If access or rights are unclear, mark the
source blocked. `CONTACT_EMAIL` stays a placeholder for any later Wikidata work;
no personal contact is inferred. Nothing in this assessment enables source policies.
