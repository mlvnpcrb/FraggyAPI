# Fragrance image rights and sources

Research date: **2026-10-19 (Asia/Manila)**. **No real image acquisition approved.**
Only policy pages were fetched. HTML image references were not followed; no
remote photo was downloaded, cached, hotlinked, transformed or published.

## Candidate assessment

| Route                                                      | Evidence and finding                                                                                                                                                                                                                                                            | Classification / next step                                                                                                                                             |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Official brand/manufacturer press or product-media package | Dior and Chanel legal research URLs were blocked by the environment proxy. No API/feed, image sublicensing grant, price or account terms could be verified                                                                                                                      | **Permission required**. Preferred future route; obtain a product-media agreement from the rights holder                                                               |
| Distributor/affiliate feeds                                | Awin product-feed documentation and GS1 service research were blocked by proxy. A distributor's ability to display an image does not prove authority to sublicense it to our API consumers                                                                                      | **Pending verification**. Confirm chain of title, exact fields, permitted applications and independent API delivery                                                    |
| Licensed image/product-data APIs, e.g. Icecat              | `https://icecat.biz/en/menu/channelpartners/index.html` returned environment CONNECT 403. No fragrance coverage, download, transformation, resale, pricing or authentication terms verified                                                                                     | **Pending verification**; no service provisioned                                                                                                                       |
| Wikimedia Commons via Wikidata file references             | Wikidata's official licensing applies CC0 to entity data, not every linked file. Wikimedia Terms of Use requires compliance with each underlying license. `https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia` was blocked by environment CONNECT 403 | **Pending verification per asset**; don't inherit metadata CC0 or treat P18 as permission                                                                              |
| Smithsonian Open Access                                    | `https://www.si.edu/openaccess/faq` blocked by environment CONNECT 403. No fragrance/bottle coverage or per-asset rights verified here                                                                                                                                          | **Pending verification**; museum-object imagery may not depict a current retail bottle                                                                                 |
| Openverse discovery/API                                    | `https://docs.openverse.org/api/` blocked by proxy. Discovery/indexing does not verify an asset's rights; no image search performed                                                                                                                                             | **Pending verification**, not selected for automatic acquisition                                                                                                       |
| Direct brand partnership                                   | No agreement or private media package supplied                                                                                                                                                                                                                                  | **Permission required**. Exact grant must be reviewed before local ingestion                                                                                           |
| Fragrantica, Parfumo, retailers or Google Images           | No appropriate source-specific image authorization. Parfumo legal notice requires consent beyond private/non-commercial copying; the Perfume Society and ScentBase also explicitly reserve image/content reuse                                                                  | **Permission required or pending verification**, as detailed in source selection; no image scraper or remote fetch path implemented                                    |
| Original fictional fixture artwork                         | Programmatically drawn bottle shapes/text by this repository's demonstration and tests, no third-party pixels                                                                                                                                                                   | **Verified eligible for synthetic validation only**. Explicit fictional copyright/attribution and per-content review exercised; this does not authorize any real photo |

## Independent permission checklist

The private `ImageRights` review must bind a source key, source page, original
SHA-256, copyright holder, complete public credit, private evidence and review /
expiry dates. The local pipeline requires affirmative grants for:

- downloading and database/file storage;
- transformation, resizing, metadata stripping and WebP thumbnail generation;
- display on the FraggyAPI website and the separate Fraggy PWA;
- commercial use and public API image delivery.

Third-party/CDN hosting and retention after source access ends are recorded
separately; both default false. Current delivery uses private local storage and
same-origin routes, not a third-party host. Public API delivery does not
implicitly grant API customers a broader sublicense than the reviewed terms.
Unsupported attribution placement or unresolved reuse conditions fail closed.
If a supplier permits display but not transformation, this pipeline refuses it;
a separately reviewed untransformed delivery design would be necessary.

Record the exact license/version, evidence URLs/date or private agreement
reference, attribution placement, changes disclosure, territory/time limits,
rights-holder chain, commercial API permission, PWA display, permitted hosts,
cache invalidation and post-contract deletion. A filename, copyright notice,
public URL, robots allowance or metadata license is insufficient.

## Revocation and retention

Image or source revocation hides metadata and bytes immediately on subsequent
requests. Responses are `no-store`, and the web proxy does not use Next's
persistent image optimizer. Already downloaded copies cannot be recalled;
API consumers must honor withdrawal and license obligations.

After a withdrawal, use the local media source-revocation command and garbage
collection (see operations in [media architecture](fragrance-media-architecture.md)).
The garbage collector also enforces expired grants and non-retention after source
rights withdrawal. Shared pixel blobs are retained while another approved-storage
asset requires them. Do not revoke a third-party holder's image merely by
editing a product's metadata license; explicitly process the image source too.
No background process, storage service or real acquisition schedule is activated.
