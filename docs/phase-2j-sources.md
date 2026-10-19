# Phase 2J — sources for the first genuine fragrance pilot

Research review: 2026-10-19 (Asia/Manila). This phase retrieves no genuine entity,
fragrance, dataset or photograph. No source is activated. PRs #8 and #9 remain
open. There was no pre-existing Phase 2J branch/PR when work began; this PR is
stacked on #9, without changing the website or its Vercel configuration.

## Evidence status and recommendation

**Recommend Wikidata structured metadata, conditionally, for 25 records.** Existing
[Phase 2G evidence](phase-2g-source-selection.md) and
[Phase 2H policy review](phase-2h-pilot-preparation.md) record official licensing
and access pages previously retrieved successfully: structured entity facts are
CC0, suitable in principle for storage, commercial reuse and redistribution from
our own database. That does not license photographs, descriptive prose, trademarks
or operating the Wikimedia service as a resale proxy.

Current HTTPS rechecks of Licensing, Data access, API policy, User-Agent policy,
Wikidata robots, WDQS robots and Parfumo terms failed (HTTP/transport errors).
No access permission, origin robot policy or new terms conclusion is inferred
from those failures. Prior observations are historical evidence, **not a fresh
Phase 2J clearance**. There are zero approved real collectors and zero reviewed
real candidate IDs in the committed proposal. No network bypass was attempted.

## Comparison

All quantities/field availability require actual source review, not inference
from a product title. `Blocked` is the execution decision; it does not assert
that a provider legally prohibits every possible use.

| Candidate                                                    | Potential fields                                                                                  | Preferred access and current availability                                                                              | Rights / attribution                                                                                                                   | Rates, authentication and cost                                                                                                                                                                       | Decision                                                                                                 |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| [Wikidata](https://www.wikidata.org/)                        | Reviewed item and brand labels/IDs, entity URL; additional fields only with reviewed semantics    | Official APIs, SPARQL and structured dumps documented previously; reuse existing SPARQL adapter; no bulk dump approved | Historical official CC0 evidence for structured facts; voluntary adjacent source/modification credit; no image grant                   | Public reads proposed without auth; monitored User-Agent required. Our cap: one connection, ≥1 second/request, timeout 10s, one retry. Actual current endpoint limits/robots unverified. No paid API | **Rank 1, blocked pending fresh access/license review, contact, candidate validation and user approval** |
| [CHANEL](https://www.chanel.com/) official brand partnership | Official product names, concentrations, sizes, launch facts; notes only if agreement covers reuse | No licensed public feed/API verified for FraggyAPI; seek an authorized export directly                                 | Public visibility is not storage/commercial/API permission. Obtain separate database and image grants; attribution negotiated          | Auth, exact limits, cost and retention unknown; reject paid proposal for this pilot                                                                                                                  | **Rank 2, permission required**                                                                          |
| [Dior](https://www.dior.com/) official brand partnership     | Product identity, concentration and sizes; other facts where licensed                             | No approved API/feed or automated access agreement verified                                                            | Direct written permission must cover storage, commercial API redistribution and permitted fields. Image rights independent             | Rates, authentication, commercial terms and cost unknown                                                                                                                                             | **Rank 2, permission required**                                                                          |
| Authorized distributor/manufacturer export                   | GTIN/SKU, brands, product variants, sizes and potentially licensed factual attributes             | No named provider/contract is currently approved; prefer a scoped CSV/JSON export over crawling                        | Affiliate display permission is not an independent database/API redistribution license. Confirm retention/revocation rights            | Provider-specific API/feed auth, quotas and cost unknown; ₱0 required                                                                                                                                | **Rank 3, permission required; not a selected source**                                                   |
| [Fragrantica](https://www.fragrantica.com/)                  | Catalog names, notes/accords/ratings where explicitly licensed                                    | Existing adapter disabled; official licensed endpoint/download not verified                                            | No verified automated-access/storage/commercial redistribution grant. Reviews, prose and images excluded                               | Limits/auth/licensing cost unknown; robots alone cannot authorize reuse                                                                                                                              | **Blocked, pending verification**                                                                        |
| [Parfumo](https://www.parfumo.com/)                          | Fragrance/brand identity, notes and perfumers if permitted                                        | Existing adapter disabled; no approved API/download                                                                    | Earlier terms review indicates permission needed for proposed reuse; current terms fetch failed. Obtain a direct grant                 | Current quotas/auth/cost unverified                                                                                                                                                                  | **Blocked, permission required**                                                                         |
| [Basenotes](https://basenotes.com/)                          | Directory identities and factual attributes if licensed                                           | Existing adapter disabled; official API/feed not verified                                                              | No verified storage/commercial API grant; reviews excluded                                                                             | Quotas/auth/cost unknown                                                                                                                                                                             | **Blocked, pending verification**                                                                        |
| [Wikiparfum](https://www.wikiparfum.com/)                    | Identities, ingredients, families if licensed                                                     | Existing adapter disabled; approved API/feed not verified                                                              | No verified automated storage/API redistribution license; descriptions/images excluded                                                 | Quotas/auth/cost unknown                                                                                                                                                                             | **Blocked, pending verification**                                                                        |
| [The Perfume Society](https://perfumesociety.org/)           | Educational families/ingredients where permission exists                                          | Existing adapter disabled; approved structured export not verified                                                     | Earlier research indicates reuse permission required; education/prose is not an open catalog license                                   | Quotas/auth/cost unknown                                                                                                                                                                             | **Blocked, permission required**                                                                         |
| [PerfumeMaster](https://www.perfumemaster.com/)              | Release and brand identities, notes if licensed                                                   | Existing adapter disabled; official endpoint/feed not verified                                                         | No verified storage/commercial API reuse grant; no text/image copying                                                                  | Quotas/auth/cost unknown                                                                                                                                                                             | **Blocked, pending verification**                                                                        |
| [ScentBase](https://www.scentbase.com/)                      | Catalog/product identities if licensed                                                            | Existing adapter disabled; official export/API not verified                                                            | Earlier review indicates permission needed; no active grant                                                                            | Quotas/auth/cost unknown                                                                                                                                                                             | **Blocked, permission required**                                                                         |
| Unverified community/Kaggle/GitHub perfume datasets          | Potentially thousands of names/notes                                                              | Structured download alone is not authorization; none downloaded                                                        | A software MIT license or uploader assertion does not establish underlying data rights. Require origin chain and explicit data license | Do not download before dataset-specific review; cost unknown                                                                                                                                         | **Blocked, no eligible named dataset verified**                                                          |

No candidate is approved for live execution. No source is called categorically
illegal without evidence; no unclear source is treated as allowed. Official
brand/distributor relationships could provide richer records later, but are not
credible immediately available free sources until an actual agreement exists.

## Evidence references and verification requirements

- <https://www.wikidata.org/wiki/Wikidata:Licensing> — CC0 structured-data scope.
- <https://www.wikidata.org/wiki/Wikidata:Data_access> — official access methods.
- <https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_API_Usage_Guidelines>
  — API conduct, licensing and service restrictions.
- <https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy>
  — descriptive monitored operator contact.
- <https://www.wikidata.org/robots.txt> and
  <https://query.wikidata.org/robots.txt> — distinct hosts; neither is a data license.
- <https://www.parfumo.com/Info/Terms_of_Use> — earlier permission review; failed
  fresh recheck. Seven-source historical evidence URLs/observations are preserved
  in [Phase 2G](phase-2g-source-selection.md), not invented anew here.

Before genuine requests, an operator must verify current documents, retain dated
scope/evidence privately, resolve conflicting terms, verify endpoint access and
applicable limits, approve the actual monitored contact, and obtain the user's
exact activity/quantity approval. If ordinary access is denied, stop. Do not
switch proxies, scrape alternative hosts or silently use another API to evade it.

Wikidata coverage may be sparse and English brand relationships incomplete.
Twenty-five valid product entities are a **target, not a verified available
catalog**. If fewer qualify, stop and request a revised scope rather than fill
with brand entities, inferred names or another unapproved source. Thousands of
records require a separate measured expansion after the pilot is reviewed.
