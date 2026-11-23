# Self-host the Mixer reference update service

`mixer-service` is the MIT-licensed reference server for signed updates.
The server runs in developer mode on a literal loopback address over plain HTTP.
You supply the release configuration, signing authority, and storage. The
workflow requires no Mixer account, hosted service, or payment credentials.
See the repository's [license map](../LICENSING.md).

## Prepare the release inputs

- Install Go 1.26.0 or later to build the service. The commands below also use
  OpenSSL, jq, and curl. Use the `mixer` CLI from the same checkout. To build it
  on macOS, use Swift 6.2 or later and run
  `swift build --package-path cli --product mixer` from the repository root.
  The binary is at `cli/.build/debug/mixer`.
- Take `host.json` and `roots.json` from your trusted installed app configuration.
  `host.json` contains one installed runtime contract, including its exact scope,
  runtime fingerprint, protocol, guest ABI, UI schema, capability hashes,
  state version, payload ceiling, and resource limits. `roots.json` contains
  the matching public Ed25519 trust records. Each record includes a key ID,
  a Base64-encoded raw 32-byte public key, scope, artifact and assignment
  permissions, revocation status, and validity bounds.
- Use your own trusted signer to prepare a candidate directory with
  `signed-manifest.json` and `payload.wasm`, plus a separate signed assignment
  JSON file. Keep private signing keys with the signer. The assignment binds the
  artifact, installed scope and runtime, channel, rollout, and sequence. See
  the [v3 signing and verification contract](protocol/README-v3.md).

The stock CLI publishes through `/v3`. The procedure below uses a protocol 3,
guest ABI 2, UI schema 1 installation. For a Feature UI v3 runtime, configure
`feature_ui_v3` with the installed descriptor, roots, and storage grant. Follow
the [Feature UI enrollment procedure](release/README-v3.md#enroll-a-local-feature-ui-v3-runtime).

## Configure and start the service

Run from the repository root. Set `MIXER_RELEASE_DIR` to a new absolute path
for the service files and persistent store. Set `MIXER_HOST_JSON` and
`MIXER_ROOTS_JSON` to the absolute paths of your inputs. The example uses
port 8080. If you pick a different port, use it in every command.

```sh
umask 077
mkdir "$MIXER_RELEASE_DIR"
```

After the directory is created, generate the publisher token and write the
config.

```sh
openssl rand -hex 32 > "$MIXER_RELEASE_DIR/publisher.token"
token_sha256=$(printf '%s' "$(cat "$MIXER_RELEASE_DIR/publisher.token")" |
  openssl dgst -sha256 -r | cut -d ' ' -f 1)

jq -n --slurpfile hosts "$MIXER_HOST_JSON" --slurpfile roots "$MIXER_ROOTS_JSON" \
  --arg data "$MIXER_RELEASE_DIR/store" --arg token_sha256 "$token_sha256" '
  {
    developer_mode: true,
    listen: "127.0.0.1:8080",
    data_directory: $data,
    tokens: [{
      sha256: $token_sha256,
      role: "publisher",
      organization: $hosts[0].scope.organization,
      project: $hosts[0].scope.project,
      actor: "local-publisher"
    }],
    roots: $roots[0],
    hosts: $hosts
  }' > "$MIXER_RELEASE_DIR/service.json"

go -C services build -o "$MIXER_RELEASE_DIR/mixer-service" ./cmd/mixer-service
MIXER_SERVICE_CONFIG="$MIXER_RELEASE_DIR/service.json" "$MIXER_RELEASE_DIR/mixer-service"
```

Keep `publisher.token` private. The service config takes only its lowercase
SHA-256 digest, scoped to one organization and project. Each configured token
digest and root key ID must be unique. The `publisher` role includes `editor`
and `reader` permissions. Add a host registration and matching roots for each
additional installed scope and runtime you intend to serve.

In a second terminal, check that the server answers. Expect HTTP 200 with
`"mode": "developer"` and `"production_ready": false`.

```sh
export MIXER_RELEASE_ORIGIN=http://127.0.0.1:8080
curl -fsS --noproxy '*' "$MIXER_RELEASE_ORIGIN/healthz"
```

The default file store needs a private directory for one service process.
To use the optional local PostgreSQL backend, follow the separate role and
migration setup. [PostgreSQL configuration](release/POSTGRES.md)

## Publish and check delivery

In the second terminal, set `MIXER_RELEASE_DIR` and `MIXER_HOST_JSON` to the same
paths. Run from the directory containing `candidate/` and `publish.json`.
The example uses a signed assignment for channel `beta` at 100% rollout. Use
your signed rollout for publish and your signed channel for both commands below.

```sh
organization=$(jq -r '.scope.organization' "$MIXER_HOST_JSON")
project=$(jq -r '.scope.project' "$MIXER_HOST_JSON")
MIXER_RELEASE_TOKEN="$(cat "$MIXER_RELEASE_DIR/publisher.token")" \
  mixer update publish ./candidate --organization "$organization" --project "$project" \
    --channel beta --rollout 100 --assignment ./publish.json
```

Use the full CLI path if `mixer` is outside your `PATH`. A successful publish
returns `"delivery": "local_only"` with the artifact digest and sequence.
Promotion, halt, and rollback require new signed assignments. See the
[local update operator guide](../docs/local-update-release.md).

Point your app's development update transport at the loopback origin if the
app can reach the service host's loopback interface. A separate runtime needs
a development transport that can reach the service. The app requests
`/v3/updates` with its installed scope, runtime fingerprint, channel, and stable
random installation ID. From the service host, check that route with a test
installation ID.

```sh
curl -fsS --noproxy '*' --get "$MIXER_RELEASE_ORIGIN/v3/updates" \
  --data-urlencode "organization=$organization" \
  --data-urlencode "project=$project" \
  --data-urlencode "app=$(jq -r '.scope.app' "$MIXER_HOST_JSON")" \
  --data-urlencode "environment=$(jq -r '.scope.environment' "$MIXER_HOST_JSON")" \
  --data-urlencode "platform=$(jq -r '.scope.platform' "$MIXER_HOST_JSON")" \
  --data-urlencode "runtime=$(jq -r '.runtime' "$MIXER_HOST_JSON")" \
  --data-urlencode 'channel=beta' --data-urlencode 'installation=install-test' \
  --output "$MIXER_RELEASE_DIR/offer.json" --write-out '%{http_code}\n'
```

HTTP 200 contains a signed assignment and a relative `artifact_url` for the
same origin and protocol version. HTTP 204 means the service has no eligible
offer for that request. After HTTP 200, fetch the artifact from the same origin.
The artifact response contains `signed_manifest` and the Base64 `payload`.
Both delivery reads are unauthenticated. Use the publisher bearer only for
operator requests.

```sh
artifact_path=$(jq -er '.artifact_url' "$MIXER_RELEASE_DIR/offer.json")
curl -fsS --noproxy '*' "$MIXER_RELEASE_ORIGIN$artifact_path" \
  --output "$MIXER_RELEASE_DIR/artifact.json"
```

The app must verify the signed assignment, manifest, and exact payload against
its installed trust and compatibility policy before staging the update. The
loopback service handles delivery. The app handles activation and recovery.
See the [native update verifier](../updates/README.md).

To stop the foreground process, press Ctrl+C. SIGINT or SIGTERM lets the
process drain requests for up to ten seconds. Restart with the same
`MIXER_SERVICE_CONFIG` and data directory to retain publications.

The public update replay checks the CLI, signed HTTP delivery, restart, rollout
changes, and rollback with disposable keys, synthetic payloads, and a fresh
file store. App activation and production serving have separate qualification.
[Public update replay instructions](../tests/integration/README.md#public-update-operator-workflow)

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

Versioned routes use the same body envelope names. The protocol registries
describe [v1](../contracts/release-v1.json) and [v2](../contracts/release-v2.json).
See the [v3 service contract](release/README-v3.md) for its enrollment and
request limits. `/v1` accepts only signed schema/protocol1;
`/v2` accepts only signed schema/protocol2, including mandatory signed capability
grants. The route, typed signed values and registered host protocol must agree.
There is no version probing, retry downgrade or unsigned grants sidecar. A host
scope/runtime fingerprint has exactly one registered protocol. Channel identity
continues to include app/environment/platform/runtime/channel, so publishing a
new fingerprint retains each older runtime's assignments. Wrong-version public
updates return204 and artifact reads return404; cross-version mutation rejects.

Admin operations require `Authorization: Bearer <operator-token>`. All mutations
require `Content-Type: application/json` and `Idempotency-Key: <identifier>`.
`X-Mixer-Reason` optionally records an operator reason of at most 512 bytes.
Idempotency is organization/project scoped and binds the exact method, path and
request bytes. A successful retry returns the original response; a changed
request with the same key returns 409. Failed requests do not reserve keys.
The versioned route participates in that same tenant-wide idempotency binding;
reusing a v1 key for a v2 operation conflicts. Audit/outbox history is shared
across both route families, and its action includes the exact versioned route.

`GET /v1/updates` and `GET /v1/artifacts/{digest}` expose only published signed
delivery data without administrator credentials. Private upload and audit
data require project authorization. Installation identifiers are bounded
app-private random pseudonyms. They are retained across account switches;
reinstalling creates a new cohort. No installation identifiers are persisted by
this reference server. Cohorts expand deterministically without shifting the
prior eligible set.
The `/v2` endpoints expose only v2 signed data. A v2 offer contains a `/v2`
artifact URL; a consumer must preserve its explicitly selected version and
verify the exact pinned scope/runtime, content digest and assignment sequence.

Validation returns `protocol_valid: true`, `compiler_eligibility_verified: false`,
`policy_approved: false`, `mobile_qualified: false`. Publish returns
`delivery: "local_only"`. These fields are deliberate limits. Actual Wasm
validation, compiler/type-check evidence, asset validation, platform UI/capability
enforcement, data-migration rollback tests, policy approval and physical-device
qualification remain external gates.

Legacy v1/v2 requests are bounded to24MiB. V3 artifact envelopes are bounded to6MiB
and other v3 mutation documents to128KiB, including whitespace. All routes retain
128 concurrent handlers and120 requests per
minute per directly connected source IP. Only direct connections are supported;
proxy forwarding headers are not trusted. Audit and outbox reads accept
`after` and `limit` (1..100). Public delivery is intentionally uncached in this
local reference; object storage/CDN delivery requires a separate implementation.

## Local durability and recovery

The default local backend stores a single private JSON snapshot under an advisory
process lock. Each transaction commits artifact/channel changes, successful idempotency
results, append-only audit events and pending local outbox records together.
Writes use a private temporary file, file fsync, atomic rename and directory
fsync. A commit error poisons the process's store; callers must restart and retry
the same key, which safely distinguishes a persisted commit from an uncommitted
one. Audit events include actor, tenant, action, reason, previous/new domain
state hashes, direct source IP, correlation ID and audit hash chain. The chain
detects accidental modification; it is not an external tamper-proof audit log.
Outbox records are durable pending records only; no dispatcher/delivery success
is claimed. Local storage is capped at 64 artifacts and has no retention service.

Legacy snapshots retain schema1 and the existing v1 record/HTTP encodings.
The first successful durable v2 write upgrades the snapshot to schema2 in that
same atomic transaction. Failed authentication, malformed/incompatible content
and idempotency conflicts cannot upgrade it. V2 stored artifacts and assignments
use closed discriminated variants; missing, mixed or unknown variants fail on
decode and reopen. Existing v1 records, idempotent response bytes and prior audit
hashes are preserved. A v1-only binary refuses the upgraded snapshot; there is no
automatic downgrade or destructive conversion.

An explicitly selected local PostgreSQL backend supplies normalized durable
transactions, tenant FORCE RLS, immutable artifact/assignment history and atomic
idempotency/audit/outbox commits. Its migration owner and runtime credentials are
separate. Production startup remains disabled. See
[`release/POSTGRES.md`](release/POSTGRES.md) for configuration, schema/transaction
contracts, limits and the real isolated PostgreSQL test runner.
The existing PostgreSQL bytea records store signed v1/v2/v3 bytes without a DDL
migration. Exact schema dispatch precedes complete typed interpretation and
scope/content checks. Migration001/checksum, FORCE RLS, role guards, append-only
rows and shared tenant transaction locks remain in place. All versions count
toward the existing development capacity limit.

The Go `updater` package explicitly supports protocol1/guestABI1/UI1 and rejects
other versions before creating state. It uses a separate private locked store. Its installed host,
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

`tests/integration/release-v2-workflow.py` builds the service and a separate
public Swift consumer, exercises real loopback HTTP for both versions, checks
typed verified v2 grants/limits, replay/version rejection, restart and an actual
older binary's refusal of schema2. Its small TEST payloads are not executable;
the Swift test consumer is not a production large-payload downloader. See
[`tests/integration/README.md`](../tests/integration/README.md). This does not
add CLI v2 publication, guest imports, activation or device OTA qualification.

## Provenance

The implementation was authored independently for this repository, without
Patch/Skip source, fixtures, generated output or dependencies. Standards used:
[RFC 8949 canonical CBOR](https://www.rfc-editor.org/rfc/rfc8949.html),
[RFC 8032 Ed25519](https://www.rfc-editor.org/rfc/rfc8032.html) and Go's standard
`crypto/ed25519`, `crypto/sha256`, filesystem and HTTP packages. Cryptographic
primitives are supplied by Go, not reimplemented. Test signing keys are generated
ephemerally with `crypto/rand` on every run and never written to source or disk.
See `THIRD_PARTY.yml` and `verification.md`.
