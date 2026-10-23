# Signed guest UI and event integration: proposed first slice

Status: root accepted, 2026-10-23. Implementation remains separately coordinated;
this document does not authorize ABI, runtime, renderer, identity, or release
implementation by an unassigned lane. The accepted document digest is sealed
in `verification/guest-ui-design/root-accepted.json`, with the read-only source
inspection receipt at `verification/guest-ui-design/inspection.json`.

## Decision and completion boundary

Implement one opt-in signed guest screen: a vertical stack containing a status
label and a **Save sample** button. Startup supplies a validated `UIDocument`.
A native button activation reaches a fixed guest export; that guest enqueues
`storage_put` through the existing capability scheduler, then consumes its
completion in the existing ready export and publishes a new document. The
native screen displays **Saved sample** only for a successful committed result.

The first integration profile supports only UI-v1 `vStack`, `text`, and `button`,
and only the `activate` event with `null` value. Unsupported nodes, properties,
actions, or transport instructions fail the attempt; no blank replacement is
permitted. This deliberately bounded profile is not the complete UI inventory
in product-plan section 8, a Swift compiler/runtime qualification, or FieldLog
W07. It adds no network, Swift async, Android renderer, store, publishing, or
physical-device claim.

Use the current C memory-copy functions and the current off-UI guest worker.
Add one narrowly scoped validate-only C entrypoint because the present native
validator cannot check the required event-export signature. Do not add a new
execution, memory, callback, capability, arbitrary-export, or public artifact
injection API to the signed coordinator.

## Observed seams

These are source observations, not executed integration results:

| Current source | Consequence for this slice |
| --- | --- |
| `sdk/Sources/MixerGuest/GuestUICodec.swift` | Encodes and validates values only; it does not execute a guest or route a native event. |
| `sdk/Sources/MixerUI/Protocol.swift`, `Validation.swift`, `Reconciliation.swift` | Strict raw UI decode, immutable validated values, increasing document revisions, native node generations, and current-snapshot action routing already exist. Reuse them. |
| `sdk/Sources/MixerApple/MixerNativeView.swift` | `MixerUIHost` and native SwiftUI controls are MainActor isolated. `onAction` is a caller closure; the signed integration needs its own internal bound closure. There is no native presentation receipt. |
| `vm/include/mixer_vm_capability.h` | Experimental sessions already have `session_read`, `session_write`, and typed `session_invoke`; memory copies are bounded to 1 MiB. |
| `experimental-capability-runtime/.../Session.swift`, `Native.swift`, `Ownership.swift` | Swift has memory read/write wrappers and one pending ordinary command. Separate calls are not an atomic UI exchange: the pump may execute autonomous completion wakes between them. |
| `vm/src/experimental_capability_guest/mod.rs` | Validation checks the installed no-argument startup and fixed no-argument, void ready export. It does not check a UI event export. |
| `capability-activation/.../CapabilityColdStartWorker.swift` | Signed selection, construction, startup, durable effects intent, enable, confirmation, and observation already have an order. Startup's returned value is currently discarded. |
| `CapabilityColdStartRuntime.swift`, `CapabilityRecoveryStore.swift` | Current public milestones are trusted embedding strings; the store records them only after actual effects confirmation. The UI integration must earn its milestones internally. |

## Opt-in and signed binding; preserve existing bytes

Keep all existing contracts, signature domains, release-v3 fields, identity-v2
fields, UI-v1 bytes, capability payloads, numeric status domains, default VM
profiles, and existing C header bytes unchanged. Add
`contracts/guest-ui-event-v1.json` and a separate `vm/include/mixer_vm_guest_ui.h`.
Their hashes are frozen only after this design is reviewed.

The trusted native app explicitly opens a new `CapabilityGuestUIRuntime` facade.
It accepts the existing `InstalledCapabilityExecution`, never a verifier,
selection, module, native session, export name, renderer callback, or artifact.
Its internal installed-mode check requires all of:

1. Existing valid identity-v2/capability-route and linked material checks.
2. Installed `execution.startup_export == "mixer_guest_ui_start_v1"`.
3. Installed dependency `mixer.guest-ui-event-v1`, version `1`, with
   `artifact_sha256` equal to the exact new contract bytes.
4. Installed dependency `mixer.guest-ui-native-header-v1`, version `1`, with
   `artifact_sha256` equal to the exact separate header bytes.
5. Those entries match the known contract/header compiled into this integration.

Identity-v2 already supports closed, bounded, sorted dependency entries. These
entries and startup are covered by the exact installed runtime fingerprint;
the signed release-v3 manifest must match that fingerprint. The guest cannot
select the mode or supply a sidecar. The new facade only narrows an installed
capability guest. It does not introduce imports or reinterpret UI-v1.

Capture the new contract/header and all actual implementation inputs in the
existing pre-embedding source, archive, bridge, and link evidence. Dependency
digests alone do not establish build consumption. Keep exactly one selected
native archive/registry in a process; the optional validator is an additive
symbol in that archive, not a second archive linked alongside it.

The existing capability-only facade rejects an identity if **either exact new
dependency ID is present, regardless of version/hash, or the reserved UI startup
export is selected**. This includes an incomplete marker pair, wrong versions,
wrong hashes, or a reserved startup with no markers. The UI facade requires the
entire exact triple; marker absence never triggers automatic UI mode. Reject
these combinations before store/reservation work. There is no public mode
boolean, marker-repair path, or try-UI-then-generic fallback. Existing identities
outside this newly reserved namespace retain their behavior. Raw experimental sessions remain development APIs and do not confer
signed selection authority. No new release or identity schema is needed for
this slice. A failure to prove these existing identity bindings blocks this
choice; do not fall back to an unchecked configuration flag.

The concrete public facade proposal is:

```swift
public final class CapabilityGuestUIRuntime: Sendable {
    public static func open(configuration: CapabilityColdStartConfiguration,
                            execution: InstalledCapabilityExecution) async throws -> CapabilityGuestUIRuntime
    @MainActor public var presentation: GuestUIPresentation { get }
    public func beginDownload(signedManifest: Data, signedAssignment: Data) async throws
    public func downloadOffset() async throws -> UInt64
    public func appendDownload(_ bytes: Data, atOffset: UInt64) async throws
    public func finishDownload() async throws
    public func cancelDownload() async throws
    public func start() async throws -> CapabilityGuestUIActivationSnapshot
    public func recoverySnapshot() async -> CapabilityGuestUIRecoverySnapshot
    public func close() async
}

@MainActor public final class GuestUIPresentation: ObservableObject {
    @Published public private(set) var state: GuestUIPresentationState
    // No public initializer, host, snapshot, document, event ingress, or receipt API.
}

public enum GuestUIPresentationState: Sendable, Equatable {
    case waiting, displaying(revision: UInt64), stopped
}
@MainActor public struct MixerGuestScreen: SwiftUI.View {
    public init(presentation: GuestUIPresentation)
}
```

Define this facade, presentation model, and bound platform wrapper in the
capability-activation target, which already owns the private attempt identity.
Add its dependencies on the existing SDK `MixerGuest`, `MixerUI`, and
`MixerApple` products. This is a one-way package dependency; SDK never imports
activation. The new Apple screen is available only on its qualified Apple
platforms. No public presentation protocol or callback factory is needed.
The presentation model's `MixerUIHost`, snapshot, render closures, and platform
probes are private; returning a read-only model must not expose a mutable host
through another public property. The new snapshot types use the existing
bounded phase/candidate/launch/sequence/effects/cleanup and durable diagnostic
fields, but replace the old terminal-cause property with
`CapabilityGuestUITerminalCause` below. They do not alter existing snapshot or
failure enums.

## Fixed guest and memory contract

The required defined, non-imported exports are:

| Exact name | Signature | Meaning |
| --- | --- | --- |
| `mixer_guest_ui_start_v1` | `() -> i32` | Existing startup turn, effects disabled. Returns unsigned bit-pattern offset of the control header. |
| `mixer_guest_ui_event_v1` | `(i32 byteLength) -> i32` | Reads one host-written event from the established buffer. Returns `0` only after accepting it. Any other result fails this first profile; no automatic retry. |
| `mixer_guest_capability_ready_v1` | `() -> ()` | Existing capability completion wake; it may change the document. |

Require exactly the existing one defined, nonshared memory. The UI mode does
not relax module, memory-page, fuel, turn, stack, import, or capability quotas.
No exported memory, allocator, arbitrary callback, or host object is required.

Startup returns the offset of this **32-byte**, unaligned, little-endian header:

| Byte offset | Width | Field |
| --- | --- | --- |
| 0 | u32 | Magic `0x3155494d` (bytes `4d 49 55 31`, `MIU1`) |
| 4 | u32 | Header size, exactly `32` |
| 8 | u32 | Current document offset |
| 12 | u32 | Current document byte length, `1...65536` |
| 16 | u32 | Event-buffer offset |
| 20 | u32 | Event capacity, exactly `4096` |
| 24 | u64 | Reserved, exactly zero |

The header offset, event-buffer offset, and capacity remain fixed for the
session. The guest may change document offset/length between successful turns.
Header, document, and entire event-buffer ranges must be pairwise disjoint and
nonwrapping. Reject range arithmetic overflow before C work; C still checks
actual memory bounds. At startup, read the event buffer once to establish its
range; memory cannot shrink. Every subsequent harvest rechecks all header
fields and range separation. No guest address escapes the off-UI exchange.

Document bytes are an ordinary UI-v1 JSON `UIDocument`, decoded exclusively by
`GuestUICodec`/`UIValidator` raw-byte preflight, then validated against this
installed subset: maximum 65,536 bytes, 256 nodes, depth 16, 64 children per node,
4,096 UTF-8 bytes per string, supported kinds `{vStack,text,button}`. Existing
closed property/action/identifier validation also applies. First revision is
positive. A larger revision replaces the latest document; an equal revision
is allowed only with byte-for-byte identical document bytes. A lower revision
or same-revision mutation is terminal. Revision exhaustion cannot wrap.

The host event is one UTF-8 JSON object, at most 4,096 bytes, with these exact
mandatory keys (example values):

```json
{"schemaVersion":1,"sequence":1,"revision":1,"nodeID":"save","actionID":"sample.save","event":"activate","value":null}
```

`sequence` and `revision` use positive shortest unsigned decimal UInt64 tokens.
`nodeID`/`actionID` preserve UI-v1 identifiers, without normalization. Only exact
`activate`/`null` is valid. No session ID, native node generation, function name,
capability name, pointer, or callback crosses in this packet. Encode with an
owned deterministic encoder (sorted keys, unescaped slashes), then strict
preflight/decode tests; do not expose unchecked Codable decoding. The 4,096-byte
bound accommodates the worst JSON escaping of two existing 128-byte IDs. The
guest fixture checks exact bytes/fields and sequence; subsequent real guest
libraries must implement the same closed decoder.

## Validate-only addition, before staging

Proposed sole new C declaration, in the separate header:

```c
uint32_t mixer_vm_capability_guest_ui_validate_v1(
    const uint8_t *module, size_t module_len,
    const MixerVmLimits *vm_limits,
    const MixerVmCapabilityLimitsV1 *capability_limits,
    MixerVmReport *out);
```

Use the existing complete capability-module validation with the fixed startup,
then inspect the already validated module's export/type table for the three
exact signatures above. Reject imported or wrong-kind exports. Use the same
configuration, feature checks, error/report/status validation, numeric pointer
preflight, and admission-before-capture limits as existing validate-only work.
No instance, mailbox, session, adapters, startup, memory allocation for an
instance, or native I/O is allowed. Reuse the existing bounded validation pool.
No second Swift Wasm parser or regex export check authorizes staging.

UI mode selects this validator internally at download finish and every startup
consumption. Construction invokes it again over the same captured bytes/config
before the existing C session create. Actual startup then validates header and
document before effects intent. Static validation cannot establish runtime UI
content. Any malformed initial content stops before effects intent/enable.
Actual construction still revalidates the complete module. Existing default
validate/create ABI and behavior remain unchanged.

The new validator must use the existing exact machine code `capability_export`
for all missing/imported/wrong-kind/wrong-signature required-UI-export checks,
including the stricter startup i32 result. Its helper creates the error with
no function and offset zero, after complete module validation. This reuses
the present helper/error/report shape; it adds no native error code or enum
case. The fixed startup constant eliminates the existing invalid-caller-
startup-name branch from this entrypoint.

The bridge recognizes this group **only in the new UI validate-only call
context**, after `NativeDiagnostics.check` has fully validated the report:
operation `.validation`, native status `1`, typed kind
`.validation(.requiredDefinedExport)`, no function, and byte offset `0`.
The underlying unchanged report has ABI1/status1/reserved0, value type/value0,
fuel/host-calls0, function `UInt32.max`, offset0, and NUL-terminated machine
code `capability_export`. The existing `NativeDiagnostics` table already maps
that code/status/context to `requiredDefinedExport`; the UI layer consumes
the checked typed classification and never parses `message` or matches code
strings itself. It cannot distinguish which export or which defect within
this group and must not claim to. Other status/kind/context combinations keep
their existing bridge classification; malformed reports retain quarantine.

## Composite exchanges on the existing guest worker

Add internal/SPI fixed operations; the public signed facade exposes none of
`invoke(String)`, memory access, arbitrary data execution, or raw handles.

* `startupGuestUIV1`: native startup, require i32 result, capture header/ranges,
  copy document, raw decode and validate, publish owned result. One admitted
  ordinary command; no await or intervening guest turn between these steps.
* `deliverGuestUIEventV1`: claim the sole accepted event, recheck live identity
  and input authority, write exact event bytes, invoke the fixed event export,
  require result i32 zero, copy/validate document, finish event. One admitted
  worker operation; no wake can split its memory write and invocation.
* After **every successful actual ready wake**, copy header and document and
  apply the same validation before another guest turn. Also harvest after
  startup/event, including successful turns that leave revision unchanged.

The guest worker owns the control-header offset, immutable buffer descriptors,
last harvested revision/bytes, and all native memory access. Raw pointers and
borrowed guest memory never reach callbacks or MainActor. Failed/trapped turns
publish no UI. Validation failure stops the attempt and admission; queued
capability requests must not begin I/O after such failure. Existing native
requests that were already admitted may still commit.

An important ordering change in **UI mode only** is that the command/ready-turn
success path must harvest and validate **before** the pump drains that turn's
capability calls. A success in the VM is insufficient if the turn emitted an
invalid UI contract. The UI bridge latches stop and closes before any later
take/admission. Existing capability mailbox turn publication remains intact;
this adds an earlier bridge admission check rather than fabricating exit.

All startup/event/ready invocations count toward the existing four guest turns
per batch. Check elapsed budget before starting each exchange. Header copy,
bounded decode, and reconciliation cost count toward recorded batch elapsed
time; an exchange can exceed the 8 ms cooperative target and is not preempted
by that target. Native turn cutoff/fuel still apply. Preserve cancellation and
expiry processing before new external-effect admission; never introduce an
immediate busy-retry loop or a second guest worker.

## Chosen cross-package SPI and queue implementation

`MixerGuest` owns these concrete types. Diagnostics are ordinary immutable
public values; queue/control methods and transient handoff values are visible
only under `@_spi(GuestUIV1)`. None is `Codable`, exposes a native address, or
accepts a host protocol, delegate, closure, executor, Task, or supplied queue.
Constructors for frame/claim/ticket values are internal to `MixerGuest`.

| Type | Exact data / operations and creator |
| --- | --- |
| `GuestUIProtocolPhaseV1` | Closed cases `validation`, `startup`, `event`, `wake`, `presentation`. |
| `GuestUIProtocolCodeV1` | Closed cases `requiredExport`, `startupResult`, `header`, `memoryRange`, `bufferChanged`, `document`, `revisionRegressed`, `sameRevisionMutation`, `eventEncoding`, `eventResult`, `sequenceExhausted`, `presentationInvariant`. No message-text classification. |
| `GuestUIProtocolFailureV1` | Immutable `phase` and `code`, conforming to `Error`; produced at the checked call site. A value alone conveys no stop, receipt, or execution authority. |
| `GuestUIProtocolTerminalV1` | Immutable failure plus `effectStage: GuestUIEffectStageV1` (`beforeIntent`, `intentEntered`), captured atomically by the exchange on the first protocol stop. |
| `GuestUIStopV1` | Closed first-stop tag: `bridge`, `cancelled`, `deadline`, `closed`, or `protocolViolation(GuestUIProtocolTerminalV1)`. The bridge detail remains in the existing checked bridge-failure sink; `bridge` does not fabricate one. |
| `GuestUIExternalStopV1` | Closed input cases `bridge`, `cancelled`, `deadline`, `closed`; cannot construct a protocol terminal or presentation receipt. |
| `GuestUIControlRejectionV1` | Separate local `Error` cases `invalidGeneration`, `busy`, `closed`, `consumerAlreadyIssued`, `readerBusy`, `staleClaim`. These are not native failures or UI protocol violations. |
| `GuestUIFrameV1` | `generation: UInt64`, `serial: UInt64`, `document: ValidatedUIDocument`. Created only by exchange `finishTurn`; serial never wraps. Raw document bytes used for equal-revision checks remain in a private fixed slot. |
| `GuestUIEventAdmissionV1` | `accepted(sequence: UInt64)`, `busy`, `stale`, `closed`, `invalid(UIRoutingError)`. Returned synchronously by exchange `offer`. |
| `GuestUIEventResultV1` | Generation, sequence, and closed outcome `delivered` or `terminal(turnBegan: Bool)`. No assertion of KV success or rollback. |
| `GuestUITurnClaimV1` | Opaque generation/claim serial and closed kind `startup`, `event(sequence: UInt64, bytes: Data)`, or `ready`. Created only by exchange claim methods. One active claim; maximum event bytes 4,096. |
| `GuestUIPresentationClaimV1` | Opaque generation/claim serial and at most one frame, one event result, and current stop tag. Created only by exchange `claimPresentation`; at most one claim. |
| `GuestUIPresentationTicketV1` | Opaque generation/frame serial/revision returned only from successful `completePresentation` with a validated native render snapshot. Its initializer is not exported. It authorizes observation of this frame, not health. |
| `GuestUIWakeV1` / `GuestUIWakeConsumerV1` | Concrete data-only wake source / one issued reader, described below. Created only inside the exchange; no injected source or handler. |
| `GuestUIExchangeV1` | One final non-actor, `@unchecked Sendable` class with one private `NSLock` and fixed state. Activation constructs it after attempt reservation, with the exact positive selected generation. Both bridge owner and presentation model receive this same object. It retains **no owner, model, signals, worker, session, observer, source, or closure**. |

The exchange's fixed callable surface is:

```swift
@_spi(GuestUIV1) public final class GuestUIExchangeV1: @unchecked Sendable {
    public init(generation: UInt64) throws
    public let deliveryWake: GuestUIWakeV1
    public let coordinatorWake: GuestUIWakeV1
    public func claimStartup() throws -> GuestUITurnClaimV1
    public func claimNextTurn(ready: Bool) throws -> GuestUITurnClaimV1?
    public func finishTurn(_ claim: GuestUITurnClaimV1, documentBytes: Data) throws
    public func offer(_ envelope: UIEventEnvelope, generation: UInt64) -> GuestUIEventAdmissionV1
    public func claimPresentation(generation: UInt64) -> GuestUIPresentationClaimV1?
    public func completePresentation(_ claim: GuestUIPresentationClaimV1,
                                    snapshot: UIRenderSnapshot?) -> GuestUIPresentationTicketV1?
    public func observePresentation(_ ticket: GuestUIPresentationTicketV1) -> Bool
    public func consumeObservedPresentation(generation: UInt64, frameSerial: UInt64)
    public func enterEffectsIntent(generation: UInt64) throws
    public func confirmEffectsEnabled(generation: UInt64) throws
    public func requireCommitEntry(generation: UInt64) throws
    public func requireEffectAdmission(generation: UInt64) throws
    public func recordProtocolFailure(_ failure: GuestUIProtocolFailureV1)
    public func stop(_ cause: GuestUIExternalStopV1)
    public func snapshot() -> GuestUIExchangeSnapshotV1
}
@_spi(GuestUIV1) public final class GuestUIWakeV1: @unchecked Sendable {
    public func takeConsumer() throws -> GuestUIWakeConsumerV1 // one issuance only
    public func signal()
    public func finish()
}
@_spi(GuestUIV1) public final class GuestUIWakeConsumerV1: @unchecked Sendable {
    public func next() async throws -> Bool // true: inspect state; false: finished
}
```

`GuestUIExchangeSnapshotV1` is a fixed immutable diagnostic record: generation,
first stop, sticky intent/confirmation flags, guest-turn/event/presentation
occupancy, latest/displayed revisions, pending native-presentation receipt,
and bounded counters. It contains no host/session/renderer references. It is
not an executable selection or a health receipt. A receipt is removed only by
the activation worker's internal consume operation after its milestone write;
this exact consume operation is idempotent by generation and frame serial.
`confirmEffectsEnabled` is called only after actual bridge enable and the
existing store's confirmation return. It opens frame delivery/input and signals
delivery again, so a pre-confirmation consumed hint cannot strand the first
frame. `claimPresentation` never hands out a live frame before confirmation.

`completePresentation` requires the returned native snapshot's whole document
to equal the claimed validated document and installs that immutable snapshot
for future input routing. Stop before completion suppresses the ticket and
clears displayed input authority. A private native probe retains this ticket;
`observePresentation` accepts it only while that same generation/frame remains
the completed displayed frame and effects are confirmed. The platform checks
are performed by the private wrapper before this call. No caller-supplied
public boolean or callback can earn a receipt. The first accepted observation
remains pending across later revisions until consumed by the coordinator or
discarded by stop.

`GuestUIWakeV1` is a small fixed queue, not `AsyncStream` handed to arbitrary
iterators: a private shared state contains `pending: Bool`, `finished: Bool`,
one consumer-issued flag, and at most one checked continuation. `signal` takes
and resumes the waiter outside its lock or sets `pending`; repeated signals
coalesce. `next` rejects a second simultaneous waiter before suspension; it
consumes pending before observing finished. `finish` wakes a waiting reader;
one already pending hint is consumed, then `next` returns false. All mutation
and resumption is outside the exchange's guard except for the short state
update itself; never resume a continuation while either lock is held.

The **existing single coordinator observation consumer** reads
`coordinatorWake` in UI mode. `CapabilityAttemptSignals` uses that same source
for its bridge/local/timer hints, rather than creating another control
consumer. Legacy mode retains its current signal implementation. Only
`CapabilityAttemptSignals.finishNotifications` finishes this control channel,
after the existing stop/notification handoff; the exchange never ends it early.
UI receipt and protocol-stop writes signal this source directly, without
waiting for MainActor or holding an owner reference.

The bridge does not need a reverse signal reference. In UI mode its existing
10 ms timer remains armed after effects confirmation until stop and polls the
one event slot. `claimNextTurn(ready:)` prefers a ready event over a ready wake.
The existing batch limits remain in force. This costs a bounded idle timer;
it adds no actor, source, detached task, callback, or owner back-reference.

`finishTurn` decodes/validates outside the exchange lock while retaining the
one turn claim, then commits under that lock only if still live. All frame,
displayed-snapshot, turn claim, event reservation, first-stop, and intent state
live under **this exact exchange guard**. `offer` routes the supplied envelope
against the exchange's last completed immutable `UIRenderSnapshot`; the
caller never supplies an action ID. It reserves the one event slot under the
guard, encodes outside it, then commits acceptance under the same guard. The
reservation blocks all guest-turn claims. If stop wins before acceptance,
offer returns closed and does not advance the sequence. The model derives an
envelope from its private currently routed snapshot; it exposes no public
offer method. No second lock in the bridge or activation may independently
decide input-versus-wake order.

Creating/accepting the offer reservation signals `deliveryWake` after releasing
the guard, as does consuming its event result in `completePresentation`.
Every harvest that changes the latest/displayed relationship also signals it.
Thus a hint with no new document still runs the fixed helper to refresh the
model's private interaction-enabled state while input is outstanding or the
display lags. This interaction state is not a public host/setter. Completion
reads the current exchange state after its atomic result consumption; no
per-event UI Task or stale enabled-state capture is needed.

`CapabilityAttemptSignals` may retain the data-only exchange and its wake
source. In UI mode, its commit check holds its existing signal lock, then
calls the exchange guard check; no exchange method calls back into signals.
Effects-intent entry first calls `exchange.enterEffectsIntent` under that
ordering, which checks stop and sets its sticky bit at the linearization
point, then mirrors the existing signal bit before filesystem entry. Bridge
failure/local close first latch the appropriate exchange stop, release the
guard, then publish their existing detail. A protocol failure latches its
typed first stop directly and prevents a concurrent milestone/health commit
without waiting for the observation consumer to run. No nested reverse
exchange-to-signals lock acquisition is allowed.

The UI attempt's authoritative stopped/first-stop view comes from the exchange
guard. The first checked bridge detail remains separately retained by the
existing signals. A `bridge` tag whose detail is still arriving blocks all
work immediately; diagnostics wait for that detail or remain unknown rather
than inventing a protocol failure. The legacy first-cause and native failure
enums are unchanged. Its UI-specific snapshot path projects the new tagged
cause, not a fabricated `.closed` or `.unknown(.bridgeInvariant)`.

The bridge also checks this same guard at new host-request admission. It must
not rely solely on its own later-updated `status.closed` after a protocol stop
from MainActor. `requireEffectAdmission` is that UI admission checkpoint;
effects already admitted before stop remain subject to existing native
cancellation/deadline/close and may commit. A pump observing a shared stop
starts its existing coalesced close path; it publishes no new guest turn or
call. No UI stop waits for a MainActor notification to stop external-effect
admission.

The bridge exposes exactly two new construction/startup SPI seams, in addition
to its existing owned enable/close/status methods:

```swift
extension ExperimentalCapabilityValidator {
    @_spi(GuestUIV1) public static func prepareGuestUIV1(
        module: Data, configuration: ExperimentalCapabilityConfiguration
    ) throws -> ExperimentalCapabilityValidation
}
extension ExperimentalCapabilitySession {
    @_spi(GuestUIV1) public static func prepareOwnedGuestUIV1(
        module: Data, configuration: ExperimentalCapabilityConfiguration,
        policy: CapabilityPolicy, adapterGroup: OwnedCapabilityAdapterGroup,
        exchange: GuestUIExchangeV1
    ) throws -> ExperimentalCapabilityConstruction
    @_spi(GuestUIV1) public func startupGuestUIV1() async throws
}
```

The validation return type is the existing one-shot
`ExperimentalCapabilityValidation`; no extra validation worker or capacity
pool is created. The fixed startup name comes from this contract,
not an argument. Activation supplies the captured signed bytes, intersected
policy, existing owned group, and its already-counted exchange. The bridge
checks the exchange generation/liveness before construction/startup; this is
not artifact authority. UI-prepared sessions reject generic public
startup/invoke/readMemory/writeMemory/development-enable operations. Only
fixed UI SPI startup, internal event/wake composites, existing owned enable
with its absolute cutoff, and close/status remain usable on that owner. This
prevents a second path from skipping the shared turn guard after construction.

## Separate typed UI terminal classification

Keep `ExperimentalCapabilityFailure*`, native report/status/import codes,
`CapabilityColdStartTerminalCause`, and the existing capability-only recovery
classifier unchanged. New immutable UI diagnostics live in `MixerGuest`, as
listed above. In activation use
`public typealias CapabilityGuestUITerminalCause = GuestUIStopV1`; the new UI
snapshot carries that tag and the independently checked
`firstBridgeFailure: ExperimentalCapabilityFailure?` plus
`firstUIProtocolFailure: GuestUIProtocolTerminalV1?`. A bridge tag can be
visible before its detail arrives; this is a stopped owner with pending
diagnostics, not a fabricated bridge error or a new native failure code.

`CapabilityGuestUIActivationSnapshot` has exactly these observed fields:
`phase`, `candidateID`, `launchID`, `acceptedSequence`, `effectsMayHaveOpened`,
`terminalCause` (the UI tag), `firstBridgeFailure`, `firstUIProtocolFailure`,
`requiresReopen`, and `cleanupPending`, with the existing field types otherwise.
`CapabilityGuestUIRecoverySnapshot` has `activation` of that new type and the
existing bounded fields `requiresReopen`, `closed`, `busy`, `acceptedSequence`,
`downloading`, `staged`, `healthy`, `previousHealthy`, `retainedCandidates`,
and `incompleteAttempt`. It exposes no payload, file path, or executable token.

The checked UI call site constructs only the closed phase/code value:

| Trigger | Typed classification and action |
| --- | --- |
| UI-specific required-export failure from the additive validator | `validation / requiredExport`, only for the exact checked `.validation` / status1 / `.validation(.requiredDefinedExport)` / function-nil / offset0 tuple specified above. Reject download before staging; no attempt was executed, so no attempt-health or native-exit claim. Other full-module failures retain existing bridge validation classification. |
| Wrong startup numeric result, invalid header/ranges, changed immutable buffer, malformed/unsupported document, lowered revision, same-revision changed bytes | Exact `startup`, `event`, or `wake` phase plus the matching closed code; synchronously `recordProtocolFailure`, stop bridge admission, signal both fixed wake channels, publish no document and drain no calls from the invalid turn. |
| Nonzero/wrong-type event result or internal event encoding overflow | `event / eventResult` or `event / eventEncoding`; no replay. Ordinary busy/stale/closed input rejection is not a protocol terminal. |
| Nonmatching native document after a current claimed reconciliation, or impossible current presentation state | `presentation / presentationInvariant`. A foreign/stale claim or ordinary stop/replacement during apply is rejected/dropped, not a terminal for the new attempt. |
| Checked VM trap, fuel, native report, adapter, cancellation or deadline failure | Existing native/bridge/local domain; never reinterpret a message string as UI protocol. Native memory-copy bounds rejection is currently status3 / machine code `invalid_arguments`, checked as `.callerAPI(.invalidNativeArguments)` in read/write context. It is not a distinct out-of-bounds code. Retain that bridge classification; do not fabricate `memoryRange` from it. Only host-side numeric range/overlap preflight produces UI `memoryRange`. |

On first UI protocol stop the exchange guard atomically captures its sticky
intent bit. `beforeIntent` means no effects-intent commit has entered. The
UI-specific store branch clears the failed staged selection, records
`lastRecovery = "ui_protocol_before_effects"`, and may select an already
authorized retained healthy candidate only after the old ordinary frame,
presentation consumer's actual return, and concrete native retirement are
joined. A native fallback is otherwise requested. No UI protocol reason is
cast to `deterministicTrap`; this first slice does not increment the existing
trap-only quarantine counter for it. Factory file/lock activity may already
have happened; this is not a claim of zero host filesystem activity.

`intentEntered` includes a race during or after intent persistence even if
native enable has not returned. The UI-specific branch records
`lastRecovery = "ui_protocol_after_effects"`, preserves effect uncertainty,
closes presentation and native admission, and requires reopen/recovery. It
never selects another guest or claims rollback in this owner. These two new
local diagnostic strings are allowed bounded identifiers in the existing
state; they do not change its schema or overwrite old failure enum values.
The bridge catches `GuestUIProtocolFailureV1` before its generic native-error
path: record the typed UI failure, then use the ordinary coalesced stop path
without converting it into `ExperimentalCapabilityError`. A valid UI protocol
rejection does not imply poisoned native state or require native quarantine.
Actual native report/poison/exit-ack failures still use their existing rules.
Any checked native read/write/invoke rejection inside a fixed UI composite is
terminal for that composite/owner, including status3. The legacy generic
development API may keep ordinary status3 rejection nonterminal; that policy
does not let a signed fixed UI composite continue after a failed transfer.
An earlier bridge/local first-stop tag remains primary; a later UI reason may
be retained as secondary diagnostics but cannot replace it. No path earns a
milestone or health from a protocol failure.

## Bounded documents and events

Document delivery is **latest value**, not a history. Per owner retain one
validated pending document and at most one claimed document being applied on
MainActor. The existing displayed snapshot and the worker's last harvested
snapshot are separate fixed slots. Replacement drops only an unpresented
document. It never drops an event. No per-document Task/actor message is made.

Use **one fixed counted presentation-consumer Task per attempt**, created only
after the outer attempt permit, before producers can publish. It owns the one
`deliveryWake` reader and a weak presentation box. Across `reader.next()` it
retains neither the exchange, model, core, worker, attempt, nor session. A
static MainActor helper resolves the weak model and applies at most one
`GuestUIPresentationClaimV1` without suspension; its strong model/frame locals
end before the helper returns to the consumer's next wait. There is no Task
per frame, replacement delivery job, or self-rescheduling actor loop.

The consumer never marks itself reusable. Its one Task handle stays counted
in activation until actual `await task.value` completes during close/fallback;
only then can the next attempt allocate a presentation consumer. This bounds
even the logical task tail and rules out an old task retaining a frame after
a replacement starts. Every changed pending slot signals the coalesced wake;
an update during apply leaves pending true for the next helper turn. A dead
weak model consumes hints without loading a frame and earns no receipt.
Stop clears pending frames, records terminal input, signals delivery, then
finishes `deliveryWake`; the final helper retires any surviving model before
the consumer returns. A stalled MainActor keeps the task counted and close
pending. Record maximum retained document bytes/objects and live consumer
count; these logical bounds do not claim a process RSS reservation.

Events have capacity **one accepted event, including its running turn and
unconsumed result** per owner. The private renderer callback first routes through the current
`MixerUIHost` snapshot. A synchronous admission check then requires current
attempt generation, current displayed node generation/revision, effects
confirmed, and displayed revision equal to last harvested guest revision.
It also requires no event or guest turn in flight. Reject `busy`, `stale`, or
`closed` before capturing event data, allocating a Task, or advancing sequence.
Disabled/unbound/invalid events keep existing UI routing errors.

The claim to begin **any** guest turn and event admission use the same short
control lock. If event admission wins, the next guest turn is that event; an
autonomous wake cannot overtake it. If a wake already claimed the turn, input
returns busy until harvest completes. No lock spans C, decode, MainActor,
publishing, or native adapter work. Native controls are locally noninteractive
while the sole event is outstanding or displayed revision lags; this does not
rewrite the guest document. Busy taps are rejected before acceptance, not
silently queued or coalesced.

Every accepted sequence is invoked at most once and completes as `delivered`
or explicit `terminal` with effect uncertainty if a turn already began. Do not
automatically retry across close, fallback, suspension, restart, or a KV error.
There is one bounded event-result slot/notification, keyed by attempt
generation and sequence. Retain the slot until the MainActor model consumes
its result, or final close retires it into the bounded terminal diagnostic;
a new event cannot overwrite an unconsumed result. The guest event's zero return acknowledges delivery,
not KV completion or durable application state. Terminally cancelled accepted
events are observable diagnostics; they do not pretend delivery succeeded.

## Ownership, terminal races, and MainActor

The exact strong-reference graph is:

```text
facade -> close core -> worker / concrete attempt -> bridge session -> NativeExitOwner
facade -> MainActor GuestUIPresentation -> GuestUIExchangeV1
close core -> fixed presentation-consumer Task -> wake reader + weak-model box
concrete attempt -> CapabilityAttemptSignals -> GuestUIExchangeV1
NativeExitOwner -> GuestUIExchangeV1 -> two data-only wake shared states
presentation platform probe -> weak presentation reference
```

The weak-model box refers weakly to the model. Wake readers retain only their
queue state. Their parked continuations retain the known consumer task but no
owner/model/exchange capture; static helper locals are released before the
next wait. `GuestUIExchangeV1` points to no owner, model, signals, worker,
session, source, observer, or callback. There is no input-port wrapper with a
hidden owner reference. The same exchange instance is the sole arbiter for
both native input and every bridge guest turn. No SDK-to-activation dependency
or bridge-to-SwiftUI dependency exists. Vanished presentation consumes hints
without creating authority; the producer's latest fixed slot remains bounded
until stop clears it.

Each attempt gets a native session generation from the existing selection /
signals lifetime. Frame, event, and presentation metadata are scoped to that
generation plus candidate/launch identity internally. Node generation alone
is insufficient: reconciler generations can restart in a later session.
Generation counters cannot wrap. An old frame, event result, display probe,
or weak delivery callback is rejected even if its revision/node ID equals a
new attempt's values.
Every opaque claim/ticket also contains a private issuer identity object,
created by its exchange and compared by reference identity inside that guard.
The issuer has no references back to exchange or owners. This scopes receipts
to the exact exchange even if a reopened store restarts its numeric generation;
the issuer never crosses the guest wire and is not a native pointer API.
No stale issuer/generation/claim can set stop, replace a live frame, or earn a
receipt in another exchange. Expected stop/stale races return the closed
local rejection/nil, bypassing both protocol and native-quarantine paths.

The model binds a new exchange only after the previous presentation consumer
has actually returned. Binding invalidates the previous private probe,
discards the old `MixerUIHost`, clears the internal displayed state, and creates
a fresh host on the first new frame. This allows the new guest's revision to
restart at 1 without defeating the existing reconciler's increasing-revision
rule. Every private native action closure captures its exact exchange/issuer
and a weak model; the model rejects it unless that exchange is still its
current binding. It must not rebuild an old callback's envelope using a new
host merely because node ID/revision match. Captured exchange objects are
data-only and retain no old session or owner.

Close and bridge terminal notification synchronously latch UI/input admission
closed **before** native close or async actor work. Clear unclaimed documents,
mark any accepted event terminal, detach presentation health authority, and
signal/finish the fixed delivery channel. Reuse the existing one close task
and native-close job; do not create one cleanup task per UI callback. The
existing close task additionally joins the fixed presentation consumer's
actual return before store/facade close reports completion or a replacement
attempt's UI consumer is admitted.

MainActor apply has a short claim/complete protocol. It claims a current frame
under the mailbox lock, releases the lock, updates `MixerUIHost`, then completes
under the lock. If close wins before claim, no update occurs. If apply claimed
first, that update may complete while close races; the postcheck suppresses
all health/input acknowledgment and retires it in the same MainActor turn.
Do not hold a lock across `@Published` reconciliation. A transient already
admitted presentation is possible until MainActor processes stop. `close()`
joins this bounded presentation-retirement tail before returning, while the
existing `cleanupPending` still reflects independently retained native exits.
If MainActor is stalled, do not claim presentation retirement completed.

Snapshot inspection remains observational. Native-exit acknowledgment still
requires actual/no-I/O adapter cleanup; a frame, event return, presentation
receipt, or UI teardown never substitutes for it. Do not alter native pool
quarantine, closing-handle, cancellation, deadline, or first-terminal rules.

## Native first-screen and health

The new facade exposes a read-only MainActor presentation model and a bound
`MixerGuestScreen` platform view/controller wrapper, with internal construction
of `MixerUIHost`/`MixerNativeView` and internal action forwarding. It has no
public `reportMilestone`, arbitrary `onAction`, document setter, or fabricated
presentation-ack initializer. New UI mode requires exactly the installed
milestone set `{feature_started, first_screen}` for this slice.
This profile permits one active native screen attachment per presentation
model. The private MainActor attachment check occurs before constructing a
hosting controller/probe. A second simultaneous attachment is a typed
`presentationInvariant` failure with normal UI stop/fallback handling; it
does not allocate another engine host, probe, consumer, or attachment queue.
Detach releases the current attachment by identity and invalidates its probe.
This slice does not qualify multiwindow presentation.

After valid startup and confirmed effects enable, the private coordinator
records `feature_started`. Offer no interactive frame before that confirmation.
Present the latest validated snapshot on MainActor. A returned `start()`, a
decoded document, `host.update`, SwiftUI `onAppear`, an offscreen `ImageRenderer`,
or a test hook must not record `first_screen`.

For iOS, the bound wrapper owns a `UIHostingController` containing the actual
native renderer. Its private presentation probe requires the same-generation
revision's root in a visible, attached `UIWindow`, active foreground scene,
completed native appearance/layout with nonempty bounds, and a committed
Core Animation transaction. A single bounded `CADisplayLink` probe waits across
a subsequent display interval, then rechecks attachment, scene, revision, and
stop state before sending its one internal receipt. Its target proxy is weak;
it is invalidated on detach/stop and cannot retain an owner. Changed revision
before acknowledgment restarts the probe for the latest displayed revision.

For macOS host evidence, the corresponding wrapper owns the `NSHostingView` /
controller in a visible `NSWindow`; layout and actual native display must
complete while the same revision remains current. A detached/offscreen image
does not earn a receipt. Platform probes describe **visible native layout and
display-cycle observation**, not a promise of compositor/pixel delivery or
human perception. Screenshot/accessibility UI-test evidence separately checks
that the intended controls and state were actually rendered.

The receipt is checked on MainActor and again against live attempt identity
before the existing store milestone call. Hold one pending receipt bit while
the existing coordinator ordinary lane is busy; do not fan out Tasks or lose a
valid receipt on `busy`. A newer document does not revoke an already earned
same-attempt native display observation; a stopped/replaced attempt does.
Stop wins before milestone/health commit entry; a
commit already entered follows existing durable uncertainty rules. The
existing observation interval and signal checks still govern `commitHealth`.
No screen receipt, alone, marks a candidate healthy.

## Independent fixture and end-to-end behavior

Author `GuestUIProgramV1` from the official Wasm encoding, independently of VM
fixture builders. Hand-authored deterministic bytes / a small original encoder
are acceptable; do not copy or generate fixture source from a competitor or
the runtime implementation. Keep an independently reviewed fixture manifest
with SHA-256 and the deliberate instruction/import inventory. The guest is a
small bytecode application, **not Swift source compiled to Wasm**.

1. Module defines sufficient bounded memory, header, initial document revision
   1 (`Ready`, button `save` bound to `sample.save`), exact expected event packet,
   KV argument bytes, and completion output space. Startup makes no KV call.
2. Only a signed manifest/assignment and existing private download/store path
   introduce it. Independent test signing keys live in test-only fixtures;
   production keys never enter source or build workers.
3. The native window displays the initial document. Its actual button event
   creates sequence 1. The guest checks the packet and invokes the existing
   `storage_put` import with namespace `entries`, key `sample`, and canonical
   base64 for sample bytes. Installed and signed grants must both allow it.
4. Guest emits revision 2 (`Saving sample`). The scheduler performs the actual
   app-private KV operation in a temporary test container through the existing
   concrete adapter. The existing native ticket/exit accounting remains live.
5. Ready wake polls the exact originating request, checks a typed successful
   storage-put completion with `committed: true`, and emits revision 3
   (`Saved sample`). Failure/denial emits a distinct failure document; malformed
   or wrong-operation completion never renders success. The fixture should
   compare the closed expected completion bytes or implement an independent
   bounded decoder; merely checking poll status or nonempty output is invalid.
6. Host verifies native displayed revision 3 and reads the same app-private KV
   container through the adapter in the test harness. The guest completion,
   displayed document, persisted value, and actual native exit are distinct
   assertions. A denied-grant variant asserts no commit and no success screen.

## Proposed file ownership after freeze

Root freezes the new contract/header hashes and integration order before any
implementation lane edits another lane's active files.

| Lane | Exclusive implementation ownership | Dependency |
| --- | --- | --- |
| Root/contracts | New `contracts/guest-ui-event-v1.json`; installed marker policy; new facade wiring; changes to `capability-activation/Sources/MixerCapabilityActivation/{CapabilityColdStartWorker,CapabilityColdStartControl,CapabilityConcreteAttempt,CapabilityAttemptSignals,CapabilityRecoveryStore}.swift`; new UI diagnostic/facade files and fixed consumer ownership; root status/gate records | Review this design; frozen candidate1 coordinator |
| VM | New `vm/include/mixer_vm_guest_ui.h`; additive C validator implementation; validated-module signature helper; `vm/tests/experimental_guest_ui_validation.rs` | Frozen signatures/status/preflight contract; preserve old header |
| Swift bridge | New shim import for the separate header; `experimental-capability-runtime/.../{Native,Ownership,Session,Validation}.swift` plus new `GuestUITurns.swift` (fixed header parsing and turn integration, no second mailbox); bounded native turns / UI harvesting; bridge tests | Frozen C validator and exact SDK exchange SPI |
| SDK/native UI | New `GuestUIExchangeV1.swift`, `GuestUIWakeV1.swift`, `GuestUIProtocolV1.swift`, and bounded event codec under `sdk/Sources/MixerGuest`; new `capability-activation/.../CapabilityGuestUIApple.swift` and private presentation-model file in that same target; narrow SDK adapter additions only if required; SDK/native-host tests | Frozen event bytes and exact exchange SPI; coordinate these new activation files with root |
| Independent verification | Independently authored Wasm guest and negative fixtures; signed integration tests; native host window/UI automation harness; preservation/receipt tooling | Reviewed implementation tree, no production edits |

`capability-activation/Package.swift` adds only needed `MixerGuest`, `MixerUI`,
and `MixerApple` product dependencies; avoid a package cycle.
The SDK native UI target must not depend on capability-activation or the
experimental runtime. The bound wrapper and presentation model live in the
same activation target as its private presentation consumer and attempt
identity. The shared data-only exchange resides in `MixerGuest`; its fixed SPI
does not expose callback/health injection APIs to public presentation users.
The bridge may depend on value-only UI/guest codecs; it never imports SwiftUI.

## Executable acceptance matrix

These are required tests to implement and run, not results claimed here.
Record exact command, tool version, captured source tree/digest, stdout/stderr,
fixture hash, configuration, scope, and accountable reviewer with each receipt.
Use existing scratch/build outputs where possible; do not consume several GiB
for speculative full builds. Phones remain disconnected; no new device runs.

| Gate / executable | Required assertions |
| --- | --- |
| VM Rust `cargo test --features experimental-capability-native --test experimental_guest_ui_validation` | Valid independently authored module; missing/imported/wrong-kind/wrong-signature startup/event/ready; unknown import; malformed module; limits and exact-zero-page fail-closed behavior; no session/instance/mailbox allocation; new C null/wrap/unaligned/alias preflight; legacy symbols/tests unchanged. Exact feature command must follow the implemented feature wiring. |
| SDK `swift test --package-path sdk --filter GuestUI` | Strict event positive/negative corpus; Unicode IDs, escaping, UInt64 boundaries, duplicate/unknown/numeric-coercion/trailing/oversize failures; profile subset; equal-revision bytes and invalid document cases; current node routing; one exchange lock arbitrates event/wake/stop/intent; offer/result-consume/lag changes signal control refresh without a new frame; each wake issues one reader, rejects a second waiter, coalesces signals, preserves final hint on finish, and resumes outside locks. |
| Bridge `swift test --package-path experimental-capability-runtime --filter GuestUI` with the selected native archive path | Exact unchanged required-export report tuple maps only in UI validation context; other module/native errors retain domain, malformed reports quarantine; memory-copy status3 stays bridge failure and stops fixed composites; startup/header/document atomic snapshot; OOB/overlap/wrap/changed immutable fields; event write+invoke cannot be split by wake; harvest after every actual ready wake; invalid UI prevents that turn's pending capability I/O; same revision mutation and lowering fail closed; bounded payload/source/job counters. |
| Signed integration `swift test --package-path capability-activation --filter GuestUI` with the selected native archive path | Only signed download selects code; every incomplete/wrong marker pair and reserved-startup combination rejects both wrong facades before store admission; absence never auto-enables UI; foreign artifact/assignment/runtime/grants reject; failed UI validation does not stage/enable; typed pre/post-intent UI failure paths preserve native failure domain, appropriate fallback/reopen, and no trap-counter coercion; first valid native screen plus full observation can earn health; absent receipt never earns health; no public host/setter/executable/artifact/export/milestone injection path. |
| Deterministic race tests in bridge/activation suites | Hold the worker before wake claim, during native event turn, after harvest, before/after MainActor frame claim, before/after effects confirmation, and before milestone/health commit. Assert every close ordering above; stale generation/revision/node callbacks never execute; event admission before wake wins ordering; wake already claimed returns busy; no sequence wrap; one accepted event through result consumption; no acceptance replay after restart; one fixed consumer and one pending frame under flooding; stall the consumer immediately before logical return and assert replacement remains unadmitted until actual Task.value completes; no owner/model/exchange capture survives its next wait. |
| Mac native window integration harness, with public signed facade | Launch an actual visible `NSWindow`, query native status/button and capture screenshot. Native click -> exact guest event -> actual temp KV commit -> autonomous wake -> displayed `Saved sample`; assert private native presentation receipt was earned. Hidden/detached/zero-size windows and offscreen `ImageRenderer` never earn it. This is Mac native host evidence only. |
| iOS simulator UI harness when separately provisioned within disk budget | Foreground visible native host, real accessibility/button interaction, screenshot and persisted-value checks; background/detach before display probe cannot earn receipt; close/view replacement suppresses stale probe. Simulator output is not physical iOS evidence. If not run, mark pending. |
| Preservation script + default package/VM focused regression | Exact hashes of every existing `contracts/*.json`, old VM C headers, and existing signed/capability fixture bytes match the inspection baseline; default imports/profile behavior and capability-only facade remain unchanged. Verify only additive symbols/new identities opt in. |

UI no-op repeated wakes, continuous new revisions, a stalled MainActor, a
renderer that disappears, and close while native KV cleanup is withheld must
be in the matrix. The latter must preserve `cleanupPending`/capacity rather
than treating a stopped UI as native exit. Check retained payload/owner counts
after actual drain and after quarantined shutdown separately.

Full Swift guest compilation and runtime semantics, complete UI inventory,
Android Compose/native event delivery, physical iOS/Android accessibility and
lifecycle/performance, memory/RSS budgets, immutable published packages in a
separate FieldLog repository, real FieldLog use, signing/store/customer review,
and all GA gates remain explicitly pending. Local signed fixtures and host
windows qualify only this bounded development integration.
