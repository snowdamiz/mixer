# Customer artifact audit codec

`MixerHosted.Audit.CustomerArtifactEvent` is the ordinary pure schema-2 codec for
the fixed seventeen-position canonical array in the
[transaction contract](hosted-customer-artifact-transaction-contract.md).
`Audit.UploadEvent` schema 1 remains unchanged. This codec grants no authority:
snapshots, identities, projections and Record structs remain forgeable data.
Storage must derive the artifact projection from the exact independently admitted
bytes, own its authorization transaction and recheck all retained bytes/columns.
There is no signing key, clock, Repo, provider, HTTP or native dependency here.

## Public contract

- `build(identity, locked_snapshot, fresh_snapshot, artifact, command)` returns
  `{:ok, %CustomerArtifactEvent.Record{event_cbor: binary, event_sha256: hex,
  display: map}}` or `{:error, :invalid_audit_event}`.
- `decode(display)` returns the same record after validating the closed semantic
  projection and reconstructing exact canonical bytes and all retained digests.
- `validate_row(record)` accepts that exact three-field struct or a closed
  atom-key map with `event_cbor`, `event_sha256`, `display`; success is `:ok`.
- `validate_edge(current, previous_or_nil)` validates both retained rows and the
  same-tenant consecutive predecessor/event/state linkage. Sequence one requires
  `nil`, the empty predecessor hash and the exact tenant genesis.
- `genesis(organization, project)` and
  `request_hash(target_array, envelope_sha256, reason)` return `{:ok, hex}`.
  Every rejected public input returns only `{:error, :invalid_audit_event}`.

Artifact is the closed nine-field atom-key map `organization_id`, `project_id`,
`application_id`, `environment_id`, `platform`, `runtime_sha256`,
`manifest_sha256`, `payload_sha256`, `envelope_sha256`. It is only a bounded
domain projection. Platform is `ios` or `android`; every digest is lowercase
64-character hex. Its full scope must equal both snapshots' exact target.

Command is the closed six-field atom-key map `sequence`,
`previous_state_sha256`, `previous_event_sha256`, `outcome`, `reason`, `source_ip`.
Outcome is `created` or `unchanged`; reason is valid UTF-8, at most 512 bytes,
including empty text; IP is absent (`nil`) or exact `:inet.ntoa/1` canonical text.
No command field supplies the request ID, actor or clock. The 32-lowercase-hex
request ID comes from equal server-generated snapshot IDs. The timestamp is
exactly `fresh_snapshot.checked_at` and locked time is exactly
`locked_snapshot.checked_at`. Their elapsed time is zero through five seconds.

Both closed snapshots are checked using ordinary `Snapshot.valid?/3` against the
verified identity and a reconstructed pure `Policy.Decision`. Principal start
must additionally be at or before each snapshot check. Action must be
`artifact.upload`, and selected roles must be owner, administrator or developer.
Identity/profile/binding/principal/credential/family, both revision heads, action,
scope and request ID must be identical across snapshots. Selected memberships
may change as windows open or close, provided each snapshot remains valid.
This validates consistency and token/window semantics; it cannot prove that a
snapshot came from a locked database transaction.

## Frozen encoding

Display is a closed string-key map of eighteen keys. Its first seventeen fields
map position for position to the canonical array:

```text
audit_schema sequence tenant actor authorization target action outcome reason
request_id source_ip recorded_at previous_state_sha256 current_state_sha256
previous_event_sha256 request_sha256 envelope_sha256
```

The final named field is `event_sha256`. Tenant, actor, authorization and target
are exactly the contract's arrays. Optional IP, membership project and numeric
ends are `[]` or `[value]`. Project bindings are the exact strings
`all_projects` and `exact_project`. Memberships are 1..64 current eligible rows,
sorted uniquely by exact UTF-8 ID bytes. Internal IDs use ordinary `Scope`
bounded printable identifiers; profile ID uses its existing bounded UTF-8
grammar. Numeric values are nonnegative integers through 2^53-1, except positive
32-bit profile version; revisions and sequence are positive. Recorded ends are
exclusive. Token `issued_at` is not an authentication-completion timestamp.

Every hash is lowercase text SHA-256. Prefixes contain an actual trailing zero
byte, not two printable escape characters. External field domain spellings are
frozen as follows:

| Field | Domain prefix | Hash input after prefix |
| --- | --- | --- |
| Binding key | `mixer.hosted.customer.binding_key.v2\0` | canonical `[profile_id,profile_version,raw_subject]` CBOR |
| Issuer | `mixer.hosted.customer.issuer.v2\0` | exact raw UTF-8 issuer bytes |
| Subject | `mixer.hosted.customer.subject.v2\0` | exact raw UTF-8 subject bytes |
| Client | `mixer.hosted.customer.client.v2\0` | exact raw UTF-8 client ID bytes |
| Credential reference | `mixer.hosted.customer.credential_ref.v2\0` | exact raw UTF-8 credential reference bytes |
| Event | `mixer.hosted.customer.audit.v2\0` | canonical event CBOR |
| State | `mixer.hosted.customer.state.v2\0` | canonical versioned genesis/created-state array |
| Request | `mixer.hosted.customer.upload.request.v2\0` | canonical `[2,"artifact.upload",target,envelope_sha256,reason]` |

The raw identity subject is hashed; the snapshot's prehashed subject is never
hashed as though it were the raw external reference. Credential, IP, request ID
and time are excluded from retry request identity. Exact target, exact envelope
digest and reason remain significant. `unchanged` retains exact previous state;
both outcomes still advance event sequence and event chain.

Every variable traversal has a prior bound. Fixed arrays have exact arity,
membership lists are proper and bounded before enumeration, maps are closed,
strings are byte-bounded before Unicode operations, and the shared ArtifactCBOR
encoder enforces 65,536 bytes/depth 16/items 4,096/container 256. Current field
bounds fit below that byte limit even with 64 maximum-sized memberships; the
encoder remains the final hard budget check. Caller input allocation is outside
this pure codec's memory claim.

Decode checks only information retained in the wire representation. It cannot
recover raw external references or the locked snapshot's earlier member rows;
it cannot authenticate hashes, prove lock/freshness/admission or detect a fully
coherent privileged history rewrite. Immutable persistence, transaction-owned
authority, database constraints, public routes, provider integration, operational
qualification, physical devices, FieldLog and GA gates remain separate work.

## Verification

Run `python3 verification/hosted-customer-artifact-event/run.py --output
verification/hosted-customer-artifact-event/run-N --source-revision <base-head>`.
The runner freezes selected ordinary sources, tests, contract, golden files and
tooling; hashes pinned general-purpose dependency BEAMs; compiles with warnings
as errors; runs the new codec tests and unchanged v1/ArtifactCBOR regressions;
and removes only its owned temporary BEAM directory. It never loads the shared
Mix app or frozen/rejected hosted lanes and starts no database/native instance.
The Python standard-library oracle checks primitive RFC 8949 vectors before
independently encoding a raw-Unicode fixture. Receipts report exact source tree,
tool versions, commands, output and scope; host success is not deployed/customer
or native acceptance.
