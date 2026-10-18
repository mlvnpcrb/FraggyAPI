# Public catalog API (v1)

The read-only contract is rooted at `/api/v1`. Stable UUIDs identify fragrance
lines and their distinct concentration/version releases. Slugs are mutable discovery
labels, not identities. No write, ingestion, account or billing routes exist.
Development `/docs` and `/openapi.json` describe query/response/error schemas;
production keeps these routes disabled under the existing operational policy.

| GET route            | Result                                                              |
| -------------------- | ------------------------------------------------------------------- |
| `/brands`            | Paginated public brand identities; optional `q`                     |
| `/brands/{slug}`     | One public brand identity, or 404                                   |
| `/fragrances`        | Paginated public fragrance lines with bounded release summaries     |
| `/fragrances/{id}`   | One public fragrance line by UUID, or 404                           |
| `/fragrances/search` | Same catalog/filter contract; requires nonblank `q` (400 otherwise) |
| `/notes`             | Paginated public note identities; optional `q`                      |
| `/accords`           | Paginated public accord identities; optional `q`                    |

## Query conventions

All list routes accept `limit` (default 20, 1–50) and `offset` (default 0,
0–10000). Invalid values and unsupported query parameters return 422, never silent
coercion to a different filter. Lookup `q` is at most 120 characters.

Fragrance list/search also accept:

| Parameter       | Meaning                                                                                                            |
| --------------- | ------------------------------------------------------------------------------------------------------------------ |
| `q`             | At most 120 characters; trim/collapse whitespace; case-insensitive name/brand search                               |
| `brand`         | One public brand slug (maximum 160 ASCII lowercase/dash characters)                                                |
| `concentration` | `parfum`, `extrait_de_parfum`, `eau_de_parfum`, `eau_de_toilette`, `eau_de_cologne`, `eau_fraiche`, `oil`, `other` |
| `year`          | Release year, 1000–2999; unknown years do not match                                                                |
| `notes`         | Repeat UUID parameter for AND matching; at most 10                                                                 |
| `accords`       | Repeat UUID parameter for AND matching; at most 10                                                                 |
| `sort`          | `relevance` (default), `name`, `name_desc`                                                                         |

All release filters must match **one public release**. An EDT from 2020 and an EDP
from 2025 cannot satisfy `concentration=eau_de_toilette&year=2025`. Response release
summaries include all public releases, not only the matching release. Filters never
use hidden fields or private note/accord associations. A private value cannot be
inferred by filtering the public result count.

Sorting is deterministic: relevance uses exact case-insensitive fragrance/brand
matches first, then `ts_rank_cd`, then normalized name and UUID. Name sorting uses
normalized name and UUID. Offset beyond the result set returns an empty array with
the total. Counts/pages are live reads, not an immutable snapshot; concurrent edits
can change totals and offset membership.

## Success and errors

Lists use `{ "data": [...], "pagination": { "limit": 20, "offset": 0, "total": 0 } }`.
Details use `{ "data": {...} }`. Unknown and non-public resources both return 404.
Malformed UUIDs/filters return 422. Empty catalogs return 200 with `data: []`.

```json
{ "error": { "code": "404", "message": "Fragrance not found" } }
```

```json
{
  "error": {
    "code": "422",
    "message": "Invalid request",
    "details": [{ "location": ["query", "limit"], "type": "less_than_equal" }]
  }
}
```

Blank required search returns 400; unexpected exceptions/database query failures
return a sanitized 500 envelope. Error bodies never echo submitted input values, SQL,
connection URLs, source evidence or exception messages. `/health` and `/ready`
retain their separate operational response formats. `/api/v1` metadata reports
phase `2B` and is not a catalog list.

## Public projection and permissions

`fraggy_api/public_catalog.py` defines explicit Pydantic allowlists. Catalog handlers
construct DTOs explicitly; they never serialize ORM dictionaries. Publication uses
the existing Phase 2A provenance schema; Phase 2B adds no migrations.

A real field requires **all** of:

1. Approved source authorization and licensing, dated review, nonempty evidence,
   that field in `permitted_fields`, and no unresolved `reuse_restrictions`.
2. Approved snapshot storage and redistribution, with the database-required separate
   storage/redistribution evidence. The snapshot must be `linked`.
3. An approved source/entity link, a `selected` and `known` field claim, approved
   field usage rights and the database-required field rights evidence.
4. Exact JSON equality between the claim and the current canonical value. Edits
   invalidate stale claims. A note/accord relationship requires membership in an
   explicitly permitted UUID array on the release, plus rights to the named entity.

These are operator-reviewed permissions, not automatic legal verification. A
selected claim is never sufficient. Nonempty restrictions fail closed instead of
being interpreted as a license. Revocation at any level hides the field on the next
request. Adapter `enabled` controls collection, not rights to existing licensed
records; this API cannot enable or invoke an adapter.

The projection uses these exact `field_path` names: `name`, `slug`, `brand_id`,
`fragrance_id`, `concentration`, `release_year`, `notes`, `accords`. Identity/name/slug
must be public to show an entity; a fragrance's brand relationship and brand must
also be public. Release publication requires its `fragrance_id` relationship.
`notes`/`accords` claims contain arrays of UUID strings. A hidden scalar becomes
null; a hidden identity/association disappears. Null can mean unknown or not public;
clients must not try to distinguish the reason.

Only UUID/name/slug/synthetic, the public brand, and bounded public release
summaries are exposed. Releases expose UUID, permitted concentration/year and
public note/accord identities. Descriptions, reviews, source claims/snapshots,
ingestion runs, review queues, evidence, URLs, credentials, media, variants and
perfumers are outside this version's allowlist. **All media are omitted**, including
approved media, until an explicit licensed-media contract exists.

Synthetic grants require a synthetic source, synthetic authorization/licensing,
synthetic snapshot storage/redistribution and synthetic field status, plus the
same reviewed-link/selected/current-value checks. `CATALOG_INCLUDE_SYNTHETIC=false`
by default; `APP_ENV=production` always disables them, even if the setting is true.
Each identity/release is labeled `synthetic`; synthetic field or relationship grants
propagate that label to containing release/fragrance summaries, including mixed
licensed/demo records. Labels are conservative, not a redistribution license. The opt-in seed command creates
explicit synthetic grants only for original invented fixture values, preserving
existing edits and conflicting candidate years. No startup/migration inserts data.

## Bounds, search and caching

The Phase 2B baseline executes five catalog SQL statements when nonempty: count, root rows, bounded
releases, bounded notes and bounded accords. There are no per-record lazy loads.
At most 20 releases per fragrance and 50 note/accord associations per release are
read, using SQL window bounds. `releases_truncated` signals the release limit;
note/accord lists are bounded summaries and have no exhaustive-list guarantee.
Lookup pages use two queries. PostgreSQL statement timeouts use the configured
`DATABASE_TIMEOUT_SECONDS` (default 3 seconds); client requests time out at 5 seconds.

Search uses the existing stored `search_vector` and GIN index with PostgreSQL
`simple` configuration and `plainto_tsquery`; all query values are bound parameters.
Brand matching uses escaped case-insensitive substring matching. Fragrance names
match complete tokens, not arbitrary substrings. No stemming, typo tolerance,
accent folding or alias expansion is promised. The optimizer may choose scans for
small tables or combined brand/FTS conditions. Production-sized latency/load and
query plans have not been benchmarked. Consider `pg_trgm` later for licensed name
prefix/fuzzy matching after measured need, reviewing migration/index costs first.
No paid search service or PostgreSQL extension was added.

Catalog responses set `Cache-Control: no-store`. Next.js server requests use
`cache: 'no-store'` with a 5-second timeout, so rights revocation is not hidden behind
a persistent app cache. No public CDN cache, ETag or offline redistribution license
is implied. See the Fraggy integration contract for consumer expectations.

## Phase 2D additive attribution

Every named record and release now includes an `attributions` array (empty when
no credit is required). Existing fields, routes, filters, pagination and error
contracts remain. Fragrances aggregate credits with relative JSON-pointer field
paths for their displayed subtree; nested DTOs carry their own local credits.
See [the complete attribution contract](attribution-contract.md) for safe public
metadata, deduplication, multiple providers, consumer obligations and limits.
Private evidence, reviewer identities and source snapshots remain excluded.

File-import policy validation adds one fixed query per request; attributed pages
add one bounded credit query. Fragrance pages use six queries without attribution
and seven with attribution, independent of page length. Existing SQL bounds and
PostgreSQL indexes remain. No migration is needed: structured attribution stays
in the existing operator-reviewed manifest/evidence JSON, separate from canonical
records. New optional manifest fields are omitted when empty, preserving old
Phase 2C manifest digests.
