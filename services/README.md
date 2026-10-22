# Mixer local update and release reference

This independently authored Go slice implements signed update authorization,
a durable local recovery model and an authenticated loopback HTTP release
workflow. It does **not** qualify a mobile updater, compile a guest, authorize
an OTA release from syntax, operate a hosted service or establish a GA gate.
The protocol registry is [`../contracts/release-v1.json`](../contracts/release-v1.json).

## Run and configuration

Requires Go 1.26.0 or newer. This slice was tested with Go 1.26.4 on macOS arm64.
It has no third-party modules. From this directory:

```sh
go test -race ./...
go vet ./...
go build -o /tmp/mixer-service ./cmd/mixer-service
MIXER_SERVICE_CONFIG=/absolute/path/to/developer-config.json /tmp/mixer-service
```

`MIXER_SERVICE_CONFIG` is mandatory. Its JSON structure matches `release.Config`:

```json
{
  "developer_mode": true,
  "listen": "127.0.0.1:8080",
  "data_directory": "/absolute/private/path/mixer-local",
  "tokens": [
    {
      "sha256": "LOWERCASE_SHA256_OF_OPERATOR_CREATED_RANDOM_BEARER_TOKEN",
      "role": "publisher",
      "organization": "my-team",
      "project": "fieldlog",
      "actor": "local-developer"
    }
  ],
  "roots": [
    {
      "key_id": "release-authority-1",
      "public_key": "BASE64_ED25519_PUBLIC_KEY",
      "scope": {
        "organization": "my-team", "project": "fieldlog", "app": "fieldlog",
        "environment": "development", "platform": "ios"
      },
      "artifact": true,
      "assignment": true,
      "revoked": false,
      "not_before_unix": 0,
      "not_after_unix": 0
    }
  ],
  "hosts": [
    {
      "scope": {
        "organization": "my-team", "project": "fieldlog", "app": "fieldlog",
        "environment": "development", "platform": "ios"
      },
      "runtime": "LOWERCASE_SHA256_OF_EXACT_NATIVE_RUNTIME_CONTRACT",
      "protocol": 1,
      "guest_abi": 1,
      "ui_schema": 1,
      "capability_hashes": {},
      "state_version": 1,
      "max_payload_bytes": 16777216,
      "limits": {"memory_bytes": 67108864, "fuel": 1000000, "startup_milliseconds": 5000}
    }
  ]
}
```

The capitalized values above are explanatory placeholders, rejected by the
server. Create credentials and public roots outside this repository. The service
never receives private signing keys; operators sign with a separate trusted
client. Each token is bound to one organization/project and has role `reader`,
`editor` or `publisher`; publisher includes editor and reader permissions. Add
separate host/root scopes for Android. Root IDs are unique in a configuration.
`0.0.0.0`, hostnames and production mode are rejected. SIGINT/SIGTERM drains HTTP
requests for up to ten seconds. No customer communication, store submission,
signing operation or production publication occurs.

## Protocol and HTTP behavior

The manifest and assignment use distinct Ed25519 signature domains and SHA256
identities. All signature integers are uint64. Canonical CBOR contains the
declared field names and values in core deterministic order; JSON/base64 is only
transport. Every manifest is bound to an exact organization, project, app,
environment, platform, runtime fingerprint, guest ABI, UI schema, capability
hash map, state range and resource budgets. A server host registration is trusted
configuration, never a client-provided compatibility decision. Separate assets,
compressed packages, unknown fields and unsupported protocol versions fail
closed. The manifest's source map hash is a reference, not a source-map fetch
or execution claim.

The HTTP endpoints and request bodies are described in the contract. A complete
workflow uploads a signed immutable artifact, validates its protocol, publishes
a signed assignment, expands with a newer assignment sequence, and optionally
rolls back with another newer sequence referencing a previously published
artifact. The unsigned route channel must match the signed channel. Promoting
does not mutate an artifact or manifest environment. Rollback cannot lower the
assignment high-water. Rollout percentage is signed; it cannot be changed by
editing an HTTP request outside the signed assignment.

Admin operations require `Authorization: Bearer <operator-token>`. All mutations
require `Content-Type: application/json` and `Idempotency-Key: <identifier>`.
`X-Mixer-Reason` optionally records an operator reason of at most 512 bytes.
Idempotency is organization/project scoped and binds the exact method, path and
request bytes. A successful retry returns the original response; a changed
request with the same key returns 409. Failed requests do not reserve keys.

`GET /v1/updates` and `GET /v1/artifacts/{digest}` expose only published signed
delivery data without administrator credentials. Private upload and audit
data require project authorization. Installation identifiers are bounded
app-private random pseudonyms. They are retained across account switches;
reinstalling creates a new cohort. No installation identifiers are persisted by
this reference server. Cohorts expand deterministically without shifting the
prior eligible set.

Validation returns `protocol_valid: true`, `compiler_eligibility_verified: false`,
`policy_approved: false`, `mobile_qualified: false`. Publish returns
`delivery: "local_only"`. These fields are deliberate limits. Actual Wasm
validation, compiler/type-check evidence, asset validation, platform UI/capability
enforcement, data-migration rollback tests, policy approval and physical-device
qualification remain external gates.

Requests are bounded to 24 MiB, 128 concurrent handlers and 120 requests per
minute per directly connected source IP. Only direct connections are supported;
proxy forwarding headers are not trusted. Audit and outbox reads accept
`after` and `limit` (1..100). Public delivery is intentionally uncached in this
local reference; object storage/CDN delivery requires a separate implementation.

## Local durability and recovery

The service stores a single private JSON snapshot under an advisory process
lock. Each transaction commits artifact/channel changes, successful idempotency
results, append-only audit events and pending local outbox records together.
Writes use a private temporary file, file fsync, atomic rename and directory
fsync. A commit error poisons the process's store; callers must restart and retry
the same key, which safely distinguishes a persisted commit from an uncommitted
one. Audit events include actor, tenant, action, reason, previous/new domain
state hashes, direct source IP, correlation ID and audit hash chain. The chain
detects accidental modification; it is not an external tamper-proof audit log.
Outbox records are durable pending records only; no dispatcher/delivery success
is claimed. Local storage is capped at 64 artifacts and has no retention service.

The `updater` package uses a separate private locked store. Its installed host,
channel and installation identity cannot change on reopening. It verifies the
signed manifest and assignment, persists the assignment high-water, downloads
resumably to a private partial file, verifies complete payload size/digest,
flushes and atomically renames the payload, then persists the staged pointer.
It reserves free space for recovery (16 MiB by default). `Offset`/`Resume` require
the caller to reopen its download source at the exact saved offset; no HTTP Range
client is implemented here. `CancelDownload` preserves sequence high-water.

Only `Start` at a safe cold start returns a provisional candidate. A launch
attempt is durable before its payload path is returned. `MarkHealthy` requires
the launch ID, required milestones and the observation window. Clock movement
backwards cannot pass the window. Only a positively classified startup trap
increments the startup-failure threshold; native crashes, force-quit and unknown
process interruptions retain their uncertainty. The next cold start after an
unknown interruption uses the healthy/native implementation for that launch.
After the threshold, the candidate is quarantined and cannot be admitted again
at a higher sequence. Recovery retains two healthy generations, a staged
candidate and an always-available native fallback selection. Missing/corrupt
cached payloads cannot block fallback. Offline healthy selection does not depend
on delivery availability or newly expired signing authority.

This is a Go/macOS/Linux protocol reference. Mobile app-private storage,
extension synchronization, HTTP resumption, OS eviction classification, native
crash attribution, monotonic platform health timers, actual app-state migration
compatibility and physical-device recovery receipts remain unimplemented.
Keeping a code fallback does not prove that saved data or external effects can
be rolled back. An unknown interruption is not evidence of a guest crash.

## Provenance

The implementation was authored independently for this repository, without
Patch/Skip source, fixtures, generated output or dependencies. Standards used:
[RFC 8949 canonical CBOR](https://www.rfc-editor.org/rfc/rfc8949.html),
[RFC 8032 Ed25519](https://www.rfc-editor.org/rfc/rfc8032.html) and Go's standard
`crypto/ed25519`, `crypto/sha256`, filesystem and HTTP packages. Cryptographic
primitives are supplied by Go, not reimplemented. Test signing keys are generated
ephemerally with `crypto/rand` on every run and never written to source or disk.
See `THIRD_PARTY.yml` and `verification.md`.
