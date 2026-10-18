# Source authorization and publication rights

A dataset's file and manifest are untrusted input. A license name/URL, provider
assertion, `authorization_status: approved`, or `storage_permissions: true` is
**never sufficient authority**. None of those values can activate a website adapter
or directly authorize storage/publication. There is no HTTP source approval route.

## Trusted review boundary

The trusted operator runs the local CLI with access to the local database. That OS
and database access is the authorization boundary; `--reviewer` is an audit identity,
not an authentication mechanism or a cryptographic signature. Do not expose the CLI
as a network service or let untrusted users run it with operator credentials.
Future production operation needs separately reviewed credentials/access policy;
this phase refuses production and non-loopback targets.

An operator must actually inspect independent ownership/provider evidence, access,
storage, field-level commercial redistribution, restrictions and attribution terms.
The software records that review; it does not establish legal truth or authenticate
an agreement. Use opaque evidence references, not credentials, signed URLs or copied
private contracts. No evidence URL is fetched by the importer.

A strict source manifest includes:

- `source_id`, `source_name`, `dataset_origin`, `provider`;
- declared `authorization_status`, `storage_permissions`, `redistribution_permissions`;
- `permitted_fields`, `attribution_requirements`, `license_evidence_references`;
- optional declared `review_date`, and `synthetic` (default false).

The actual trusted review timestamp is written by the operator command using UTC,
not accepted from the file's date. Missing/empty evidence reference lists are
invalid. The manifest's complete validated content is hashed using deterministic
JSON. Formatting changes do not change the digest; policy/provider changes do.

```sh
# Only after independently reviewing the provider evidence:
pnpm catalog:manage source-review \
  --manifest data/examples/source-manifest.json \
  --allow-storage \
  --publish-fields name,slug,brand_id,fragrance_id,concentration,release_year,notes,accords \
  --reviewer local-operator \
  --reason 'Reviewed the original fictional fixture and permitted fields'
```

Source review requires exactly one of `--allow-storage` and `--deny-storage`;
omitting a storage action cannot accidentally withdraw/purge existing snapshots.

This stores an `operator_source_review` event in `data_sources.evidence`, including
reviewer, reason, time, digest and reviewed policy. Import authorization requires
that DB-owned event, matching digest and current approved storage status. Changing
a file flag afterward makes it unreviewed, rather than increasing its privileges.
Every supplied nonempty record field must be in the reviewed storage field list;
publication fields must also be explicitly listed and separately selected by the
operator command. Include both source names (`brand_name`, `fragrance_name`) and
permitted derived public fields (`name`, `slug`, `brand_id`, `fragrance_id`) when the
reviewed license supports that transformation/publication.

Omit `--publish-fields` for private storage-only imports. Mandatory attribution is
recorded but not yet supported in public DTOs: such sources may be stored/reviewed
with permission, but publication is refused. This fails closed instead of silently
dropping required credits. Explicit `--deny-storage` withdraws future raw storage
and purges stored raw snapshot payloads for that source, retaining minimal audit
metadata/provenance for review. Independently review retention requirements for
existing canonical/audit metadata; the CLI does not claim a universal deletion law.

## Quarantine and publication

Without trusted storage approval, import retains only minimal source identity,
record/manifest hashes, run and review metadata. It does not retain raw record
payloads, original provider record IDs, source URLs, canonical fragrance data or
field values. Dry-run likewise reports hashes and rights-review categories only.
After source authorization, reimport the original local file to stage a reviewed
snapshot; a hash-only quarantine entry cannot be approved into canonical data.
Reject/defer older quarantine entries explicitly as appropriate.

Approved storage is not approval to publish. Canonical review creates private,
rights-pending field claims. After that, `publish --record-id ... --fields ...`
requires the current source review, linked snapshot and an explicit permitted field
list. It records a separate audit event and evidence reference. Only selected,
known field claims receive publication rights; conflicts and unknowns cannot be
published by that operation. The Phase 2B projection also compares each claim to
the current canonical value, requires reviewed source policy/record/field rights,
and never serializes raw snapshots, reviews, credentials or license evidence.

`revoke --source SOURCE_ID --reviewer ... --reason ...` immediately restricts the
source's publication, all snapshot redistribution and all field usage grants.
It retains historically authorized storage/provenance. Re-reviewing a source also
invalidates existing publication grants: it cannot resurrect prior publication.
A new explicit record publication decision is required. The public API remains
`Cache-Control: no-store`, so application caches do not conceal revocation.

The manifest digest is immutable in staged snapshots. A policy/provider change
requires reimport and a new review revision, not reuse of old authority. Human
review decisions remain append-only through the CLI; source events and publication
queue events retain reviewer/time/reason. Trusted DB administrators can alter the
DB directly; tamper-proof external audit infrastructure is not claimed.

## Synthetic data and pending websites

Fictional examples set `synthetic: true`. They still require an operator source
review and record/publication decisions. Their source type is
`synthetic_file_import`, with synthetic source/record/field rights. They are visible
only with the development `CATALOG_INCLUDE_SYNTHETIC=true` setting and always hidden
in production. A source cannot change between real and synthetic types through a
manifest edit. Existing Phase 2A synthetic fixtures retain their original behavior.

All seven website source identifiers are reserved and rejected by file-source
review/import commands. Their adapters/configuration stay disabled and
`pending_review`. A separate licensed file source does not grant website collection
rights. Do not download a dataset or scrape a site merely to test this workflow.
