# Private Android signed UI binding: review proposal

Status: **proposal only, awaiting root acceptance**, 2026-10-23. This document
implements no binding, changes no installed contract and grants no Android,
health, release or GA qualification. The current non-Apple unsupported stub stays
in place until a complete, separately reviewed integration replaces it. Source
and tool observations are in
`verification/android-signed-ui-binding-design/receipt.json`; the selected source
manifest, rather than a moving checkout HEAD alone, identifies this inspection.

This refines `android-signed-guest-ui-design.md` against the implemented
`android-guest-ui-transport-design.md`. The latter supersedes the older proposal's
per-owner endpoint removal: use its singleton two-FD pipe, one ALooper registration,
static userdata, sixteen numeric owner slots and later-callback return fence.
The transport's required `mxuit_drain`/`mxuit_complete` symbols remain fixed.
Its current API has one integration gap: no notification when the no-helper
callback advances the return fence. The narrowly scoped addition below requires
root review before implementation; it is not silently assumed to exist.

## Boundary and current evidence

The next private binding joins the existing signed selection, capability VM,
`GuestUIExchangeV1`, portable `UIReconciler`, and owned Android widgets. It must not
reuse `AndroidSessionRegistry` or reinterpret the compiled reducer's operation 1.
That registry executes synchronous value-semantic reducers under its lock and
cannot own an async activation, presentation Task or native capability exit.

The inspected Apple binding takes the sole `deliveryWake` reader and returns one
Task. `CapabilityColdStartObservation.finish()` really awaits its `.value`, and
the worker binds before consuming/constructing/starting the selected guest. Keep
those orderings. Android adds a counted pre-bind lifetime and native fence join;
the existing raw `Task` field alone cannot represent either obligation.

The current C transport has executable host and Android object/link evidence in
`verification/android-guest-ui-transport/`, with independent probes in
`verification/android-transport-review/`. Those receipts do not execute Swift
continuations, JNI, Java widgets or Android's Looper. In particular,
`mxuit_request` itself schedules work: repeatedly registering it immediately
after completion spins even without `mxuit_hint`. This proposal does not rerun or
relabel the C evidence as binding evidence.

## Minimal public and private contracts

The signed runtime remains the only public execution authority. Its common
`open(configuration:execution:)`, signed-download methods, `start`, recovery and
`close` become platform-independent after integration. Preserve the Apple
`@MainActor presentation` accessor and `MixerGuestScreen` unchanged in behavior.
Android receives a read-only presentation reference/snapshot through an
Android-specific accessor; its public screen factory accepts that exact reference,
not a caller-supplied integer. The reference constructor and raw token conversion
are internal. Neither platform gains public `offer`, `render`, event-name/export,
document, callback, executor or `reportMilestone` entry points. Diagnostic state
cannot supply an observation receipt.

Use these internal operations, with names/signatures finalized by root before
dependent edits:

| Internal seam | Authority and result |
| --- | --- |
| `CapabilityGuestUIPresentationBinding.prepare(reservation)` | Acquire presentation obligation and one endpoint lifetime before returning the facade. No Android MainActor await. |
| `bind(exchange) -> CapabilityGuestUIPresentationLifetime` | One exact exchange, one sole delivery reader and one binding identity. Return the already-counted pre-bind lifetime; reject rebinding until that lifetime's actual Task join and native reclaim. |
| `lifetime.finish()` | Explicit stop, actual `await task.value`, `mxuit_consumer_joined`, then event-driven `mxuit_try_reclaim`. Internal typed receipt; callers cannot assert native retirement. |
| `binding.close()` | Stop/join the current lifetime even when `bind` was never called. The existing coordinator cleanup Task owns the join; this adds no cleanup Task. |
| `binding.requestClose()` | Synchronous data-only close latch and input/probe revocation, called by core `requestClose` before any async close work. Wake the pre-bind gate or stop the bound exchange; no off-thread JNI. |
| `mxuit_drain(owner, waiter, PRESENT\|RETIRE)` | Fixed synchronous hook. Resolve only this numeric owner and exact waiter; transient weak-model lookup on the verified native UI thread. Return only OK/FAILED. |
| `mxuit_complete(owner, waiter, kind, result)` | Fixed scalar completion. Consume only the matching one-shot rendezvous; never look up a model or call Java. |
| Proposed `mxuit_progress(fenced_epoch, fault)` | Fixed process bookkeeping hook described below. No callback registration, pointer context, owner lookup or execution authority. |

Private Java/JNI entry points belong to one final `MixerGuestScreen` wrapper:
`nativeInstall()`, `nativeAttach(presentationRef, screen)`,
`nativeActivate(inputRef, revisionBits, nodeIDBytes, generationBits)`,
`nativeObserve(attachmentRef, probeSerial)`, and `nativeDetach(attachmentRef)`.
Native-to-Java calls have fixed methods for apply/interaction/retire on that known
class. No caller-selected class/method, reflection, arbitrary `Runnable`, raw
Swift object, guest pointer or global Activity/context is admitted.

Presentation/attachment/input/probe references are positive checked counters
bounded by `Int64.max` for unambiguous Java tokens; zero and exhaustion reject.
They never wrap or get retargeted. Transport owner IDs remain internal UInt64
values. Revisions/node generations use all 64 bits of `jlong`, converted by bit
pattern, never signed ordering. Node identifiers cross as 1...128 exact UTF-8
bytes through region APIs. Native forms `.activate(.null)` and routes it against
the saved exchange/snapshot; Java supplies no action ID or value.

## Ownership, storage and thread domain

An outer reservation must issue a new **presentation obligation at open**, before
model, endpoint or JNI-owner allocation. Existing store/adapter obligations are
insufficient: close-before-start otherwise permits outer capacity reuse while an
Android endpoint survives. Extend `CapabilityAttemptReservation` with one
presentation obligation, its retained owner, retirement-destructor fence and
quarantine behavior, matching the existing ownership discipline. It remains
independent of concrete capability exit and its adapter obligation.

| Owner/storage | Strong ownership while live | Fixed bound and release |
| --- | --- | --- |
| Outer presentation obligation | Private binding/lifetime owner; never the public facade, worker or core | One per outer reservation, at most16. Released only after all endpoint lifetimes reclaim and the retained owner's destruction returns. An abandoned obligation quarantines. |
| Binding/model | One current lifetime, one portable reconciler/current snapshot, one exact data-only exchange, current ticket and attachment scalars | One model per facade; each attempt gets a fresh reconciler. No previous snapshot/ticket/packet history. |
| Swift process registry | Sixteen fixed records: numeric IDs, weak model box, data-only attempt/rendezvous state | No strong model/runtime/core/worker/session/Activity. No growing dictionary. Numeric owner and identity must both match. |
| Sole presentation Task | Pre-bind reader or exchange delivery reader, weak-model box, data-only lifetime/rendezvous state | Exactly one per endpoint, including pre-bind/closing. It retains no frame/snapshot/model/Java object across suspension. The exchange is data-only and owns no Task/callback; a fixed stop record may retain it until retirement. |
| C transport | Fixed scalars, one waiter/helper/completion state per owner | Existing static16 slots; two FDs and one registration/process-lifetime Looper reference total. No per-owner FD or thread. |
| Facade JNI attachment slot | At most one weak global reference to the current wrapper, current scalar identity | At most16 weak references, charged to the outer presentation obligation even between attempts. Promotion is local to one synchronous helper. Delete on main Looper during final facade RETIRE/detach; never store `JNIEnv*`. |
| Java wrapper | One root/renderer/current packet and one pending probe | Activity owns the wrapper; native retains it weakly. Listeners/probe capture a Java `WeakReference` plus scalars, not packet/Activity/native owner. |
| Native drain scratch | One claim, candidate reconciler/snapshot and encoded packet | At most one helper per owner, serialized on one UI thread; guest65,536-byte/256-node/depth16/64-child/4,096-byte-string limits remain. JNI packet ceiling1MiB. |
| Java apply scratch | One validated candidate packet/native candidate tree plus current packet/tree | At most one synchronous candidate; clear discarded listeners and retire whole tree on failure. UI node bound256 per candidate. |

`GuestUIPresentation`'s Android mutable render fields are confined to the verified
Java main-Looper thread, **not Swift MainActor**. Data admission/rendezvous/weak
lookup use short explicit mutexes; an Android `@unchecked Sendable` annotation must
state this proof and cannot substitute for it. No strong model lookup spans an
await. Cross-thread binding installs only an immutable pending attempt descriptor
under a gate; the next UI helper installs it into render state synchronously.
Read-only snapshots use a separately locked scalar mirror.

Java verifies `Looper.myLooper() == Looper.getMainLooper()` at installation and
every screen entry. Native independently compares those fixed Java method results,
captures the installing pthread and calls `mxuit_install` on it; a non-null
`ALooper_forThread` alone does not prove Java's main thread. Every native drain
checks captured thread, Java Looper identity and non-reentrancy. JNI may be entered
again synchronously by Java during apply; the private UI-helper guard rejects
activate/attach/observe reentrancy, while scalar detach/stop may only latch revocation
for the helper's mandatory postcheck. No lock spans JNI or continuation resumption.
The Android Looper APIs identify the actual application main thread; this mapping
is a binding design, not a claim about Swift executors.
([Looper](https://developer.android.com/reference/android/os/Looper))

Keep a fixed JavaVM pointer and bounded global references only to the known wrapper
and Looper classes/method metadata. No global Java context is allowed. Each helper
uses `GetEnv`; a detached thread rejects. Binding workers never call JNI and this
slice performs **zero AttachCurrentThread/DetachCurrentThread operations**. Never
detach Java's existing UI thread. Future native-created threads require a separate
reviewed attach/exit policy. Promote a weak wrapper with `NewLocalRef`, use a bounded
local frame (`PushLocalFrame(16)`, at most8 live local references in the reviewed
helper), and delete locals before completion. Check exceptions after fixed
calls/array operations; a native Looper callback has no Java caller to receive a
pending exception, so classify/clear it and fail closed before further ordinary
JNI calls. Java-origin failures return a fixed status or preserved exception;
neither path drops diagnostics or leaves a partly usable tree.
([JNI guidance](https://developer.android.com/ndk/guides/jni-tips))

## Sole Task, exact waiter and wake protocol

Create the one presentation Task as soon as an endpoint is acquired at open,
before any later recoverable throwing setup. Its pre-bind state awaits a fixed
**bind-or-close** data gate, with a pending bit and one consumer; it is not a
general command queue. `bind` atomically chooses the exact exchange/reader or
observes sticky close. Close before, during or immediately after bind signals the
correct gate; no code waits on two sources concurrently. A consumed pre-bind close
requires no exchange and goes directly to RETIRE. After successful binding this
same Task awaits only the existing exchange reader and fixed native rendezvous.

Normal delivery is precisely:

1. Await `deliveryWake.next()` **before every normal PRESENT request**. The existing
   wake preserves a pending hint between waits, including publication while JNI
   applies or immediately after the prior helper returns. Do not resubscribe to
   C as a way of waiting for a future exchange change; request is immediate demand.
   No new exchange callback, subscription, Task or signal-forwarder is necessary.
   `mxuit_hint` is not used to replace the exchange's sole-reader ownership.
2. Increment a checked lifetime-local waiter token; never reset it for a live C
   owner. Publish `(owner, lifetimeID, waiter, requestedPhase, continuation)` into
   its one Swift rendezvous cell **before** calling `mxuit_request`. This prevents
   a fast main-Looper callback from completing an unpublished continuation.
3. Call C outside the gate lock. A rejected request resolves only that exact token,
   and only if the completion hook has not already consumed it. Once C accepted
   it, the caller must await completion; cancellation cannot abandon the waiter.
   Closing may turn a requested PRESENT into actual RETIRE, so completion matches
   owner/waiter/lifetime first and validates the actual kind against sticky close.
4. Drain synchronously claims at most one exchange presentation and completes it
   against the same candidate `UIRenderSnapshot`. It consumes the event result,
   updates input/probe state and releases all claim/frame/model/JNI locals before
   returning. A hint arriving during it remains pending in the exchange wake.
5. Completion atomically removes that exact rendezvous, unlocks, then resumes it.
   Duplicate/stale completions cannot consume a successor's waiter. C consumes
   its old waiter before this hook and keeps its separate completing lease;
   the resumed same Task may register a needed successor while that hook returns.

When close is observed, latch `mxuit_begin_close` before the terminal request.
There are three terminal paths: an already queued request becomes RETIRE; a running
PRESENT returns CLOSE_PENDING/FAILED and this same Task issues one RETIRE; or no
request exists and this Task issues RETIRE directly. This bounded terminal request
is allowed without a new exchange hint, since close is sticky work. If stop follows
the final normal await, `deliveryWake.finish()` preserves its terminal pending
hint; it is never mistaken for successful UI retirement. A RETIRE helper consumes
any terminal result, clears input/probe/ticket/render/exchange state, removes native
listeners/views. A final facade RETIRE also deletes its weak JNI reference; an
attempt-only RETIRE retains at most that facade-owned weak reference as described
below. A pre-bind RETIRE simply has no exchange to consume. RETIRE failure
pins/quarantines instead of retrying uncertain
teardown. The Task exits only after its RETIRE rendezvous returned (or an explicit
transport fault classified it as unreclaimable), not on a local `finished` flag.

One coalesced hint can cover several exchange changes: the helper reads current
state, and changes/refresh set while it runs yield at most the existing next pending
hint. It is acceptable to execute one no-op PRESENT from a coalesced stale hint;
after consuming it, the Task parks again. Repeated empty drains must settle to idle.
Waiter, binding, attachment, probe and progress-sequence exhaustion stops admission
and pins uncertain state; no wrap, timestamp or callback address substitutes for
an identity.

## Reclaim progress without polling or a circular fence

After successful RETIRE, `lifetime.finish()` first performs actual
`await task.value`. Only this join owner may then call `mxuit_consumer_joined`.
The C RETIRE completion can return later than the Task, and its platform callback
can return later still. Both remain counted by C; `.value` is necessary but does
not bypass either native fence. `mxuit_try_reclaim == BUSY` keeps close/replacement
pending. No main-thread blocking wait, timer, busy retry, second presentation Task
or per-owner Handler runnable is introduced.

Add the fixed required hook
`void mxuit_progress(uint64_t fenced_epoch, int32_t fault)` to the private C header.
The C callback publishes its new `fenced` epoch under its mutex, unlocks, and invokes
this hook on an actual advancement, including the existing final no-helper callback.
It invokes no Swift hook under the transport lock. Also publish the first sticky
fault through this hook after unlocking on every origin of that fault, including
worker-side pipe failure. Missing progress implementation must fail the final link.
The original two required hook signatures and owner state-machine semantics stay
unchanged. Concurrent publications merge `max(fenced_epoch)` and a sticky first
fault in the process cells; a delayed healthy notification cannot erase a fault or
regress a fence. The C lane must independently implement/test this small addition before
the binding depends on it.

The hook accesses only process-lifetime fixed **progress cells**, numeric epoch/
fault values and bounded continuation signals. It must not resolve a weak model,
retain an endpoint owner, access a JNI reference, call transport reclaim or execute
an owner closure. It neither changes an owner's `last_hook_epoch` nor sets a new
pipe hint. Thus a no-helper fence callback can end idle, and notification does not
create an endless new owner fence requirement.

Each cell has a checked sequence, numeric owner/lifetime identity and at most two
joined close waiters: the worker's moved observation finish and the existing core
close owner. This fixed overlap limit follows from admission/control ownership;
a third caller is an internal invariant failure, not an unbounded waiter list.
Both callers may await the same actual Task; C's joined latch is idempotent. Neither
may release the obligation until exact reclaim success is published. No extra Task
is created to coalesce these callers.

The join algorithm takes a cell sequence, tries reclaim, then registers its numeric
wait token only if that sequence still matches; it **tries reclaim again after
registration**. If progress happened between either read and park, the pending
bit/sequence mismatch or second reclaim avoids a lost wake. A successful reclaim
removes/cancels only that exact waiter token and publishes one idempotent result
to the other joined caller. Continuations move out under the progress lock and
resume after unlocking. Their awaiting stacks may retain counted closing owners;
this is an explicit bound of two, released only after resume and actual caller
tails. The progress hook's own remaining tail can touch only its permanent process
cell/scalars, never those resumed stacks or reclaimed per-owner storage.

Serialize C acquire/Swift-record publication and C successful reclaim/Swift-record
removal under a separate admission mutex, so a newly issued owner cannot race an
uncleared old record. Never hold that mutex over a hook, JNI, continuation resume or
await. Progress-cell locks never call C; admission may call only non-callback C
acquire/reclaim operations. A first-fault notification must consequently be emitted
only by operations which can actually create a fault, after their locks are gone.
After owner removal, a late numeric completion/observation fails identity lookup.

This avoids a circular fence: progress signals that the **previous** owner callback
returned; its current hook has no per-owner context to reclaim. A resumed close
caller may release the old endpoint while that process bookkeeping hook is still
returning because the hook no longer has any access to endpoint-owned memory.
This is a design proof obligation, not a tested property yet. A progress hook that
captures a model/endpoint, retries retirement, stores a closure or reads an old slot
after resuming violates this proposal. Hold that exact progress tail in tests and
prove old owner reclamation is safe while every owner-dependent tail still pins.

Transport faults wake the exact pending Swift rendezvous with a typed failure and
stop the saved data-only exchange; they cannot fabricate a C RETIRE success. If
registration/fd failure makes native retirement impossible, the presentation
obligation and C slot remain quarantined, `cleanupPending` remains true, and no
replacement is admitted. A stalled Looper yields no progress and leaves close
pending. Neither a fault wake nor cancellation is a callback-return receipt.

## Native apply, input and first-screen identity

Use a fresh portable reconciler for each exchange. A PRESENT helper can prepare
one current snapshot before the first Java attachment, but earns no native
observation. On a later first attachment, its fixed synchronous helper applies
that same snapshot with a fresh renderer and postchecks the current binding; it
does not reconcile the same revision as a successor. The standalone fixture
attaches before start, so this path is also a required negative/late-attach test.
If an attached weak wrapper unexpectedly disappears, revoke its authority and
stop rather than retarget a later object to it.

Encode the existing schema1 document/identity packet from the authoritative
snapshot, preserving exact UTF-8 and UInt64 decimal values. A signed decoder
strictly enforces the guest subset/limits before any View mutation. Reuse shared
owned decoding/widget mappings through an internal signed constructor, not the
compiled engine/reducer or unrestricted renderer event adapter. Decode validates
the entire candidate; failure retires the visible tree and records
`presentation/presentationInvariant`, retaining the original before-/after-intent
classification and any existing first bridge failure.

Listeners capture only immutable input reference, attachment, revision, exact
node-ID bytes and generation, with a weak wrapper. The Swift table resolves the
saved exchange issuer/binding/attachment and checks exact current snapshot route
before `offer`; it never rebuilds input against a new runtime. Removed/detached
Views have listeners cleared. Effective enabled state is authored ancestor-enabled
AND attached AND effects-confirmed AND live AND no guest turn/event outstanding
AND displayedRevision == latestRevision. A separate interaction overlay updates
this gate without guest document mutation or `requireSuccessor` at equal revision.
Busy/stale/closed/invalid outcomes are local fixed statuses; acceptance is at most
one exchange event, never permission to invoke a selected export directly.

The private native probe stores the opaque exchange ticket only in the Swift
model. Java has attachment/probe/frame serials and its native root identity. On
each current apply invalidate the old probe and arm at most one probe object.
The actual root's `dispatchDraw` override calls `super.dispatchDraw` first, then
records successful nonempty child-draw completion and a checked draw epoch. It
schedules one `Choreographer.FrameCallback` from that same main Looper. In the
later callback require the draw stack to have returned, exact current draw epoch,
unchanged root/attachment/probe/frame identity, resumed non-finishing/non-destroyed
Activity, attached/shown/window-visible/focused root, completed positive layout
and nonempty visible intersection. It then calls the fixed private observation
entry with only attachment/probe serial. Native rechecks those identities and
exchange live ticket/effects state before `observePresentation(ticket)`.

No observation is earned by apply returning, `onResume`, a manually invoked probe,
offscreen Canvas, old frame callback, layout without draw, or `OnDrawListener`.
The frame callback is tied to its Choreographer's Looper; the draw-plus-later-frame
sequence is a conservative binding inference and must execute on Android before
acceptance. It proves a native layout/draw/display-cycle observation, not compositor
pixels or human visibility. Stop/revision replacement/pause/detach invalidate the
probe and remove the pending callback; an already queued old callback checks
scalar identity and does nothing. One receipt may remain pending in the existing
exchange while the worker is busy; only the existing coordinator earns
`first_screen` and health after its full interval.
([FrameCallback](https://developer.android.com/reference/android/view/Choreographer.FrameCallback),
[OnDrawListener](https://developer.android.com/reference/android/view/ViewTreeObserver.OnDrawListener))

Pause/detach first revoke input/probe authority synchronously and clear native
listeners/views, then request the existing coalesced close. They never block the
main Looper on async `close`. A resumed/recreated screen gets a new runtime only
after both presentation reclaim and the existing required concrete-retirement
barrier; no accepted-event replay, background execution or automatic restoration
claim is added in this first profile.

## Early setup and failure transfer

| Failure/race | Required retained owner and cleanup |
| --- | --- |
| Wrong Java thread, API<30, absent Looper, class/method/cache or install failure | Reject before presentation owner admission. Release unregistered resources using their creating thread. If process installation failed sticky, expose unavailable; do not retry with a Swift executor. |
| Outer reservation acquired, presentation obligation acquisition fails | Existing open catch begins outer close. No model/C owner/JNI weak reference was allocated. |
| Obligation acquired, before C acquire succeeds | A local setup guard owns/retire-joins its data allocations; explicitly retire the unused presentation obligation. No `consumer_joined` assertion for a nonexistent owner. |
| C acquire succeeds | Publish its numeric record and create the sole pre-bind Task before any subsequent recoverable throw. The obligation now retains the setup/closing owner. No plain catch/deinit can drop it. |
| Model/weak wrapper/setup fails after acquire, or core construction/open throws | Latch close. Before a core exists, the already-running async `open` caller retains the setup guard and awaits that lifetime's finish; after core ownership transfers, the existing coordinator cleanup owner does so. The same Task issues RETIRE even without an exchange, joins actual Task, then reclaim. Open's catch awaits cleanup or records quarantine before reservation release. No detached emergency Task. |
| Facade closes/deinits before `start`/`bind` | Fixed pre-bind gate wakes the same counted Task. Core closes this lifetime even with no observation. No native owner is left awaiting a consumer that was never created. |
| Close races `bind` or `installPresentationConsumer` | One gate linearizes bound-vs-closed. If install loses, worker stops the exact exchange and `await lifetime.finish()` before unwinding. Core may overlap the bounded second join; no second presentation Task. |
| Attempt stops/fallback selection exists | Moved observation finishes its typed lifetime before fallback; old concrete retirement remains a separate barrier. Only then may a new endpoint/Task be acquired under the still-live facade obligation, with fresh IDs/reconciler/input binding. |
| JNI apply/decoder/renderer failure | Stop exact exchange, clear candidate/current visible state, retire via same Task. Preserve pre-/post-intent uncertainty. A Java root must not remain interactive after failed postcheck. |
| RETIRE failure, missing progress, transport fault or missing actual Task join | Do not release capacity or report successful presentation shutdown. Sticky fault pins/quarantines; no-progress close remains pending. Expose `cleanupPending` independently of capability native exit. |

The existing core close order needs a narrow extension: synchronously stop/revoke,
finish the moved observation, await ordinary operation tail, finish any remaining
pre-bind/current binding lifetime, then close store and begin outer reservation
close. A lifetime already finished is idempotent. Do not await the worker actor from
a presentation callback or await that callback's consumer from itself. Swift fatal
allocation/process termination is not represented as a recoverable Java exception.

The prepare-to-core handoff is an explicit one-shot move under a setup guard:
`open` owns obligation + prepared lifetime until `CapabilityColdStartCloseCore`
successfully accepts them; only then does the guard disarm. A throwing constructor,
cancellation check or opening admission cannot bypass the guard's explicit async
cleanup. Do not perform async cleanup from deinit. Before C owner acquisition the
guard can retire an unused obligation synchronously; after acquisition it must
retain it through the same real Task/fence join or quarantine it. Ownership moves
only once, so the open catch and core close cannot each start a replacement Task.
The fixed lifetime record also tracks checked setup stages: acquired-empty,
model-published, wrapper-published, bound, retiring, reclaimed/quarantined. An
acquired-empty RETIRE may succeed without model lookup because no model/JNI state
was ever installed. A missing weak model after model-published is an invariant
failure and cannot be interpreted as proof of cleanup. A newly created JNI weak
reference remains a main-thread local cleanup obligation until successful slot
publication; a rejected/closed attach deletes it on that same thread before
returning. Thus each recoverable setup failure has either a known-empty retirement
or a concrete still-counted owner; there is no untracked interval after C acquire.

Attempt retirement and facade retirement differ only in the facade attachment
lease. For in-call signed fallback, attempt RETIRE clears the old Java tree,
listeners/probe and every old attachment/input identity, then releases its endpoint
after the full join/fence. The facade may keep one weak wrapper reference charged
to its outer presentation obligation; that reference has no valid input or health
authority. A next bind acquires a fresh endpoint/Task, and its main-Looper helper
issues a new attachment identity to that same previously admitted weak wrapper.
This is a fresh numeric entry, never retargeting the old attachment/input entry.
Java stores the new current detach token synchronously; old listener/probe tokens
stay stale even if revision/node values match. No strong wrapper/Activity is held
while between attempts.

If final close arrives after an attempt endpoint already reclaimed, `binding.close`
acquires one fresh **terminal-only pre-bind lifetime** to delete that facade weak
reference and retire model state on the main Looper. It uses the same presentation
Task protocol; it adds no concurrent Task or alternative cleanup executor. Acquisition
is serialized with bind, and the old Task has actually joined before this Task is
created. If acquisition is unavailable/faulted, retain/quarantine the counted weak
reference and report `cleanupPending`; do not delete it on an arbitrary Swift worker
or release the obligation. A final close latch already visible to the old RETIRE
allows that helper to delete it directly, avoiding this sequential extra lifetime.
The binding must test all three final-close timings: before, during and after the
attempt RETIRE. A pre-bind endpoint with no attachment still runs its bounded
terminal protocol before reclaim.

## Bounded implementation ownership after acceptance

All paths below are a proposed assignment. Root must freeze this contract and
assign each shared file before work starts. Keep the existing unsupported
non-Apple fallback and CLI capability/resource rejection guards until final link
and integration acceptance; a helper-only cross-build cannot enable signed mode.

| Lane | Exclusive production ownership | Tests/evidence |
| --- | --- | --- |
| Root / common activation | `capability-activation/Package.swift`; `CapabilityGuestUIRuntime.swift`; conditional split of `CapabilityGuestUIPresentation.swift`; `CapabilityInstalledExecutionMode.swift`; `CapabilityAttemptReservation.swift`; typed lifetime field/joins in `CapabilityColdStartControl.swift`, `CapabilityColdStartWorker.swift`, `CapabilityColdStartRuntime.swift`; new common `CapabilityGuestUIPresentationLifetime.swift` | Apple signed facade/model/window regression; outer obligation/pre-bind/close-install/fallback tests; root owns STATUS/work graph/gates and final integration. |
| C transport owner | Existing `native/android/signed-guest-ui/transport/{transport.c,platform_android.c,include/mixer_ui_transport.h,internal.h}` only | Independently authored fixed progress/fault/lost-wake/held-progress-tail tests, existing26 cases and reviewer probes; no Swift/UI source. |
| Swift binding owner | New `capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIAndroid.swift` and `CapabilityGuestUIAndroidRendezvous.swift`; new private C module/header wiring assigned by root | Weak lookup, scalar registry, fixed exported hooks, native helper/data-only progress gates and deterministic host integration tests. No independent activation coordinator. |
| JNI / Java owner | New `native/android/signed-guest-ui/bridge/{signed_ui_jni.c,mixer_signed_ui_jni.h}`; new wrapper/probe files under its `app/src/dev/mixer/android/`; coordinated **sole** shared edits to existing `Json.java`, `UiPacket.java`, `NativeRenderer.java` | JVM decoder/scalar/overlay/probe-state tests; real host JNI weak/exception/UTF8 tests; actual Android Looper/widget harness. No edits to compiled `bridge/jni.c`, `mixer_android.h` or checklist Activity. |
| Integration owner | Explicit signed fixture Swift entry/Activity/manifest/build driver and integration tests under `native/android/signed-guest-ui/` | Full native VM/activation/JNI/class source closure and unsigned APK inspection; signed host end-to-end, emulator receipts separately. No generator migration/published package claim. |

The proposed transport import must expose only its independently authored private
C header; do not copy C into generated Swift source or add a second implementation.
No third-party engine, generated code/test fixture or new dependency is needed.
Do not freeze a public Android profile digest until the actual supported closure
exists. Root separately reviews identity2/release3/profile/milestone selection,
API30 floor and installed adapter availability before enabling mode checks.

## Required executable acceptance, all currently pending for this binding

| Executable suite | Minimum assertions and scope |
| --- | --- |
| Swift Debug/Release/TSan | Existing Apple suites; one pre-bind Task; no model/frame retained while parked; close at every setup transfer; double bind; failed consumer install; actual Task held after RETIRE; store/adapter/presentation obligation independence; capacity16; fallback cannot reuse a pinned endpoint. Host evidence only. |
| Native rendezvous + Swift runtime | Publish-before-request; complete-before-request-return; stale/duplicate/wrong owner/waiter/kind; checked exhaustion; terminal request once; hints before wait/during apply/after completion; empty-drain count settles; explicit cancellation does not abandon waiter. Real Swift continuations required, not synthetic C joined flags. |
| Progress integration | Fence before/after registration and second check; hold completion C tail, platform callback tail, actual Task tail and progress hook tail separately; verify only owner-dependent tails block owner reclaim; progress owns no model/JNI/endpoint; no no-helper callback loop; fault originates on worker/callback; two bounded joined callers; late old token after slot reuse. |
| JNI/JVM | Known classloader/install checks, region/fullUInt64/exactUTF8, pending exception/allocation failures, weak root collection, local-frame release, wrong thread/reentrancy, no attach/detach, stale reference table entries. Ordinary JVM test renderer is no Android widget proof. |
| Android API30 arm64 compile/link/package | Full existing signed facade/native VM/dependency closure plus actual hooks/JNI/classes; undefined hooks fail link; exact source/archive/tool hashes and ELF/APK inspection. Existing SDK triple28 may build minAPI30 app; profile/manifest must both say30. No downloads or signing keys. |
| Android emulator native integration | Actual Java main Looper and NDK callback thread identity; signed fixture start -> native button -> fixed guest event -> granted KV completion -> replacement widget -> native draw/later-frame observation -> worker milestone. Negative hidden/unfocused/no-layout/no-draw/paused/stale-probe paths; no health without observation; teardown/lifecycle/reopen and stalled callback races. Emulator is permitted and separate from physical evidence. |
| Physical Android/iOS / FieldLog / release / GA | **Pending, excluded here.** No physical discovery/run/reconnect request. Immutable separately published FieldLog packages, dual-platform meaningful OTA, accessibility/performance/recovery and accountable gate reviewers remain required by the product plan. |

Record real commands, tool versions, selected source/tree hashes, outputs and
scope per run. Independent review must cover progress-hook lifetime safety and
the exact Android main-Looper/JNI mapping before root enables the binding. This
design and its inspection receipt are not executable tests of unimplemented code.
