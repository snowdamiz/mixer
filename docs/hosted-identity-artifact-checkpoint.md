# Hosted identity and artifact component checkpoint

The bounded configured-key owner and signed v3 artifact admission now have
[root component acceptance](../verification/hosted-component-integration-root-review/acceptance.json).
The exact artifact overlay is applied; all 56 source/fixture inputs match the
composed host run. The API still exposes health only. Application wiring,
authenticated routes and authoritative database membership remain next.

The key owner maintains explicit reviewed profiles, current trust snapshots,
bounded HTTPS/DNS refresh and a final generation/freshness check after token
verification. Standard OTP TLS and JOSE retain the existing pure RS256 profile.
Root acceptance includes the fixes for TLS-controller cleanup and bounded
process-lifetime identity/version history. See the frozen
[implementation](hosted-key-owner-implementation.md) and
[independent review](hosted-key-owner-independent-review.md).

An absent key may consume a bounded negative entry and eligible refresh within
an already configured profile, even when token claims are foreign or malformed.
It still returns unauthenticated. This explicit
[contract clarification](../verification/hosted-key-owner-root-review/unknown-kid-scope-clarification.json)
does not let a token create profiles, endpoints or authority. History remains
process-local; graceful shutdown can wait for owned TLS cleanup, and large
close-delimited responses can exhaust the fixed deadline. Provider/fleet and
durable database authority remain unqualified.

Artifact admission checks exact bounded JSON, duplicate/closed schemas,
canonical base64, current explicit host/root policy, standard Ed25519 signatures,
payload digest and signed target. Retained checked values are reparsed under
current policy before reuse. This grants no tenant, publication or execution
permission. See the frozen [implementation](hosted-artifact-admission-implementation.md)
and [independent review](hosted-artifact-admission-review.md).

Evidence includes 45 macOS/46 Linux producer identity tests, 12 additional
independent cases on both platforms, 316 independent artifact cases, 257 new
same-input Go comparisons, 208 original comparisons and 15 retained-data checks.
The combined suite passes 73 tests, production release compilation and expected
missing-configuration rejection. One Linux namespace test is explicitly skipped
on macOS; actual isolated Linux DNS/rebinding execution is retained separately.
Both shared protocol fixture files are bound into the host receipt and hosted CI
triggers. No new combined hosted-CI result is claimed before its pushed run.

The first root postprocessor rejected the newer ExUnit summary format after all
product commands and cleanup passed. Its original failure remains intact; the
[completion receipt](../verification/hosted-component-integration-root-review/completion.json)
verifies those unchanged outputs. No second runtime execution is inferred.

Current membership, private artifact/audit/idempotency transactions, credential
registration, HTTP admission, provider deployment, Oban release jobs, native
execution, physical devices and all GA gates remain pending. The selected
[transaction seam](hosted-transaction-context-preflight.md) and atomic-writer
preflight are the next storage prerequisites. Physical phones remain deferred.
