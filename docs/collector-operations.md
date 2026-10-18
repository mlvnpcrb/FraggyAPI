# Local collector operations

Use the existing isolated checkout, pinned Python/pnpm tools and PostgreSQL Compose
service. Do not create another worktree, enable services on app startup or point
operator commands at production/remote databases.

```bash
cd /workspace/FraggyAPI
bash scripts/setup.sh
docker compose up -d --wait
.venv/bin/alembic -c apps/api/alembic.ini upgrade head
pnpm catalog:collect -- list
pnpm catalog:collect -- quality
```

`list` exposes source/collection UUIDs, activation, scheduling, due times and leases;
`history COLLECTION_UUID` returns the latest 50 run summaries. Neither returns
private endpoints, checkpoint tokens or review evidence. Run summaries include
counts, timestamps, static errors, input quality and ingestion-run UUIDs for
existing review/provenance tools. Lists are bounded (100 sources/50 runs); query
older private history through trusted local PostgreSQL access when necessary.

## Explicit original fictional demonstration

```bash
.venv/bin/python scripts/demo_collection.py
.venv/bin/python scripts/demo_collection.py --records 100
.venv/bin/python scripts/demo_collection.py --records 1000
```

The explicit demo creates only its own UUID-named local `fraggy_demo_*` database,
uses existing original fictional metadata with invented variations, migrates it,
starts a loopback HTTP server and reviews that fictional source/grant. It explicitly
activates one local schedule, collects pages, reruns idempotently, checks zero public
records before manual review, manually publishes only two records, queries real
FastAPI ASGI routes with adjacent credits, runs the Phase 2E quality report, then
withdraws source/collection permission and proves API removal/network denial.
The larger fixtures leave 98/998 records for manual review. It disposes its engine,
stops its server and drops only its own database in `finally`. It never resets the
application database or contacts an external site. Output contains counts/statuses
and UUIDs, not record payloads or private policies. CI runs the two-record demo.

## Later separately authorized pilot

After exact source access/storage/commercial/API/attribution rights are verified
and the pilot is explicitly approved, review the source manifest and collection
grant as described in [authorization](collector-authorization.md). Configure a
supported adapter and exact endpoint, conservative page/record/timeout/retry and
minimum-request-interval budgets, required field mapping and secure credential
binding. Start with a small manually checked pilot; verify network/TLS/authentication
against the approved service without working around restrictions.

Activation and execution are separate. Activation, cancellation and revocation
require a reviewer/reason and retain a private source audit event:

```bash
pnpm catalog:collect -- activate COLLECTION_UUID --reviewer OPERATOR --reason REASON
pnpm catalog:collect -- run COLLECTION_UUID
pnpm catalog:collect -- activate COLLECTION_UUID --reviewer OPERATOR --reason REASON --schedule --interval 86400
pnpm catalog:collect -- tick
pnpm catalog:collect -- history COLLECTION_UUID
pnpm catalog:collect -- cancel RUN_UUID --reviewer OPERATOR --reason REASON
pnpm catalog:collect -- revoke COLLECTION_UUID --reviewer OPERATOR --reason REASON
```

These commands default to synthetic loopback HTTP only. A future authorized real
pilot needs the additional `--allow-external` flag on `run`/`tick`; do not supply it
for this phase or install a cron entry with it. Existing seven adapters cannot be
activated through these commands. Never commit private grant files or credentials.

For an explicitly approved local synthetic schedule, a user cron entry may invoke
`cd /workspace/FraggyAPI && pnpm catalog:collect -- tick` once per minute with the
same local environment and restrictive log permissions. `tick` exits; no paid
queue, Redis, cloud scheduler or system daemon is needed. No cron was installed.
The configured per-source frequency controls actual due runs; schedules start off.
Each tick considers at most 100 due sources and executes them sequentially. Multiple
ticks are safe: row locks, a partial unique active-run index and fencing prevent
concurrent source runs. Use UUID summaries to investigate; do not log bodies/URLs.

## Failures, recovery and limits

Transient network failures, timeouts, 429 and 500/502/503/504 use bounded exponential
backoff and honor numeric/HTTP-date Retry-After. Longer valid provider delays are
persisted; runs defer instead of holding a connection or immediately retrying.
Unsupported/non-finite/extreme delays fail closed. Access denials and redirects
are never retried. Rate reservations survive a worker crash; they may conservatively
reduce throughput, never increase it. No retry or lease recovery publishes data.

Each page commits atomically. A malformed page, exhausted retry or failed rights
check leaves that page's cursor/data unchanged. Earlier committed pages survive.
A page cap returns `partial`; a later run resumes. An expired lease marks its old
run `interrupted` and issues a new fencing token; the old worker cannot overwrite
new state. SIGINT/task cancellation is bounded by request/socket deadlines, releases
the lease when cooperative cleanup runs, and otherwise recovers after expiry.
An in-flight HTTP thread can finish until its timeout; final authorization/token
checks prevent its late page from being staged. Checkpoint loss can cause refetches;
existing content/manifest digests prevent duplicate snapshots for identical data.

Record/Pydantic validation rejects malformed metadata before staging. Input quality
reuses Phase 2E concentration/version/flanker distinctions and records bounded
pair analysis; optional missing data remains missing. Canonical quality is a
separate read-only `quality` report, never automatic publication. Investigate
incomplete reports and ambiguous candidates manually. Endpoint schemas are limited
to the documented envelopes and embedded-JSON HTML: custom auth, cursor protocols,
arbitrary HTML layouts, webhooks, robots fetching and browser rendering need
source-specific implementation/review rather than guessed extraction.
