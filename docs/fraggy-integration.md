# Fraggy application integration contract

This contract is for the separate Fraggy PWA. This change does not modify that
repository. No subscription, payment or API-key system is implemented.

Use `/api/v1/fragrances`, `/api/v1/fragrances/search`, `/api/v1/fragrances/{uuid}`,
`/brands`, `/brands/{slug}`, `/notes` and `/accords` as documented in
[public-api.md](public-api.md). Configure the API origin in the consumer environment;
never distribute PostgreSQL credentials or internal source credentials.

## Identity and response example

Persist a fragrance UUID for the fragrance line and a release UUID for the chosen
concentration/version. Never derive an identity from a name/slug or merge EDT, EDP
and reformulations. Slugs are presentation/discovery attributes and may change.
Unknown and hidden values remain null; do not invent years or concentrations.
This invented example is illustrative, not evidence of a licensed live catalog:

```json
{
  "data": [
    {
      "id": "7333308a-5815-57bf-b291-a52de0e195b9",
      "name": "Amber Geometry",
      "slug": "amber-geometry",
      "synthetic": true,
      "brand": {
        "id": "b7b46dca-613e-4a8a-a7c7-9be0ccaf4c17",
        "name": "Morrow Grove",
        "slug": "morrow-grove",
        "synthetic": true
      },
      "releases": [
        {
          "id": "d1d98964-2a9b-4a26-b18e-19c829c8db94",
          "concentration": null,
          "release_year": null,
          "notes": [],
          "accords": [],
          "synthetic": true
        }
      ],
      "releases_truncated": false
    }
  ],
  "pagination": { "limit": 20, "offset": 0, "total": 1 }
}
```

UUID values in examples are illustrative; obtain actual identities from responses.
Detail responses wrap the same object in `data` without pagination. No release
lookup/write endpoint exists yet. The release summary deliberately omits internal
version metadata, media, descriptions and raw provenance. More than 20 releases
sets `releases_truncated`; do not treat summaries as complete inventories.

## Paging, filters and versioning

Send `limit=20&offset=0`, then increment offset by the returned limit while
`offset + limit < total` (offset is capped at 10000). Stable name/UUID tie-breakers
prevent random order, but concurrent edits can move records between pages.

Search: `/api/v1/fragrances/search?q=Paper&brand=nacre-workshop`.
Release filtering: `concentration=eau_de_parfum&year=2025`.
Use repeated `notes=<uuid>&notes=<uuid>&accords=<uuid>` for AND matching on one
release. Use UUIDs from the public taxonomies; hidden/private notes do not match.
`sort=name`, `name_desc` or `relevance` is explicit; limits and input sizes are bounded.

Changes within v1 may add optional fields/routes. Consumers should tolerate extra
response properties, preserve unknown/null values, and not parse display strings
as stable enums. Breaking changes require a new API version and a documented
migration/deprecation policy before adoption; there is no commercial SLA yet.

## Errors, rights and cache behavior

Errors use `{ "error": { "code": "404", "message": "Fragrance not found" } }`.
Validation errors use 422 with safe `details` locations/types. Missing search text
uses 400; unavailable/unexpected catalog failures use sanitized 500. Do not retry
invalid input or a 404 indefinitely. Network/5xx retries should use capped
exponential backoff and cancel requests when the user changes the search.

Respect `Cache-Control: no-store`. Do not persist catalog responses in a service
worker/offline store, public CDN, local database or export without separately
verified redistribution/storage rights. Refetch details before use; a previously
visible identity can become 404 after rights revocation. Saved user references can
retain UUIDs but must gracefully show unavailable catalog metadata. Existing local
user notes are separate from catalog response content.

Demo identities carry `synthetic: true`; show a clear demo label and keep them out
of production inventories. Production API configuration always excludes synthetic
grants. No image URL, review, copyrighted description or licensing evidence is
part of the public DTO. Do not infer rights to such material from a public identity.

The Next.js reference client performs server-side GETs using `API_BASE_URL`, no
credentials and no caching. The directory uses accessible GET forms and URL filters;
mobile/desktop share the same contract. Its dropdowns show only the first 50 public
brands/notes/accords; the brand directory itself is paginated. A later UI can use
paginated lookup/autocomplete without changing the API. The current UI selects one
note and accord at a time; direct API consumers may repeat these filters.

## Phase 2D consumer update

The separate Fraggy PWA has not been modified. Its integration must preserve and
render the new public `attributions` arrays beside every displayed record and
lookup/filter value, including multiple providers and modification disclosures.
[Attribution contract](attribution-contract.md) defines fields, relative JSON
pointers, safe links, additive compatibility and revocation refresh requirements.
Do not infer licensing from a label or discard credits while combining records.
The repository Next.js frontend demonstrates cards, details, brands and filter
credits; empty arrays add no UI panel.
