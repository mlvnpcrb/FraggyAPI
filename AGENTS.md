# FraggyAPI engineering rules

## Boundaries and phase

- Phase 2J prepares the 20–50-record first real-data pilot using offline
  synthetic fixtures only. No genuine discovery/entity queries, imports, schedules
  or publication are authorized. CONTACT_EMAIL stays a placeholder. Live Phase 2K
  requires fresh source evidence, monitored contact, exact scope/candidate IDs and
  explicit user approval. Preserve PRs #8/#9, Vercel demo files, PWA and all source
  restrictions. New preparation commands cannot approve or activate collectors.

- The explicitly requested Vercel demo is a read-only, original-only bundled
  snapshot, enabled only by `FRAGGY_DEMO_MODE=synthetic`. Its committed public
  demo media are an exception to private storage for original fixture assets only.
  Never export real source data/evidence or use fixtures as an API-error fallback.
  FastAPI/PostgreSQL, authorization and collector defaults remain unchanged.
  No public deployment until the user approves the exact preview configuration.

- Phase 2H is offline pilot readiness, original-only local preview and audit.
  Keep CONTACT_EMAIL as the user-required placeholder until a real monitored
  contact and exact discovery/collection scope are separately approved. Do not
  infer an email or invent genuine Q IDs. Policy research alone is permitted.
  preview:local explicitly creates only its own UUID disposable database and
  original fixture artwork. Never reset the application DB. Stop owned preview
  processes before builds/outage smoke; restart the requested preview afterward.
  Loopback URLs are local to the running machine, never public cloud access.
  Record unpatched dependency advisories and launch blockers without claiming a
  penetration test or waiving rights/security checks. Phase 2H stays unmerged.

- Phase 2G prepares the Wikidata source adapter and independent local media rights
  pipeline. Never run a genuine source query or download a real image without a
  separate source/asset-specific pilot authorization. Policy/documentation research
  is allowed. Fictional Q IDs must never be sent to a real endpoint. Keep images
  private until independent hash-bound storage and publication reviews pass;
  source/image revocation must hide bytes as well as metadata. Use media GC for
  expired/withdrawn storage, preserving shared hashes. No static media mount,
  external hotlink, paid CDN, PWA changes or automatic licensing approval.

- Phase 2F adds explicitly reviewed, disabled-by-default automated collection to
  the existing import/review/publication system. External network remains off by
  default; never activate real collection or the seven website skeletons in this task.
  Durable collection policies, leases and checkpoints do not authorize publication.
- Phase 2E adds read-only catalog quality reports, source/license research and
  disposable synthetic PostgreSQL benchmarks to the reviewed attribution/import
  foundation and trusted local operator review,
  on the Phase 2A schema and Phase 2B read-only public API. Keep parsing, matching,
  staging, canonical review and field publication separate. No automatic merge,
  website collection, public admin/upload route, Phase 2F collection or Phase 3 without a task.
  Preserve operational health/readiness and all earlier phase tests.
- Manifest flags are untrusted: only an explicit operator-reviewed manifest digest
  in PostgreSQL authorizes storage; publication requires a separate record decision.
  Quarantine unverified inputs as hashes/metadata only, never raw payloads.
  Operator commands stay non-production/loopback in this phase. Real datasets,
  private evidence/manifests and reports must not be committed.
- Quality commands are non-production/loopback, PostgreSQL read-only and never
  merge/correct/approve data. Reports expose sanitized counts/UUIDs, not legal
  evidence. Explicit truncation is not a clean audit. Benchmark writes are only
  original synthetic fixtures in UUID-owned disposable databases; never reset or
  benchmark-load the application database. Keep report artifacts in ignored paths.
- Attribution is public-only, adjacent-record plain text with safe HTTPS links.
  Human acceptance, complete metadata, current verification date and no unresolved
  conditions are required. Never expose private review evidence. Preserve additive
  DTO compatibility; whole-source and individual field withdrawal remove credits
  with grants. Keep all seven adapters disabled.
- `apps/web` is Next.js App Router; `apps/api` is FastAPI. Browser code must never
  import Python, database credentials or server environment configuration.
- Web pages use the typed public API client in `apps/web/src/lib/api.ts`; never
  fall back to frontend fixtures on API failures. Label synthetic records.
  `CATALOG_INCLUDE_SYNTHETIC` is opt-in and is always ignored in production.
  Only explicit rights-checked projections may leave the API; selected claims
  alone do not authorize redistribution. Do not use unlicensed images.
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
- The initial revision establishes history; subsequent revisions own catalog,
  provenance, search and data-quality changes. Import model metadata in Alembic,
  never call create_all at startup. Run destructive round trips only in randomly
  named disposable local test databases, never in the application database.
- Canonical UUIDs are independent of names/slugs. Do not merge releases or versions
  based on names. Preserve nulls, conflicting claims and field-level rights evidence.
- Demo seeding requires an explicit flag, refuses production/remote CLI targets,
  and must not overwrite existing rows. No seed runs in migrations or startup.

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
