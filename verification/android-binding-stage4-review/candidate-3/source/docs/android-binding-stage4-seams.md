# Stage 4: real Swift/C Android binding seams

Status: v2 proposed for root coordination, 2026-10-23. This is a bounded next-lane
proposal, not implementation acceptance. The binding authority is
`docs/android-signed-ui-binding-contract.md`, accepted in
`verification/android-binding-contract-acceptance.json`. Product scope remains
`mixer-product-plan.md`; Android signed UI stays unsupported.

The v1 proposal, matrix, collector and original receipt are preserved verbatim in
`verification/android-binding-stage4-contract/v1/`. This v2 narrows stage 4 to a
standalone host binding and type-separated host evidence.

The frozen prerequisites are C facade/entry/progress checkpoint `d6505ac` and
stage 2 owner source tree
`8d540e60a53c40267e68de822cee181e22f92b69e61fe023d03e05ad6f247f47`.
Stage 2 evidence is `verification/common-presentation-lifetime/final-1/receipt.json`,
`portable-1/receipt.json`, and
`verification/common-presentation-lifetime-review/review.json`. Current source is
checked against those receipts by this proposal's collector. The collector proves
input binding and matrix completeness only; it executes no proposed binding.

## 1. Bounded deliverable and file ownership

One implementation lane owns these **new** production files only after root
accepts their seams and assigns the paths:

| New path under `capability-activation/Sources/MixerCapabilityActivation/` | Responsibility |
| --- | --- |
| `CapabilityGuestUIAndroidBinding.swift` | Standalone resource-free facade shell, its own setup guard/final obligation gate, bind/final-close state machine and checked moves. |
| `CapabilityGuestUIAndroidRegistry.swift` | Process-lifetime 16 facade records, 16 endpoint records, one admission mutex, checked IDs, lookup/publication/removal. |
| `CapabilityGuestUIAndroidLifetime.swift` | Sole pre-bind Task, bind-or-close gate, exact rendezvous, native authoritative join and sealed endpoint evidence. |
| `CapabilityGuestUIAndroidResources.swift` | Reservation-owned reconciler/exchange/ticket/render state, checked transient aliases, synchronous leased inner helpers and sealed cleanup evidence. |
| `CapabilityGuestUIAndroidProgress.swift` | Sixteen permanent progress cells and fixed C exports `mxuit_drain`, `mxuit_complete`, `mxuit_progress`. |

The lane also owns a new `native/android/signed-guest-ui/binding/include/` header
and module map importing the **unchanged** transport header and declaring the
three already-frozen `mxis_*` methods. The stage 4 lane may not edit transport
sources/tests, existing runtime/control/worker files, installed modes, profiles,
JNI/Java, renderer or packet code. Root freezes the shared seam in section 2, then explicitly delegates that one
common file plus all five new files together to the same implementation lane.
No concurrent shared-file editing is permitted.

Independently authored host fixtures, harness and command runner belong to a new
`verification/android-binding-stage4/` directory. They compile unchanged new
production Swift files, the exact C `transport.c`, real `MixerGuest`/`MixerUI`, and
root's common lifetime changes together. No replacement source, fake common
lifetime, stubbed Task join, generated fixture or imported implementation is
allowed. Any general-purpose dependency must be recorded in `THIRD_PARTY.yml`;
none is required by this proposal.

The normal package gets no new dependency or supported route in stage 4. The
harness compiles the actual production files and common source with two real C
modules available: `CMixerUITransport` (unchanged transport plus fixed binding
header) and `CMixerUIAndroidHostBridge` (fixed host-native implementation). Every
new stage 4 Swift declaration and the added concrete common backend use:

```swift
#if canImport(CMixerUITransport) && canImport(CMixerUIAndroidHostBridge)
import CMixerUITransport
import CMixerUIAndroidHostBridge
// Stage 4 declarations below.
#endif
```

The host bridge module is supplied only by the verification build's explicit
module map and exact fixed native object. Its `mxis_*` functions actually own and
clear the bounded host fixture state; no setter/driver/protocol/closure is injected
into production code. Normal Apple and portable builds lack that module, retain
the frozen paths and allocate no Android state. Supplying a module does not enable
a public runtime/profile. A `-D` flag, caller Boolean or caller scope enum is never
a preparation or evidence input. Android cross-compilation of this exact host
slice may supply the same declarations and fixed fixture object; its artifacts
remain explicitly host-harness-scoped and prove no JNI/Looper execution.

## 2. Exact shared seam and standalone entry points

The existing common lifetime is an Apple implementation: its receipt has only a
`fileprivate init(apple:...)`; facade cleanup construction is private; `finish`
awaits the actual optional Task and then weakly calls the Apple retirement
protocol returning `Bool`. Its concrete `CapabilityGuestUIPresentationBinding`
is `@MainActor` on Apple, and `CapabilityPreparedPresentation` stores exactly that
type. A new Android binding cannot be passed to that guard on the host.

Stage 4 therefore uses a **standalone private Android binding and its own setup
and final gate**. It consumes a real `CapabilityAttemptReservation` and the real
common lifetime/permit cells. It adds no activation coordinator, worker, store or
health owner. Existing signed-core/Prepared/facade integration is deferred to
stage 6. Do not edit `CapabilityPreparedPresentation.swift`,
`CapabilityGuestUIPresentation.swift`, `CapabilityColdStartControl.swift`,
`CapabilityColdStartRuntime.swift` or `CapabilityColdStartWorker.swift` for stage 4.
The new binding does not conform to the Apple retirement protocol.

Only `CapabilityGuestUIPresentationLifetime.swift` needs a shared source change.
Root freezes its contract and delegates that file to the same newfile lane. Add a closed concrete backend case under the guard above. There is no
arbitrary backend protocol and no `.androidNative` case/factory in stage 4. The
existing Apple initializer selects the Apple case. Android construction consumes
the sealed capsule below and selects the host case internally. Keep the existing
common receipt/facade-receipt constructors unchanged and inaccessible; host uses
separate receipt types. All signatures below are proposed declarations with
implementation bodies omitted, not a compilation receipt.

### 2.1 Android lifetime source: capsule and native join

`CapabilityGuestUIAndroidLifetime.swift` owns these declarations. All initializers
marked `fileprivate` are callable only inside that exact trusted source file;
`@testable` clients cannot construct the values.

```swift
struct CapabilityAndroidHostLifetimeKey: Sendable, Equatable {
    let facade: UInt64
    let lifetime: CapabilityPresentationLifetimeID
    let endpoint: UInt64
    fileprivate init(facade: UInt64,
                     lifetime: CapabilityPresentationLifetimeID,
                     endpoint: UInt64)
}
final class CapabilityAndroidHostLifetimeCapsule: @unchecked Sendable {
    fileprivate init(key: CapabilityAndroidHostLifetimeKey,
                     task: Task<Void, Never>,
                     control: CapabilityAndroidLifetimeControl)
    func takeForCommonLifetime() -> CapabilityAndroidHostLifetimeStart?
}
struct CapabilityAndroidHostLifetimeStart: Sendable {
    let key: CapabilityAndroidHostLifetimeKey
    let task: Task<Void, Never>
    let control: CapabilityAndroidLifetimeControl
    fileprivate init(key: CapabilityAndroidHostLifetimeKey,
                     task: Task<Void, Never>,
                     control: CapabilityAndroidLifetimeControl)
}
final class CapabilityAndroidLifetimeControl: @unchecked Sendable {
    // Private constructor; a fixed spawn method inside this class consumes the
    // registry's sealed acquired-endpoint token. It accepts no caller Task.
    func requestStop(_ cause: CapabilityAttemptLocalStop)
    func bind(_ exchange: GuestUIExchangeV1) throws
    func joinNative(after returned: CapabilityAndroidHostTaskReturnEvidence) async
        -> CapabilityAndroidHostNativeJoinResult
}
enum CapabilityAndroidHostNativeJoinResult: Sendable, Equatable {
    case retired(CapabilityAndroidHostEndpointRetirementEvidence)
    case quarantined(CapabilityAndroidHostFailure)
}
struct CapabilityAndroidHostEndpointRetirementEvidence: Sendable, Equatable {
    let key: CapabilityAndroidHostLifetimeKey
    let callbackFence: UInt64
    let uiEntryFence: UInt64
    let facadeCleanup: CapabilityAndroidHostFacadeCleanupEvidence?
    fileprivate init(key: CapabilityAndroidHostLifetimeKey,
                     callbackFence: UInt64, uiEntryFence: UInt64,
                     facadeCleanup: CapabilityAndroidHostFacadeCleanupEvidence?)
}
```

The capsule's constructor is not a general Task-attachment seam. The fixed
registry/lifetime source calls it only after real C endpoint acquisition, exact
record publication and creation of its one nonthrowing pre-bind Task. No caller
can supply a Task, control, native outcome or scope through a factory. `take`
moves its one actual Task/control tuple once; a second take returns nil. Capsule
abandonment quarantines the same obligation/record through scalar stop state and
creates no cleanup Task. The capsule/start/control contain no strong resources.

`joinNative(after:)` checks all three identities, its terminal outcome and its
one-shot join state; only that method calls actual `mxuit_consumer_joined` and
reclaim, using section 4's progress algorithm. Its evidence constructor is reached
only after successful real C reclaim. There is no joined/cleaned Boolean input.
A copied valid task-return evidence cannot create a second native joiner.

### 2.2 Common lifetime source: actual Task join, shared permit, disjoint result

Root adds these host-only declarations in the common lifetime file, under the
same two-module guard. Constructor and permit moves remain in that file.

```swift
struct CapabilityAndroidHostTaskReturnEvidence: Sendable, Equatable {
    let key: CapabilityAndroidHostLifetimeKey
    fileprivate init(key: CapabilityAndroidHostLifetimeKey)
}
struct CapabilityAndroidHostFacadeCleanupReceipt: Sendable, Equatable {
    let facade: UInt64
    let cleanupSerial: UInt64
    let finalEntrySerial: UInt64
    let bridgeSlotGeneration: UInt64
    // Private init; fileprivate validator consumes only sealed host evidence.
    fileprivate static func validate(
        _ evidence: CapabilityAndroidHostFacadeCleanupEvidence,
        for key: CapabilityAndroidHostLifetimeKey
    ) -> CapabilityAndroidHostFacadeCleanupReceipt?
}
struct CapabilityAndroidHostLifetimeReceipt: Sendable, Equatable {
    let key: CapabilityAndroidHostLifetimeKey
    let taskJoin: CapabilityPresentationTaskJoin // Always .joined.
    let facadeCleanup: CapabilityAndroidHostFacadeCleanupReceipt?
    // Private init; fileprivate validator requires exact actual-Task and C proof.
    fileprivate static func validate(
        taskReturn: CapabilityAndroidHostTaskReturnEvidence,
        native: CapabilityAndroidHostEndpointRetirementEvidence
    ) -> CapabilityAndroidHostLifetimeReceipt?
}
enum CapabilityAndroidHostFinishResult: Sendable, Equatable {
    case retired(CapabilityAndroidHostLifetimeReceipt)
    case quarantined(CapabilityAndroidHostFailure)
}
enum CapabilityAndroidHostJoinStatus: Sendable, Equatable {
    case pending
    case finished(CapabilityAndroidHostFinishResult)
    case invariant(CapabilityPresentationInvariant)
}
final class CapabilityAndroidHostInstallation: @unchecked Sendable {
    let key: CapabilityAndroidHostLifetimeKey
    fileprivate init(lifetime: CapabilityGuestUIPresentationLifetime,
                     permit: CapabilityPresentationJoinPermit)
    func move() -> CapabilityAndroidHostInstallation?
    func bind(_ exchange: GuestUIExchangeV1) throws
    func requestStop(_ cause: CapabilityAttemptLocalStop)
    func finish() async -> CapabilityAndroidHostJoinStatus
    var status: CapabilityAndroidHostJoinStatus { get }
}
extension CapabilityGuestUIPresentationLifetime {
    static func consumeAndroidHost(
        _ capsule: CapabilityAndroidHostLifetimeCapsule
    ) throws -> CapabilityAndroidHostInstallation
    fileprivate func finishAndroidHost(
        using permit: CapabilityPresentationJoinPermit
    ) async -> CapabilityAndroidHostJoinStatus
}
```

`consumeAndroidHost` consumes a real capsule once, privately constructs the closed
backend, and issues the **existing** common `CapabilityPresentationJoinPermit`.
The new wrapper uses the existing permit's `move/begin/consume` cells; it does not
create another join-authority implementation. The wrapper retains a private,
resource-free lifetime readback even after its permit moves, so old wrappers can
read the immutable exact result but cannot join again. It exposes neither a raw
permit nor a lifetime property nor any conversion to common installation/status.

`finishAndroidHost` admits the moved permit once, requests stop and performs
**actual `await task.value`**. Only the statement following that await constructs
the file-private task-return evidence. It then calls the fixed concrete
`joinNative(after:)`, validates exact identities/evidence, consumes the permit and
publishes its host-only immutable result. Android never emits `noTaskCreated`.

The existing common `installation()`, `attach(_:exchange:)`, `isBound(to:)`,
`finish(using:)` and `status` must explicitly reject/return false or
`.invariant(.invalidState)` for the host backend **before** any Apple permit or
receipt construction; they cannot translate host completion into
`CapabilityPresentationJoinStatus`. The private constructor of the existing
`CapabilityPresentationInstallation` also asserts an Apple backend. Thus a host
installation is a different Swift type and cannot be injected into
`CapabilityPresentationBindingGate.accept`, observation installation or any
Apple `isRetired => obligation.retire()` path. No Apple gate source change is
required. Compile-negative checks cover every attempted injection/conversion,
and ordinary/@testable negative compilation covers attempts to extract a raw
lifetime/permit or invoke private host finish. Root source review verifies the
mandatory rejection guards; no production test-only readback or success flag is
added merely to exercise otherwise inaccessible entry points.

No stage 4 type can construct `CapabilityFacadeCleanupReceipt` or
`CapabilityPresentationLifetimeReceipt`. Future native JNI evidence will use
separate native types/factories reviewed in stage 5/6; no host-to-native conversion
or caller-supplied enum scope exists. The literal host scope in receipts/diagnostics
is derived from these distinct types and the linked fixed host object.

### 2.3 Resource source: exact facade-cleanup evidence

`CapabilityGuestUIAndroidResources.swift` owns this sealed scalar evidence and its
constructor. The helper can issue it only after section 5's actual operations.

```swift
struct CapabilityAndroidHostFacadeCleanupEvidence: Sendable, Equatable {
    let key: CapabilityAndroidHostLifetimeKey
    let cleanupSerial: UInt64
    let finalEntrySerial: UInt64
    let bridgeSlotGeneration: UInt64
    let clearedExchangeGeneration: UInt64? // nil only for never-bound pre-bind.
    let clearedResourceStageRevision: UInt64
    fileprivate init(key: CapabilityAndroidHostLifetimeKey,
                     cleanupSerial: UInt64, finalEntrySerial: UInt64,
                     bridgeSlotGeneration: UInt64,
                     clearedExchangeGeneration: UInt64?,
                     clearedResourceStageRevision: UInt64)
}
```

The fixed helper/native-slot implementation must retain its exact scalar
postcondition in the permanent facade/bridge state before constructing this
value. Its arguments are not caller inputs to a receipt factory. Native state
still present or missing after publication produces failure and no evidence.

### 2.4 New binding source: standalone setup/final obligation owner

`CapabilityGuestUIAndroidBinding.swift` owns these concrete types. This is the
only stage 4 preparation entry and it is internal/host-scoped under the guard.

```swift
final class CapabilityGuestUIAndroidBinding: @unchecked Sendable {
    // Private allocator in this type; no caller-supplied driver or scope.
    static func prepareHost(reservation: CapabilityAttemptReservation) async throws
        -> CapabilityAndroidHostPreparedPresentation
    func bindHost(_ exchange: GuestUIExchangeV1) async throws
        -> CapabilityAndroidHostInstallation
    func requestFinalClose(_ cause: CapabilityAttemptLocalStop)
    func finishFinalClose(using installation: CapabilityAndroidHostInstallation?) async
        -> CapabilityAndroidHostFinalCloseStatus
    var finalStatus: CapabilityAndroidHostFinalCloseStatus { get }
}
final class CapabilityAndroidHostPreparedPresentation: @unchecked Sendable {
    let binding: CapabilityGuestUIAndroidBinding
    fileprivate init(binding: CapabilityGuestUIAndroidBinding,
                     reservation: CapabilityAttemptReservation,
                     initial: CapabilityAndroidHostInstallation)
    func transferToBinding() throws
    func cleanupAfterFailure() async -> CapabilityAndroidHostFinalCloseStatus
}
struct CapabilityAndroidHostFinalReceipt: Sendable, Equatable {
    let facade: UInt64
    let lastLifetime: CapabilityAndroidHostLifetimeReceipt
    let facadeCleanup: CapabilityAndroidHostFacadeCleanupReceipt
    let facadeReturnFence: UInt64
    fileprivate init(facade: UInt64,
                     lastLifetime: CapabilityAndroidHostLifetimeReceipt,
                     facadeCleanup: CapabilityAndroidHostFacadeCleanupReceipt,
                     facadeReturnFence: UInt64) // After real retire() returns.
}
enum CapabilityAndroidHostFailureCode: Sendable, Equatable {
    case invalidState, unavailable, transportIO, retireFailed
    case missingPublishedResources, identityExhausted, setupFailed, cleanupPending
}
struct CapabilityAndroidHostFailure: Sendable, Equatable {
    let key: CapabilityAndroidHostLifetimeKey? // nil only before endpoint issue.
    let code: CapabilityAndroidHostFailureCode
    // Internal diagnostic construction cannot authorize successful retirement.
    init(key: CapabilityAndroidHostLifetimeKey?, code: CapabilityAndroidHostFailureCode)
}
enum CapabilityAndroidHostFinalCloseStatus: Sendable, Equatable {
    case pending
    case finished(CapabilityAndroidHostFinalReceipt)
    case quarantined(CapabilityAndroidHostFailure)
    case invariant(CapabilityPresentationInvariant)
}
```

`prepareHost` issues the real one-shot presentation obligation before any facade,
resources or C endpoint. It is called with an actual acquired reservation; tests
must also call its normal `beginClosing()` and account for any other obligations.
Its own setup guard retains the initial host installation until
`transferToBinding()` moves it to this binding's final gate exactly once. A throw
before return explicitly awaits that same guard's cleanup; abandonment quarantines.
There is no transfer to an existing signed core/Prepared object in this stage.

After transfer, `bindHost` moves the initial/current host installation to its
caller and installs the real exchange under the bind/close gate. Its final gate
retains only resource-free current lifetime readback. A failed bind stops the exact
exchange and awaits the same local installation before throwing. Host endpoint replacement requires the prior exact host finish to have returned.
Actual signed fallback must additionally join concrete attempt retirement; that
integration remains stage 6 work. The stage 4 standalone factory starts no VM or
concrete attempt and cannot assert that retirement on a real signed runtime. A
real adapter obligation/destructor may be held to test independent reservation
accounting, without claiming it is an integrated signed-attempt fallback.

`finishFinalClose(using:)` accepts a moved matching host installation if its caller
still owns one, otherwise consumes the final gate's remaining initial installation
or reads the exact finished current result. Nil with an unfinished externally owned
installation returns `.invariant(.wrongJoinOwner)` and creates no joiner.
Concurrent reentry while the one final owner is in flight returns `.pending`. One final-owner move
executes section 6 and retires the real obligation **after** exact facade cleanup,
actual Task/native joins, final facade fences and zero aliases. It publishes final
completion only after the actual resource destructor returns. This gate owns no
store/core/coordinator and spawns no additional Task. The current Apple gate is
never involved.

### 2.5 Fixed C symbols and future integration boundary

The C ABI remains exactly the frozen header. The production progress source
exports the three functions below; the fixed host object supplies `mxis_apply`,
`mxis_interaction`, `mxis_retire` and the fixed platform register/pump implementation.
No product hook receives a function pointer or arbitrary context.

```swift
@_cdecl("mxuit_drain")
func capabilityAndroidDrain(_ owner: UInt64, _ waiter: UInt64, _ kind: UInt32) -> Int32
@_cdecl("mxuit_complete")
func capabilityAndroidComplete(_ owner: UInt64, _ waiter: UInt64,
                               _ kind: UInt32, _ result: Int32)
@_cdecl("mxuit_progress")
func capabilityAndroidProgress(_ callbackFence: UInt64, _ uiEntryFence: UInt64,
                               _ stickyFault: Int32)
```

Keep the registry, task/rendezvous, progress and resource-clear algorithms in
private concrete engine helpers, with host proof types at their trusted edges.
Future JNI integration may add separate native witness overloads around those
same helpers; it must not duplicate the engine/coordinator or convert host proofs
to native authority. The stage 4 module guard does not itself admit native scope.

Root freezes this one-file common seam before delegating that file and the five
new files together to one implementation lane. Stage 5
owns JNI/Java/native-witness construction. Stage 6 must separately design how a
native Android installation integrates with `CapabilityPreparedPresentation` and
signed core ownership, exact normal factories, platform compilation and native
profile admission. The standalone host binding and type-separated receipts cannot
be used as a shortcut to that integration.

## 3. Fixed graph and accounting

| Object/storage | Allowed retained contents and maximum |
| --- | --- |
| Binding/public reference | Scalar identities/mirror, weak resources, current resource-free lifetime/control and immutable exact result; no resources, model/frame, reconciler, Java reference, owner closure, executor or Task capture of resources. |
| Reservation | Exactly one persistent strong `CapabilityGuestUIAndroidResources` through `CapabilityPresentationObligation.retainOwner`. No second issue on fallback. |
| Resources | One current reconciler/snapshot, exchange/opaque ticket, pending descriptor, render/input/probe/attachment tuple and a bridge slot disposition; no binding/core/runtime/worker/Task/obligation/callback. |
| Facade record, 16 fixed | Reserved/published state, stable C facade ID, close/fault/resource-stage scalars, weak box, current lifetime/endpoint IDs, alias counts, cleanup serial/evidence, final-owner move bit. No history list. |
| Endpoint record, 16 fixed | Reserved/published IDs, exact Task control/stop descriptor, one native rendezvous, scalar terminal outcome; no strong resource owner or owner callback. |
| Progress cell, 16 permanent | Maximum callback/entry fences, sticky first fault, checked sequence and one `(token, Void continuation)`; cells never die on record reuse. |
| Presentation Task, at most 1/facade | Exact IDs, weak box, one bind gate or exchange reader, stop record, rendezvous. No resource/model/frame/packet/Java object survives an await. |
| Transient resource aliases | At most 1 setup/closing alias plus 1 synchronous UI-helper alias, explicitly counted. None spans await. |

There remain at most 16 presentation suspensions plus 16 join-progress suspensions.
Bind-gate and exchange/native-rendezvous states are mutually exclusive states of
one presentation Task. No coordinator consumer/timer or core cleanup Task is created by this
standalone slice; any future integrated existing owners remain separately counted; no join-coalescing, detached cleanup, polling, timer,
per-owner thread/FD/Handler, dynamic dictionary or growing receipt history is added.
A suspended final joiner may indirectly retain its reservation through its closing
stack; that is a bounded reference, not a scalar or resource alias.

The weak box never means cleanup succeeded: after resources are published, failed
promotion is a typed invariant/quarantine. Only an exact acquired-empty stage may
retire without promotion. Setup must transfer the persistent resource reference to
the obligation and relinquish its local alias before transfer to the standalone
final gate or awaiting failure cleanup. A UI outer trampoline enters C first, checks Swift scalars, then
promotes only in a synchronous inner function. That function returns scalar data;
all strong Swift/native locals end before the outer alias decrement and
`mxuit_ui_leave`. Its remaining tail is fixed scalar return code.

## 4. Endpoint/task/rendezvous and join algorithm

Reserve the Swift facade record before C facade acquire. Reserve the Swift
endpoint record, issue the lifetime ID and prepare its data-only gate before C
endpoint acquire. Under admission publish exact returned identities; immediately
create and publish its sole nonthrowing pre-bind Task before any subsequent
recoverable throw. The local capsule/setup guard already owns cleanup authority.
Acquisition creates no hook; only the listed C acquire/reclaim operations may run
under admission. All other C calls, continuations, destruction and awaits happen
after releasing Swift locks. Only one short record/progress lock is taken at a
time; it never takes admission.

Bind consumes the exact exchange's delivery reader once and installs a data-only
descriptor under the same gate as sticky close. Close winning stops that exchange
and uses the same Task. No accepted native waiter is abandoned by cancellation.
PRESENT first consumes a delivery hint; RETIRE needs no hint. Before `mxuit_request`
publish `(facade,lifetime,owner,waiter,requestedPhase,Void continuation)`; requests
occur unlocked. Completion may precede request return. Only the exact rendezvous
can consume either rejection or completion. A PRESENT request may complete as
RETIRE when close won before C claim; a running PRESENT can yield CLOSE_PENDING,
then the same Task requests its one RETIRE. Reject mismatched kind, old owner,
waiter, lifetime, duplicate completion and zero/exhausted IDs without touching a
successor. Synchronous C drain alone performs resource/native helper work under
its exact PRESENT/RETIRE UI lease.

The sole host wrapper owner uses the real common permit, waits actual
`Task.value` and passes its unforgeable return evidence to `joinNative`. That
method validates exact IDs and its one-shot state, reads the terminal outcome, and calls `mxuit_consumer_joined` exactly once
only for a successful RETIRE. Fault/failed RETIRE cannot reach that assertion.
No second caller awaits the Task, acquires a continuation, reclaims C, or joins its
own presentation/coordinator consumer; reentry returns pending or the exact
retained immutable result.

The authoritative join samples the permanent progress sequence, attempts C
reclaim under admission, then on BUSY registers one checked token iff the sequence
is unchanged and **attempts reclaim again after registration**. A sequence change
or the second attempt defeats a lost wake. Success removes only its token,
publishes exact immutable native retirement evidence before removing the endpoint
record, and returns before fallback can admit a successor. Fault quarantines;
BUSY without a later event stays pending indefinitely. A completed old lifetime
can be read after slot reuse without scanning the old slot or retaining history.
The same progress cell is sequentially reused for final facade reclaim, never
with both endpoint and facade waiters simultaneously.

`mxuit_progress` handles permanent process cells only: max fences, sticky first
fault, checked sequence, move one continuation, unlock, resume. Its post-resume
tail cannot reread an owner/slot, reclaim, promote resources or generate a hint.
Fault fanout first makes admission irreversibly quarantined; outside locks it
stops each exact data-only exchange/pre-bind gate and consumes each exact native
rendezvous with failure. A Task waiting on delivery has no native waiter, so both
paths must be exercised. Quarantine preserves uncertain counted ownership.

## 5. Exact final-cleanup evidence, no Boolean authority

A sealed `CapabilityAndroidHostFacadeCleanupEvidence` instance contains only:

- Exact facade, lifetime, endpoint, active UI-entry serial and checked cleanup
  serial; native bridge-slot generation/disposition (host scope is fixed by the type).
- Exact cleared exchange generation/attempt tuple and the resource-stage revision
  at which pending descriptor/snapshot/reconciler/packet/ticket/tree/listener/
  input/probe/attachment state became empty.
- The authoritative fixed-native retirement outcome associated with the same
  facade/entry; no task, object, closure, existential error or caller-supplied
  `cleaned`, `joined`, `nativeOK`, `testMode` or similar flag.

The resource inner helper is the only producer. While its C lease is still valid,
it performs the fixed `mxis_retire(facade,entry,1)` operation where native state
exists, clears the exact Swift exchange/render state, checks the native slot's
postcondition and issues the next cleanup serial. It then disables future weak
resource lookup and publishes the sealed evidence/permanent scalar cleanup record
under the facade gate **before returning**. Partial clearing, failure, missing
published resource/weak wrapper, wrong entry/slot generation, or a reentrant close
which changed the required final decision yields no evidence. Normal endpoint
RETIRE (`final=0`) never issues final evidence.

The fixed `mxis_retire` ABI stays unchanged. Its `OK` is trusted only as the
postcondition of that exact fixed implementation under `mxuit_ui_validate`, not
as a replaceable callback or general `Bool` seam. Stage 5 must implement deletion
of the exact weak global before returning final OK; scalar bridge-slot publication
and deletion receipts belong exclusively to that implementation. No status from
an unrelated facade/entry or from host fixture code can be promoted to native
cleanup evidence. C `facade_try_reclaim` does not verify these facts.

Stage 4 has no JNI publisher. A bridge slot tracked from acquisition as
**never-published and never-attached** may prove known-empty cleanup, after the
real Swift clear and entry checks above. A native JNI attached/published slot requires the
sealed stage 5 native witness; until it exists, finalization remains pending or
quarantined. A null/missing weak reference cannot turn a published slot into a
never-published slot. Host fixtures may own and actually clear host tree/listener/
weak-owner resources, but can issue only a distinct host witness, never the JNI
witness. Their receipts are the distinct `CapabilityAndroidHost*Receipt` types. The
existing common/native receipt constructors remain untouched and inaccessible;
there is no type conversion from host evidence. Host validators reject wrong IDs.

## 6. Final close, aliases and destruction

Final close first latches Swift close/revokes input/probe under its gate, then
unlocks, calls C facade close and signals the exact data-only stop record. It
promotes no resource and is safe during helper reentrancy and between attempts.
The standalone setup guard owns final cleanup before transfer; the new binding's
final gate owns it after transfer. Its one-shot move bit prevents a second final
joiner. Real signed-core ordinary/observation transfer remains stage 6 work; the
host harness must not claim those integration moves have executed.

Final finish joins the current host installation through its real common permit
(or reads its exact completed receipt after the external host owner finished).
Nil plus an unfinished current lifetime
is an invariant, never new authority. It then checks the **exact final cleanup
record**, not endpoint absence or an earlier close sample. If absent, reserve one
new Swift endpoint, acquire one C TERMINAL endpoint only after the previous Task
actually joined and its endpoint reclaimed, immediately stop its sole pre-bind
Task and perform final RETIRE. Final close before the old helper's decision may
avoid the extra endpoint. Close just after that decision or after its completion
must use this terminal path. Failure to acquire/prove it pins resources; there is
no uncertain retry and no guest restart or accepted-input replay.

After final cleanup plus last endpoint join, use the single progress cell to wait
for C facade reclaim under admission. This includes owner-independent late
CLEANUP/INGRESS return fences which may occur without an endpoint. A held inner
helper, entry leave, completion, platform callback or later nonreentrant return
prevents reclaim as specified by C; a held **process-only healthy progress tail**
may coexist with joined Task return because it accesses no facade resources.

Before final release verify exact cleanup evidence, no linked endpoint, C facade
reclaimed, lookup disabled and **both transient alias counts zero**. Remove Swift
lookup under admission only after preserving the exact cleanup and last lifetime
results in the resource-free shell; after unlocking relinquish every
local resource alias and call the obligation's `retire()` once. Publish the shell's
final completed status only after that call returns. Its retained resource
destructor must return before outer capacity is reusable.
Neither binding nor closed public reference owns that resource. The harness must
hold the actual resource destructor and observe pinned capacity, then release it
and observe actual weak nil/capacity return. Do not infer destruction merely from
cleared accounting, `retire()` invocation or missing weak promotion.

## 7. Executable acceptance plan

`verification/android-binding-stage4-contract/acceptance-matrix.json` is the exact
required host test inventory. Every case is pending implementation. Each names
an actual Swift/C schedule, observable pass condition and covered contract clause.
The future runner must build fresh binaries per process-fault scenario; permanent
C/progress storage is never reset as production behavior. Test-only C fault/
exhaustion controls may force real failure origins, but can never synthesize
cleanup/join/native success. Holds use independently authored barriers around real
operations; they do not replace those operations.

Required modes are Debug (`-Onone`), Release (`-O`) and TSan for rebuilt Swift/C
sources. The current concrete Apple binding and common Prepared guard are compiled
unchanged alongside the added host backend; no verification source replaces them. C-only ASan/UBSan can supplement this; a missing Swift-compatible mode is
reported as pending, not a pass. Full activation builds and frozen Apple/core/
portable regressions remain required. Private-constructor negative compilation
must run with ordinary and `@testable` imports. Linux CI linkage is a separate
check; Android API30/Swift6.3.3 compile/link is scope-limited cross-compilation.
No host pump, host pthread or MainActor proves Android's Java main Looper.

Each run records command/argv, environment, tool version/hash, source revision and
complete source/dependency manifest, output hashes, binary hashes, cases executed,
instrumentation limits, skips and the host scope fixed by its evidence types.
Root reviews exact source and receipt bindings before committing. Host success cannot establish Java weak
global deletion, actual JNI/Java stack return, draw/Choreographer health, mobile
lifecycle, a published FieldLog consumer, release/signing/store/customer/operational
or accountable GA acceptance. Phones remain disconnected; no discovery, physical
runs or reconnection requests are permitted.
