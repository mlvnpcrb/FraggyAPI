# Phase 2M delivery gate — blocked pending independent verification

Reviewed 2026-10-19. Approved implementation commit:
`6df3ca272ffca6fc72d64bd9a5dc31c6a40e7342`, branch
`feat/phase-2m-search-enrichment`. No push, PR, deployment or settings mutation.

## Read-only findings

- GitHub's commit-status API still reports Vercel success for Phase 2L head
  `99737e199d4b4e8b1f8243d06e2febb9640a88cf`, at 08:35 UTC on October 19.
- The [Vercel bot comment on PR #12](https://github.com/mlvnpcrb/FraggyAPI/pull/12#issuecomment-6263104744)
  identifies a GitHub integration, `fraggyapi-demo`, root `apps/web`, and a Ready
  preview. This is historical GitHub evidence, not a current Vercel API inspection.
- `.github/workflows/ci.yml` builds and tests locally; it contains no deployment
  command. Skipping Actions cannot be treated as disabling the Vercel GitHub App.
- `apps/web/vercel.json` specifies build commands/framework/output only. It has no
  branch deployment prevention rule. No repository rule was added or guessed.
- Read-only `git ls-remote --heads origin feat/phase-2m-search-enrichment` returned
  no branch. PR #12 remains open with base `feat/phase-2k-multisource-offline`.
- Requests to official Vercel Git documentation and the project API failed at the
  network proxy with CONNECT 403 Forbidden. This is not proof of team permission
  status. There is no callable Vercel connector in this session.

The separate Vercel GitHub integration is the observed deployment mechanism.
Exact webhook event (push versus PR), current branch rules, ignored-build behavior
and current project configuration cannot be verified with available access.
No branch-specific safeguard satisfying the user's conditions was independently
verified. No push or PR is permitted under the conditional authorization.

Draft PRs, commit-message CI skips and GitHub Actions branch filters are not
verified Vercel safeguards. A build-time abort is not sufficient evidence that no
deployment object will be triggered. Testing by pushing would violate the gate.

Next decision: restore read-only Vercel configuration/documentation access or
provide an independently reviewable operator verification of a branch-specific
deployment block covering both push and PR events. Any proposed settings change
requires separate approval; this document authorizes none. After verification,
push without rewriting history and stack the PR on `feat/phase-2l-intelligence`.
Then verify actual GitHub CI and Vercel activity; neither is claimed here.

## Existing benchmark and future concentration optimization

The [local report](phase-2m-local-report.md) documents the reproducible 10,000-record
fictional benchmark: 100 brands, 21,000 releases, 42,000 variants, 235,100 provenance
claims and 100 reviewed aliases. Ten measured requests follow one warmup per case.

| Search                 | Median ms |  p95 ms |
| ---------------------- | --------: | ------: |
| Exact                  |   195.434 | 235.765 |
| Typo and brand         |   225.485 | 320.940 |
| Alias                  |   208.713 | 282.961 |
| Concentration          |   347.030 | 536.665 |
| Absent Lattafa Khamrah |    40.960 |  45.039 |

These are existing measurements, not a new run. They include ASGI and real
PostgreSQL rights-aware projection, excluding browser/network latency. Zero errors
occurred in 55 requests; the small sample does not establish a production SLA.

Concentration is the slowest measured case. The cause has not been profiled;
future work should:

1. Capture `EXPLAIN (ANALYZE, BUFFERS)` in an owned disposable database, separating
   candidate filtering, release eligibility, field-rights checks, window counting
   and projection costs across selective and broad concentrations.
2. Measure whether restricting release eligibility to indexed text candidates
   before repeated rights predicates improves the plan. Preserve same-release
   semantics, variant distinctions and current revocation checks.
3. Evaluate composite release indexes using actual plans and selectivity; measure
   read benefit, index size and write cost before adding a migration.
4. Profile repeated provenance/rights subqueries and compare set-based eligibility
   evaluation. Never replace current authorization with stale cached permission.
5. Measure exact-total window counting separately; any pagination/count tradeoff
   must preserve the public API contract or receive explicit API review.
6. Re-run identical workloads at 10,000 and larger bounded datasets, with more
   timed samples and controlled concurrency. Report latency, SQL reads and memory
   rather than assuming a particular index or rewrite will help.

This delivery investigation changes no search implementation, provider policy or
source licensing. Open Beauty Facts remains one independent disabled provider in
the multi-source system. No genuine requests/imports/publication were performed.
