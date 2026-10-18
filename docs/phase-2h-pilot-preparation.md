# Phase 2H — real-data pilot preparation (disabled)

Verified 2026-10-19, Asia/Manila. **No live discovery, fragrance query, genuine
dataset, photograph or external publication has been authorized or performed.**
The genuine candidate list is empty. Creating a purported reviewed list of real
Q IDs without permitted research would invent evidence; it remains blocked.

## Contact and source policy

The user explicitly supplied the project identifier and required this template:

```text
FraggyAPI/0.1 (https://github.com/mlvnpcrb/FraggyAPI; CONTACT_EMAIL)
```

Keep `CONTACT_EMAIL` unchanged until the user provides and approves a monitored
address. Do not infer personal contact information from Git history or project
files. The disabled proposal in `config/wikidata-pilot-proposal.json` contains no
entity IDs. Its offline checker cannot activate or approve anything:

```bash
pnpm pilot:check -- config/wikidata-pilot-proposal.json
```

Observed: `offline_only=true`, `network_requests=0`, `enabled=false`,
`real_candidate_count=0`, `qualified_candidate_count=0`. Blockers explicitly cover
missing contact, user discovery/collection approval and endpoint review. Real
Wikidata collection-grant validation now rejects placeholder/example contacts;
synthetic protocol fixtures retain their explicitly fictional test-only behavior.
A syntactically acceptable address still needs human monitoring/approval evidence.

## Current evidence

Policy/documentation research only; no entity or discovery requests were sent.

| Official evidence                                                                                              | Observation and scope                                                                                                                                                                                            |
| -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Wikidata Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing)                                         | HTTP 200; structured entity metadata CC0. Project prose, photographs, logos, trademarks and third-party rights are separate                                                                                      |
| [Data access](https://www.wikidata.org/wiki/Wikidata:Data_access)                                              | HTTP 200; documents public programmatic APIs, EntityData, query service and downloads. No download performed                                                                                                     |
| [API Usage Guidelines](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_API_Usage_Guidelines) | HTTP 200; descriptive User-Agent/contact, content-license compliance, throttling/backoff and robot-policy compliance. Limits may change; no service-level guarantee or right to resell the Wikimedia API service |
| [User-Agent Policy](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy)       | HTTP 200; identifying project/contact required. The placeholder is not a monitored contact                                                                                                                       |
| [Wikidata robots](https://www.wikidata.org/robots.txt)                                                         | HTTP 200; restrictions on special routes and other paths. Its directives do not establish another hostname's policy or grant redistribution rights                                                               |
| [WDQS robots](https://query.wikidata.org/robots.txt)                                                           | Environment proxy rejected CONNECT with 403, before an origin response. No bypass or alternate network path attempted; endpoint-specific access review remains blocked                                           |

Proposed exact collection endpoint: `https://query.wikidata.org/sparql`. The adapter
uses pinned HTTPS, bounded responses, no redirects, per-source delays/retries and
external access off by default. A reachable policy page does not verify actual
endpoint availability, acceptable encoding/compression, robot policy or current
operational restrictions. Verify these separately before collection approval.

CC0 structured facts are eligible for database storage, commercial reuse and
republication through our own API under the reviewed scope; a license label is
not the operator authorization event. Preserve the existing independent storage,
collection and publication decisions, current evidence dates/expiry and manual
review. Proposed attribution is voluntary adjacent Wikidata/source/CC0 credit
with a transformation notice; the exact public credit needs operator acceptance.

## Exact proposed discovery and collection budget

This is a **proposal with zero approved requests**, not instructions to run it.
Require separate approval of each activity and the real contact before using any
external flag or network client.

| Activity                                                         | Proposed bound                                                                | Maximum HTTP attempts |
| ---------------------------------------------------------------- | ----------------------------------------------------------------------------- | --------------------- |
| One discovery-only query, after ontology/class scope is approved | At most 100 rows; one request plus at most one retry; no pagination expansion | 2                     |
| Collection of separately reviewed eligible Q IDs                 | At most 100 unique IDs, four fixed 25-ID pages, at most one retry per page    | 8                     |
| Optional idempotency pass, only if included in approval          | Same four pages and retry limit                                               | 8                     |
| **Total ceiling if all three are explicitly approved**           | No recurring schedule or image requests                                       | **18**                |

One connection, minimum **1 second** between all attempts, 10-second request
timeout, exponential backoff (1 second base) and provider Retry-After honored.
Provider limits always take precedence. A single response remains bounded to
2 MiB. Re-review any policy/configuration change; F grants support bounded retries
but this proposal reduces the configured maximum to one retry. Missing or
ambiguous pages fail before staging/checkpoint advancement. Do not increase
budgets or switch endpoints to evade a denial. Structured dumps are unsuitable
for this bounded pilot and are not approved for download.

A discovery template for review, intentionally **not runnable** until the class
placeholder is resolved and separately approved:

```sparql
SELECT DISTINCT ?item ?itemLabel ?class ?brand ?brandLabel ?manufacturer
WHERE {
  VALUES ?approvedFragranceClass { wd:APPROVED_CLASS_QID }
  ?item wdt:P31 ?class .
  ?class wdt:P279* ?approvedFragranceClass .
  OPTIONAL { ?item wdt:P1716 ?brand }
  OPTIONAL { ?item wdt:P176 ?manufacturer }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
ORDER BY ?item
LIMIT 100
```

Include standard WD/WDT/Wikibase/BD prefixes when the final query is reviewed.
The class ID and exact final query text must be verified and approved first;
this document does not assert that an invented ontology identifier is correct.
No discovery command or automatic discovery implementation is provided.

## Per-candidate review before the second authorization gate

Save only legally authorized results in ignored private files. For each eventual
candidate, check the entity URL/identity, explicit fragrance classification,
English fragrance name, brand relationship and manufacturer separately. A brand,
ingredient, perfume house, similarly titled work or manufacturer-only result is
not automatically a valid fragrance. Reject unresolved multi-brand/flanker/
concentration/reformulation ambiguity. Never merge products based on labels alone.

Assess concentration, release year with its actual meaning/precision, notes and
accords individually. `P571` inception is not automatically a commercial release
year; an ingredient relation is not automatically a note pyramid; a creator is
not automatically a perfumer. Record unknowns and missing statements explicitly.
The current adapter collects only reviewed item/brand names/IDs and source URL;
other fields remain unknown until a separately reviewed mapping exists.

`Candidate` supports these field assessments, classification, ambiguities,
reviewer/date and safe evidence URLs. Qualification requires all eight assessment
checks, a verified brand relationship and entity evidence; a synthetic candidate
can never qualify as genuine. Duplicate/oversized lists, malformed IDs, future
dates and unsafe evidence URLs are rejected. This is an offline review aid, not
proof of rights or a way to enable collection. **Actual genuine reviewed IDs: 0.**

## Final approval package

Request approval only when the package contains the real monitored contact,
verified exact endpoint/policies, qualified actual ID list, exact discovery/query
scope and budget, allowed fields, private storage/collection evidence with expiry,
commercial/public API reuse scope, attribution text, manual review/publication
plan, cancellation owner and revocation/retention procedure. Cost: existing local
PostgreSQL/files, intended **₱0/month**; no paid provider, production hosting or SLA.

Cancel using existing `catalog:collect cancel RUN_UUID`, disable/revoke collection,
revoke source publication, and verify public record and byte withdrawal. Image
rights must be processed independently using media source revocation and GC.
No command is run merely because this proposal is reviewed or Phase 2H is merged.

## Real image readiness — separate approval

The original-only preview and tests exercise validation, optimization, thumbnails,
shared hashes, manual approval, galleries, exact release/variant selection,
credits, missing-image fallbacks, revocation and unused-blob cleanup. No genuine
photo is authorized. Prefer a direct brand/manufacturer media agreement; assess
authorized distributor feeds, licensed image APIs or individually verified open
assets separately. Source-specific evidence and earlier blocked research are in
[the image-source assessment](image-rights-and-sources.md).

Any real image proposal must specify exact assets/hashes, rights holder and
attribution, download/storage, transformation, FraggyAPI/PWA display, commercial
API delivery, hosting and post-access retention. CC0 metadata or a Wikidata image
reference does not grant those rights. No genuine photograph is requested here.
