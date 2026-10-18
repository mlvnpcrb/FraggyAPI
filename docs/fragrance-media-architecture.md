# Fragrance media architecture and local operations

Phase 2G extends the existing `media_assets` table and `source_entity_links`.
A link targets exactly one fragrance, release (including its concentration and
version), or bottle variant. The media source is the linked source record's
`DataSource`; it need not be the source that supplied other canonical facts.
Image rights never inherit approval from metadata claims or a Wikidata file link.

## Storage and review boundaries

Migration `0006_media` adds `content_sha256`, private `media_metadata` and
`image_policy` JSON objects, an indexed hash, object/hash checks and a partial
unique index for an active link/content pair. Applied migrations are unchanged;
upgrade/downgrade and schema drift are tested. Existing assets without the new
review proof remain hidden. No new database table or paid storage is introduced.

The image policy records source key, safe source URL, copyright holder, complete
public attribution, exact original content hash, private evidence, review/expiry
dates and independent permissions described in [image rights](image-rights-and-sources.md).
A digest binds this grant to the exact source/link, canonical fragrance identity,
release concentration/year/version, variant identity/size/GTIN/packaging and
rendition metadata. Changing a binding requires review again. Private evidence,
reviewer names, filesystem paths and unapproved images never enter public DTOs.

1. A trusted local operator reviews storage and transformation rights and supplies
   an original local file. No remote download client or public upload endpoint exists.
2. Validate a bounded regular file, SHA-256 and declared/detected MIME; safely decode
   an allowed single-frame raster. Refuse symlinks, SVG, GIF, unsupported formats,
   empty/truncated files, animated WebP, files over **5 MiB**, sides outside
   **32–4096 pixels**, and more than **12 million pixels**. Decoder bomb warnings
   fail closed. Pillow is pinned in both dependency declaration and dev lock.
3. Apply orientation, copy pixels into a new image, strip EXIF/ICC/XMP/comments,
   encode WebP display (maximum side 1200) and thumbnail (320). Transformation
   permission is mandatory. WebP is the portable supported output; AVIF is not
   required or emitted. No original file is copied into the managed store.
4. Store private immutable WebP blobs under their SHA-256 names, exclusive creation,
   no symlink following, fsync and restrictive permissions. Identical renditions
   share bytes, but assets keep independent targets, sources and rights reviews.
   Duplicate active original hash on one source link is refused idempotently.
5. Store an image as `pending_review` for publication. Separate explicit approval
   verifies current rights, bindings and both stored hashes. Approving a new
   primary demotes previously valid primary selections for that same exact target,
   recording the operator action; galleries remain independently attributable.
6. Public projection and byte delivery recheck current source, record, link,
   independent image rights and expiry. Release/variant bytes also require their
   parent release to be public. No EDP/EDT/reformulation image substitution occurs.
7. Revocation restricts usage; storage withdrawal clears rendition references.
   Garbage collection deletes unreferenced hashes without deleting shared assets.
   It enforces expired grants and non-retention after source withdrawal. Invalid
   private storage metadata stops cleanup for operator investigation.

`MEDIA_ROOT` defaults to the ignored `data/private/media` directory. It is a
trusted operator-managed directory, outside web static mounts, on one local
filesystem shared by the API and operator process. Protect its parents and the
original local files; these are trusted local operations, not a public filesystem
sandbox. A failed database transaction may leave private orphan blobs; run GC.
File deletion cannot participate in a PostgreSQL rollback: a failed cleanup can
leave a missing image, which fails closed to a placeholder, never an unauthorized
public file. Don't independently manipulate the store while writers/GC run.

## Additive public API

Fragrance and release DTOs add `primary_image: object | null` and `images: []`;
releases additionally add `variant_images: [{variant_id, primary_image, images}]`.
Existing fields retain their meanings. No private bottle/variant attributes are
published merely because an image exists. Lists are capped at 12 images per target.
A single page-scoped batch (maximum 1000 candidates; overflow hides media) adds
one SQL read, independent of card count. Without assets, fields default null/empty.
Missing files are omitted; corrupt files fail hash verification on byte delivery.

Approved image metadata includes UUID, width/height, alt, role, source ID/page,
public license/copyright/credit, synthetic flag and relative delivery URLs:

```text
GET /api/v1/media/{image_uuid}/display
GET /api/v1/media/{image_uuid}/thumb
```

Both are local rights-checked WebP responses, no redirects, raw paths or static
mount. They verify hash and bounded file read, return 404 on withdrawal/missing
files, `no-store`, `nosniff` and restrictive CSP. The website proxies only these
UUID/preset routes through its server-only `API_BASE_URL`, bounds responses to
5 MiB, refuses redirects/foreign MIME and does not expose that configuration to
browser code. It uses responsive intrinsic sizes, lazy decoding/loading, plain
same-origin images without persistent optimizer cache, adjacent image credit,
and an original labelled bottle placeholder for unavailable/failed images.
Cards cover search/brand-filter listings; detail pages include release/variant
galleries. No external hotlinks, CDN or separate Fraggy PWA changes are needed.

## Local operator commands

All commands reject production and remote database targets. No command grants
real acquisition approval. Private rights files and real originals must stay out
of Git. Supply exact reviewed `ImageRights` JSON, including the original SHA-256,
source key, full `Attribution`, seven affirmative permission flags and dates.
The fixture demonstration in `scripts/demo_collection.py` shows a complete
original-only object; do not reuse its fictional agreement for genuine images.

```bash
pnpm catalog:media -- ingest LINK_UUID data/private/original.png data/private/image-rights.json --mime image/png --alt 'Approved bottle alt text' --role primary --reviewer OPERATOR --reason REASON
pnpm catalog:media -- approve IMAGE_UUID --reviewer OPERATOR --reason REASON
pnpm catalog:media -- revoke IMAGE_UUID --reviewer OPERATOR --reason REASON
pnpm catalog:media -- revoke-source SOURCE_UUID --reviewer OPERATOR --reason REASON
pnpm catalog:media -- gc --reviewer OPERATOR --reason REASON
```

First perform a source/record/link review using the existing import workflow;
image-only evidence does not approve unrelated fragrance metadata. Commands emit
sanitized status/UUIDs/counts, not raw images, URLs or evidence. After source
withdrawal stop/revoke collection, revoke metadata, revoke the image source and
run GC. Repeat GC after restoring a failed database/storage operation and verify
metadata and byte 404s. No automatic scheduler or cleanup daemon is started.

## Validation and limits

Original procedural raster tests cover malformed/MIME/size/dimension/symlink/
animation/EXIF handling, rights gates, expiry, galleries, exact target selection,
binding changes, hash deduplication, independent approvals, primary replacement,
source/image revocation, shared bytes, cleanup and API compatibility. Frontend
tests cover placeholders, failures, safe paths, responsive lazy rendering, credit
placement and proxy limits/outages. The 100-record offline demo exercises
collection through manual publication and image approval through revocation.

This is a local, bounded foundation, not a deployed image service: no multi-host
storage coordination, automatic photo acquisition, AVIF encoder, real image
license, SLA, consumer license enforcement or production deployment is included.
Before an authorized pilot review dependency security updates, exact asset
conditions, endpoint access, disk capacity, backups/deletion and operator ownership.
