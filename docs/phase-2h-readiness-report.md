# Phase 2H — application readiness report

Assessed **2026-10-19, Asia/Manila**. Primary target: original-only local preview
and evidence-based preparation, not a live data pilot or production deployment.

## A. Project status

| Item                | Evidence / status                                                                                                                                    |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Branch              | `feat/phase-2h-pilot-readiness`                                                                                                                      |
| Latest commit       | Final branch HEAD; immutable delivery SHA is recorded in the PR and final delivery report. `git rev-parse HEAD` reproduces the checked-out SHA       |
| Phase 2G merge      | `f7d391dbfafcce47064591e8f6bee826f804847a`                                                                                                           |
| Phase 2H PR         | Pending creation after local validation; must remain open/unmerged                                                                                   |
| Tests               | **408 passed**: 359 backend, 46 frontend, 3 ingestion; all 380 baseline tests preserved                                                              |
| GitHub CI           | Pending final pushed-head verification; local checks do not imply remote success                                                                     |
| Migrations          | `0006_media (head)`; upgrade/current/drift check successful; no Phase 2H schema change                                                               |
| Application startup | PostgreSQL + FastAPI + Next development server actually started; verified synthetic preview and browser QA. Final instance restarted before delivery |

## B. Exact local preview

**The application works locally with synthetic records and original fixture images.**
These URLs refer to the machine running FraggyAPI. In this cloud task, loopback
is **inside the development environment**, not the user's computer or public Internet.

| URL                                        | Actually tested                                                         | External accessibility |
| ------------------------------------------ | ----------------------------------------------------------------------- | ---------------------- |
| Frontend `http://127.0.0.1:3000/`          | HTTP 200 and Chromium desktop/tablet/mobile                             | Loopback only          |
| Catalog `http://127.0.0.1:3000/fragrances` | HTTP 200, search/filter/pagination/detail navigation                    | Loopback only          |
| API docs `http://127.0.0.1:8000/docs`      | HTTP 200, development OpenAPI UI                                        | Loopback only          |
| Health `http://127.0.0.1:8000/health`      | HTTP 200; remains 200 during database outage                            | Loopback only          |
| Readiness `http://127.0.0.1:8000/ready`    | HTTP 200 with PostgreSQL; 503 during outage; returns 200 after recovery | Loopback only          |

No forwarded preview URL was available through this environment's tools. No
public tunnel or deployment was provisioned. **You cannot open this cloud
machine's loopback URL from your laptop without platform forwarding.** To use
FraggyAPI on your own computer, check out this branch, install its documented
Node/Python/Docker prerequisites and run:

```bash
bash scripts/setup.sh
docker compose up -d --wait
pnpm preview:local
```

Then open `http://127.0.0.1:3000/` **on that computer**. The explicit preview
command authorizes only original fixtures, creates its own UUID-named database,
migrates it and starts owned loopback servers. It never resets the application
DB or collects external records. The supervisor is validated on Linux and uses Unix process signals (macOS/WSL2-compatible workflow; native Windows process supervision is not verified). Ports 3000/8000 must be free; alternate local
ports are available via `--web-port` and `--api-port`. Stop with Ctrl-C in the
original terminal; in managed cloud terminals use the recorded owned supervisor
PID and SIGTERM if terminal interruption detaches the process. Verify the ignored
`data/reports/local-preview.json` says `running=false` and owned DB cleanup finishes.
Its `running=true` record is current-process state, not proof of future availability.

## C. Catalog inventory and genuine/synthetic distinction

SQL inventory and actual API projection were checked. Preview fixtures are kept
in a separate owned `fraggy_preview_<uuid>` database and removed on clean shutdown.
The application database retains earlier original demonstration rows unchanged.

| Count                                     | Owned preview                              | Existing application DB                                           |
| ----------------------------------------- | ------------------------------------------ | ----------------------------------------------------------------- |
| Brands                                    | 10                                         | 2                                                                 |
| Fragrances                                | 100                                        | 4                                                                 |
| Releases                                  | 210                                        | 6                                                                 |
| Bottle variants (internal canonical rows) | 420                                        | 4                                                                 |
| Source-record snapshots                   | 100                                        | 3                                                                 |
| Published source snapshots                | 100 synthetic                              | 1 synthetic                                                       |
| Visible public fragrance records          | 100 with explicit preview synthetic opt-in | 0 with default synthetic visibility off; 4 if explicitly opted in |
| Genuine fragrance records                 | **0**                                      | **0**                                                             |
| Synthetic fragrance records               | 100                                        | 4                                                                 |
| Synthetic source snapshots                | 100                                        | 3                                                                 |
| Approved genuine bottle images            | **0**                                      | **0**                                                             |
| Approved original synthetic images        | 4                                          | 0                                                                 |
| Sources approved for real collection      | **0**                                      | **0**                                                             |

“Published source snapshots” and public fragrance API records are different units;
one source snapshot may support several canonical products. A canonical variant
count does not mean private variant metadata is publicly licensed. Every stored
fragrance is accounted for by synthetic provenance; website sources have zero
records. All seven website policies in both DBs are
`pending_review/pending_review/enabled=false`. No genuine candidate ID was invented,
queried or collected. The current disabled proposal has zero genuine candidates.

## D. Readiness scorecard

PASS applies only to the evidence/scoped behavior stated here. BLOCKED means a
necessary external approval, evidence or launch prerequisite is missing. No
untested capability is labeled PASS.

| Component                       | Status  | Evidence                                                                                                                            | Remaining work                                                                                                            |
| ------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Frontend website                | PASS    | Actual HTTP/browser checks, navigation/search/empty/error states; confirmed hero-credit overlap fixed                               | External forwarding if user wants access to this cloud instance                                                           |
| Mobile responsiveness           | PASS    | Chromium at 390 px, tablet 768 px and desktop 1440 px; no horizontal overflow, credit/art separation, all four detail images loaded | Broader device/assistive-technology testing before launch                                                                 |
| Backend API                     | PASS    | Actual endpoints plus typed/rights/input regression suites and outage recovery                                                      | Production operation/load/security design                                                                                 |
| PostgreSQL database             | PASS    | Healthy Compose, real queries, owned disposable fixtures and recovery                                                               | Production backup/restore/hosting choices                                                                                 |
| Database migrations             | PASS    | Head 0006, no drift, disposable upgrade/downgrade tests                                                                             | Deployment-specific migration rehearsal                                                                                   |
| Fragrance search                | PASS    | Actual browser/API query, filtering, pagination and benchmark                                                                       | Representative authorized corpus validation                                                                               |
| Fragrance detail pages          | PASS    | Exact UUID detail, unknown-ID behavior, concentration/reformulation/variant distinctions                                            | Real content quality review                                                                                               |
| Bottle image pipeline           | PASS    | Original fixtures, validation/WebP/thumbnail/hash/approval/gallery/variant/revocation/GC tests                                      | Source-specific real assets and production storage plan                                                                   |
| Image rights and attribution    | PASS    | Independent reviewed rights, source/publication gates, credits, rejected/unapproved/revoked assets hidden                           | Genuine image agreements remain absent                                                                                    |
| Data collector engine           | PASS    | Existing local scheduled synthetic collection, checkpoints/rate/retry/cancellation/idempotency/manual publication/revocation tests  | Individually authorized real source configuration                                                                         |
| Wikidata integration            | BLOCKED | Offline adapter/proposal tests pass; CC0/API policy pages reviewed                                                                  | Monitored contact, approved genuine IDs/discovery, endpoint robot/access review, explicit pilot approval                  |
| Genuine perfume data            | BLOCKED | 0 imported/published, 0 reviewed genuine candidates                                                                                 | Separately approve discovery, validate candidates and then approve collection/review/publication                          |
| Real bottle images              | BLOCKED | 0 approved genuine assets, none downloaded                                                                                          | Independently verified asset rights and explicit image-pilot approval                                                     |
| Security controls               | BLOCKED | Core rights/input/network/file/secret controls verified; 0 Python/prod-JS known vulnerabilities                                     | One unpatched high development-tooling advisory prevents a clean full dependency clearance; no penetration test performed |
| Performance                     | PASS    | Reproducible synthetic search/filter/page/detail/image timings and bounded reads, 0/30 failures                                     | Representative real-data, concurrent and deployment/load tests                                                            |
| CI and automated testing        | BLOCKED | Local baseline and Phase 2H regression checks; remote final-head execution pending                                                  | Verify actual pushed-head workflow success                                                                                |
| Production deployment readiness | BLOCKED | Local-only validated scope; no production service provisioned                                                                       | Authorized corpus/images, security acceptance, production hardening/monitoring/backups/load/hosting review                |

## E. Separate overall assessments

1. **Local development preview: READY**, within this machine and the explicit
   synthetic/loopback scope. A forwarded cloud URL is not available; this does not
   stop using the same workflow locally on the user's own computer.
2. **Authorized real-data pilot: BLOCKED**. Contact, genuine candidate discovery/
   qualification, exact endpoint access and explicit authorization are incomplete.
3. **Public beta: BLOCKED**. No genuine catalog or real image rights, unresolved
   tooling advisory, no external preview/hosting or beta operating/security plan.
4. **Production launch: BLOCKED**. No production deployment/load/backup/monitoring
   validation and none of the real-data/image launch prerequisites are cleared.

No subjective percentage is presented as a measured readiness score.

## F. Critical blockers and follow-up

Effort estimates are engineering estimates, not external provider response SLAs.

| Severity                   | Blocker / impact                                                                                                                            | Recommended fix                                                                                                                                     | Estimated effort                                                                                | User approval required                                                                             |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Critical for pilot         | Live discovery/collection not authorized; no genuine candidate list                                                                         | Review exact two-stage discovery/collection scope and budget in pilot preparation, then explicitly authorize the relevant activity                  | 1–2 engineering days after approval/access, plus source quality review; external timing unknown | **Yes**, separate activity/scope approval                                                          |
| High for pilot             | No real monitored contact; `CONTACT_EMAIL` deliberately remains a placeholder                                                               | Supply and approve the monitored address in the required User-Agent; never infer one                                                                | Under 1 hour after supplied contact/approval                                                    | **Yes**                                                                                            |
| High for pilot             | WDQS-specific robot/access evidence blocked by environment proxy                                                                            | Review environment access policy through normal controls, then recheck policy/endpoint without bypass; no fragrance query until separately approved | 1–3 hours after access is available; policy/provider timing unknown                             | **Yes** for required environment policy changes or live query scope                                |
| High for real images       | No genuine asset-specific storage/transform/commercial/API/PWA rights                                                                       | Obtain verified brand/feed/API/open-asset evidence and exact asset/hash approval independently of metadata                                          | 1–2 engineering days after suitable agreement/assets; provider timing unknown                   | **Yes**, asset/pilot approval                                                                      |
| High, development tooling  | `braces <=3.0.3`, GHSA-vfj7-8cjw-p6xm, stack-exhaustion DoS via deeply nested patterns; dev ESLint chain, absent from production-only audit | Keep build/lint inputs trusted, monitor upstream; review tested patched dependency/lock update or explicit mitigation when available                | 0.5–1 day once a supported fix exists; no published patch today                                 | Approval needed to accept unresolved risk for broader/untrusted use; no exception silently granted |
| Medium for cloud usability | No forwarded URL; user cannot reach this cloud instance from their browser                                                                  | Use local checkout/start commands, or separately configure supported platform port forwarding                                                       | Under 1 hour if platform forwarding is available; otherwise external blocker                    | Platform/user action required for external access                                                  |
| High for beta/production   | No hosting, backup/restore rehearsal, concurrency/load target, monitoring or incident/security acceptance                                   | Separate launch plan after authorized pilot review, with free-first options and explicit deployment scope                                           | Several engineering days; estimate refined once scope/targets are approved                      | **Yes** for deployment/services/new phase                                                          |

## G. Final recommendation

**READY FOR LOCAL PREVIEW.** The application actually runs with 100 clearly
synthetic fragrances, source credits and four original approved image fixtures.
Desktop/tablet/mobile use, error recovery and the rights-aware backend/media path
are exercised. Genuine fragrance count and approved genuine image count are both
**zero**. Do not treat this status as pilot, public-beta or production approval.

The next phase should resolve monitored contact, source access/policy evidence
and the narrowly bounded discovery authorization, followed by candidate review
and a separately approved real-data collection pilot. Real image acquisition is
a separate permission decision. Review and merge Phase 2H only after its actual
CI passes and human approval is given; this task leaves it unmerged.
