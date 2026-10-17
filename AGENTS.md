# FraggyAPI engineering rules

## Boundaries and phase

- Phase 1B establishes infrastructure and synthetic UI only. Do not add fragrance
  database models, ingestion orchestration, or live source collection without an
  explicit later-phase task. Preserve existing ingestion tests and fixtures.
- `apps/web` is Next.js App Router; `apps/api` is FastAPI. Browser code must never
  import Python, database credentials or server environment configuration.
- Keep synthetic frontend data in `apps/web/src/lib/mock-data.ts` until a scoped API
  client replaces it. Label invented data clearly. Do not use unlicensed images.
- Use the existing isolated cloud checkout. Do not create worktrees unless requested.

## Conventions

- Python 3.12+, typed functions, Pydantic v2 settings and SQLAlchemy 2 async sessions.
  Run Ruff using repository configuration and mypy strict mode.
- TypeScript strict mode; ESLint Next rules and Prettier. Use server components by
  default, client components for interactions, and accessible semantic controls.
- Keep handlers small. Inject sessions through `get_session`; close sessions and
  dispose engines. Bound network/database operations with timeouts.
- API routes live under `/api/v1`; operational `/health` and `/ready` are unversioned.
  `/health` must work without a database; `/ready` must execute an actual query and
  return 503 on failure. Do not return internal exception text to users.

## Migrations

- All schema changes require reviewed Alembic revisions, upgrade/downgrade behavior
  and tests. Do not call `metadata.create_all()` on application startup.
- Never edit applied migrations or reset user data to resolve failures. Use a direct
  or session-pooler URL for migrations; never assume a transaction pooler supports DDL.
- Phase 1B metadata is intentionally empty; the initial revision only establishes
  Alembic history. Catalog models belong to Phase 2.

## Collection and security

- All seven sources remain disabled and pending review. Registry flags alone cannot
  activate adapters. Review access, storage and commercial redistribution evidence
  before any later implementation. Never bypass access controls or rate restrictions.
- Never commit `.env`, credentials, tokens, database dumps or private agreement text.
  `.env.example` contains disposable localhost settings only. Use secure deployment
  settings for real credentials. Never expose secrets in `NEXT_PUBLIC_*` variables.
- Log structured, sanitized events. Exclude bodies, query strings, connection URLs,
  exception messages, credentials and user identifiers from routine logs.
- Use explicit CORS origins. Do not disable TLS verification or package checksums.

## Tests, documentation and completion

- For changes, run relevant checks; before phase completion run `pnpm build`,
  `pnpm lint`, `pnpm test`, `pnpm typecheck`, `pnpm format:check` and the real database
  tests (`RUN_DB_TESTS=1 pnpm test`) after Compose is healthy.
- Verify Alembic upgrade/current/check and real `/ready` success, database outage 503,
  and recovery. Restore services you stop during tests. Test frontend routes and
  unknown slugs. Preserve meaningful assertions; never disable checks to pass.
- Document setup, environment changes, decisions and limitations. Update the audit
  with commands and actual results. Keep unrun/skipped/failed checks distinct.
- CI success requires an actual remote run; local success alone cannot prove it.
  No paid resources, deployments, commits or pushes unless authorized by the task.
- Phase completion requires executable setup, tests, builds and docs, plus reusable
  startup instructions when needed. Do not silently proceed to the next phase.
