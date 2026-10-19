# Vercel original-only website preview

Prepared 2026-10-19 (Asia/Manila). **No Vercel deployment has been created.**
Public deployment requires the user's approval of the configuration below.
This preview is a separate, read-only website mode. FastAPI, PostgreSQL,
Alembic, provenance, image approval/revocation and all collector policies retain
existing behavior. This is not a genuine-data pilot, beta or production launch.

## Approval configuration

| Setting                                     | Exact proposed value                                                                                                                                                     |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Project                                     | `fraggyapi-demo` (or an available equivalent; final URL assigned by Vercel)                                                                                              |
| Repository                                  | `mlvnpcrb/FraggyAPI`                                                                                                                                                     |
| Source branch                               | `feat/vercel-synthetic-demo` at the final reviewed PR head                                                                                                               |
| Deployment target                           | **Preview**, never `--prod`; do not promote to Production                                                                                                                |
| Framework preset                            | Next.js                                                                                                                                                                  |
| Root Directory                              | **`apps/web`**                                                                                                                                                           |
| Include source files outside Root Directory | **Enabled** for workspace root, lockfile and packages                                                                                                                    |
| Node.js version                             | **24.x**, matching `.node-version` and root engines                                                                                                                      |
| Package manager                             | **pnpm 11.25.0**, root `packageManager`; preserve frozen lockfile                                                                                                        |
| Install command                             | `cd ../.. && pnpm install --frozen-lockfile`                                                                                                                             |
| Build command                               | `pnpm run build` (inside `apps/web`, not root `pnpm build`)                                                                                                              |
| Output Directory                            | `.next`                                                                                                                                                                  |
| `FRAGGY_DEMO_MODE`                          | **`synthetic`**, Preview environment, build and runtime                                                                                                                  |
| `ENABLE_EXPERIMENTAL_COREPACK`              | **`1`**, Preview environment, for pinned pnpm selection                                                                                                                  |
| API/database/collector credentials          | **None**; leave `API_BASE_URL`, `DATABASE_URL`, `MIGRATION_DATABASE_URL`, and all collector secrets unset                                                                |
| Public variables                            | No `NEXT_PUBLIC_*` values required                                                                                                                                       |
| Resources                                   | No database, backend, Blob, storage/CDN add-on or paid integration                                                                                                       |
| Access                                      | Retain Vercel Authentication for this first Preview; owner signs in on phone/laptop. Do not disable protection or add paid protection features without separate approval |
| Indexing                                    | `X-Robots-Tag: noindex, nofollow, noarchive`; this is not authentication                                                                                                 |
| Billing                                     | Existing eligible free plan and included quotas only; no paid upgrades, commercial-plan assumptions or paid resources                                                    |

`apps/web/vercel.json` stores the framework and commands. Root Directory,
Node version, source-files setting and environment scopes are **project settings**;
`vercel.json` alone does not configure them. Do not add Python to the Vercel
install/build. Existing FastAPI hosting is deliberately outside this preview.
Root Turborepo builds include `FRAGGY_DEMO_MODE` in their environment/cache inputs.
Changing mode requires a rebuild and matching runtime configuration.

## Deploy only after approval — no Mac/Docker required

An operator can execute these steps in the existing cloud checkout. The user
needs only a browser to open the resulting URL. No deployment or login is run
by this implementation task.

1. Review the PR, exact final commit and this configuration. Obtain explicit
   permission to create the preview and the desired access/sharing policy.
2. Use the user's authorized Vercel account/team through its normal login flow;
   never paste tokens into chat or commit `.vercel`/`.env` files. Use an eligible
   free plan, subject to its actual usage terms and quotas. Stop if Vercel asks
   for a paid plan/resource or cannot support the pinned toolchain.
3. From the repository root on the reviewed branch, run `pnpm dlx vercel link`.
   Choose the authorized team, create/link `fraggyapi-demo`, and use the repository
   checkout as the local project directory. **Linking is not deployment.** Do not
   use an import flow that immediately deploys `main` or connects automatic Git
   deployments before the configuration is reviewed.
4. In Vercel Project Settings, enter every setting in the approval table. Ensure
   Root Directory is `apps/web` and outside-root source access is enabled. Add
   the two non-secret environment variables to **Preview**, not Production.
   Keep automatic Git deployments disconnected for this controlled first preview.
5. From the repository root (not `apps/web`, to avoid a doubled root path), run:

   ```bash
   git switch feat/vercel-synthetic-demo
   git rev-parse HEAD # must match the approved final PR head
   pnpm dlx vercel deploy --target=preview
   ```

   Do not use `--prod`, promote a deployment, attach services or change billing.
   The CLI version used for this later action should be recorded in deployment
   evidence; the application dependency lockfile is unchanged by `pnpm dlx`.

6. Inspect Vercel build logs: Node 24.x, pnpm 11.25.0, frozen install, only the
   Next.js build, no Python, database URL or API requests. If a prerequisite or
   setting differs, stop and correct the setting rather than bypassing checks.
7. Copy the **actual** successful deployment URL from Vercel, not a guessed
   hostname. Test `/`, `/brands`, `/fragrances`, brand/concentration/year/note/accord
   filters, search, pagination, details, four original images, placeholders,
   credits and unknown-ID 404. Test at phone/tablet/desktop widths.
8. Test the URL on the user's phone/laptop. If Deployment Protection prevents
   access, use the approved account/share mechanism. Disabling protection or
   making the preview accessible to anyone is a separate explicit access decision.
   Report the deployment URL, source SHA, target, actual checks and limitations.

Vercel documentation references: [monorepos](https://vercel.com/docs/monorepos),
[package managers](https://vercel.com/docs/package-managers),
[Node versions](https://vercel.com/docs/functions/runtimes/node-js/node-js-versions),
[CLI link](https://vercel.com/docs/cli/link),
[CLI deploy](https://vercel.com/docs/cli/deploy).
Requests to these pages were blocked by this environment's CONNECT proxy (403),
so their current contents and actual Vercel build behavior are **not verified**.
Local Next production builds/smokes are evidence of application compatibility,
not proof of a completed Vercel deployment or free-plan eligibility.

## Data and image boundaries

The committed snapshot is the public DTO projection of the existing Phase 2H
owned fictional preview: **100 fragrances, 10 brands, 210 releases, 24 notes and
8 accords**. All records are synthetic. It contains no genuine fragrance records,
external dataset, private licensing evidence, raw import manifest or credentials.
It was copied only from the owned loopback synthetic API, never from a real source.
The 420 internal bottle variants are not exported as a new public variant catalog;
the existing public variant-image group remains on its applicable release.

Four bottle images (primary, gallery, release and variant) were drawn originally
by `apps/api/fraggy_api/preview.py`, processed through the existing
local media approval pipeline, and copied from approved public delivery. The
snapshot contains their existing approved public metadata. Eight bundled WebP
files are the four displays and their thumbnails, not third-party photographs.
Most fragrances intentionally use the existing attractive missing-image placeholder.
SHA-256 hashes in `apps/web/src/demo/media-hashes.json` protect snapshot integrity.

Demo credits explicitly describe original project fixtures and preview use,
in place of fictional workshop/example.invalid permission links. They do not
claim a third-party agreement, real licensing approval or a general open license.
This task authorizes preparing these original assets for the proposed preview;
actual public hosting still requires the user's deployment approval.

Only `FRAGGY_DEMO_MODE=synthetic` selects the bundled server-side data. Unset
means the existing FastAPI path; API failure never falls back to the snapshot.
Invalid mode values fail rather than enabling demo data. Search is bounded,
case-insensitive substring matching of fictional fragrance/brand names with
stable name sorting. It is not PostgreSQL full-text relevance ranking. Brand,
concentration, year, repeated note/accord filters, sorting and pagination work;
release constraints must match the same release. No changes are persisted.

`/media/:id/:preset` permits only the snapshot's known IDs and display/thumb
presets, then redirects to same-origin original static WebP. The existing live
rights-aware proxy remains in use outside demo mode. Static demo assets are
public by design and do not have per-request database revocation. To remove an
original demo asset, update the snapshot/hashes, delete the file, redeploy and
remove old deployments as required. **Never put real or revocable licensed
assets in this static folder**: real-source publication must use the existing
rights-aware backend and separate approval.

There are no account, upload, import, collection or purchase endpoints. The
website does not pretend its self-contained read model is the public REST API;
`/api/v1/fragrances` remains absent in this deployment. All seven real website
adapters and Wikidata live configuration remain disabled. `CONTACT_EMAIL`
remains unchanged. No separate Fraggy PWA files are modified.

## Verification

Run normal backend/frontend checks with demo mode unset. For the isolated mode:

```bash
FRAGGY_DEMO_MODE=synthetic API_BASE_URL=http://127.0.0.1:1/unreachable pnpm --filter @fraggy/web build
node scripts/check_vercel_demo.mjs
```

The second command starts/stops its own loopback production Next process on an
unused port with an unreachable API and checks pages, search, filters, empty/
missing records, all eight WebP files, read-only media and no-index headers.
It needs no database or Python. Browser QA uses the same owned production app
with `self_contained_demo=true` in an ignored local report; it must not use the
API-outage option because this mode has no API process to pause.

## Remaining limits

No actual Vercel build, account eligibility, URL, deployment protection or phone
access has been verified because deployment is not yet authorized. No hostname
is promised before Vercel assigns it. The demo does not provide live freshness,
accounts, collection management, purchasing or a hosted FastAPI REST service.

The Phase 2H audit's high development-only `braces` advisory
`GHSA-vfj7-8cjw-p6xm` remains disclosed; there is no dependency/lockfile change
in this PR and no claim of a clean full security clearance. Keep build/lint inputs
trusted. Production suitability and genuine catalog/image rights remain outside
this preview approval. See [Phase 2H security and readiness findings](phase-2h-readiness-report.md).

## Recorded local results

- `RUN_DB_TESTS=1 pnpm test`: **425 passed** — 359 backend, 63 frontend,
  3 ingestion; all 408 pre-existing tests retained, 17 demo regressions added.
- `pnpm lint`, `pnpm typecheck`, `pnpm format:check`, Ruff formatting,
  normal forced monorepo build and isolated demo production build: PASS.
- `node scripts/check_vercel_demo.mjs`: **21 checks passed** with an unreachable
  API, including all eight WebP files, unknown records and media POST 405.
- Production Chromium: **25 scenarios passed**, desktop/tablet/mobile, all four
  detail images loaded, no horizontal overflow and no external requests.
- Alembic upgrade/current/check: `0006_media`, no new operations or drift.
- Secret scan: zero findings. `pnpm audit --prod`: zero known vulnerabilities;
  the separate development-tooling advisory remains as documented above.

The initial full run hit the pre-existing backend
`test_benchmark_fixture_rights_filters_and_credit_deduplication` 10-second query
timeout (358 backend tests passed, one failed). The isolated diagnostic passed
with JIT off; the final standard full run passed after browser work ended.
The initial failing query plan was not captured and the cause is **not proven**.
A subsequent GitHub PR run reproduced the same timeout, while the push run passed.
The observed diagnostic plan started rights lookups at source records before
narrowing the entity link. A narrow SQL-only correction now resolves reviewed
entity links first, then verifies each link's claims and source policy in a
correlated inner existence check. All rights/value/selection predicates, fixture
policies, and the original 10-second test limit remain unchanged. No schema or
backend architecture change is introduced.
The original timeout plan was not captured; a universal performance guarantee
is not claimed. The self-contained Vercel demo does not execute that SQL path.

CI retains the complete foundation checks and adds a separate Node-only
`vercel-demo` job: frozen install, web production build and the 21-check smoke,
without Python or database setup. Actual final-head CI status and immutable
commit are recorded in the delivery PR; local results alone do not prove a
successful GitHub or Vercel deployment.
