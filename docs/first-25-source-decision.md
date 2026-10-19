# Decision brief: first 25 genuine, reviewed fragrances

Research date: 2026-10-19, Asia/Manila. **Preparation only. No product endpoint,
discovery query, genuine dataset or image was fetched. No live source is approved.**
This work is local on `feat/first-real-source-readiness`; pushing/opening a PR could
trigger Vercel, so neither is performed. PRs #8–#12 remain unmerged.

## Recommendation

**Open Beauty Facts is the strongest concrete non-Wikidata pilot candidate found
in this review**, conditional on source-specific access/terms verification. It has
an official structured contract, an actual perfume taxonomy and an explicit
publisher statement that its database is open for reuse. It can potentially supply
product names, brands, barcode identities and bottle quantities without scraping
HTML. Its actual number of usable, distinct perfumes is not verified: no discovery
was executed. It is not a substitute for a rich notes/perfumers catalog.

Wikidata currently has the strongest freshly verified license evidence (CC0 for
structured facts). Retain it as an independent complementary source, not the sole
catalog strategy. Its fragrance coverage/field density remains unmeasured.

For rich notes, accords, years and perfumers, an explicitly licensed official
brand export is the strongest long-term route among these options. No named
brand has granted FraggyAPI an export/API agreement. Fragrantica and Parfumo
cannot become executable recommendations merely because their catalogs are rich.

**No candidate currently passes every execution prerequisite.** Do not silently
fall back from a blocked source to another, or promise 25 unique perfume identities
from 25 SKU/barcode records. The next useful action is resolving the Open Beauty
Facts terms/access and copyleft decision, not another generic engine.

## Practical comparison

| Source                                                               | Useful fields / access                                                                                                                                                                                          | Current rights and technical evidence                                                                                                                                                                                                                                                                                                                  | Cost and decision                                                                                                                                     |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Open Beauty Facts                                                    | Official Product Opener JSON search; product name, brands, code, quantity, taxonomy and modification timestamp. No verified structured launch year, perfumer, note pyramid or accords in the selected contract. | Official project README permits reuse for any purpose and identifies the shared server. Official server publishes the search/product schema and beauty perfume taxonomy. Source-specific terms/data pages could not be reached (CONNECT 403); precise license applicability, attribution/share-alike, endpoint restrictions and robots remain pending. | Open-data candidate; no paid resource proposed. **First non-Wikidata candidate, blocked pending verification/approval.**                              |
| Wikidata                                                             | Official SPARQL/entity APIs and dumps; IDs/labels/relationships, other claims only where semantics and coverage are verified.                                                                                   | Licensing, Data access, API policy, User-Agent policy and WDQS implementation pages all returned 200 in this review. Structured entity data CC0; page prose/images are separate. No query or entity API call made. Monitored contact, endpoint-specific checks, exact query and activity approval still needed.                                        | No paid API proposed. **Best verified license; complementary/fallback candidate, not an exclusive strategy.**                                         |
| Fragrantica                                                          | Potentially rich name/brand/year/concentration/perfumers/notes/accords; seek licensed export/API before HTML. Availability of each field/API remains unverified.                                                | Terms request returned 429; stopped without retry/evasion. No current automation/storage/commercial API grant or authorized live parser.                                                                                                                                                                                                               | License cost unknown, not assumed free. **Permission required / blocked.**                                                                            |
| Parfumo                                                              | Potentially rich product/release/concentration/perfumer/notes data; prefer an authorized export/API.                                                                                                            | Previously cited terms URL now returns 404, not a reuse grant. No current official API/export contract or FraggyAPI authorization verified.                                                                                                                                                                                                            | Cost/rates unknown. **Permission required / blocked.**                                                                                                |
| CHANEL / Dior or another named manufacturer                          | Authoritative brand/product/concentration/size/SKU; year/perfumers/notes only if supplied and licensed. Prefer a scoped CSV/JSON/PIM export.                                                                    | Official legal requests failed proxy CONNECT 403. No named feed, written permission or API schema verified. Public product pages do not establish reuse permission.                                                                                                                                                                                    | A free partnership/export must be agreed; no purchase. **Permission required.**                                                                       |
| Manufacturer/distributor feeds, including Open Icecat as a candidate | Potentially structured identifiers, quantities and manufacturer metadata; fragrance coverage must be checked.                                                                                                   | Icecat terms request failed proxy CONNECT 403. No independent catalog retention/public API redistribution grant verified; affiliate/display rights are insufficient.                                                                                                                                                                                   | Free tier availability does not prove fragrance coverage or reuse rights. **Pending verification.**                                                   |
| FragDB/fragrance-database                                            | Publisher advertises a rich structured fragrance catalog and CSV/Parquet/API products. README/license research only; no sample/data/API download.                                                               | Publisher labels sample data/code MIT but full database commercially licensed. Upstream provenance and authority to license copied catalog/review content are not verified. A code/sample license does not clear the full catalog.                                                                                                                     | README advertises only 10 fragrance sample rows and paid full tiers ($200 Core / $400 Full at review). **Not suitable for this 25-record, ₱0 pilot.** |

## Verified contract and small implementation

Official source evidence:

- [Open Beauty Facts publisher README](https://github.com/openfoodfacts/openbeautyfacts/blob/89fcee881b0fd205dc17e3e58b34228a1f0a6238/README.md)
  describes open reuse and explicitly identifies the shared server.
- [Official search envelope](https://github.com/openfoodfacts/openfoodfacts-server/blob/f7f60fb43a8fa54d30d748589265a19f4b27d1d3/docs/api/ref/responses/search_for_products.yaml),
  [product fields](https://github.com/openfoodfacts/openfoodfacts-server/blob/f7f60fb43a8fa54d30d748589265a19f4b27d1d3/docs/api/ref/schemas/product_base.yaml),
  [beauty product type](https://github.com/openfoodfacts/openfoodfacts-server/blob/f7f60fb43a8fa54d30d748589265a19f4b27d1d3/docs/api/ref/schemas/product_type.yaml),
  [beauty taxonomy](https://github.com/openfoodfacts/openfoodfacts-server/blob/f7f60fb43a8fa54d30d748589265a19f4b27d1d3/taxonomies/beauty/categories.txt),
  and [search request](https://github.com/openfoodfacts/openfoodfacts-server/blob/f7f60fb43a8fa54d30d748589265a19f4b27d1d3/docs/api/ref/api.yaml).
- [Official server API guidance](https://github.com/openfoodfacts/openfoodfacts-server/blob/f7f60fb43a8fa54d30d748589265a19f4b27d1d3/docs/api/index.md)
  documents a custom monitored User-Agent, 10 search requests/min/IP and 15 product
  read requests/min/IP; read access needs no account beyond identification. These
  are shared-server documentation, **not freshly verified OBF endpoint quotas**.
  It recommends v3 for new integrations but explicitly retains structured search
  in v2; v3 search is not documented as available. It asks users to read terms and
  fill the usage form before using the API. The license tutorial describes contact
  as appreciated rather than mandatory; resolve this guidance discrepancy before
  execution. No form/message was submitted.
- Server docs specify ODbL/database and DbCL/contents, with separate image terms.
  **Do not infer OBF's complete current terms from the food database's documentation.**
  Verify attribution/share-alike and derived-database/API obligations explicitly;
  segregating observations alone does not remove those obligations. The official
  ODbL license request also failed CONNECT 403, so that legal text was not freshly
  reviewed here. No closed/proprietary redistribution compatibility is asserted.

`collection/openbeautyfacts.py` is a pure reader for that documented search shape.
It makes no requests and has no collector registration or activation path. It
returns raw observations/hash/source/time separately from a proposed existing
`Record`, field mapping provenance and manual-review issues. It validates page
counts, product codes, field types and a 25-product/2 MiB page bound; fails on
duplicate IDs/unrequested fields; checks GTIN length/checksum; and maps only a
single explicit ml quantity (never a multipack's combined volume).

Perfume category is a source claim, not proof. Missing names, ambiguous brands
or non-beauty/non-perfume categories cannot yield a proposed canonical record.
Product titles remain verbatim: no invented concentration/year, brand stripping,
flanker/reformulation identity or notes inferred from ingredients. Every result
still requires identity/release review. Rights remain pending, import/publication
false. Original test examples validate the **publisher-documented interface**;
live response compatibility remains untested. Existing matching/import/provenance
systems will be reused after approval, not bypassed.

Local validation of this small preparation change:

- `pytest apps/api/tests/test_openbeautyfacts.py apps/api/tests/test_import_formats.py -q`:
  **45 passed** (three focused contract checks plus 42 existing format checks).
- `pnpm typecheck`: Python/mypy (50 source files) and TypeScript passed.
- `pnpm lint`, Python formatting checks and `pnpm format:check`: passed.
- `scripts/check_secrets.py`: 244 working-tree files, 39 commits, 410 historical
  blobs; zero heuristic findings before these local changes are committed.
- No new dependency, database migration, frontend change or live-source test.
  Full application suite/build and remote CI were not rerun for this isolated
  preparation change. No push/PR was made because it could trigger Vercel.

## Exact proposed pilot scope — not executed

Source: Open Beauty Facts, structured JSON API, proposed endpoint:

```text
https://world.openbeautyfacts.org/api/v2/search
  ?categories_tags_en=perfumes
  &page=1
  &page_size=25
  &fields=code,product_name,brands,brands_tags,categories_tags,quantity,product_type,last_modified_t
```

Whitespace above is illustrative; encode query parameters normally. Pages 1–4
only, **maximum four HTTP attempts including retries**, one connection, at least
10 seconds between starts, 10-second request timeout, maximum 2 MiB per response.
At most one retry, counted inside that four-attempt budget. Honor Retry-After;
stop if it exceeds the reviewed budget. Stop on 401/403/CAPTCHA, schema drift or
uncertain permission. No proxy rotation, alternate-host collection, detail-page
requests, image URLs/bytes, descriptions, reviews, ingredients or full dataset dump.

This means **up to 100 candidate SKU observations to select at most 25 distinct,
human-reviewed fragrance identities**, not approval for 100 canonical fragrances.
Repeated pages/IDs and conflicting versions are flagged; timestamp and hash track
observations, never establish factual truth. Category/brand/name, concentration
where actually known, release and bottle distinctions need manual review. Deduplicate
using existing Phase 2L review evidence without merging ambiguous records. If fewer
than 25 qualify, report the shortfall and stop; no expanded crawl is implied.

The endpoint/category syntax is backed by the official shared-server schema and
taxonomy, but OBF host behavior and coverage remain untested. This URL is a proposal,
not an executable authorization or a guarantee of 25 usable records.

## Private storage, retention and rollback proposal

- Destination: one dedicated, randomly named **non-production PostgreSQL database
  in the existing development Docker host**, with existing local-only access.
  This is local PostgreSQL on the cloud development machine, not a managed cloud
  service or the user's Mac. No database is provisioned in this preparation.
- Store bounded raw pages privately under ignored `data/pilots/<owned-run-id>/`
  (directory 0700/files 0600), recording source URL, UTC acquisition time, response
  hash, parser/schema version, authorization evidence and run ID. No contact/token
  in raw records/logs. Store normalized proposals/review/conflicts in the isolated
  staging/review system; no write to the existing catalog, Vercel bundle or PWA.
- Target 25 reviewed records, no public API publication, images, scheduled jobs or
  automatic imports. No FastAPI exposure of raw evidence. No paid resources; ₱0
  additional service cost proposed, subject to existing free development resources.
- Retain raw/staged pilot content for **30 days**, then delete unless separately
  approved for continued storage. Retain a non-content audit (counts, run ID,
  hashes, review/rights decisions) for 90 days. No external backups/cloud upload.
- Rollback: stop only the owned pilot run, revoke its source/run permission, remove
  only run-owned staging/proposals/raw files and its ownership-verified disposable
  database using existing cleanup conventions. Preserve unrelated databases/files.
  No public records or deployed demo assets require rollback because none are
  published. Any later canonical import/publication needs a separate reviewed plan.

## Approvals and external prerequisites before the first product request

1. Retrieve and review OBF-specific terms/data/robots and applicable endpoint
   policies through authorized access; settle exact database/content licensing,
   storage, commercial/public API reuse, attribution and share-alike obligations.
2. Decide whether those obligations fit FraggyAPI's eventual commercial API.
   Written provider clarification may be necessary; **no outreach is authorized or
   sent by this task**. If incompatible, request a free brand export rather than
   relabelling third-party scraped data as open.
3. Supply a real monitored contact via private runtime environment settings, not
   committed files or inferred personal details. `CONTACT_EMAIL` stays a placeholder
   until then; approve any required provider registration/usage notification.
4. Explicitly approve this source, exact endpoint/fields, maximum four requests /
   100 candidates / 25 reviewed identities, limits, isolated destination, retention,
   rollback and ₱0 cost. This is distinct from approving parser preparation.
5. Approve safe code delivery or a deployment-control change separately before a
   push/PR; the current Vercel integration automatically deploys repository changes.

Do not request execution approval as though prerequisite 1 had succeeded. Current
blockers are source-specific verification, licensing compatibility, contact and
explicit activity approval. No genuine collection starts in this milestone.

## Additional evidence and observed access results

Fresh official Wikidata pages, all HTTP 200 on this review:
[Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing),
[Data access](https://www.wikidata.org/wiki/Wikidata:Data_access),
[API usage](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_API_Usage_Guidelines),
[User-Agent](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy),
[WDQS implementation](https://www.mediawiki.org/wiki/Wikidata_Query_Service/Implementation).
The latter documents 60-second query timeout, 60 seconds processing time/client
per 60 seconds and 30 error queries/minute. These are not a recommended request
budget; endpoint availability/robots are still not verified by a genuine query.

Other attempted official references:
`https://world.openbeautyfacts.org/terms-of-use`, `/data` (CONNECT 403);
`https://www.fragrantica.com/terms.php` (429);
`https://www.parfumo.com/Info/Terms_of_Use` (404);
`https://www.chanel.com/us/legal/`,
`https://www.dior.com/en_us/beauty/legal-terms`,
`https://icecat.biz/en/menu/terms/index.html` (CONNECT 403).
Direct hosted server documentation was blocked too; the publisher's independent
official GitHub documentation/schema was available. No access denial was bypassed.
Failed or guessed legal paths do not establish terms content or a prohibition.

[FragDB publisher README](https://github.com/FragDB/fragrance-database) was reviewed
for pricing/licensing claims only. No sample CSV, parquet, images or paid API was
retrieved; its marketing claims are not independently verified rights evidence.
