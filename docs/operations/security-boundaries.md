# Security boundaries under implementation

| Boundary | Current rule | Verification / remaining qualification |
| --- | --- | --- |
| Project generation | New destination only; reject symlink snapshots; hash vendored SDK | CLI integrity, overwrite and export tests; signed SDK distribution pending |
| Migration analysis | Read-only advisory report, never update authority | Report marks eligibility unverified; compiler closure still required |
| Guest | Owned Rust validator, bounded profile and execution | Invalid binary, fuel and memory tests; full Swift, fuzz campaign and external audit pending |
| UI messages | Versioned schema, bounded trees, explicit stable identities | SDK validation/reconciliation tests; physical IME/accessibility matrix pending |
| Update content | Deterministic CBOR + Ed25519 + SHA-256 | Protocol tests; mobile integration and key delegation pending |
| Delivery | Signed scope/cohort/sequence distinct from artifact | Replay, cross-scope and rollback tests; hosted delivery pending |
| Service | Explicit credentials, local-only mode, no release private keys | Tenant/idempotency tests; production refuses startup until isolation and durable hosted backend qualify |

Full independent security review remains pending. A source signature does not
establish VM safety, correct app behavior, store policy approval, or
recovery-compatible data.

Use the loopback drill to rehearse a build API alert and verify that signed
delivery remains available during checkout exhaustion. [Rehearse a local build API outage](rehearse-local-build-outage.md)

## Local hosted telemetry

The supported local Phoenix startup uses stock Logger and internal transaction
receipt callbacks. It has no telemetry exporter. Keep the transaction callbacks
enabled because they verify database acknowledgments for authorization and
build operations.

Treat raw Bandit, Phoenix, and Ecto telemetry as privileged process data. These
events can contain session headers, request bodies, query strings, and SQL
results. If you add an observer, emit only an explicit allowlist of coarse
operational fields. Keep raw event metadata out of log sinks and exporters.

The local SCRAM replay tested both native retention profiles. Logger and
PostgreSQL recorded their positive controls with zero private-marker hits.
The deliberate in-process observer found 74 events with markers in ordinary
mode and 78 with retention enabled. Strict telemetry mode exited 2.
Proxy and deployment egress and installed iOS privacy require separate
verification. [Replay evidence](../../verification/receipts/l07-hosted-privacy-v86-551576a0-test.json)
· [Source review](../../verification/receipts/l07-hosted-privacy-boundary-d89c742e.json)
