# Explicit v3 development release service

This slice composes the reviewed Go release3 primitives with the existing local
development HTTP and storage services. Production mode remains disabled. It does
not validate Wasm, approve policy, execute a guest, sign on behalf of a caller or
deploy a service. The native client independently verifies all signed bytes and
installed execution material.

Add explicit `/v3` counterparts of the existing artifact upload/read, release
validation, channel publish/promote/rollback, public update and artifact routes.
Only an explicitly registered protocol3/ABI2/UI1 host accepts v3. Use
`ValidateHostV3` and the v3 root-count ceiling for configurations containing v3.
The existing scoped credentials, roles, bounded concurrency, idempotency, audit,
current signing authority and runtime-scoped sequence checks remain mandatory.
No fallback from one protocol verifier to another is permitted.

Use distinct `ArtifactV3`, `Record.Version3` and `Channel.Version3` variants. Mixed
or absent variants reject. Stored v1/v2 wire bytes remain unchanged. V3 records
carry exact discriminator3 and `artifact_v3`/`signed_assignment_v3` fields. The
in-memory store schema advances monotonically to3 only on a successful v3 commit;
later v1/v2 writes never downgrade it. Reopen allows an older variant in a newer
container, rejects a newer variant in an older container, and preserves audit
hashes and idempotent responses. The prior service binary must reject schema3.
The PostgreSQL migration stays byte-identical: existing opaque signed-byte columns
already hold the closed v3 values, while application decoding dispatches explicitly
on schema3. No live cluster migration or production mutation is involved.

V3 HTTP reads are bounded before decoding: artifact envelopes allow at most6MiB
(canonical base64 for4MiB payload plus64KiB manifest and envelope); other v3 mutation
bodies allow at most128KiB. Each signed nested value is still limited to64KiB by
its checked decoder and payload bytes to4MiB by verification. The envelope is a
closed object; missing/null/duplicate/unknown fields reject. Limits apply to the
whole HTTP document including whitespace. Legacy24MiB HTTP body behavior stays
unchanged. Public delivery is version-filtered; it never exposes an unpublished
record or overwrites another runtime's channel.

Qualification requires original v3 HTTP tests for coexistence, scope/roles,
signature and host mismatch, malformed and oversized documents, concurrent
idempotency and increasing sequences, greater-sequence rollback, corruption,
schema upgrade/reopen, injected uncertain writes and exact v1/v2 response/audit
preservation. Run the full Go race suite and vet. Add PostgreSQL v3 integration
tests against an isolated disposable local cluster with forced RLS and retry/fault
checks, preserving the existing migration checksum. Independent review must cover
the final source. Serving v3 metadata is not durable client activation or public
production delivery qualification.
