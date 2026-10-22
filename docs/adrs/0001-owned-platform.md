# ADR 0001: Owned engine and conservative compatibility

Status: accepted implementation baseline, October 22, 2026.

Use the official Swift compiler for native and guest outputs; own the public Swift
UI/state API, native adapters, Rust interpreter, update verifier and hosted workflow.
No third-party production Wasm runtime or competitor implementation is permitted.

All guest/native boundaries carry bounded versioned values, never heap pointers.
Production updates activate at cold start, require an exact runtime fingerprint,
and retain a native fallback. Artifact and assignment signatures are separate.
Canonical CBOR, SHA-256, and Ed25519 are the initial release protocol choices.
Standard library/provider cryptography implements primitives.

Partial VM/UI support is explicitly versioned and fails closed. Early integer VM
fixtures do not demonstrate full Swift execution. Physical-device and store
qualification cannot be replaced with host tests or provider mocks.
