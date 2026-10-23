# Independent review of the private Android signed UI binding proposal

**Verdict: accept the direction for staged implementation only after the four
contract corrections below. Do not yet accept a complete binding implementation
contract or enable signed Android mode.** This is a review of an unimplemented
proposal, not a reproduced defect in an installed Android binding.

Reviewed proposal: `docs/android-signed-ui-binding-design.md`, SHA-256
`55ec2f34f031c744683272a8250fb2c614144cd4edb79f9b6be6c5bbeb458097`.
All 27 inputs in its inspection receipt still match. `receipt.json` and the
before/after manifests identify this review's selected sources, commands, tool
versions, six original host probe executions and their exact scope. The source
revision is `e299f1a60eb06dc9405021fc49ced215eaa42336`; other lanes have unrelated
dirty work, so the selected source manifests identify the inspected tree.

## 1. Blocker: count every JNI/model helper entry, including its return boundary

Proposal lines 69-75, 107-122, 276-283 and 331-335 allow fixed Java-origin entries
to attach/apply, activate, observe and detach. Only `mxuit_drain` has the C active
lease and `last_hook_epoch` update (`transport.c:237-260`). C reclaim checks only
that lease, completion, joined flag and prior callback epoch (`201-209`). Native
UI thread identity and a non-reentrancy boolean establish execution domains; they
do not register an independent JNI entry as an owner-dependent return obligation.

The unsafe permitted ordering is: an old attempt has retired, joined and been
fenced; a Java-origin helper resolves its model/attachment or promotes its weak
wrapper; another thread latches close and obtains the old endpoint's reclaim
success while the helper still owns its local model, JNI reference or postcheck.
Any direct helper permitted during the between-attempts facade lease is outside
the old C callback epoch. A model/JNI-local helper tail remains live even if its
last visible mutation finished. The proposal does not forbid that admission or
count that tail. In particular, a guard checked only after weak-model promotion
already acquires a per-facade owner outside the native retirement proof.

Freeze one of two structural contracts before the JNI lane starts:

- Every owner-dependent JNI/model helper first acquires a checked UI-entry lease
  in permanent numeric bookkeeping **before** weak-model lookup or JNI promotion.
  Final close prevents new leases. At most one non-reentrant entry may be active
  on the verified UI thread. Clear its local model/claims/packets/JNI frame before
  finishing the lease, then require a later accepted non-reentrant main-Looper
  callback to fence its return. Reclaim/facade retirement must check both the
  existing transport fence and this entry fence. Reuse the singleton wake path;
  a new per-owner Handler, queue, FD, thread or timer is unnecessary. The exact
  additional transport operation/epoch contract requires root/C-owner agreement.
- Or make all Java-origin ingress permanently allocated, scalar-only publication
  that cannot load a model, promote a wrapper, apply UI or destroy per-owner state;
  defer every such action to the already counted fixed drain. Merely naming an
  entry "fixed" is insufficient, and temporary weak-reference allocation needs a
  counted publication/rollback owner even under this alternative.

Tests must hold attach/activate/observe/detach after their last UI operation but
before their native return, race final close and fill the other 15 outer/native
slots. No capacity or resource release is allowed until the actual entry return
fence. Also hold a nested callback attempt while the entry is active: it must not
advance that fence. No MainActor dispatch is an Android Looper receipt.

## 2. Blocker: preserve facade lifecycle authority across attempt retirement

`nativeDetach(attachmentRef)` is the sole proposed detach entry (69-72). Attempt
RETIRE invalidates every old attachment/input identity (378-387), retains a weak
wrapper, and only a later helper issues the replacement attachment token. This
leaves no currently valid detach token between those two operations.

Concrete ordering: old attempt RETIRE clears token A; Java `onPause`/detach occurs
before the next bind helper; its only token A is stale and cannot resolve a live
attachment; fallback later creates token B for the still-reachable weak wrapper.
The required synchronous stop was lost, so the proposal permits replacement
admission after pause/detach. Observation visibility checks do not repair this
lifecycle admission failure.

Give the wrapper a distinct never-reused **facade lifecycle identity**, valid
until final facade cleanup, in addition to the attempt attachment/input/probe
identities. A fixed private lifecycle entry must resolve that exact facade and
wrapper and latch final close in the between-attempts interval. Alternatively,
define an equivalent permanent scalar lifecycle latch that replacement admission
must check before loading the wrapper. Do not restore input or observation
authority to old tokens or retarget A to B. Test pause/detach before, during and
after old RETIRE, between endpoint reclaim and replacement acquire, and just
before the replacement helper publishes B.

## 3. Blocker: endpoint reclaim is not final facade resource retirement

Lines 87-105 require one presentation obligation per outer reservation and release
only after retained-owner destruction. Lines 390-401 provide a terminal-only
lifetime when final close finds an already-reclaimed attempt. The proposal still
needs an authoritative result recording whether **facade** cleanup occurred;
checking whether an endpoint was present when close began is insufficient.

Concrete race: attempt RETIRE selects attempt-only cleanup; final close latches
after its final-delete check but before its return/completion/reclaim; `close`
joins that still-present lifetime successfully. The weak wrapper still exists.
Unless close examines an exact facade-retirement receipt after that join, it can
release the obligation or omit the necessary sequential terminal-only lifetime.
Testing "during RETIRE" must force this exact late-latch interval, not just close
before the helper's first load. Treat old-helper final cleanup only as an
optimization: after every reclaimed attempt, final close must examine the actual
facade cleanup state and, if needed, run the sequential terminal-only lifetime.

There is a second ownership issue in the proposed retained owner. The current core
and worker both strongly retain their binding (`CapabilityColdStartRuntime.swift:
95,104-106`; `CapabilityColdStartWorker.swift:13,23`), and the Apple binding strongly
owns its model (`CapabilityGuestUIPresentation.swift:241-243`). A presentation
obligation that simply retains that same binding cannot use
`reservation.retire` as a final-destruction receipt: the reservation only drops
its own reference (`CapabilityAttemptReservation.swift:77-96`); core/worker/setup/
closing-stack aliases can keep the model/resources alive. That destructor fence
only proves actual destruction when it drops the final resource-owning alias.

Freeze a resource-owning presentation object separately from the facade/control
shell. The reservation may retain that object, the public Android reference and
core/worker may retain only its read-only shell/numeric identity or a weak lookup,
and synchronous helpers may promote it only under the counted entry lease. The
one presentation Task must not retain it. Progress may retain it only indirectly
through the explicitly counted pending closing stacks discussed below. After actual
Task join, all native return fences, final weak-reference deletion, helper local
release and closing-owner tails, explicitly drop/move the final resource owner
outside locks before retiring the obligation. Empty public facade/snapshot shells
can outlive closure only if the contract excludes resources and execution authority
from those shells. An object merely becoming unreachable from a registry is not
proof of its destructor returning.

Required tests include a held final owner destructor, a second closing alias,
close-before-start, close-before-bind, each post-acquire constructor failure,
failed consumer installation, and final close after attempt reclaim. Filling all
16 slots must reject outer slot 17 until the real resource owner/destructor and
all required return fences finish. Store, adapter and presentation obligations
must retire independently; failure/quarantine of any one cannot release another.

## 4. Blocker: freeze join ownership, result handoff and record reuse together

Lines 231-248 permit two simultaneous join callers, while 250-256 remove the
Swift record immediately after C reclaim. The one-shot result's lifetime and
caller-tail acknowledgements are not assigned to storage. C's idempotent
`consumer_joined` is not an idempotent reclaim: a second `try_reclaim` after success
returns STALE (`transport.c:201-209`).

Concrete schedule to cover: both close continuations are signalled; caller A
reclaims/removes the old record; caller B remains queued; that fixed record is
reused for a new owner or terminal-only lifetime; B resumes with a Void wake and
rechecks its old identity. It must receive A's original exact success, not STALE,
the new lifetime's result, or a quarantine based on a successful prior reclaim.
It must not read per-owner storage after another caller destroyed that storage.

The smallest common-runtime change is to exploit existing ownership moves:
`detachObservation` moves the observation exactly once (`Control:184-189`), the
worker returns its old concrete aliases before fallback joins (`Worker:72-89`),
failed consumer installation joins locally (`112-119`), and core close joins the
moved observation then waits the ordinary tail before closing the binding
(`Runtime:113-118`, proposal 353-356). Assign one authoritative join owner per
lifetime; later idempotent calls read a retained immutable typed receipt. This
avoids simultaneous native reclaim callers without a new Task.

If root retains the proposed two-caller scheme, define a fixed result cell or
typed completion result that survives both callers, prevent record reuse until
all required result/tail acknowledgements have moved out, and reserve an eligible
Swift record **before** calling C acquire. Otherwise C can return an owner while
all 16 Swift records are still occupied by old joined results. Freeze the lock
order for admission, result publication and numeric record removal; no lock may
span a hook, JNI or continuation resumption. Counters reject overflow. Test A/B
in both orders, A held after success before publication, B held after wake, slot
reuse, terminal-only lifetime creation and a fault during the handoff.

## Progress-hook review and actual Swift host observation

The missing C fence notification is real: the current no-helper callback advances
`fenced` at `transport.c:229` and invokes neither fixed Swift hook. Existing C owner
and reviewer receipts are valid context for that C state machine; they are not
Swift/JNI/Android execution and were not rerun by this review.

A pending Swift continuation is not scalar-only ownership. It can retain its
suspended task and therefore its async stack's strongly captured closing owner.
That is acceptable only as an explicitly counted bounded closing lifetime. The
proposal recognizes two retained stacks, but the result/tail protocol in finding
4 and final resource release in finding 3 must make that accounting concrete.

I did **not** find evidence that every copied continuation necessarily perpetuates
that retention after resumption. `ContinuationLifetimeProbe.swift` is an original
host semantics probe using real `CheckedContinuation<Void,Never>` and
`Task<Void,Never>`, not a simulated C join flag. Its parked task strongly captures
an owner. A process-only callback moves the continuation, calls `resume`, and
holds both the copied continuation and its post-resume call tail. The actual
`task.value` returns, the weak owner becomes nil, and that owner's deinit flag is
set **before** the held process tail is released. This passed Debug, Release and
TSan with installed Apple Swift 6.4 (`swiftlang-6.4.0.34.1`), arm64 macOS. A second
case confirms that early terminal data does not replace an actual Task join while
the task body is parked. Total: two cases in three modes, six executions.

This supports the possibility of the proposal's non-circular healthy progress
hook. It does not establish Android Swift runtime behavior or prove any future
production capture list. Preserve the following narrow structure and test it
against the final Android toolchain:

1. Permanent fixed cells own checked numeric epoch/fault/sequence and bounded
   Void continuations. Before resume each continuation can indirectly retain its
   closing stack and owner; count that physical reference. Store no additional
   owner closure, model, JNI reference, endpoint object or frame alongside it.
   After consuming resume, test that the copied continuation no longer retains
   that completed owner on the final toolchain, as the host probe observed here.
2. Move exact continuation values out under the permanent-cell lock; merge fence
   monotonically and fault stickily; unlock before resume. After resume the hook
   may touch only permanent cells/scalars and consumed continuation values. It
   may not look up an owner again or execute a per-owner object's destructor.
3. Resumed closing stacks remain separately counted until their resource-owning
   aliases and tails have ended. Endpoint reclaim must not itself retire the
   entire facade obligation. Do not introduce a new owner epoch for this healthy
   process-only hook, which would recreate a circular fence requirement.
4. Explicitly define the fault fanout. A live presentation Task may be parked in
   `deliveryWake.next()` with no native rendezvous, so waking native waiters alone
   strands it. The saved data-only exchange/stop record mentioned at lines 100
   and 267 must stop all such tasks. If the fault path accesses that per-attempt
   object, first latch irreversible quarantine so it cannot race successful
   release; do not describe that branch as healthy scalar-only bookkeeping.
5. In final integration, independently hold actual Task tail, UI-entry/helper
   tail, C completion tail, platform callback tail, and healthy Swift progress
   tail. The first four owner-dependent tails must pin the appropriate resource;
   a proven process-only final tail need not pin an already-retired endpoint.

## Smallest safe implementation sequence

| Stage | Bounded contract and acceptance before the next stage |
| --- | --- |
| Common lifetime/obligation | Root owns a typed lifetime plus immutable exact receipt, single join authority or fully specified two-caller cell, presentation obligation at open, setup guard move, close latch and final facade resource state. Preserve Apple's public presentation behavior. Test setup/close/bind/fallback and held owner destruction on host. Keep Android unsupported. |
| C progress/entry fence | C owner implements independently reviewed fixed epoch/fault notification and the chosen additional JNI-entry fence contract. Preserve singleton pipe/static userdata/16 slots. Add first-fault, no-helper wake, lost-wake, held-entry and held-progress-tail probes plus existing C suites. Do not infer Task.value from C flags. |
| Swift binding | New owned files implement fixed registry/rendezvous, one pre-bind-or-delivery Task, publish-before-request, exact waiter/result matching, fault stop fanout and helper leases. Use a real Swift/C host harness with held actual task tails; no model/frame capture across suspension. |
| JNI/Java | New fixed wrapper/bridge, facade lifecycle token and fresh per-attempt attachment/input/probe identities; known-class/method calls only; scalar listeners; complete decoder before mutation; synchronous revocation; weak JNI promotion and local frame only inside counted helper. JVM/JNI receipts are scoped host evidence. |
| Android integration | Full signed VM/runtime/source link and package closure, actual Java main-Looper/pthread mapping, native widgets and draw/later-frame probe, lifecycle/fallback/fault tests on permitted emulator. Retain unsupported-mode guards until root accepts this complete integration. Physical Android/iOS remain explicitly pending. |

The official sources read for the thread/JNI boundary were Android's
[Looper API](https://developer.android.com/reference/android/os/Looper),
[NDK Looper API](https://developer.android.com/ndk/reference/group/looper), and
[JNI guidance](https://developer.android.com/ndk/guides/jni-tips). The API describes
thread-associated Loopers and thread-local JNIEnv use. The proposed later-entry
fences and this review's entry-lease recommendation remain implementation
reasoning requiring execution evidence; they are not claims of a platform
destruction guarantee.

Only `verification/android-binding-design-review/**` was written. No production
source, design document, dependency, status, graph, gate, original receipt, C code
or C test was changed. No phone discovery/query/run/reconnection request, emulator
execution, download, commit, push, publication or customer message occurred. No
GA, store, physical-device, immutable FieldLog or release gate is passed here.
