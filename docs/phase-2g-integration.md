# Phase 2G — first-source integration

The Phase 2F collector remains the only collection engine. `wikidata_sparql`
extends its shared adapter dispatch and pinned transport. No second scheduler,
import implementation, public upload API or separate PWA changes are introduced.

## Implemented source contract

- Exact proposed external endpoint: `https://query.wikidata.org/sparql`.
- Operator-reviewed, unique Q identifiers, at most 300; fixed query construction,
  25 identifiers per request, deterministic numeric page checkpoints. Arbitrary
  query text, cursor URLs, alternate public hosts and field-map overrides refused.
- The fixed query uses truthy P1716 (brand), English item/brand labels. Both must
  exist; missing labels are not replaced with Q IDs. Manufacturer is not silently
  substituted for brand. Multiple brand rows or repeated entity IDs fail closed
  rather than choosing one arbitrarily. Unrequested IDs are rejected. Missing
  requested IDs fail the page before staging/checkpoint advancement; the operator
  must resolve coverage rather than silently skipping items.
- Mapped fields: brand name, fragrance name, source item URL and record Q ID.
  Private `source_metadata` retains item/brand IDs, property and mapping version.
  This field requires explicit manifest storage permission and is never a public
  DTO or canonical attribute. Changes in referenced brand identity alter the
  staged content digest even when labels happen to be unchanged.
- Concentration, release year, reformulation, notes, accords, perfumers, sizes and
  GTIN remain unknown unless a later, reviewed mapping supplies those facts. This
  deliberately narrow first adapter does not claim full Wikidata coverage.
- JSON / SPARQL-results JSON accepted; HTTP/body limits, rate delay, retries,
  checkpoint fencing, source digest reviews, staging and manual decisions reuse F.
  Existing F endpoint/record serialization excludes absent new fields to preserve
  already-reviewed configuration/content digests.
- Real grants require HTTPS, current independent source storage/collection review,
  suitable record/page bounds, at least one second between requests and a contact
  User-Agent. No contact/address is preapproved by this code. A later pilot must
  recheck endpoint etiquette, robots, compression expectations and current limits.
- Real network still defaults off; a registry flag, CC0 label or fixture grant
  cannot enable it. All seven website skeletons remain disabled.

## Safe offline reproduction

```bash
bash scripts/setup.sh
docker compose up -d --wait
RUN_DB_TESTS=1 pnpm test
.venv/bin/python scripts/demo_collection.py --first-source --records 100
```

The demonstration starts its own literal-loopback HTTP server, creates a UUID-owned
disposable database, migrates it, and tears both down. Every Q ID, name, credit and
bottle raster is invented. Its real source-style queries only reach that owned
server. It reviews synthetic source storage and collection, activates a **local
fixture-only** schedule, stages 100 records across four pages, skips unchanged
records on the repeat, manually publishes two, then independently approves one
original image. It checks real FastAPI responses, source withdrawal, denied
collection, image withdrawal and shared-store cleanup. No application catalog or
persistent source configuration is populated by this command.

The first-source fixture intentionally reports 100 unknown release years and 100
missing-note records. Canonical quality covers only manually materialized rows;
a zero-error canonical report is not proof of complete real-source coverage.
Original concentration/reformulation/dedup regression tests remain in place; the
adapter neither merges identities nor invents the missing distinctions.

## Before a genuine pilot

Complete [the approval package](first-real-data-pilot.md), including a qualified
list of actual perfume entity IDs and missing/ambiguous-item accounting. Obtain
separate explicit user approval before any source query or genuine image file.
Then perform trusted local manifest and collection review using the existing
`catalog:manage` and `catalog:collect` tools. Each review stores the exact grant
hash; activate only the approved source. Do not run `tick --allow-external` while
unrelated policies are enabled. Run a single explicitly approved source instead.

Collection/storage permission still does not publish fields or media. Review the
staged rows, resolve identity ambiguity, grant only licensed fields, and apply a
separate image content review if images are ever included. Source revocation must
also disable its collector and process its image retention/removal obligations.
