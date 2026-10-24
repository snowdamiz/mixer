# Explicit release v3 protocol

The v3 types and functions are an additive route for protocol3, guest ABI2 and UI1.
Legacy v1/v2 acceptance and signing domains remain unchanged. The new route checks
the frozen capability map and resource ceilings, canonical CBOR signatures, current
root scope/role/time/revocation, payload hash and assignment bindings. Go DTOs remain
mutable values; they are not opaque executable authority or a native session.

At a byte or HTTP boundary, use `DecodeSignedManifestV3`,
`DecodeSignedAssignmentV3`, or `protocol.DecodeJSON` with the explicit v3 destination.
These enforce the 65536-byte ceiling on the complete supplied document. Direct
`encoding/json.Unmarshal` passes only the JSON value to its custom unmarshaler,
discarding surrounding whitespace first; it cannot enforce that transport ceiling.
Direct DTO decoding still checks the bounded value's strict shape and commits a
decoded destination only after successful parsing. Semantic validation, signature
verification and current authority checks are separate required operations.

Shared original vectors in `testdata/signed-release-v3.json` and
`testdata/release-v3-cases.json` are mirrored byte-for-byte in the Swift tests.
`testdata/generate-v3.go` uses explicitly test-only deterministic keys. The corpus
does not authorize its synthetic payload for execution. The existing hosted routes
and persistence still use their existing protocol versions; v3 hosted admission,
durable update selection and activation require subsequent implementation.
