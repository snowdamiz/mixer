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

No independent security review has occurred. A source signature does not establish
VM safety, correct app behavior, store policy approval, or recovery-compatible data.
