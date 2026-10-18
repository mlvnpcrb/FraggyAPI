# Collector authorization

A downloaded manifest, license URL, robots permission, registry flag or schedule
cannot authorize collection. The trusted operator must independently review access,
storage, commercial reuse, API redistribution, attribution, rate limits and access
restrictions. The current source terms and actual supplier authority require human
evidence review; this software does not establish legal rights.

## Independent approvals

1. Use the existing `catalog:manage source-review` workflow to review a local
   manifest's storage permission and permitted publication fields/attribution.
   This does not activate collection or publish any record.
2. Prepare a private strict `Grant` JSON matching `collection/policy.py`:
   `manifest`, `endpoint`, true `automated_access`, `database_storage`,
   `commercial_reuse`, `api_redistribution`, `attribution_accepted`, nonempty
   `access_restrictions`, timezone-aware `reviewed_at` and `expires_at`, and an
   `evidence` object with those seven corresponding evidence categories
   (`attribution`, `rate_limits` and `access_restrictions` use those exact keys).
   Bind the exact manifest, adapter, field map, endpoint, rate and retry budgets.
   Do not approve restrictions the configured transport cannot enforce.
   Evidence references/reviewer reasons must remain private and bounded.
3. Run `pnpm catalog:collect -- review data/private/collector-grant.json
--reviewer OPERATOR --reason REASON`. This records a trusted digest review and
   returns a collection UUID with both activation flags false. Editing JSON or
   directly changing the digest invalidates authorization. Re-review resets
   activation and incremental state; stop active workers first.
4. Activation is a distinct operator action. A future real-source pilot also needs
   separately authorized external-network execution. Neither this phase nor the
   example demonstration supplies that authorization.
5. Staging never approves canonical identity. Manually decide each pending record
   using existing review commands; separately publish explicitly allowed fields.

Before DNS/socket work, including every retry, the worker checks the current grant
is approved, enabled, within review/expiry dates, digest-consistent, bound to the
same source, and consistent with the latest trusted storage/attribution policy.
Missing, future, expired, restricted, revoked or inconsistent approval fails closed.
Authorization-denied run attempts have static durable error summaries. The worker
checks again before committing a page. An already issued request can finish during
revocation, but its page cannot be stored after the final gate fails.

## Network and credential restrictions

External network is off by default even for a reviewed source. Synthetic policies
permit only literal `http://127.0.0.1:PORT/PATH` with no credentials. Public targets are denied. Never
use a loopback relay or synthetic flags to disguise real collection. Real policies require
HTTPS, exact endpoint URLs without credentials, query strings or fragments, and
an individually reviewed adapter/configuration. Local/private/link-local/multicast
DNS answers are denied, including mixed public/private answers. The actual TLS
socket uses a validated address while verifying the original hostname. Redirects
and compressed responses are refused. Response bytes, parsed records, nesting,
request duration, retries, pages and run records are bounded.

An optional `credential_env` names a `FRAGGY_COLLECTOR_*` environment variable used
only as a Bearer header for that source's exact endpoint. No credential value goes
into a manifest, policy, checkpoint, log or commit. Missing/malformed bindings fail
before DNS. No credential/proxy placeholders were configured or tested against a
real service. Future deployment must verify its supported credential/network route;
never bypass the environment's network controls to obtain access.

## Withdrawal

`catalog:collect revoke COLLECTION_UUID --reviewer OPERATOR --reason REASON` stops collection and schedules and marks
an active run for cancellation. Existing `catalog:manage revoke` withdraws source
redistribution and removes its grants/credits from subsequent API reads; storage
withdrawal uses existing source review to remove unauthorized snapshots. These
are separate decisions. A publication-only withdrawal also blocks further
collection because the required collection grant includes intended API reuse.
Already delivered client copies require refresh; the collector cannot retract
remote copies or cancel bytes already on the wire.

All seven website sources remain disabled and pending review. A future authorized
pilot must verify the Phase 2E source register's unresolved access, storage,
redistribution, attribution and rate questions. Do not activate a reserved website
skeleton by editing flags, or use CAPTCHA bypass, evasive proxies or login
circumvention. No real dataset or source was approved in Phase 2F.
