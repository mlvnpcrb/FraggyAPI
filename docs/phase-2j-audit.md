# Phase 2J — offline pilot preparation audit

Assessed 2026-10-19 (Asia/Manila). Scope: prepare a 20–50-record one-source real
pilot safely; **no genuine discovery, collection, import, images or publication**.

## Repository and preserved work

At start, only open PRs #8 (Phase 2H) and #9 (Vercel synthetic demo) existed.
Local/remote branch and documentation review found no Phase 2J work to resume.
`feat/phase-2j-real-data-readiness` is stacked on #9's approved commit
`462afdbb02108674f260d1cfc7832d191754ed00`. No predecessor PR was merged. No web,
Vercel configuration, separate PWA, collector policy, registry permission or
existing adapter mapping was modified. The Vercel account/deployment is not
queried or changed by this phase; no new claim about its live status is made.

## Implementation and commands

- `PilotPlan` extends the existing disabled proposal; quantity is 20–50, candidates
  cannot exceed it, and all live-approval flags remain literal false. Readiness
  reports separate collection/storage/publication decisions, exact-list/stale
  review blockers and request ceilings. No flag can activate a source.
- Original SPARQL fixture generation and `dry_run` reuse the existing Wikidata
  parser and quality rules. Missing/extra/duplicate/malformed identities and
  incomplete pagination fail. Content digests are stable; changed payloads differ.
  Equal labels with absent release identity require manual review, not merging.
- CLI `pnpm pilot:prepare [--dry-run]` reads bounded local JSON and emits a report.
  It imports no transport, opens no DB, writes no state, stages/publishes nothing,
  and has no live/schedule option. Static errors avoid input/exception leakage.
- Existing full collector/import/provenance/rights/revocation tests remain intact.
  Real import rollback reuses source revocation and recorded ownership; it does
  not pretend to physically erase shared canonical records.

## Actual local verification

| Check                            | Result / evidence                                                                                                                                                       |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RUN_DB_TESTS=1 pnpm test`       | **PASS: 445** — 379 backend, 63 frontend, 3 ingestion; all 425 previous tests retained                                                                                  |
| New preparation regressions      | **20 passed**; quantities 20/25/26/50, illegal sizes/flags, no-network socket guard, identity/duplicate/malformed/page failure, repeatable hashes and unknown fields    |
| `pnpm pilot:prepare --dry-run`   | **PASS**: 25 synthetic records, five fictional brands, one page, 25 unknown years/notes, quality complete; zero requests/writes/staged/published/images; schedule false |
| `pnpm lint`                      | PASS; Ruff and ESLint                                                                                                                                                   |
| `pnpm typecheck`                 | PASS; mypy strict (44 source files), Next/TypeScript                                                                                                                    |
| `pnpm format:check`, Ruff format | PASS                                                                                                                                                                    |
| Forced monorepo production build | PASS; normal API mode preserved                                                                                                                                         |
| Alembic upgrade/current/check    | PASS; `0006_media`, no drift/schema changes                                                                                                                             |
| Secret scanner                   | PASS; zero findings                                                                                                                                                     |
| Fresh policy verification        | **BLOCKED**; legal/access/robots page requests failed; no rights inferred                                                                                               |
| Real pilot/discovery/publication | **NOT RUN**, explicitly unauthorized                                                                                                                                    |

The existing Node-only Vercel demo job remains in CI, alongside foundation
checks and the new offline pilot rehearsal. Actual final-head GitHub results and
immutable SHA are recorded in the PR delivery report; local success is not a
remote-success claim. PR #8/#9 and this PR must remain open and unmerged.

## Legal and operational status

Wikidata is the conditional first-source recommendation, not an enabled source.
Historical official CC0 evidence is referenced; current access/licensing/robot
rechecks were unsuccessful. All seven websites remain disabled and unapproved.
No verified free manufacturer/distributor data agreement or alternative open
fragrance dataset was established. No real candidate IDs were invented.

`CONTACT_EMAIL` remains the approved placeholder. No contact, source grant,
discovery query/class, real candidate list, collection run, publication or mass
collection is silently approved by this PR. No paid resources, database resets,
public deployment or image downloads occurred. The existing development-only
braces advisory remains disclosed in Phase 2H/Vercel docs; this phase changes no
dependency versions and makes no new full-security-clearance claim.

**Conclusion:** offline Phase 2J implementation and pilot planning complete;
Phase 2K real execution **BLOCKED** until the source-specific decisions in
[the pilot plan](phase-2k-pilot.md) are satisfied. The dry-run is runnable now;
the live pilot is not yet legally/operationally cleared.
