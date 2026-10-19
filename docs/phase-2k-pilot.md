# Phase 2K — proposed 25-record genuine metadata pilot

**Execution blocked; Phase 2J performs no genuine collection.** This is the
specific next-step proposal, not authorization. The existing 100-fragrance
Vercel demo remains fictional and unchanged; no real data is added to its bundle.

## Scope, mapping and unknown values

Source: Wikidata structured entity metadata. Method: existing official SPARQL
adapter at `https://query.wikidata.org/sparql`, conditional on current endpoint
policy and user approval. Target: **25 genuine fragrance products**, one reviewed
source, one one-off run, no schedule, no images, no automatic publication.

| Input                                              | Existing mapping / decision                                                                                 |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Reviewed item URI                                  | `source_record_id` Q ID; entity URL; stable source identity retained independently of canonical UUID        |
| English item label                                 | `fragrance_name`, original source snapshot plus normalizer; not proof of product classification             |
| Explicit `P1716` brand URI + English label         | `brand_name`; original brand Q ID/property kept in `source_metadata`; ambiguous/multiple brands reject page |
| Manufacturer `P176`                                | Candidate review evidence only; never silently substituted for brand                                        |
| Concentration                                      | Null: current adapter does not collect a semantically reviewed concentration property                       |
| Release year                                       | Null: do not convert `P571` inception into product release year                                             |
| Notes / accords                                    | Empty unknown lists, not an assertion of absence; current adapter does not map them                         |
| Perfumer, gender, family, sizes, GTIN              | Not collected by this adapter; do not infer from labels or other sites                                      |
| Descriptions, reviews, ratings, photographs, `P18` | Excluded entirely                                                                                           |

This limited pilot validates identity/provenance and the existing pipeline, not
complete perfume profiles. Improving optional fields requires a separately
reviewed mapping/source and new tests. Concentrations, flankers, launch/relaunch
years and reformulations remain separate review decisions. Equal names are not
permission to merge. Same normalized brand label with conflicting brand IDs is
a review blocker; do not force canonical creation or discard source identity.

## Approval sequence — two distinct activities

1. **Policy/contact gate:** refresh the licensing/access/robots evidence in
   [the source assessment](phase-2j-sources.md). Supply an actual monitored email;
   retain `CONTACT_EMAIL` until supplied. No inferred or fictional live contact.
2. **Discovery gate:** user approves the exact discovery query/class and bounded
   endpoint requests. No query/class is invented as a verified fragrance ontology.
   Reuse [Phase 2H's intentionally non-runnable template](phase-2h-pilot-preparation.md),
   replace its class placeholder only after evidence review, and submit the exact
   final query for approval. Discovery itself retrieves genuine records and is
   prohibited in Phase 2J. Proposed ceiling: one request plus one retry, LIMIT 50.
3. Review up to 50 discovered candidates to select exactly 25 genuine product Q
   IDs. Validate entity vs house/ingredient/work classification, English name,
   explicit brand relation, all eight `Candidate.checked_fields`, source evidence,
   missing fields, ambiguous statements and dates. Reviews older than 30 days
   must be refreshed. No fabricated Q IDs. Current reviewed real candidates: **0**.
4. **Collection gate:** submit the exact 25 IDs and one-off scope to the user.
   No live collection until separately explicitly approved. Independently record
   collection, storage and eventual publication decisions in existing review tools.

For 25 approved IDs: one VALUES page, one connection, ≥1 second between attempts,
10-second timeout, one retry with exponential backoff/Retry-After, **two maximum
collection attempts**. With separately approved discovery, total ceiling **four**.
No idempotence re-fetch, recurring sync, alternative host or request-budget growth
is included. If operating limits are stricter, reduce the request rate/budget.
A 50-record alternative requires revised approval: two pages, four collection
attempts. Twenty to fifty is enforced by the offline plan.

## Safe command available now

```bash
.venv/bin/python scripts/prepare_real_pilot.py
.venv/bin/python scripts/prepare_real_pilot.py --dry-run
```

These read `config/phase-2j-pilot.json`. They contain **no network transport,
database session, review approval, activation or publication**. The dry-run
constructs only clearly invented local SPARQL responses, passes them through the
existing Wikidata parser and Phase 2E/2F quality/normalization rules, validates
pagination, preserves unknown fields and emits deterministic content digests.
It writes nothing, stages/publishes nothing, starts no schedules, and reports the
remaining live blockers. Changing `quantity` to any integer 20–50 rehearses that
size; every live-approval flag is restricted to false. Editing this file cannot
approve a collector. The fictional test-only User-Agent is used in a parser
configuration with loopback port 1; it is never sent anywhere.

## Operator workflow only after all approvals

Prepare a **dedicated local non-production PostgreSQL database** named for the
pilot, with an explicit operator-reviewed `DATABASE_URL`/migration URL supplied
through secure environment settings. No database is created/reset by Phase 2J.
Do not point at application/demo/production databases or commit credentials.
Migrate using the existing Alembic command. Record the database name, source key,
manifest/configuration digests and baseline counts before collection.

Prepare a private real (non-synthetic) manifest and collection `Grant` containing
current evidence, expiry, exact 25 IDs, true independently reviewed permissions,
only `wikidata_sparql_v1` mapped fields, no images, no credentials and the approved
monitored User-Agent. Use a unique source key such as `wikidata-pilot-2k-001`.
The future private Grant's endpoint must use these exact bounds for 25 records:
`adapter=wikidata_sparql`, `url=https://query.wikidata.org/sparql`,
`entity_ids=<exact approved 25 Q IDs>`, `minimum_interval_seconds=1`,
`timeout_seconds=10`, `retries=1`, `backoff_seconds=1`, `max_pages=1`,
`max_records=25`, the approved monitored `user_agent`, empty `field_map`, and no
`credential_env`. Do not copy the rehearsal's fictional IDs or test-only contact.

A manifest alone cannot grant rights; the normal trusted-operator source review
and separate collector review are required. Private files stay in ignored
`data/private/` and must not be copied into the synthetic website snapshot.

The existing executable workflow is:

```bash
# No commands below are executed during Phase 2J.
pnpm catalog:manage source-review --manifest data/private/pilot-manifest.json --reviewer OPERATOR --reason APPROVAL_REFERENCE --allow-storage --publish-fields name,slug,brand_id --accept-attribution
pnpm catalog:collect review data/private/pilot-grant.json --reviewer OPERATOR --reason APPROVAL_REFERENCE
# Record returned COLLECTION_UUID; review its digest and exact IDs before enabling.
pnpm catalog:collect activate COLLECTION_UUID --reviewer OPERATOR --reason APPROVAL_REFERENCE
# No --schedule and no tick; this is the separately approved one-off network run.
pnpm catalog:collect run COLLECTION_UUID --allow-external
pnpm catalog:collect history COLLECTION_UUID
pnpm catalog:manage pending --source wikidata-pilot-2k-001 --limit 50
```

`APPROVAL_REFERENCE`, `OPERATOR` and `COLLECTION_UUID` are intentionally unresolved
placeholders. `source-review` publication fields define an upper bound, not an
individual record's publication approval. Verify exact command help/configuration
and source manifest identity before the operator runs anything. Missing/expired/
revoked grants, access denial, malformed/omitted/extra/multiple-brand rows or an
unapproved endpoint stop collection. Never log raw payloads, credentials, private
review text or arbitrary exceptions. Collect summaries and sanitized error codes.

Review all staged products manually using existing `catalog:manage review`,
explicitly resolving `approve_new`, `link_existing`, `separate_release`, `defer`
or `reject`. Run `catalog:collect quality` and the Phase 2E quality report.
Inspect record-level provenance and unknown attributes. Publication is a later
explicit `catalog:manage publish --record-id ... --fields ...` action only for
licensed fields and individually approved records. **This pilot proposal does
not authorize public publication.** Source credit and source entity URLs must
survive the approved public projection. Do not publish real records into the
static demo or use its synthetic-only visibility to expose genuine records.

## Idempotency, interruption and rollback

The collector retains source IDs, payload hashes, checkpoints, run history,
review digests and timestamps. Retry is bounded; absent records do not advance
past an incomplete page. Resume/re-run requires operator inspection and any
additional request budget approval. Existing source-ID/hash checks make unchanged
records idempotent; a changed payload stages a review, not an automatic merge.

Stop a running pilot using `catalog:collect cancel COLLECTION_UUID --reviewer ...
--reason ...`. Then revoke the collector with `catalog:collect revoke` and revoke
source publication with `catalog:manage revoke --source wikidata-pilot-2k-001
--reviewer ... --reason ...`. If any field was explicitly published later,
`catalog:manage unpublish` can withdraw selected fields. Verify API disappearance,
review the run history, and preserve an audit trail. Revocation hides publication;
it is **not physical erasure**, canonical-row deletion or automatic restoration
of edited values. Never delete shared/pre-existing canonical records to roll back
one source. Staged snapshots can remain private under their storage policy; an
explicit retention/erasure decision is required if storage rights end.

Because the first pilot uses its own new database, full physical rollback can be
an operator-approved drop of **only that recorded pilot-owned database** after
exporting the sanitized audit and satisfying retention obligations. No automated
drop command is supplied and no existing database is reset. No photographs means
there is no image/CDN rollback. Keep a rollback ledger of run/source/review IDs,
created vs linked records, publication changes and before/after visibility.

## Success criteria and decisions needed

- Exactly 25 validated genuine products, or stop and request a quantity revision.
- No guessed metadata, ambiguous automatic merges, unauthorized fields or images.
- Complete source/run/record provenance, quality and error summaries; unknowns
  reported, not filled. Manual review for every record; zero public records by default.
- Bounded requests, disabled schedule, cancellation/revocation tested synthetically.
- Report received/validated/staged/unchanged/rejected/deferred/published counts,
  missing attributes, duplicate classes, elapsed time, request count, checkpoints,
  error codes, manifest/config hashes, audit IDs and rollback result.

User decisions: monitored contact; current source/access evidence acceptance;
exact discovery activity/query/class and request budget; final 25 candidate IDs;
collection/storage destination and retention; rollback ownership; and separate
public publication approval. Images, larger catalog expansion, scheduled sync,
production hosting, paid services and the existing Vercel/PWA are outside scope.
