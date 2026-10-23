# Private Android signed UI binding: staged implementation contract

Status: **corrected contract proposed for final root review**, 2026-10-23.
This supersedes the implementation choices in
`android-signed-ui-binding-design.md` only after root accepts it. It changes no
production source, installed profile or supported mode. Android signed UI remains
unsupported until the complete binding receives its separate integration review.
The binding product scope remains `mixer-product-plan.md`.

The accepted independent review and scoped Swift semantics observation are frozen
under `verification/android-binding-design-review/`. New document evidence belongs
only to `verification/android-binding-contract/`. C, Swift binding and JNI lanes
must wait for final root contract review; the standalone reservation prerequisite
in stage 1 is already assigned to root.

## 1. Identities, fixed storage and execution domains

| Identity | Issuer, range and use |
| --- | --- |
| Facade/lifecycle ID | New C facade counter, positive `1...Int64.max`, never reused. One read-only public Android reference and its fixed Java wrapper carry this ID. It survives every attempt and can authorize only fixed facade operations. |
| Endpoint owner | Existing C monotonically increasing UInt64 owner. One endpoint at a time per facade; attempts and final terminal-only cleanup receive fresh owners. No integer supplied by app code can construct a public presentation reference. |
| Lifetime ID | Checked internal Swift UInt64, never reused. Every endpoint record, Task, join permit and receipt matches exact facade/lifetime/owner IDs. |
| Waiter/entry/probe/input/attachment IDs | Positive checked counters. Java-facing counters stop at `Int64.max`; transport waiter and UI-entry serials use UInt64 internally. All reject zero, overflow and reuse. |
| Revision/node generation | All UInt64 bits, crossing `jlong` by bit pattern. No signed comparison. Node IDs cross as 1...128 exact UTF-8 bytes through region APIs. |

Permanent process storage contains: the existing two-FD pipe, one static
ALooper registration/userdata and one retained Looper reference; 16 C endpoint
slots; **16 additional scalar C facade slots**; 16 Swift facade slots; 16 Swift
endpoint slots; 16 permanent Swift progress cells; fixed JavaVM/class/method
metadata for the final wrapper and Looper classes; 16 separate facade-owned JNI
bridge weak-reference slots. No pointer to Swift, model, frame, guest, Activity
or Java object enters **C transport** storage. JNI weak globals stay only in the
bridge's separately accounted fixed slots, created/deleted under UI-entry leases.
No growing dictionary,
owner closure registry, per-owner FD/thread/Handler, polling, timer or queue is
added. A reserved Swift record is unavailable even before its C ID is published.

One facade has at most one endpoint/presentation Task, one authoritative join
permit, one facade weak global wrapper, one reconciler/current snapshot, one
pending descriptor and one input/probe/attachment tuple. A progress cell has at
most one Void continuation for its authoritative joiner. An endpoint rendezvous
has at most one Void continuation for its presentation Task. Total new persistent
waiters are bounded by 16 join signals plus 16 presentation rendezvous; pre-bind
and exchange delivery waits are mutually exclusive states of the same Task.
Existing coordinator notification consumers and the one existing core cleanup
Task per facade remain separately counted. No Task coalesces joins.

Installation and all resource/model/JNI operations run on the actual Java main
Looper thread. Java and native independently compare `myLooper` with
`getMainLooper`; native also checks the captured installation pthread. A Swift
MainActor or DispatchQueue.main hop is not this proof. Worker-side code calls
only fixed scalar C operations, immutable exchange/gate operations and joins.
No `JNIEnv*` is stored; no thread is attached or detached by this profile.

## 2. Resource ownership and reservation API

Stage 1 freezes the following trusted internal API, parallel to existing store
and adapter obligations:

```swift
func reservePresentation() throws -> CapabilityPresentationObligation

final class CapabilityPresentationObligation: @unchecked Sendable {
    func retainOwner(_ owner: any AnyObject & Sendable) throws
    func retire()
    func quarantine()
}
```

There is one presentation obligation **per outer reservation**, issued before
model, C facade/endpoint or JNI-owner allocation. It is independent of store and
adapter IDs, owners and retiring flags. A second issue, including after first
retirement, rejects. Abandonment quarantines. Its retiring flag covers destruction
of the moved retained owner outside locks before outer capacity is released.
**The caller must relinquish every other resource-owner alias before `retire()`;
the reservation cannot prove final alias ownership.** Dropping its retained
reference while another strong alias exists is not a destruction receipt.

The Android object graph is fixed as follows:

| Object | Permitted strong graph |
| --- | --- |
| `CapabilityGuestUIPresentationBinding` | Resource-free control shell: scalar identities, weak resource box, public scalar mirror, current lifetime/data stop record, exact receipts. Core and worker may retain it. It owns no model, reconciler, snapshot, JNI reference or owner closure. |
| `GuestUIAndroidPresentationReference` | Read-only resource-free shell/mirror. Internal constructor; raw identity inaccessible publicly. A retained closed reference contains scalars only and cannot reopen a runtime. |
| `CapabilityGuestUIAndroidResources` | Reservation-retained private resource owner: reconciler/snapshot, exact exchange/ticket, weak JNI wrapper handle and render/input/probe state. It owns no core, worker, runtime, Task, executor, callback or obligation. |
| Presentation Task | Weak resource box, exact numeric IDs and data-only gate/reader/rendezvous/stop record. It never retains resources, model/frame/packet or Java objects across suspension. |
| Setup/UI/closing alias | Explicit checked alias scope, described below. Never hidden in a signal, result, closure, Task capture or public accessor. |

The reservation supplies the one persistent strong resource reference. Weak
promotion requires an active UI-entry lease and a matching published resource
stage. A known-empty acquired endpoint may retire without promotion; a missing
weak resource after publication is an invariant failure, never empty cleanup.

All transient strong resource aliases are counted in the permanent facade record:
at most one setup/closing alias and one synchronous UI-helper alias. The setup
guard relinquishes its alias before transferring to core or awaiting failure
cleanup. A UI helper's inner function owns all strong resource/JNI locals and
returns scalar results only; the outer trampoline drops the alias count and
leaves its C UI-entry lease **after that inner function actually returns**. No
defer may leave a lease before Swift/JNI locals leave scope. A closing operation
must move any exceptional strong resource alias into the same checked alias
scope and relinquish it synchronously before joining/retiring. No such alias may
be parked across await. Pending join continuations can retain the resource-free
closing shell/reservation indirectly; that does not create an additional direct
resource alias, and it never permits retiring a still-counted alias.

Final release requires exact facade cleanup, actual Task joins, native return
fences, zero transient alias counts, disabled resource lookup and no endpoint.
Then the trusted retirement owner calls `obligation.retire()` outside every
binding/progress/admission lock. The reservation moves and destroys its final
resource reference under its retiring fence. Only after that destruction returns
may outer capacity become reusable. The closed public/core shells can remain.

## 3. Concrete Swift seams and the single join authority

Names below are internal contracts, not new public execution authority. IDs are
small immutable value types; all receipt/result constructors are private to their
trusted implementation. Receipts contain scalars only.

```swift
struct CapabilityPresentationLifetimeID: Sendable, Equatable { /* checked ID */ }
enum CapabilityPresentationTaskJoin: Sendable { case noTaskCreated, joined }
struct CapabilityPresentationFailure: Sendable {
    // Exact scalar facade/lifetime/endpoint IDs and a finite internal failure
    // code; bounded value diagnostics only. No any Error, object, closure or Task.
}
enum CapabilityPresentationInvariant: Sendable {
    case wrongJoinOwner, joinInFlight, missingPublishedResources, invalidState
}
struct CapabilityFacadeCleanupReceipt: Sendable, Equatable {
    let facade: UInt64
    let cleanupSerial: UInt64
    let finalEntrySerial: UInt64
    // Constructed only after tree/probe/input/exchange clear + weak JNI deletion.
}
struct CapabilityPresentationLifetimeReceipt: Sendable, Equatable {
    let facade: UInt64
    let lifetime: CapabilityPresentationLifetimeID
    let endpoint: UInt64? // nil only for an Apple lifetime
    let taskJoin: CapabilityPresentationTaskJoin // noTaskCreated or joined
    let facadeCleanup: CapabilityFacadeCleanupReceipt?
    // Construction asserts actual Task.value and all required native joins.
}
enum CapabilityPresentationFinishResult: Sendable {
    case retired(CapabilityPresentationLifetimeReceipt)
    case quarantined(CapabilityPresentationFailure)
}
enum CapabilityPresentationJoinStatus: Sendable {
    case pending
    case finished(CapabilityPresentationFinishResult)
    case invariant(CapabilityPresentationInvariant)
}

final class CapabilityPresentationJoinPermit: @unchecked Sendable {
    // Private one-shot move cell: owned -> inFlight -> consumed.
    // Exact lifetime identity; no model/JNI/resource object.
}
final class CapabilityGuestUIPresentationLifetime: @unchecked Sendable {
    func requestStop(_ cause: CapabilityAttemptLocalStop) // synchronous/data only
    func finish(using: CapabilityPresentationJoinPermit) async
        -> CapabilityPresentationJoinStatus
    var status: CapabilityPresentationJoinStatus { get } // immutable once finished
}
struct CapabilityPresentationInstallation: Sendable {
    // One-shot move cell containing lifetime + sole JoinPermit.
}
final class CapabilityGuestUIPresentationBinding: @unchecked Sendable {
    static func prepare(reservation: CapabilityAttemptReservation) async throws
        -> CapabilityPreparedPresentation
    func bind(_ exchange: GuestUIExchangeV1) async throws
        -> CapabilityPresentationInstallation
    nonisolated func requestFinalClose(_ cause: CapabilityAttemptLocalStop)
    func finishFinalClose(using: CapabilityPresentationJoinPermit?) async
        -> CapabilityPresentationJoinStatus
    var finalStatus: CapabilityPresentationJoinStatus { get }
}
```

`CapabilityPreparedPresentation` is a one-shot setup guard plus shell and the
initial pre-bind join permit. Its `transfer(to:)` is accepted exactly once by the
core before the guard disarms. Its explicit `cleanupAfterFailure()` is awaited
inside the already-running async `open`; it creates no detached cleanup Task.
After endpoint acquire it uses the same real Task/native join or quarantines.
Abandoned setup state quarantines; deinit never performs async cleanup.
`prepare` is async specifically so a throw before returning its guard can await
that local guard's cleanup in its own catch. It contains no Android MainActor
hop. After it returns, open's catch owns cleanup until transfer; after transfer,
the existing core cleanup owner does. Creating core and admitting `.opening`
must both be inside this protected catch, closing the existing admission gap.

Apple retains its current MainActor binding/model and accessor behavior. The
common API's async prepare/bind permit that actor hop; its nonisolated close latch
touches only data gates. Stage 2 wraps the existing Apple Task without creating a
new pre-bind Task: an unbound Apple lifetime can return `taskJoin.noTaskCreated`
after known-empty MainActor retirement, while a bound Apple lifetime requires
the actual existing Task.value and final retirement turn. Android always creates
its pre-bind Task and requires `taskJoin.joined`. Android's separate resource
object/destructor proof does not silently redefine Apple's publicly retainable
model; Apple receipts cover its existing view/resource retirement, not public
model destruction. Keep these receipt scopes explicit in tests and diagnostics.

`bind` installs an immutable descriptor and moves the initial/current join permit
into an installation object under the binding gate. It takes the exact exchange's
sole delivery consumer only once. The pre-bind Task selects bind-or-close under
the same gate; if close wins, the exact exchange is stopped and the same lifetime
retires. There is no second reader or second presentation Task. For fallback,
bind allocates a fresh endpoint only after the old authoritative `finish` returned
and its exact receipt is stored. The facade resource object/reconciler is cleared
for that attempt; each bound exchange receives a fresh reconciler and IDs.

Join authority moves at these existing common-runtime points:

| Point | Sole owner and required next move |
| --- | --- |
| Async open before core acceptance | Setup guard owns initial pre-bind permit. Any throw/cancellation awaits its cleanup in that same async open frame. |
| Core accepted, no bind installation | Core's binding slot owns the permit. Final close joins it after the ordinary operation tail. |
| Worker called bind, install pending | Local installation owns the permit. Core close cannot take it; core first detaches any observation, then waits ordinary tail. |
| `control.installPresentationLifetime(installation, signals, op)` succeeds | A single locked move stores permit/lifetime in that exact observation and empties the installation. Success requires current ordinary op, matching signals and open control. |
| Installation loses close | Installation remains local. Worker stops the exact exchange and awaits `finish(using:)` before its ordinary tail returns, replacing current `Worker:114-117` raw Task join. |
| `control.detachObservation()` | The existing one-shot move at `Control:184-189` transfers observation and permit to either worker fallback/recovery cleanup or core cleanup, never both. `endingObservation` follows the same rule. |
| Worker fallback/recovery | The inner selection helper returns old concrete aliases before the existing `Worker:72-89` join. Observation finish uses its permit; only its returned exact receipt can admit a fresh endpoint. |
| Notification consumer terminal path | `endObservationFromConsumer` retains the ending observation for the later owner and never joins its own consumer/permit. |
| Core final cleanup | Existing cleanup Task: scalar close first, finish moved observation, await ordinary tail, then join any remaining core-owned pre-bind lifetime, perform final facade cleanup, close store, begin outer reservation close. |

The observation's presentation field becomes a one-shot installation/permit cell,
not a copyable raw Task field. Observation `finish` stops the exact exchange,
joins timer and coordinator consumer as today, then consumes its presentation
permit. Only its first authorized caller runs the async lifetime join. An
asynchronous re-entry with no owned permit returns `pending` or `invariant` data;
it never registers another waiter, calls native reclaim or creates a Task. After
completion, later idempotent calls read the retained immutable exact result.

The lifetime retains its immutable scalar result outside the reusable endpoint
record. A successful authoritative join publishes that result before removing
the record. Its caller returns and relinquishes the installation/observation
ownership before admitting the next endpoint. No second caller needs old record
storage, and no receipt/history list accumulates across fallback.
Only setup before core transfer or the one existing core cleanup job after that
transfer may call `finishFinalClose`. Its final-retirement ownership bit is
one-shot under the facade gate. Re-entry reads pending/finished data and cannot
acquire an endpoint, register a waiter or perform reclaim. The optional argument
is the remaining core-owned lifetime permit; nil is valid only if no current
lifetime needs joining or its exact finished receipt already exists. Once the
ordinary/observation moves have completed, nil plus an unfinished current lifetime
is an invariant failure, not permission to create a new join authority.

## 4. New private C contract and return fences

The original unattached `mxuit_acquire`/request/close/join/reclaim API and its tests
remain compatible and keep their existing checks. Binding endpoints use a
separate new acquire function. All new functions are required fixed symbols;
there is no callback setter, caller context or function-pointer argument.

```c
enum mxuit_endpoint_purpose { MXUIT_ATTEMPT = 1, MXUIT_TERMINAL = 2 };
enum mxuit_ui_entry_kind {
    MXUIT_UI_INGRESS = 0, MXUIT_UI_PRESENT = 1,
    MXUIT_UI_RETIRE = 2, MXUIT_UI_CLEANUP = 3
};
int32_t mxuit_facade_acquire(uint64_t *facade);
int32_t mxuit_acquire_for_facade(uint64_t facade, uint32_t purpose,
                               uint64_t *owner);
int32_t mxuit_facade_begin_close(uint64_t facade);
int32_t mxuit_ui_enter(uint64_t facade, uint64_t owner, uint64_t waiter,
                      uint32_t kind, uint64_t *entry_serial);
int32_t mxuit_ui_leave(uint64_t facade, uint64_t entry_serial);
int32_t mxuit_ui_validate(uint64_t facade, uint64_t entry_serial);
int32_t mxuit_facade_try_reclaim(uint64_t facade);

// Existing required hooks stay unchanged:
int32_t mxuit_drain(uint64_t owner, uint64_t waiter, uint32_t kind);
void mxuit_complete(uint64_t owner, uint64_t waiter, uint32_t kind, int32_t result);
// New fixed process-only hook:
void mxuit_progress(uint64_t callback_fence, uint64_t ui_entry_fence,
                    int32_t sticky_fault);
```

Every output is zeroed before validation. Existing MXUIT statuses apply. Null
output, unknown enum/invalid combination/zero identity rejects INVALID; absent
identity is STALE; occupied lease is BUSY; admission after close is CLOSED; wrong
thread is WRONG_THREAD; capacity/exhaustion/I/O remain distinct fail-closed states.

Each C facade slot stores only `id`, `closing`, `terminal_issued`,
`current_endpoint`, `active_entry`, `last_entry_serial`. The process stores one
global active-entry facade/serial, checked `ui_entry_issued` and
`ui_entry_fenced`. Each linked endpoint adds `facade_id`, `purpose`,
`last_entry_serial` and its exact active drain kind to existing fields.

| C operation | Exact behavior |
| --- | --- |
| Facade acquire | Worker-safe after installation; select an empty fixed slot, issue positive Java-safe ID. It creates no endpoint, UI object, Task or callback. |
| Acquire for facade | Require a live facade with no current endpoint. ATTEMPT requires not closing. TERMINAL requires closing and `terminal_issued == false`; successful allocation sets that sticky bit. Reserve a normal C owner slot and link both records atomically. Inherit facade's current last-entry serial, including an in-flight cleanup entry. |
| Facade begin close | Worker-safe scalar-only idempotent close latch; deny new normal ingress/attempt endpoints, mark any current endpoint closing. It calls no UI hook and creates no fault. It is permitted during UI-helper reentrancy. |
| UI INGRESS | UI thread only, owner=waiter=0, facade not closing, no active UI entry anywhere. Admit before any model/weak/JNI lookup. |
| UI CLEANUP | UI thread only, owner=waiter=0, no active UI entry anywhere; may enter a closing facade for fixed synchronous detach cleanup. No guest execution/input/observation authority. A cleaned/reclaimed Swift facade rejects using permanent scalars before resource lookup. |
| UI PRESENT/RETIRE | UI thread only inside current C callback; exact linked owner/waiter/kind must be its currently active drain. Closing permits RETIRE and a PRESENT already claimed before close. No active UI entry anywhere. |
| Successful UI enter | Issue checked serial, set global and facade active entry, set facade and current endpoint last-entry serial. The lease pins facade accounting even when no endpoint exists. |
| UI leave | Same thread/exact facade/entry only. After inner resource/JNI helper returned, clear active entry and schedule one coalesced pipe demand for a later return fence. It does not itself advance either fence. Tail touches permanent C/scalars only. |
| UI validate | Read-only exact active facade/entry plus installing thread check; no hook or resource lookup. Every fixed native-to-Java bridge helper calls this before GetEnv/weak-reference lookup. |
| Endpoint try reclaim | Original retirement/actual-join/helper/completion/callback-fence checks plus no active entry for its facade and endpoint `last_entry_serial <= ui_entry_fenced`. On success unlink exact facade current endpoint and clear endpoint slot atomically. |
| Facade try reclaim | Caller must already hold exact final Swift cleanup receipt. C additionally requires closing, no linked endpoint, no active facade entry and its last entry fenced. Successful zeroing frees only this scalar C facade record; it is not a Swift resource-destruction receipt. |

At every callback entry, **before pipe read, epoch advancement, progress hook or
owner scan**, reject wrong thread, nested `in_callback`, or any active UI-entry
lease. A callback nested synchronously by Java while a helper is executing returns
BUSY without consuming its pending byte, advancing a fence or running a hook.
The fixed Android wrapper keeps registration on BUSY. It emits no new wake for
this rejected attempt. The outer helper eventually leaves, and a later normal
callback consumes the existing/coalesced byte. There is no retry loop in the
binding. Tests must drive this exact native-to-Java nested-entry schedule.

An accepted non-reentrant callback reads the byte and advances the existing
callback fence to the previous callback epoch and the new UI-entry fence to the
issued serial of entries which have returned. It sets `in_callback` before
unlocking. It then publishes changed fence scalars through `mxuit_progress`
outside the C lock, and performs the existing one-helper-per-slot scan. The
PRESENT/RETIRE helper acquires its UI-entry lease inside the already counted
drain. The final no-helper callback emits no further byte unless new work/entry
return occurred. UI leave and callback-tail demand coalesce into the same byte.

After UI leave, the Swift/C trampoline and its private Java listener/entry tail
must be fixed scalar return code: no model/slot lookup, user callback, JNI,
resource destruction, nested-loop dispatch or deferred owner work. All Java
apply and native postcheck work happens while the entry is active. A later
accepted callback therefore cannot be nested inside an owner-dependent entry
tail. This is an explicit implementation proof obligation to verify on Android,
not a claim that thread identity alone establishes a destruction barrier.

## 5. Admission and lock order

Use one Swift admission mutex for record reservation/publication/removal. Fixed
facade/endpoint locks protect only numeric state, weak boxes and data descriptors;
progress locks protect sequences and signal tokens. C has its existing mutex.

1. Under admission, reserve an eligible Swift facade record **before** C facade
   acquire, and a Swift endpoint record **before** C endpoint acquire. Publish
   returned IDs before releasing admission. An endpoint is never requested until
   its Swift rendezvous record is published. C acquisition functions create no
   hook/fault; they return an existing fault, so these C calls may occur under
   admission. No resource/model/JNI lookup occurs here.
2. Under admission, successful C endpoint/facade reclaim and corresponding Swift
   record removal/result publication are atomic with respect to new admission.
   C reclaim calls create no hook/fault. C record success never authorizes removing
   the retained resource owner without section 2's separate conditions.
3. At most one short facade/endpoint or progress lock is held at a time. Admission
   may then take one such lock for scalar publication; those locks never acquire
   admission. No Swift lock may call C except admission's listed acquire/reclaim
   operations. UI entry obtains/releases C first, then checks Swift scalars and
   promotes weak state after all C/Swift locks are released.
4. No lock spans JNI, weak-resource helper execution, continuation resumption,
   resource destruction or await. Every hook runs after releasing C's lock. After
   moving a continuation out, resume only after its Swift lock is released.
5. Scalar final-close/reentrant lifecycle paths first latch Swift admission closed
   and revoke input/probe IDs under the fixed facade lock, unlock, then call C
   facade begin close and signal the data-only stop gate. A racing UI entry which
   got its C lease in the interval must see the Swift close latch before weak/JNI
   lookup and return scalar CLOSED. The lease still receives its return fence.

If C facade acquisition fails, release only the reserved empty Swift facade
record; no C identity exists. If endpoint acquisition fails, release only its
empty reserved Swift endpoint record, then explicitly close/reclaim the known-empty
C facade if possible. If that cannot be proven because of a sticky fault, retain
the facade record/obligation and quarantine. Never zero a live C identity by
discarding only its Swift record. Rollback does not assert consumer join for an
owner which was never acquired.

## 6. Sole Task, rendezvous and authoritative join algorithm

For Android, immediately after successful endpoint acquisition and numeric publication, create
its sole presentation Task **before any later recoverable throw**. It initially
waits a fixed one-consumer bind-or-close gate. Gate close is sticky, including
close before registration; bind and close have one linearization point. Before
successful binding it waits no exchange; afterward it waits only the exact
exchange delivery reader and exact native rendezvous. Cancellation never abandons
an accepted native waiter.

For every normal PRESENT, first consume one `deliveryWake.next()` result. Request
is immediate demand, not subscription. Publish exact `(facade,lifetime,owner,
waiter,requestedPhase,continuation)` before calling `mxuit_request` outside Swift
locks. Rejected request/fault resolution consumes only the same one-shot token;
fast complete-before-request-return is valid. Completion matches all identities,
validates actual kind against sticky close, moves the rendezvous out and resumes
after unlocking. Duplicate/stale completion cannot consume a successor. Only a
fixed synchronous drain resolves resource/JNI state, under section 4's lease.

On stop, begin C close before the terminal request. An already queued request can
be RETIRE; a running PRESENT can return CLOSE_PENDING/FAILED and this same Task
then requests one RETIRE; with no request the Task requests RETIRE directly.
Terminal demand needs no extra delivery hint. Pre-bind RETIRE has no exchange.
RETIRE returns OK only after all admitted attempt state/listeners/tree/probe/input
and terminal exchange results are cleared. Final cleanup additionally deletes
the facade weak global and publishes its exact cleanup receipt. RETIRE failure
or transport fault records quarantine; no uncertain retry is permitted.

The Task exits after its exact RETIRE rendezvous or explicit unreclaimable fault
classification. It records a scalar terminal outcome before returning, but no
local terminal flag is a join receipt. The sole authorized `finish(using:)`:

1. Consumes its matching join permit from owned to inFlight, requests stop, and
   performs **actual `await task.value`**. The Task never joins itself.
2. Reads the terminal outcome only after `.value`. On successful RETIRE, calls
   `mxuit_consumer_joined` for that exact owner. A failure quarantines and returns
   an immutable typed failure; it cannot fabricate C retirement.
3. Reads the permanent progress sequence, attempts exact C reclaim under admission,
   and, on BUSY, registers its one checked numeric wait token only if sequence is
   unchanged. It attempts reclaim **again after registration**. An intervening
   sequence/pending-bit change or the second attempt prevents lost wake.
4. A successful reclaim consumes/cancels only that wait token, publishes the
   immutable exact lifetime result, removes the Swift endpoint record under
   admission and consumes the permit. No other caller performs reclaim. The
   lifetime's resource-free result outlives fixed-record reuse.
5. BUSY with no later event stays pending. Fault produces quarantine and a typed
   failure. There is no polling/timer, MainActor blocking wait or synthetic success.

## 7. Healthy progress and fault fanout

`mxuit_progress` merges max callback/UI-entry fences and a sticky first fault in
permanent cells, bumps checked sequences, moves at most one Void continuation per
facade out under its progress lock, then resumes outside locks. It does not look
up a weak model, touch JNI, reclaim, invoke an owner closure, add an owner epoch or
set a new pipe hint. It must not reread an old owner/slot after resuming. Its
remaining tail contains only permanent process state/scalars and consumed
continuation values. A C first fault is published once outside C locks at every
origin which can create one, including worker pipe failure and callback failure.

A pending continuation physically retains its suspended closing stack. Count that
bounded indirect reference; do not call it a scalar. The frozen real Swift probe
observed that actual Task.value and captured-owner deinit completed while a
consumed `CheckedContinuation<Void,Never>` copy and post-resume hook tail remained
held in Debug/Release/TSan on Apple Swift 6.4. This supports this exact process-only
healthy-tail construction; final Android Swift execution remains pending.

Fault fanout is separate from healthy bookkeeping. A task parked on delivery has
no native rendezvous. First latch irreversible global/facade quarantine and revoke
admission, then use each fixed data-only stop record to stop its exact exchange
or pre-bind gate and resolve its exact native rendezvous with failure. That stop
record contains no resource/model/JNI/Task/owner closure. Its exchange can contain
bounded data snapshots; quarantine keeps their accounting pinned throughout this
fault path. Preserve existing bridge failure and before-/after-intent uncertainty.
A fault cannot produce a facade cleanup or native return receipt. No replacement
is admitted after transport fault, failed RETIRE or missing actual join.

## 8. Facade lifecycle, final cleanup and late close

Every fixed Java-origin entry carries the stable lifecycle ID as well as its
attempt token. Proposed private wrapper methods are:

```text
nativeInstall()
nativeAttach(lifecycleRef, exactPresentationReference, wrapper)
nativeActivate(lifecycleRef, inputRef, revisionBits, nodeIDBytes, generationBits)
nativeObserve(lifecycleRef, attachmentRef, probeSerial)
nativeRequestClose(lifecycleRef, reason)             // scalar-only, reentrant
nativeDetachUI(lifecycleRef, attachmentRef)           // counted cleanup lease
```

The Swift-facing bridge header uses scalars/byte regions, never JNI types or
caller-selected methods. Freeze these fixed operations for the assigned JNI lane:

```c
int32_t mxis_apply(uint64_t facade, uint64_t entry, uint64_t attachment,
                   uint64_t input, uint64_t probe,
                   const uint8_t *packet, uint32_t packet_bytes);
int32_t mxis_interaction(uint64_t facade, uint64_t entry, uint32_t enabled);
int32_t mxis_retire(uint64_t facade, uint64_t entry, uint32_t final_facade);
```

Each verifies `mxuit_ui_validate` before GetEnv or weak lookup, uses only known
cached class/method IDs and returns a fixed OK/FAILED status with a classified
diagnostic. A newly created weak global is a local counted attach obligation until
its exact facade slot is published; failed publication deletes it on that same UI
thread before leaving. Attach passes its Java receiver only within the fixed JNI
trampoline, never through a Swift Task/transport pointer. `mxis_retire(final=1)`
must delete the facade weak global as well as clear the renderer; final=0 retains
at most that one weak global. No current global Activity/context is stored.
An endpoint which never attached has a known-empty JNI slot. After successful
weak publication, unexpected null promotion is failure/stop and quarantine, not
evidence that Java teardown ran. An already published exact final-cleanup receipt
permits later scalar CLOSED handling without promoting that deleted reference.

Signed apply uses the existing portable reconciler and authoritative exact
exchange snapshot. It accepts only vStack/text/button and the current guest
limits: 65,536 guest bytes, 256 nodes, depth 16, 64 children, 4,096-byte strings;
the expanded identity packet is at most 1 MiB. Decode/validate the entire candidate
before any native View mutation. Do not use AndroidSessionRegistry, compiled
reducer operation 1 or its unrestricted event adapter. A fixed listener supplies
only saved lifecycle/input/attachment/revision/node-ID/generation scalars and
`.activate(.null)`; Swift routes against the exact current snapshot/exchange.
The interaction overlay requires authored ancestor-enabled, attached, effects
confirmed, live, no outstanding turn/event, and displayed==latest revision.

Only the private native draw-plus-later-Choreographer-frame path may request an
observation; its opaque exchange ticket remains in Swift resources. Check current
attachment/probe/frame, actual nonempty root child draw and returned draw stack,
positive visible layout/intersection, resumed/non-finishing Activity, attached/
shown/focused/window-visible root, then the exact live effects-confirmed ticket
under the counted observation entry. Apply/resume/layout alone, offscreen/manual
draw, old probes and diagnostics earn no receipt. The existing coordinator alone
earns first_screen and health after the full interval. This remains pending actual
Android execution, not compositor-pixel or human-visibility proof.
Before first attachment, PRESENT may prepare the authoritative snapshot but earns
no native observation. First attachment uses a fresh Java renderer and applies
that exact saved snapshot; it does not reconcile the same revision as a successor.

`nativeRequestClose` is permitted during helper reentrancy. It performs only
permanent scalar identity/close/input/probe revocation and data-only stop signalling;
it does no weak/model/JNI lookup or tree cleanup. It remains valid between
attempts. `nativeDetachUI` acquires a CLEANUP lease before model/JNI work; if a
helper is already active it returns BUSY after the scalar close latch, and that
helper's mandatory postcheck retires the UI before its lease leaves. No cleanup
command queue is created. Non-reentrant pause/detach calls scalar close first and
then fixed cleanup; no lifecycle callback blocks the Looper awaiting async close.
After permanent final-cleaned state, cleanup ingress returns scalar CLOSED without
resource lookup. A stale attempt token never regains input/health authority.

Attempt RETIRE clears its Java tree, listeners, probes and every attempt token;
it may retain the one facade-owned weak wrapper. Fallback creates a new endpoint,
Task, reconciler and attachment/input/probe IDs only after the old authoritative
join returned and required concrete retirement separately completed. The wrapper
receives its new current attachment token synchronously; old tokens stay stale.
Facade lifecycle ID remains close-capable throughout the interval. A disappeared
weak wrapper stops the facade; no later object can retarget that lease.

Final RETIRE constructs `CapabilityFacadeCleanupReceipt` only after the exact
wrapper's fixed cleanup method succeeded, listeners/tree/packet/probe/input and
Swift render/exchange state were cleared, the weak global was deleted, and resource
lookup was disabled under the facade gate. Its final entry serial and receipt are
published in permanent scalar state before returning. No public diagnostic can
construct this receipt. Subsequent C endpoint join/fences still must complete.

`finishFinalClose` never infers final cleanup from endpoint presence or from a
close flag sampled before a helper. It first joins the uniquely owned current
lifetime (or reads its completed result), waits any required ordinary/observation
ownership move, then checks the exact permanent facade cleanup receipt. If absent,
it reserves a Swift endpoint record and acquires **one sequential TERMINAL**
endpoint under the same obligation. The previous Task actually joined and its
endpoint was reclaimed first. That fresh pre-bind Task is immediately closed and
performs one final RETIRE. If final close reached the old helper before its final
cleanup decision, that helper can publish the receipt and avoid this extra lifetime.
If close arrived after that decision but before completion/reclaim, the missing
receipt still forces terminal cleanup. This resolves the late-close race.

After exact final cleanup and last endpoint join/reclaim, the authoritative final
owner waits facade UI-entry fences using the same single progress cell, calls C
facade try reclaim, disables/removes its Swift facade lookup under admission, checks
zero transient aliases and retires the final reservation-retained resource owner
as in section 2. Failure to acquire the terminal endpoint or prove cleanup pins
the facade weak reference/resources/obligation and reports cleanupPending. It
never deletes JNI references on an arbitrary worker. Final closing never restarts
the guest, replays accepted input or reopens an old reference.

## 9. State tables and failure transfer

| Facade state | Admission and next state |
| --- | --- |
| reserved-empty | Swift record reserved; no C identity. C acquisition failure rolls back only this empty reservation. |
| acquired-empty | C facade exists; known no resources/JNI/UI entry. Close/reclaim synchronously only if C proves empty/fenced; otherwise quarantine. |
| prepared | Obligation retains resources; endpoint/pre-bind Task published; core/setup owns join permit. Attach may use normal counted ingress. |
| live/attempt-retiring/between-attempts | One exact resource owner; at most one endpoint. Lifecycle close always valid. Normal input/observe require current live tuple; fallback admission requires previous receipt and concrete retirement. |
| final-closing | Scalar latch sticky; no normal ingress/attempt acquire. Cleanup ingress is leased; one terminal endpoint may be issued if exact cleanup receipt missing. |
| final-cleaned | Exact cleanup receipt published; resource lookup disabled. No new model/JNI access. Await endpoint/facade return fences and zero aliases. |
| reclaimed | C and Swift facade records gone; final resource destructor returned and obligation retired. Public scalar shells remain closed. |
| quarantined | Sticky, no reuse/replacement/health. Preserve all uncertain counted owners. |

| Lifetime state | Required next step |
| --- | --- |
| endpoint-acquired-empty | Numeric record published; sole Task created before later recoverable throws. Empty RETIRE is valid only if resources were never published. |
| pre-bind | One bind-or-close wait. Permit belongs to setup/core or moves through installation. |
| bound | Exact exchange reader; normal hint-before-request protocol. |
| retiring | Begin close sticky; same Task obtains its one RETIRE result. |
| task-returned | Outcome is data; authoritative permit must still await actual Task.value before consumer_joined. |
| joined/native-pending | One authoritative progress wait; C callback and UI-entry fences still required. |
| reclaimed | Immutable exact receipt published before record reuse; permit consumed. |
| quarantined | Immutable failure; resources/outer capacity remain pinned. |

| Failure | Ownership/result |
| --- | --- |
| Wrong Java thread, API<30, missing Looper/class/method/cache/install | Reject before facade/model admission; creating thread releases unregistered resources. Installation failure stays unavailable; no Swift executor fallback. |
| Presentation obligation issue fails | No model/C/JNI allocation; existing open catch begins outer close. |
| C facade exists, endpoint not acquired | Explicit known-empty guard cleanup, no consumer_joined for nonexistent endpoint. Global fault can require quarantine even for empty facade. |
| Any recoverable throw after endpoint acquire | Same pre-bind Task already exists. Setup relinquishes local resource alias, latches final close and awaits explicit cleanup in async open. No extra Task/deinit cleanup. |
| Core/opening admission fails after transfer | Existing core cleanup Task owns joined cleanup; open catch requests close and awaits it. Ordinary admission itself must be inside that protected catch. |
| Close races bind/install | One gate selects bind/close; failed install remains local join owner and finishes before ordinary tail. Core waits that tail before taking its remaining binding permit. |
| Missing published weak resources/JNI apply failure/decoder failure | Stop exact exchange, revoke input/probe, retire visible candidate/current tree under lease; preserve failure/intent classification. No missing lookup is successful cleanup. |
| RETIRE/transport/facade cleanup failure, exhausted IDs | Typed quarantine; no replacement, receipt fabrication or capacity release. |
| Stalled Looper/no later return fence | Cleanup remains pending without polling or timeout-based success. |

## 10. Staged implementation ownership and acceptance

| Stage | Exclusive work and acceptance |
| --- | --- |
| 1. Reservation prerequisite, root owns now | `CapabilityAttemptReservation.swift` and reservation tests only: one presentation issue per outer reservation, retained owner, independent retiring flag/quarantine, held final destructor and concurrent store/adapter/presentation retirement. No binding/core/runtime or supported-mode changes. This can proceed independently of new C/Swift/JNI work. |
| 2. Common lifetime/setup seams, root after contract acceptance | Common typed lifetime/permit/receipt and explicit setup guard; root-owned changes to signed facade/core/control/worker. Apple keeps its MainActor model/public accessor/native probe behavior and uses a typed wrapper around its actual existing Task, with explicit noTaskCreated for the existing empty pre-bind case. Issue/retire the common obligation without pretending to destroy Apple's publicly retainable model. Android prepare stays unsupported: no C facade/endpoint/resource owner is allocated, and any unused obligation is explicitly retired in guarded cleanup. Test moves, close-before-start/bind, failed installation, constructor/opening admission and fallback ownership with real host Tasks. No platform receipt is fabricated. |
| 3. C facade/entry/progress, C owner after root freeze | Only assigned transport sources/header/tests. Preserve all original unattached tests; add fixed16 facade+endpoint reservation, single linked endpoint, terminal-once, UI-entry identity/exhaustion, nested Java-shaped callback, held entry/platform/completion/progress tails, first-fault and final no-helper progress tests. Missing required hook must fail link. Scope remains C host/Android objects until execution. |
| 4. Swift Android binding, assigned new files | Fixed registry/rendezvous/resource graph and real Swift/C host harness. Requires stage 2/3 APIs frozen. Test actual Task.value, weak owner/destructor, one joiner/idempotent exact result, fast completion, lost wake, record reservation rollback/reuse, fault fanout and final-close late-latch/terminal-only path. No JNI or supported-mode enablement. |
| 5. Fixed JNI/Java wrapper, assigned new sources | Stable lifecycle ID, counted ingress/cleanup, fixed known class/methods, exact UTF-8/UInt64 and bounded local refs, no attach/detach, scalar listeners/overlay, signed subset decoder and draw/later-frame probe. Shared renderer/packet edits have one assigned owner. Real JVM JNI receipts are scoped host evidence. |
| 6. Android integration, root/integration owner | Full actual signed facade/VM/native dependency/source closure, API30 compile/link/APK inspection, real Java main Looper and NDK callback mapping, widgets, signed event/KV/replacement/draw observation and lifecycle/fallback/fault behavior in permitted emulator. Keep unsupported-mode/profile guards until root accepts full integration. |
| Excluded pending gates | Physical Android/iOS discovery/runs/reconnect requests remain prohibited while phones are disconnected. Immutable separately published FieldLog packages, store/signing, dual-platform meaningful OTA, accessibility/performance/recovery and accountable GA reviewers remain pending. |

The only parallel-safe work before shared contracts freeze is stage 1 and this
document/evidence. After root accepts stage 2/3 signatures and assigns exclusive
paths, C implementation and common lifetime work can proceed independently;
Swift binding depends on both. JNI scalar/decoder/probe unit work can proceed only
against the fixed wrapper contract, with no shared renderer edits until ownership
is assigned. Integration depends on the full source closure. No helper-only build,
host MainActor test or synthetic joined flag qualifies native Android execution.

Official references: [Java Looper](https://developer.android.com/reference/android/os/Looper),
[NDK Looper](https://developer.android.com/ndk/reference/group/looper),
[JNI guidance](https://developer.android.com/ndk/guides/jni-tips),
[Choreographer frame callbacks](https://developer.android.com/reference/android/view/Choreographer.FrameCallback).
The numeric leases, later non-reentrant entry fences and draw/later-frame
observation are binding design reasoning requiring separate executable review.
