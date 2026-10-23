# Capability-authorized execution — draft for review

Status: **draft ready for integration contract review**, 2026-10-23. No schema, runtime, authority, release,
profile or acceptance change is implemented or authorized by this draft. Inspected
baseline: `bd24e7c8058788f39407b8ec27ed11ec221df252`, with the reviewed native
boundary at `b25e3b7de2391a80d12e7fd75e60903495bec120`. The unfinished Swift
implementation was not used as evidence; its public design is a prerequisite,
not qualification. Prepared with `gpt-6.1-sol`, `xhigh`.

The product requires exact installed fingerprints, a native capability envelope,
signed grants, complete executable validation and cold-start recovery
([plan §§9–12](../mixer-product-plan.md#9-native-capability-and-extension-system)).
The minimum new route is **identity-v2 + release-v3 + guest ABI2**, over the
unchanged table-memory-v3 instruction grammar. Keep identity-v1, release-v1/v2,
activation-v1, profiles1–3, old C/session routes and default Rust admission frozen.
Do not introduce a VMProfile4 or infer a route from imports, inventory or a failed
legacy validation.

## Existing stops and exact change boundaries

| Boundary | Current code/schema | Required additive change |
| --- | --- | --- |
| Installed identity | `runtime-identity/Sources/MixerRuntimeIdentity/RuntimeIdentity.swift:23–45,72–94`; `contracts/runtime-identity-v1.json` | Separate schema2 parser/type and domain; old initializer still rejects schema2. Derive its verifier and execution configuration together. |
| Signed protocol | `updates/Sources/MixerUpdates/Verifier.swift:150–155,268–295`; `services/protocol/protocol.go:143–151`; `services/protocol/v2.go:75–93,221–229`; `contracts/release-v2.json:16–32` | Separate v3 types/validation/signing domains. V2 cannot be widened: its temporary v1 validation view intentionally requires guest ABI1. |
| Activation | `activation/Sources/MixerActivation/InstalledExecution.swift:61–101`; `StartupWork.swift:41–65`; `ColdStartRuntime.swift:102–175` | A new capability coordinator/factory and complete capability-specific validator. Existing checks still reject all nonempty hashes/grants. |
| Concrete policy | `sdk/Sources/MixerCapabilities/Host.swift:16–42,95–113`; `InstalledCapabilityAdapters.swift:7–20` | Bind captured installed grants/configuration to the actual concrete objects; raw public DTOs and adapter objects do not establish release authority. |
| Build binding | `runtime-identity/build-tools/capture.py:155–165,191–210,252–287`; `embed.py:17–47` | Explicit schema2 inspect/embed selection; retain every actual digest binding and load through the v2 parser. Existing source emitter calls the v1 parser. |
| Delivery | `services/release/server.go:104–111,267–288`; `versioned.go:18–44,280–320`; `store.go:93–107`; `storage.go:119–150` | Explicit v3 route/host/record variant if hosted delivery is included. Never try v2 after v3 rejection. |

## Proposed frozen contracts and version tuple

Add four files, without editing the old contracts' normative bytes:

1. `contracts/capability-execution-v1.json`: the new authorizing execution-route
   specification. It fixes `route = "capability-guest-v1"`, base grammar
   `mixer-table-memory-v3`, guest ABI2, UI schema1, native capability ABI1,
   payload-wrapper ABI1, six exact additional capability imports plus the two
   unchanged `mixer` imports, and the defined no-argument wake
   `mixer_guest_capability_ready_v1`. Installed startup remains a separately selected
   defined no-argument export. Its startup result keeps existing supported value
   semantics; wake must return void. No Wasm start section runs implicitly.
2. `contracts/runtime-identity-v2.json`: schema2, same restricted canonical data
   model and bounds, fingerprint `SHA256("mixer.runtime.identity.v2\0" || CBOR)`.
3. `contracts/release-v3.json`: schema/protocol3, guest ABI2, UI schema1, artifact
   domain `mixer.artifact.v3\0`, assignment domain `mixer.assignment.v3\0`.
4. `contracts/activation-v2.json`: only the new installed route, lifecycle, effect
   gate, health and recovery rules below. Activation-v1 remains unchanged.

The execution contract references the **existing frozen wire file** SHA-256
`052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439`.
Reuse its import signatures, status domains, payload/JSON schemas, memory rules,
tokens and charge-before-copy semantics. Do not rewrite its historical
`planned_profile: mixer-capability-v4`, `runtime_implemented:false` or
`import_admission:false` fields (`guest-capability-transport-v1.json:5–17,38–40`).
Those describe that file's development authority; the new execution contract
explicitly selects the reviewed separate admission context. It is not a claim
that the old file itself authorized execution. Capability semantic hashes, grant
schema1, generated payload bytes and existing UI schema1 need no change.

The accepted tuple is closed:

| Identity | Release | Guest ABI | Base grammar / execution route |
| --- | --- | --- | --- |
| v1 | v1 or v2 | 1 | unchanged explicit profile1/2/3 + Legacy |
| v2 | v3 | 2 | table-memory-v3 + capability-guest-v1 only |

Every other combination rejects, including v2-release/ABI2 and v3-release/ABI1.
Native C ABI1 is a distinct version namespace from guest ABI2. Keep the old
`RuntimeIdentity(json:)` and `ReleaseVerifier.init(host:roots:)` validation sets
unchanged; introduce explicitly named v2/v3 entry points or types. Shared private
canonical helpers may be reused, with the route selected once and never retried.

## Exact identity-v2 and release-v3 field proposals

Identity-v2 retains all existing mandatory root objects/fields, adds one mandatory
closed object `capability_execution`, and changes these existing fixed values:
`schema=2`, `engine.profile="mixer-table-memory-v3"`, `engine.guest_abi=2`,
`engine.ui_schema=1`, `execution.protocol=3`. No optional defaults or permissive
old/new union parser is needed. Proposed additional object:

```text
capability_execution = {
  route: "capability-guest-v1",
  contract_sha256: SHA256(exact new capability-execution-v1.json bytes),
  transport_sha256: "052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439",
  native_header_sha256: "9213c34ebf0f14d14f3319172e83647f704f3a02a60d413b4de990884357b4a6",
  maximum_requests: unsigned integer 1..8,
  reservation_bytes: unsigned integer 1..8388608,
  timeout_milliseconds: unsigned integer 1..30000,
  turn_milliseconds: unsigned integer 1..50,
  bridge_policy_sha256: SHA256(exact canonical captured bridge-policy file)
}
```

`contract_sha256` must equal the exact proposed execution-contract bytes during
review, and is frozen only with that contract after root acceptance. The
header value identifies the current reviewed native feature; a changed header or
native implementation requires a new installed fingerprint. The contract fixes
wrapper/native ABI versions, wake, six imports and
`effects_gate="after-verified-startup-v1"`; these are not guest-selected fields.
All added digest fields participate in capture's complete binding coverage.

Existing engine source/artifact, dependencies, generated bridge/link inputs,
capability native/configuration/grants, permissions, entitlements, trust roots and
resource-policy hashes must cover the actual native-feature archive, matching
headers, Swift bridge/SDK, compiler and configuration. Use the dependency fields
for handwritten bridge artifacts; do not mislabel handwritten source as generated.
The effective Rust and host request ceilings must be the same narrowed `N`.
Identity-bearing generated source and the final signed binary cannot be hashed
back into their own descriptor: retain the existing pre-embedding input rule,
then bind the final binary in a separate signed build attestation.
Preserve module4MiB, linear-memory64pages, fuel1M, operand4096, depth64 and
host-calls1024 ceilings, plus all current decoder/function/global/table quotas.
Mailbox reservation, Swift buffers/DTOs, storage and URLSession memory are separate
accounting categories; this is not a total-RSS or recoverable-OOM guarantee.

V3 can retain v2's exact manifest and assignment *field sets*, with the fixed
version/ABI changes above and new signature domains. The exact runtime fingerprint
already binds the installed execution route and contract, so no unsigned execution
selector or redundant downloaded policy is needed. Retain explicit schema1
`capability_grants` with its current descriptor hash
`b394ffd165ef28977de9743b1c1a98c419504787f2912e30d419cfb1582e15e1`;
missing/empty entries deny. Capability hashes continue to prove compatibility,
not permission. Signed memory/fuel/startup limits may only narrow installed
values; capability ceilings are fixed installed identity values in this first
version. No new asset, compression, WASI or broad filesystem support is implied.

## Installed material and the verified factory

Use a new capability activation package/target depending on the experimental
capability runtime, updates, identity and SDK. **Do not add that runtime to the
current activation target**: `activation/Package.swift:9–17` already imports
`MixerRuntime`, which selects the default archive. One executable must select the
single distinct experimental static archive containing both C families and the
shared registry. Neutral type/link factoring, if wanted later, is another review.

The new factory owns an immutable schema2 identity plus captured canonical installed
material, never arbitrary caller-supplied policy/adapters. Verify exact captured
file bytes against each identity digest *before parsing*. Require the canonical
representation when those bytes are specified as canonical material; never hash
one representation and instantiate from another file, mutable path or DTO.

The installed material proposal is bounded, closed and versioned. Material files
use the capture convention: sorted JSON keys, compact separators, ASCII escaping,
unsigned decimal integers, and one final LF. Hash the exact captured bytes and
require re-encoding equality; do not substitute a semantic hash of different bytes.


- Per-capability grant files use the existing closed entry fields
  `capability_id,schema_sha256,permissions,origins,methods,namespaces`, strictly
  sorted unique arrays, with the current exact family rules. Their exact canonical
  file bytes bind `capabilities[].grants_sha256`.
- HTTP configuration: `{schema:1, implementation:"urlsession-normal-tls-v1",
  maximum_concurrent_requests:N}`. No arbitrary closure, session/delegate,
  protocolClasses, cookie/trust override or supplied response implementation.
- Storage configuration: `{schema:1, implementation:"app-private-kv-v1",
  container:"application-private", directory_component:identifier,
  maximum_total_bytes:1..4194304, maximum_entries:1..1024}`. The directory
  component uses ASCII1..64 letters/numbers/underscore/hyphen, with no dot, slash
  or path traversal. Namespace authority
  derives from the same installed grants. The native embedding supplies its real
  application-private container; no release/guest path chooses a root. Container
  instance UUID/absolute device path is not part of a universal binary fingerprint.
- The bridge-policy file contains fixed semantics plus narrowed rate values
  `{schema:1, burst:1..8, starts_per_second:1..32}`. The execution contract fixes
  the current bounded scheduler/timer/queue policy; no arbitrary worker or callback
  is selectable. Configuration bytes bind `configuration_sha256`; bridge-policy
  bytes bind the new named digest. Native implementation bytes bind existing
  `native_sha256` and captured dependency identities. Empty installed storage
  namespaces deny and omit the adapter: the existing SDK constructor requires a
  nonempty namespace set; do not fabricate a namespace to satisfy it.

The factory parses these same verified snapshots and constructs the concrete
`URLSessionHTTPTransport`/`AppPrivateKeyValueStore`/installed-adapter host itself.
It requires the known SDK native identity and matching installed schema hashes.
Do not accept a matching declared hash alongside independently constructed objects.
An absent capability/adapter or denied permission never dispatches its native
operation. Perform binding and complete payload admission before adapter creation.
Trusted adapter initialization may create/lock its app-private storage; a
zero-dispatch test must not be reported as zero host filesystem activity.

Only the updater's exact `ColdStartSelection` payload plus opaque
`VerifiedArtifact` from that pinned verifier can supply release grants. Intersect
installed and verified signed permission/origin/method/namespace sets, using the
existing SDK policy semantics. No union, wildcard, schema-hash permission, DTO,
sidecar or caller-chosen host/session identity can grant access. Raw development
constructors remain development APIs, never an OTA admission proof. Existing
snapshot capture still does not discover the graph, prove build consumption,
attest compiler truth or attest final signed embedding; those gates stay open.

## Bridge API prerequisites — separate reviewed follow-on

Root's candidate API review identifies two gaps which this design must not assume
are already implemented:

- The current public bridge provides `prepare`/`create` and development enable,
  but no standalone complete validate-only entry point for the updater before
  staging. Add a bounded validation API taking the **same** module, installed
  startup, execution context and effective signed/installed limits as construction.
  It validates every body/import/wake/memory shape without constructing a guest
  instance/mailbox, creating adapters, starting an export or enabling effects.
  Bound validation admission before queuing/capturing module Data; no unbounded
  detached validation backlog. Construction still performs its own matching
  admission/instantiation checks; a validate result is not a retargetable proof.
- Current `ExperimentalCapabilityError` exposes `code:String` and `nativeStatus`,
  insufficient as the activation coordinator's stable typed failure classifier.
  Add structured machine-code classification at the checked native boundary:
  closed known native-code mapping for deterministic guest traps, explicit
  cancellation/deadline, panic/quarantine, API/resource and unknown categories,
  with relevant bounded function/offset metadata. Unknown codes/status combinations
  remain conservative unknown interruption. Never classify using a human message,
  substring, description, or status2 alone. Tests must distinguish a known trap
  from cancel, allocation, poison/panic and an unknown future code even when their
  descriptions imitate a deterministic trap.

Identity/signed positive `memory_bytes` may floor to **0pages**. Existing C/v3
supports matching defined zero-page modules, while the current bridge configuration
review reports a `1...64` guard. The same-config follow-on should support exact0
through a separately reviewed narrow change for parity; otherwise reject before
staging. Never round up to1page or use different validation/construction limits.
The scheduler counts one coalesced detached host-close Task separately from one
coalesced native-close dispatch job per owner; neither is per-callback fanout.

These may be additive bridge APIs, or an equivalent private checked C boundary in
the new activation package **using the same one archive**. Freeze/review the chosen
interface and executable tests before the verified factory/coordinator depends on
it. This draft changes neither the frozen candidate nor those APIs. Concrete SDK
adapter factories run only after all installed-material and payload validation.

## Selection, effects, health and failure ordering

The new coordinator keeps its bridge private. It supplies the updater's complete
executable validator itself; callers do not supply an accepting closure. Before
staging/selection, bind scope/fingerprint/protocol/ABI/transport/grants/limits,
signatures, assignment sequence, exact immutable payload length/hash and installed
material. Invoke the capability C validator with that same startup/limits tuple;
validate every body/import, exact defined wake and required memory. Inventory is
non-authorizing. Construction must use the same route and tuple, without retrying
legacy admission or another profile.

The new coordinator distinguishes `idle`, `startingDisabled`, `provisionalGuest`,
`healthyGuest`, `stopping`, `recoveryRequired`, `nativeFallback`, and `closed`.
`effectsEverOpened` is an irreversible per-attempt latch, not the health flag.
A post-enable terminal failure reports `recoveryRequired`; it cannot masquerade
as a safe native-fallback launch or reopen a replacement guest. These states are
new-route API semantics, not a change to activation-v1.

The fixed ordering is:

1. Reserve bounded construction ownership; retain the verified selection and
   record the durable attempt before executing. Cancellation, changed material,
   mismatch or an exhausted cap rejects before effects or queued unbounded work.
2. Construct and invoke the installed startup exactly once **with effects
   disabled**. Startup enqueue results remain unavailable permanently; later
   enable never makes those earlier requests drainable. Trap, deadline, close or
   cancellation discards the attempt and cannot dispatch its queued work.
3. Recheck the same attempt generation, open latch, cancellation and signed
   monotonic startup deadline after every await. Publish only a completed successful
   startup, then privately enable effects under that still-current attempt. No
   failed/cancelled/closed attempt can become enabled. The public OTA owner exposes
   neither the raw bridge nor development effects-open controls.
4. A provisional guest may now perform granted effects. Only successful guest
   turns publish requests. Startup success, enabling, a completion callback or a
   rendered test label is **not health**. Health separately requires installed
   real milestones plus the durable updater's monotonic observation interval
   (`ColdStartRuntime.swift:178–188`). A retained healthy artifact is still fully
   rebound/revalidated and reruns disabled startup on each process launch.

Effects can occur before provisional health and cannot be undone by later failure.
Cold-start selection/startup failure may choose at most one compatible retained
healthy attempt, then the actual compiled native fallback. After effects open,
stop admission/guest turns on terminal failure; do not silently live-switch to
another guest. Retain native exit owners/tickets and actual `didExit` obligations
through close, timeout, cancellation and fallback decisions. Close/terminal payload
is not native exit; poison/quarantine can retain counted capacity indefinitely.
The embedding must reconcile possibly committed external effects before any
conflicting fallback work. No finite drain time, effect rollback or zero-I/O race
after a final admission check is promised.

Typed permission/I/O/deadline outcomes are not deterministic guest traps. Preserve
explicit VM trap classification; cancellation, native panic/poison, allocation
failure and unknown interruption must not be relabelled healthy or deterministic
app failure. Health/fallback state and recovery need the new bridge's typed errors,
not error strings. Full UI/FieldLog milestones and data-compatible recovery are
pending evidence, not invented by this coordinator.

## Downgrade, persistence and dependency order

Reject all untabled identity/protocol/ABI/route combinations, unknown fields,
missing limits/material, wrong domain signatures, retargeted payload/selection,
wrong concrete implementation, transport/schema/header mismatch and a limit above
installed or frozen ceilings. Never guess/probe/fallback to another verifier or
validator on rejection. Old API and vector acceptance/rejection stay unchanged.

Keep assignments monotonic per scope/runtime/channel; rollback signs an older
compatible artifact with a **greater** new sequence. Preserve replay state on
failure. Existing `ColdStartUpdater.swift:285–291` compares the complete installed
host; an old identity's state directory must reject, not be erased/reinitialized
for a new host. Use explicitly installed per-runtime storage or a separately
reviewed migration. Existing retained-healthy/offline authority rules remain
explicit; v3 cannot use v2 authority or an expiry reset to accept new content.

For hosted v3 delivery, add explicit `/v3` routes, strict registered host tuples,
typed record variants, signature/shape decoders and immutable content handling.
A local snapshot schema3 should upgrade only on the first successful v3 write and
remain able to read valid schema1/2; older programs refuse schema3. Preserve prior
response/audit bytes and cross-version idempotency conflicts. PostgreSQL's opaque
signed byte storage may need only strict v3 dispatch, not an assumed SQL migration;
verify that independently. Hosted changes are not prerequisites for initial local
signed-fixture qualification and must not be claimed by that test.

Implement in this order: freeze execution/identity/release/activation contracts and
cross-language vectors; qualify explicit identity-v2 capture/inspect/embed; add v3
Go/Swift verifier types with opaque typed authority; freeze/review the Swift bridge
and the bounded validate-only/structured-error follow-on; implement the material-bound factory and separate activation package; exercise
local signed recovery; then add hosted v3 routes/storage and distribution. Device,
actual published-package consumer and GA gates remain separate and pending.

## Meaningful acceptance tests

| Layer | Required original tests |
| --- | --- |
| Preservation | Every old identity/release canonical vector/signature/digest and rejection unchanged; old VM/default/session/stream admission still rejects the six imports, even with the native feature linked. No second Rust archive. |
| New identity/material | Closed schema2 parsing, duplicate escaped keys, exact/+1 quotas, every field/digest mutation changes fingerprint; unknown tuple rejected; captured bytes differ from supplied DTO/path/object; wrong concrete adapter/bridge/native identity fails before I/O. Golden domains differ from v1. |
| V3 authority | Independent Go/Swift canonical CBOR and Ed25519 vectors; wrong v1/v2 domains, ABI/route/scope/fingerprint/grants/payload, stale assignment and invalid sorting reject. Cross-module negative constructors cannot manufacture verified grants/artifacts. |
| Full admission | Standalone same-config validation must perform no instance/adapter/startup work, obey admission/cancel caps and reject retargeting; original real Wasm with all six imports/direct/indirect/exported returns; wrong/uncalled import, unsupported instruction, start/wake/memory/type/limit mismatch rejects before startup. No metadata-only acceptance. |
| Lifecycle/health | Cancel/close/deadline at each await/publication/enable boundary; trapping or disabled startup causes zero dispatch; first successful granted turn dispatches; forged/early milestones and success callbacks cannot mark healthy; health durability failure cannot invent success. |
| Effects/ownership | Real private storage bytes with narrowed namespaces; denied HTTP origin/method/permission reaches no adapter; equal tokens in different owners never cross; callback-before-submit/late-exit/close/failure retains actual ack obligations and aggregate16/eight-request caps. No timeout refresh on actor queues/resume. |
| Recovery/delivery | Signed v3 download/reopen, corruption, power-failure injection, healthy fallback, greater-sequence rollback, old-store mismatch without replay reset, strict mixed-version storage/routes and idempotency. Prove no silent live replacement after effects. |
| Deferred qualification | Normal-trust HTTPS success needs an explicitly provisioned fixture; no TLS bypass. Physical mobile lifecycle/performance, full Swift/UI/FieldLog, immutable published packages, complete build graph/embedding/signing and store/GA claims remain pending. Phones stay disconnected. |

The four new JSON files are **proposed candidate immutable definitions**. Their
proposal/implementation/qualification status lives in this design, rather than
volatile flags inside their byte-hashed normative content. Their exact cross-file
hashes support review and future fingerprint binding, not runtime authority.
Definition-only authority clauses remain true even after implementation. Old contract
bytes, VM/C/SDK/bridge/parser/service implementations and the frozen builder remain
unchanged. Root must freeze these normative contracts before dependent work.

Current prerequisite status at this proposal: schema2 identity/capture/embed,
release3 verifier/service, installed-material factory and capability activation are
not implemented. Root candidate review reports missing standalone full validation,
structured machine-code errors and zero-page bridge parity; these require a
separate bounded implementation/review. The new JSON lists their permanent API
requirements without mutable implemented:false fields. No full UI/FieldLog health,
recovery compatibility, complete build-attestation, published-consumer or new device
gate is closed. Updating these facts must not rewrite frozen execution-contract
bytes or change an already installed identity merely to update documentation.
