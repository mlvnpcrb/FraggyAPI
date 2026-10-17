# ADR 001: Free-tier development and future hosting

Date: 2026-10-17. Status: accepted for local development; hosted rollout deferred.
No resources, accounts, paid services, scheduled ingestion or deployments were created.

## Decision

Keep FastAPI + SQLAlchemy + asyncpg on standard CPython, PostgreSQL in local Compose,
and Next.js on Node 24. Supabase Free is the candidate hosted PostgreSQL service.
Cloudflare Free is a candidate for frontend delivery, subject to a separate adapter
compatibility task. A commercial API needs capacity, rights review and availability
planning before launch; free tiers are an evaluation budget, not a production SLA.

## Options and constraints

| Option                               | Evaluation                                                                                                                                                                         | Decision                                                                                                                           |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Supabase Free                        | Compatible PostgreSQL service; hosted credentials and verified TLS needed; direct endpoints may need IPv6, session pooler supports IPv4. Free limits can pause/block usage.        | Candidate database; no live connection or account created.                                                                         |
| Cloudflare Workers Free              | JavaScript/edge execution; Python runs under Pyodide/WebAssembly, not an ordinary CPython VM. FastAPI support alone does not prove the native database driver works.               | Do not deploy this Python API unchanged.                                                                                           |
| Cloudflare Pages Free                | Good for static exports. This app's `/fragrances` reads server search params dynamically, so the current Next build cannot be treated as a plain Pages static export.              | Static delivery would need an explicit, separately tested frontend adaptation.                                                     |
| Cloudflare Next.js on Workers        | Current official guide recommends beta vinext; also describes OpenNext as another path. Both require a compatibility check and adapter-specific validation, not just `next build`. | Preserve native Next.js now; evaluate an adapter in a deployment task.                                                             |
| GitHub Actions scheduled ingestion   | Ephemeral standard Linux runners can run Python, but schedules are best-effort and storage/compute quotas apply. Not a persistent API host.                                        | Future authorized small imports only; no ingestion schedule in Phase 1B.                                                           |
| Standard CPython ASGI/container host | Runs Uvicorn/FastAPI and native asyncpg without a Wasm rewrite. A free Render web service or an existing user-owned Linux machine is a candidate for evaluation.                   | Recommended API runtime class; provider choice and eligibility remain unverified. No promise of an always-on free commercial host. |

### Quotas observed in official documentation

The following were read on 2026-10-17 from providers' official documentation source
repositories over verified HTTPS. Public documentation websites were blocked by the
cloud proxy (403); official GitHub raw sources were accessible. Revalidate before
provisioning because quotas and terms change and account-specific limits can differ.

- **Supabase Free:** two active free projects, 500 MB database per project, 1 GB
  storage, and 5 GB egress in the billing table. Free projects can be paused; the
  exact current inactivity threshold was not independently verified. Monitor the
  dashboard; do not create artificial activity to evade plan restrictions. Paid
  organization upgrades affect all projects in that organization.
- **Workers Free:** 100,000 requests/day, 10 ms CPU/request and 128 MB isolate memory;
  the documented daily cap returns error 1027 on exhaustion. CPU time differs from
  wall-clock database wait time. These budgets are a poor assumption for untested
  Python ORM initialization or CPU-heavy imports.
- **Pages Free:** 500 builds/month, one concurrent build, 20-minute build timeout,
  20,000 files/site and 25 MiB per asset. Pages Functions consume Workers quotas.
- **GitHub Actions:** standard public-repository runners are free; private GitHub
  Free accounts include 2,000 minutes/month and 500 MB shared artifact storage.
  Cache allowance is 10 GB/repository. Larger runners are billed even for public
  repos. Scheduled workflows may be delayed/dropped; public schedules are disabled
  after 60 days without repository activity. Set short retention and job timeouts;
  never rely on exact execution time or store database state in artifacts.
- **ASGI host:** current Render free hours, idle suspension interval, commercial
  eligibility, egress and database access constraints were not verified from its
  documentation because its site was blocked. Do not assume any numeric allowance
  or create an account until those terms are reviewed.

### FastAPI compatibility decision

Cloudflare documents FastAPI on Python Workers and support for pure Python,
PyEmscripten and Pyodide-included packages. It does not establish compatibility of
our entire stack: asyncpg uses native components and CPython asyncio networking;
SQLAlchemy's async path also depends on greenlet. No Workers-compatible artifacts
or real PostgreSQL connectivity were validated for these dependencies. Alembic
should run in a separate trusted CPython migration job regardless of the request
runtime. Keep FastAPI and choose a standard CPython container/ASGI host rather than
silently rewriting the API in JavaScript or dropping SQLAlchemy.

### Database connections and security

The API's pool is 3 plus 2 overflow per process; two workers can therefore consume
10 connections before migration/admin connections. Free compute has finite server
and pooler connection limits: read the project's exact current limits rather than
assuming the pooler removes them. Bound replicas, keep a safety margin and monitor
pool wait/timeout metrics. Migrations use a direct or session-mode URL and NullPool.
Statement caches are disabled, but transaction pooling still needs separate tests.
The Supabase direct/session setup is configuration-compatible, not live verified.

Use server-side secret storage, `ssl=verify-full` for asyncpg with the correct trust
chain, explicit CORS, and a separate migration URL if needed. No database password
or service-role key may enter frontend builds. Public API availability must report
readiness failures during free-project suspension instead of claiming health.

## Suspension, commercial restrictions and upgrades

Do not sell uptime that a sleeping/suspendable free instance cannot provide. Review
provider acceptable-use, commercial-use and account eligibility terms before launch;
fragrance source collection and redistribution licenses are a separate prerequisite.
Free hosting never grants dataset rights. Quota exhaustion must fail safely without
an automatic paid upgrade. Keep billing disabled or capped when the provider allows
it; this task authorizes no spending.

Upgrade the database when size, egress or connection headroom is insufficient, choose
an always-on CPython host when latency/availability matters, and consider paid edge
capacity only after measuring a compatible frontend build. Keep migrations, portable
PostgreSQL URLs and native ASGI entry points so these changes do not require a stack
rewrite. Backups/export and restoration must be validated before real catalog data.

## Evidence and references

Official source documents successfully retrieved during this task:

- [Supabase billing source](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/platform/billing-on-supabase.mdx)
- [Supabase connection guide source](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/connecting-to-postgres.mdx)
- [Workers limits source](https://github.com/cloudflare/cloudflare-docs/blob/production/src/content/docs/workers/platform/limits.mdx)
- [Python Workers packages source](https://github.com/cloudflare/cloudflare-docs/blob/production/src/content/docs/workers/languages/python/packages/index.mdx)
- [Python Workers runtime source](https://github.com/cloudflare/cloudflare-docs/blob/production/src/content/docs/workers/languages/python/how-python-workers-work.mdx)
- [Next.js on Workers source](https://github.com/cloudflare/cloudflare-docs/blob/production/src/content/docs/workers/framework-guides/web-apps/nextjs.mdx)
- [Pages limits source](https://github.com/cloudflare/cloudflare-docs/blob/production/src/content/docs/pages/platform/limits.mdx)
- [Actions billing source](https://github.com/github/docs/blob/main/content/billing/concepts/product-billing/github-actions.md)
- [Actions included quotas source](https://github.com/github/docs/blob/main/data/reusables/billing/actions-included-quotas.md)
- [Scheduled workflow source](https://github.com/github/docs/blob/main/content/actions/reference/workflows-and-actions/events-that-trigger-workflows.md)

Runtime/provider validation still required: Supabase connectivity and TLS, selected
Cloudflare adapter build, account-specific quotas/terms, CPython provider suitability,
and commercial-use review. These do not block local Phase 1B development.
