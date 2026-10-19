# Phase 2L audit

Verification date: 2026-10-19. Branch: `feat/phase-2l-intelligence`, based on
Phase 2K `4d5af2026edc0b79b339b65bb0ace1fe5dcc1daf`. The PR is stacked on
`feat/phase-2k-multisource-offline`; PRs #8–#11 remain open and unmerged.

## Demonstrated behavior

Run `pnpm catalog:intelligence` for machine-readable evidence. Original examples:

| Pair                                                 | Evidence score | Explanation                                           |
| ---------------------------------------------------- | -------------: | ----------------------------------------------------- |
| Same fictional brand/name/year, EDP vs eau_de_parfum |             90 | Concentration aliases agree; ready for human review   |
| Lumiere Archive vs Lumière-Archive                   |             79 | Orthographic candidate; manual identity verification  |
| Lumiere Archive vs Lumiere Archive Intense           |             49 | Possible flanker; cannot infer shared release         |
| EDP vs EDT                                           |             20 | Distinct concentration guard                          |
| Original vs a labelled 2022 reformulation            |             49 | Edition and conflicting release-year guards           |
| EDP vs unknown concentration labelled Elixir         |             49 | Unknown strength identity; no invented Parfum mapping |

These are heuristic evidence points, not calibrated confidence probabilities.
Multiple competing candidates are additionally capped at 69. Conflicting perfumers,
notes, accords and families retain source claims for review. Variant and missing-field
flags remain separate from identity scoring and existing completeness reporting.
No scenario authorizes merging or publication.

Diagnostics demonstrate 403 access restriction (stop, no bypass), 429 rate limiting
(honor Retry-After/budget), timeout (bounded retry), missing required field paths,
changed response format, duplicate page and incomplete pagination. Actual local
HTTP/PostgreSQL collector tests verify immediate 403 failure and three-attempt
timeout exhaustion; no real upstream data is involved. Bodies and exception text
are excluded. The priority demonstration selects a higher-priority task and defers
its duplicate fingerprint, but cannot dispatch anything.

## Performance measurements

Commands: `pnpm catalog:intelligence --benchmark --size 10000`, repeat with
`--size 50000`, and `--size 10000 --hotspot`.

|          Original observations | Evaluated pairs |  Elapsed | Traced peak |    Labelled counterparts retrieved | Overflow events |
| -----------------------------: | --------------: | -------: | ----------: | ---------------------------------: | --------------: |
|            10,000, two streams |           5,000 |  3.367 s |   37.65 MiB |                      5,000 / 5,000 |           3,600 |
|            50,000, two streams |          25,000 | 15.862 s |  190.04 MiB |                    25,000 / 25,000 |          43,600 |
| 10,000, identical-name hotspot |    10,000 (cap) |  4.277 s |   49.26 MiB | Not a qualified identity benchmark |          39,744 |

One local Python process, generated inputs/index/scoring included, with
`tracemalloc` overhead. No HTTP, database, disk persistence or production service
throughput is measured. Normal workloads use 100 invented houses, unique numbered
names and 10% diacritic variations in the second stream. Retrieving these labelled
counterparts does not establish general real-world precision or recall.

**All three runs report `complete_within_candidate_rules=false`.** Common-token
bucket capacity is exceeded even in the numbered-name runs. Hotspot processing
also hits the pair limit; its identical names do not identify unique true matches.
Overflow counts are attempted bucket insertions, not unique dropped records.
These measurements demonstrate bounded execution and expose recall tradeoffs;
they do not prove exhaustive deduplication at catalog scale. Existing persisted
rehearsal limits remain 5,000 observations, not 50,000.

## Verification

| Local check                                                                                    | Actual result                                                                                                                                     |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RUN_DB_TESTS=1 pnpm exec turbo run test --force` + `.venv/bin/python -m unittest discover -v` | 429 backend + 63 frontend + 3 ingestion = **495 passed**, no skips; preserves 465 existing tests and adds 30                                      |
| `pnpm lint` and `ruff format --check apps/api scripts workers`                                 | Passed; 102 Python files formatted                                                                                                                |
| `pnpm typecheck`                                                                               | mypy (49 source files) and TypeScript passed                                                                                                      |
| `pnpm format:check`                                                                            | Prettier passed                                                                                                                                   |
| `pnpm exec turbo run build --force`                                                            | Backend compile and Next.js production build passed                                                                                               |
| Alembic `upgrade head`, `current`, `check`                                                     | `0006_media (head)`; no new upgrade operations                                                                                                    |
| `scripts/smoke.py --manage-services --check-db-outage --demo-catalog`                          | API/web routes and unknown 404s passed; readiness 503 during DB outage and 200 after recovery, health 200 throughout; PostgreSQL restored healthy |
| `scripts/check_secrets.py`                                                                     | 240 working-tree files, 38 commits, 394 historical blobs; zero heuristic findings before this commit                                              |

Final check results and remote workflow links are recorded in the Phase 2L PR.
The local completion checks cover the full PostgreSQL-backed suite, frontend and
ingestion tests; Ruff lint/format, mypy, TypeScript, Prettier; forced production
build; Alembic upgrade/current/check; runtime readiness/outage recovery; and the
repository heuristic secret scan. New regressions exercise extraction contracts,
identity/reformulation/concentration distinctions, aliases, provenance/conflicts,
index bounds/ambiguity, malformed responses, pagination, access failures, retry
budgets and the unsigned planner. Existing tests are retained without weakened
assertions. No dependency or migration changes are necessary.

The existing development-only `braces` advisory GHSA-vfj7-8cjw-p6xm remains a
documented limitation; this phase is not a penetration test or security waiver.

## Remaining activation requirements

- Verify current official source access, storage, intended commercial reuse and
  public redistribution rights separately, with evidence and expiry/revocation.
- Obtain explicit approval for a named source, exact endpoint/fields, quantity,
  request budget, destination, retention and rollback. A monitored contact remains
  necessary where required; `CONTACT_EMAIL` is still a placeholder.
- Current source evidence cannot be refreshed where official policy access is
  blocked. Do not invent permissions or bypass those denials. Existing source
  comparisons remain assessments, not new approvals.
- Validate source-specific schemas against independently authorized examples.
  Fictional Fragrantica/Parfumo contracts cannot be enabled as real parsers.
- Review ambiguous identity, provenance, factual claims and separate field/image
  publication rights. No images were acquired; image approval remains independent.
- Review index recall under authorized representative data before increasing
  persisted batch limits. Priority dispatch integration remains future work, not
  an enabled recurring collection service.

All seven website adapters remain disabled. No genuine records, images, imports,
publications, paid services, Vercel changes, deployments or PWA changes occur here.
