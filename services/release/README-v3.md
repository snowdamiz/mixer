# Explicit v3 development service

The additive `/v3` routes use reviewed release schema3/protocol3/guestABI2/UI1.
They retain the existing scoped bearer roles, current signed authority checks,
idempotency, audit/outbox transaction and runtime-scoped channel identity. The
service remains loopback-only development software. It does not validate Wasm,
select installed capability policy, execute a guest, approve activation, sign for
a caller, dispatch the outbox or publish a production release.

Every existing artifact upload/private read, release validation, channel
publish/promote/rollback, public update and public artifact route has an explicit
`/v3` counterpart. Audit/outbox history remains shared. A v3 host must be explicitly
registered and pass `protocol.ValidateHostV3`; a configuration containing v3 also
has at most128 trust roots. Legacy-only configuration keeps its existing rules.
A scope/runtime has one registered protocol. There is no verifier probing or
fallback. Wrong-version public updates return204 and artifact reads return404;
wrong-version mutation rejects.

V3 artifact envelopes contain exactly `signed_manifest` and `payload`. Assignment
mutation envelopes contain exactly `signed_assignment`; release validation has
exactly `artifact_sha256`. Missing/null/duplicate/unknown/alternate-case fields
reject. Canonical base64, nested closed protocol shape and strict JSON remain
mandatory. The whole artifact HTTP document is at most6MiB, including whitespace;
other v3 mutation documents are at most128KiB. The checked signed-value decoders
separately enforce64KiB and payload verification enforces4MiB. These are logical
input bounds, not allocator/RSS or constant-time guarantees. Existing v1/v2 body
handling remains24MiB;128 concurrent handlers and the existing direct-IP rate
limit cover all route families.

Local snapshots use explicit `protocol:3` with `artifact_v3` and
`signed_assignment_v3` storage variants. Mixed, absent or mismatched variants
reject atomically. The first committed v3 write upgrades the container to schema3;
older writes cannot downgrade it. A newer container can retain older v1/v2
variants, while newer variants reject in older containers. Existing v1/v2 wire
encodings, cached response bytes and earlier audit hashes remain unchanged.
The earlier service binary rejects schema3; there is no automatic conversion or
downgrade. An uncertain local write poisons the store until reopen and same-key
retry, preserving the existing durable transaction contract.

PostgreSQL keeps migration001 byte-for-byte unchanged. Its opaque signed BYTEA
values dispatch explicitly on signed schema3 before complete checked v3 decoding;
FORCE RLS, immutable rows, tenant transaction locks, capacity and role guards are
unchanged. The v3 tests use separate disposable Unix-socket PostgreSQL17 clusters
with TCP disabled, including real immediate restart at the pre/post commit points.
No installed cluster, production credential or trust setting is changed.

From the repository root, development checks are:

```sh
go -C services test -race ./...
go -C services vet ./...
python3 services/verification/postgres.py --output /absolute/fresh/pg-evidence
python3 -B verification/release-v3-service/old-binary.py \
  --output /absolute/fresh/old-new-evidence
```

The new tests exercise original v3 coexistence, private/public scope and roles,
current revoked roots, host/ABI/signature mismatch, malformed and oversized HTTP,
exact payload/whole-document limits, concurrent idempotency/sequence, newer-sequence
rollback, local upgrade/reopen/corruption/faults, PostgreSQL RLS and actual restart.
The old/new binary probe uses only `New`/`Close` for the updated consumer and never
starts HTTP. Exact final source and command receipts require independent review;
working-tree development logs are not a source freeze or a hosted/device/GA gate.
