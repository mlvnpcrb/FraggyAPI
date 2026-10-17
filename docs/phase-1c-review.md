# Phase 1C implementation review

Date: 2026-10-17. Scope: finalize the Phase 1 foundation; no Phase 2 work.

## Review and corrections

- Confirmed the existing GitHub remote is `mlvnpcrb/FraggyAPI`. It had no refs at
  the start of review. The first foundation commit targets `main`; any intervening
  remote refs must be reported rather than overwritten. No force push is permitted.
- Made frontend type checking run `next typegen` before strict TypeScript so it
  works before the first production build. Disabled type-check caching so a cached
  check cannot skip regeneration of missing types. Added root Ruff configuration
  as a Turbo global dependency so lint caches reflect policy changes.
- Excluded generated `apps/web/next-env.d.ts` from Git/Prettier alongside `.next`,
  caches, node_modules, Python bytecode, venvs and build outputs. Only source,
  templates, lockfiles, configuration and documentation should be staged.
- Pinned CI actions to verified official release SHAs and fixed the runner to
  Ubuntu 24.04 after the first successful run warned of deprecated action runtimes
  and an impending `ubuntu-latest` OS migration.
- Disabled checkout credential persistence in CI and enabled manual workflow
  dispatch in addition to main pushes and pull requests. CI remains read-only,
  bounded to 20 minutes and uses local Compose without paid services.
- Reviewed SQLAlchemy session disposal, migration metadata and async driver options.
  Alembic has an empty foundation revision and no fragrance models. Upgrade/check
  and real database outage/recovery passed. No database secret enters web code.
- Confirmed explicit CORS, safe exception responses, sanitized structured logs and
  ignored environment files. The public disposable local database password is a
  development template, not a production credential. No secret values were logged.
- Preserved all seven disabled source adapters and fixtures. The UI remains clearly
  synthetic, with original CSS illustrations and no external image licenses needed.
- Preserved the free-first decision record: native CPython API, portable PostgreSQL,
  no assertion that Workers supports the complete asyncpg/SQLAlchemy dependency stack,
  and no hosted deployment, account creation or spending.

## Security review evidence and remaining advisory

`pnpm audit --prod --json` reported zero production dependency vulnerabilities.
`pip-audit -r apps/api/requirements-dev.lock --no-deps --disable-pip` (with a writable
temporary cache) reported **No known vulnerabilities found**. The full JavaScript
audit reported one **high** development-only advisory:

- [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm): `braces`
  3.0.3 stack-exhaustion denial of service through deeply nested glob patterns.
- Path: `eslint-config-next` → `@next/eslint-plugin-next` → `fast-glob` →
  `micromatch` → `braces`.
- The registry reported no published patched version; `pnpm view braces version`
  returned 3.0.3 and the installed Next ESLint configuration is the current release.
  The advisory has not been suppressed or represented as fixed.
- This affects development lint tooling, not the public API or production dependency
  set. Do not feed externally supplied glob patterns into that tooling. Review an
  upstream patch as soon as one is published; replacing the dependency without a
  compatible upstream fix would require a separately validated tooling change.

Secret scanning found no credential matches in nonignored files. It prints only
paths/counts and scans reachable committed blobs as well. This heuristic and
manual review do not guarantee detection of every possible secret format.

## Local validation

- Frozen pnpm installation and peer dependency check passed.
- Removed generated route types and the Next environment declaration, then ran
  `pnpm typecheck`: generation and strict checks passed without requiring a build.
- `pnpm lint`, `pnpm build`, `pnpm format:check` passed.
- `RUN_DB_TESTS=1 pnpm test`: 14 API + 3 web + 3 ingestion tests passed, no skips.
- Alembic check: `No new upgrade operations detected.`
- Managed production smoke passed frontend route/content checks and real readiness
  200 → 503 → 200, with liveness staying 200 during PostgreSQL outage.
- No browser code references database URLs or database password settings.

## Remote verification boundary

Local validation is not GitHub CI evidence. At review time the GitHub API request
was blocked by the environment network proxy; the repository and Actions HTML
pages were accessible. An `api.github.com` domain addition was saved as an
unpublished environment draft, preserving the package-manager presets. Saving
that draft alone does not change running access. Actual remote commit/workflow
status must be inspected after push and reported with its exact URL and SHA.

The Phase 1B audit is a historical record of the pre-commit local baseline. The
final Phase 1C report in the task response records the pushed commit and actual CI
outcome; do not infer remote success from this review document.
