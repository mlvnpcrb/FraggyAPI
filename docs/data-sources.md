# Candidate data sources

Phase 1 contains configuration and synthetic fixtures only. No website has been
accessed or assessed for permission as part of this implementation. Candidate
status is not a finding that access is forbidden or allowed. No source is approved;
none has a verified restricted determination. All seven remain pending and disabled.

| Source              | Website                        | Authorization  | Commercial license | Live ingestion |
| ------------------- | ------------------------------ | -------------- | ------------------ | -------------- |
| Fragrantica         | https://www.fragrantica.com/   | pending_review | pending_review     | disabled       |
| Parfumo             | https://www.parfumo.com/       | pending_review | pending_review     | disabled       |
| Basenotes           | https://basenotes.com/         | pending_review | pending_review     | disabled       |
| Wikiparfum          | https://www.wikiparfum.com/    | pending_review | pending_review     | disabled       |
| The Perfume Society | https://perfumesociety.org/    | pending_review | pending_review     | disabled       |
| PerfumeMaster       | https://www.perfumemaster.com/ | pending_review | pending_review     | disabled       |
| ScentBase           | https://www.scentbase.com/     | pending_review | pending_review     | disabled       |

The machine-readable registry is `config/sources.json`. Empty permitted-field and
collection-method lists mean **nothing permitted**, never unrestricted access.
Zero rate limits mean no requests. Null synchronization times mean never synced.
The empty error histories mean no attempts have occurred, not demonstrated health.
All fixture data is invented and uses reserved example.invalid URLs.

## Required review before any future activation

A reviewer must record dated evidence for current terms, relevant robots directives,
official API or licensing options, automated access, storage, and commercial
redistribution. Robots permission alone does not establish a redistribution license.
Each evidence entry should include an evidence URL or private agreement reference,
retrieval date, reviewer, scope, decision, expiry or next review date, and relevant
terms/version. Do not store confidential agreement contents in public configuration.

Record allowed methods, licensed fields, attribution obligations, retention limits,
territories and downstream reuse restrictions explicitly. Reviews, descriptive prose,
and image content must remain excluded unless rights specifically cover their use.
Image references themselves also require review. Source facts and ratings are not
assumed reusable merely because they are publicly visible.

Future approval must check every boolean in `compliance_review`, require current
evidence, and enforce permissions at collection, storage, and public export. Conflicts
or expired evidence must stop collection/publication and enter review. Never bypass
CAPTCHA, authentication, access controls, or rate restrictions. Prefer licensed APIs,
authorized exports, or agreements when available.

Phase 1 intentionally rejects activation even if a registry entry is edited. A later
phase must implement and test the compliance gate before live adapters are added.
Runtime synchronization/error history should eventually live in durable storage,
with bounded sanitized errors and timestamps; the registry provides initial state.
