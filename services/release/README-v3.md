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

## Inspect channel history

The `/v3/.../audit` route serves the stored audit chain. A v3 publish, promote,
halt or rollback records `channel_change` with the app scope, runtime and
channel. Its `previous` and `current` heads contain the signed sequence,
artifact digest and rollout basis points observed by the committing transaction.
The first assignment omits the previous head. The canonical event hash covers
the change. An idempotent retry returns the original response and adds no event.

The v1 and v2 audit routes use the original event schema, including
`rollout_halt` where recorded. All versions keep the same event IDs, state
commitments, cursor positions and event order. The v1 and v2 hash chains share
the canonical prefix through the last event before the first `channel_change`.
From that change onward they hash the legacy event bytes and link to the
preceding legacy hash. Verify a chain using one audit version throughout.
The legacy view derives its cursor hash from the stored prefix. PostgreSQL
does this within the configured query deadline. Stored events and canonical
v3 hashes are preserved, including on reopen and restore.

## Halt an unhealthy rollout

Use a scoped publisher token to POST
`/v3/orgs/{org}/projects/{project}/channels/{channel}/halt`. Send the existing
`Idempotency-Key` and a JSON body with exactly two fields.

- `signed_assignment` binds the current artifact and channel at a higher sequence
  with `rollout_basis_points` set to zero. Sign it with a currently authorized
  assignment key.
- `health` includes `sequence` for the observed rollout, unsigned counts for
  `activated` and `pending` installations in the sample, and a positive
  `adverse_signals` count. An adverse signal can come from an installation that
  already activated. The publisher supplies these observations.

The service compares the observed sequence with the current channel head before
committing the halt. A newer publication or promotion makes the request stale.
Successful responses and the tenant's `/v3/.../audit` events include the same
halt scope, sequences, artifact, and observed counts. The audit record captures
the sample at halt time.

Subsequent update checks for that channel and runtime return HTTP 204. Installed
clients keep their local state. An installation holding an earlier signed offer
can still exercise its cached authority under the existing verifier rules. To
resume offers, publish or promote with a higher signed sequence.

## Rotate preinstalled keys

Pin the replacement public roots in the installed identity before rotation. Give
the artifact and assignment keys their respective roles and align the service's
configured validity windows with the installed roots. During the overlap either
authorized generation can sign. After expiry, the old generation loses fresh
authority. An offline installation can still reopen its committed healthy
release and accept a higher assignment signed by the preinstalled replacement
generation when it reconnects. A root absent from the installed identity
requires an updated binary. Suspected compromise of an installed root may also
require an updated binary.

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

## Enroll a local Feature UI v3 runtime

Add a `feature_ui_v3` object to the operator-owned file named by
`MIXER_SERVICE_CONFIG`. Use the local file backend, a loopback listener,
and a config file with group and world write access disabled.

- `scope` is the installed application's organization, project, app,
  environment, and platform.
- `fingerprint` is the installed runtime's lowercase SHA-256 fingerprint.
  Obtain it from the trusted installed runtime.
- `descriptor_json` and `trust_roots_json` are standard padded Base64 of
  the exact installed descriptor and root JSON bytes.
- `storage_policy` contains the installed storage grant's `namespace` and
  `"operations": ["get"]`.

The origin derives the runtime fingerprint from the descriptor's canonical
CBOR and checks the exact root-file bytes against the descriptor's digest.
It checks the namespace against the descriptor's grant digest and requires
the signed manifest to carry that same namespace. Enrollment accepts only
the declared operation `get`. The installed Swift storage adapter enforces
the operation and per-key access when the guest calls storage.

For a service dedicated to this enrollment, set the top-level `hosts` and
`roots` arrays to `[]`.

Remove `feature_ui_v3` and restart with a valid service configuration to
disable release operations and delivery for that runtime. Stored UI3
assignments yield HTTP 204 on update checks, and stored UI3 artifacts yield
HTTP 404 on artifact reads.

Run the enrollment and release tests.

```sh
go -C services test ./protocol ./release -run 'TestFeatureUI(Enrollment|RequiresExplicitVerifier|Service|Release)'
```

To replay the retained F10 deliveries through the ordinary CLI, set
`MIXER_F10_REPLAY_INPUTS` to the retained `public/android` directory named
in the verification receipt. The directory contains `identity.json`,
`roots.json`, `host.json`, and the `prior`, `exact`, and `rollback` candidates.
Set `MIXER_F10_REPLAY_CLI` and `MIXER_F10_REPLAY_ORIGIN` to the absolute
paths of the built `mixer` and `mixer-service` executables. Then run the replay.

```sh
go -C services test -count=1 -v ./release -run '^TestFeatureUICLIOriginReplay$'
```

The replay verifies the original signed envelopes at their historical
signing time. It uses temporary in-memory signing keys for live delivery and
checks the served predecessor, 14,503-byte successor, and rollback bytes.
