# Phase 2K multi-source offline audit

2026-10-19 (Asia/Manila). User requested architecture/implementation plan first,
then safe offline implementation and an unmerged PR. The reported plan reuses
existing collection jobs/transport/authorization/staging/provenance/publication;
Wikidata is one candidate, not an exclusive source.

## Delivered

Four independent synthetic-contract adapters, seven original fixture observations,
bounded cross-source comparison, conflict/variant review, attribute-completeness
scores, repeatable change hashes and resumable local fixture reports. Raw values,
source/dataset identity, collection timestamp, mapping/transformation metadata and
fixture-only rights remain independent. No automatic merge or source winner.

The two website-shaped contracts are **not validated live website parsers**. The
brand feed and Wikidata fixture adapters reuse existing mapping implementations.
New parsers are not wired into live `Endpoint` registration or authorizations.
This is an executable offline integration foundation on the existing engine,
not a claim to have collected a real catalog or tested remote website compatibility.

Architecture, bounds, command examples, missing-field behavior, scale limitations
and future source approval gates are in
[the architecture](phase-2k-multisource-architecture.md). Candidate fields,
collection methods and access/reuse restrictions are in
[the source assessment](phase-2k-source-coverage.md). The earlier Wikidata-specific
pilot document is explicitly marked as an optional unapproved example.

## Local verification

| Command / check                              | Actual result                                                                                                                                                                                                                                           |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RUN_DB_TESTS=1 pnpm test`                   | **465 passed**: 399 backend, 63 frontend, 3 ingestion; all 445 previous tests retained                                                                                                                                                                  |
| New offline regressions                      | **20 passed**: independent mappings, denied sockets/live calls, note positions, conflicts/release distinctions/variants, checkpoint continuation/rollback-on-failure, replay/change hashes, bad inputs, explicit limits and thousand-observation replay |
| `pnpm catalog:rehearse`                      | Seven new source observations, four pages, 12 review pairs; comparison complete; zero external requests/DB writes/publication                                                                                                                           |
| Rehearsal with `--resume-report`             | Seven unchanged, zero new/changed; all source observations retained                                                                                                                                                                                     |
| Thousand-observation fixture stream          | 20 pages, 1,000 new; checkpoint round-trip/replay produces 1,000 unchanged; no timing/production-scale SLA inferred                                                                                                                                     |
| `pnpm lint`, `pnpm typecheck`                | PASS (Ruff/ESLint, strict mypy and TypeScript)                                                                                                                                                                                                          |
| Prettier/Ruff formatting and diff whitespace | PASS                                                                                                                                                                                                                                                    |
| Forced monorepo production build             | PASS                                                                                                                                                                                                                                                    |
| Alembic upgrade/current/check                | PASS, `0006_media`, no drift/schema changes                                                                                                                                                                                                             |
| Secret scanning                              | PASS, zero findings                                                                                                                                                                                                                                     |

Initial targeted tests found a test expectation mismatch: the reused JSON extractor
returns its existing sanitized `CollectionError` for malformed records, rather than
Pydantic's raw validation exception. The test now checks that public contract and
still verifies that the input checkpoint is unchanged. No existing test/assertion,
rights predicate or timeout was removed or weakened. Type checks use the actual
package configuration; an early ad-hoc root invocation did not apply the API's
Pydantic mypy plugin and was replaced by the repository-supported command.

CI adds the offline rehearsal while retaining the complete foundation and Node-only
Vercel demo jobs. Actual final-head workflow URLs/results and immutable SHA are
recorded in the PR delivery report; local success alone is not remote success.

## Preserved boundaries and remaining work

No existing transport, collector policy, canonical matching logic, schema, website,
Vercel configuration or separate PWA is modified. No predecessor PR is merged.
The Phase 2K branch is based on the unmerged Phase 2J branch; all existing PRs stay
open. No source registry permissions are changed, and all seven website skeletons
stay disabled. No source terms/license/access assertion becomes a grant.

No real HTML, API records, datasets or photographs were fetched for these parsers.
No source evidence was invented or access denial bypassed. Current official-policy
verification remains blocked as described in earlier research. No genuine database
imports, automatic schedules, paid services or public deployment were performed.
No new dependency versions are introduced; the previously disclosed development
advisory is not claimed resolved by this work.

Next review: select any individually authorized source, verify actual fields/schema,
access, reuse, storage/commercial/API rights and rates, then approve a bounded real
pilot. Images, publication, mass acquisition and scheduled updates remain separate
approval decisions. Real thousands-record coverage and throughput require actual
licensed data, measured quality and the existing durable PostgreSQL pipeline;
fixture success cannot establish those outcomes.
