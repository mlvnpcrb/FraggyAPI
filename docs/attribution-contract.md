# Public attribution contract

Phase 2D adds `attributions: []` to every named catalog DTO and release DTO on
all seven existing endpoints. IDs, names, slugs, synthetic flags, pagination,
filters, errors and nullable fields retain their previous meanings. Consumers
must tolerate additive response properties. Strict clients that reject unknown
properties must update their schemas; required credits must not be discarded.

Each credit contains only operator-approved public information:

```json
{
  "id": "sha256-of-public-credit-metadata",
  "provider": "Fictional Workshop",
  "text": "Original invented metadata courtesy of Fictional Workshop.",
  "source_url": "https://example.invalid/workshop",
  "license_name": "Fictional pilot permission; not a real license",
  "license_url": "https://example.invalid/permission",
  "copyright_holder": "Fictional Workshop",
  "placement": "adjacent_record",
  "modification_disclosure_required": true,
  "modification_disclosure": "Names normalized and records matched by FraggyAPI.",
  "redistribution_conditions": [],
  "last_verified": "2026-10-18",
  "fields": ["/name", "/brand/name", "/releases/0/concentration"]
}
```

`fields` are sorted, unique JSON pointers relative to the DTO carrying that
credit. A fragrance aggregates credits for its displayed subtree; its brand,
releases, notes and accords also carry credits relative to their own DTOs.
Array indexes refer to that response, not stable identifiers. Relationship grants
are traced to the related public `/id` path. A release's `fragrance_id` grant is
represented at its `/id` path because that grant authorizes inclusion of the
release in its parent fragrance. Internal relationship/provenance IDs never appear.

Identical public metadata produces the same opaque SHA-256 credit ID, independent
of private source/record IDs. Credits with the same ID combine their field paths,
including when two approved sources have identical public attribution. Distinct
providers or license versions remain distinct. An entry lists only displayed
values that still match selected, known, authorized claims. Unknown, conflicting,
revoked or stale values acquire no credit and remain unpublished. Credits are
conservative: every eligible selected contributing claim is credited, even when
another independent grant could also authorize the field.

Storage rights, reviewed source permissions, approved record redistribution,
field-level rights, approved links and current canonical values are all required.
Attribution never replaces these checks. License names and links are informational;
they cannot approve a source. Private evidence references, manifests, reviewer
identities, source snapshots, audit events and transformation logs remain private.

Supported obligations are plain text beside the displayed record, source/license
links, optional copyright and an operator-written modification disclosure.
Required modification disclosure must be nonempty. Provider must match the
reviewed manifest provider. `last_verified` must be today or within the past 365
days (UTC server date). Expired/future dates block the source. This is a conservative
operational policy, not a determination of a license's legal duration.

Global-footer-only placement, custom placements and additional redistribution
conditions are unsupported. Both manifest-level and credit-level
`redistribution_conditions` must be empty; unresolved restrictions block
publication. Existing free-text `attribution_requirements` are retained privately
and must be explicitly accepted with a complete supported structured credit.
Human review must determine that the structured credit fully satisfies them.

Public URLs must use HTTPS, a valid public-style DNS hostname, no credentials,
query strings, IP literals, localhost/local hosts, nonstandard ports, whitespace,
backslashes or control characters. No URL is fetched. This deliberately excludes
some legitimate license URLs; an operator must obtain a suitable public URL rather
than bypass validation. Attribution text is plain text, never HTML/Markdown.

## Fraggy PWA consumer obligations

The separate PWA is not changed by this phase. Before consuming attributed data:

1. Render all credits beside the corresponding displayed record, including in
   search cards, details, brand lists and lookup/filter metadata. A fragrance's
   root credits cover its displayed subtree without rendering duplicate nested
   credits; do not discard a provider when combining independently fetched DTOs.
2. Display provider, required text, license name/link, source link, copyright when
   present, and modification disclosure when present. Escape all text. Use safe
   HTTPS links with `rel="noopener noreferrer"` for new tabs.
3. Preserve field paths when caching or composing data. Rendering the entire
   original record's credits is acceptable; dropping required credits is not.
4. Revalidate on each request. API uses `Cache-Control: no-store`; Next uses
   uncached fetches. Do not persist catalog values past a rights withdrawal.
   Already downloaded copies and already open browser pages cannot be recalled;
   a reload/new request reflects committed revocation. Third-party clients must
   implement their own refresh/withdrawal behavior.
5. Empty attribution arrays need no section. Synthetic flags remain mandatory and
   synthetic data is always excluded by the API in production.

Public request sessions use PostgreSQL REPEATABLE READ so policy, values and
credits share one snapshot. A withdrawal committed during an in-flight response
is visible to the next request; it cannot produce a mixture of policy versions.

Policy reads are bounded to 1,000 active file-import policies. Overflow hides all
file-import grants. One bounded credit query runs per nonempty page that has
attributed sources; more than 20,000 candidate claims returns a sanitized 503
rather than a partial attribution set. This keeps credits complete within current
pilot limits. Query count stays independent of page length: six queries for an
unattributed fragrance page, seven for an attributed page.
