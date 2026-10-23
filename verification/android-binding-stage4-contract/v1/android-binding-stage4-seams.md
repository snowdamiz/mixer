# Stage 4: real Swift/C Android binding seams

Status: proposed for root coordination, 2026-10-23. This is a bounded next-lane
proposal, not implementation acceptance. The binding authority is
`docs/android-signed-ui-binding-contract.md`, accepted in
`verification/android-binding-contract-acceptance.json`. Product scope remains
`mixer-product-plan.md`; Android signed UI stays unsupported.

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
| `CapabilityGuestUIAndroidBinding.swift` | Resource-free facade shell, preparation/setup guard, bind/final-close state machine and checked moves. |
| `CapabilityGuestUIAndroidRegistry.swift` | Process-lifetime 16 facade records, 16 endpoint records, one admission mutex, checked IDs, lookup/publication/removal. |
| `CapabilityGuestUIAndroidLifetime.swift` | Sole pre-bind Task, bind-or-close gate, exact rendezvous, native authoritative join and sealed endpoint evidence. |
| `CapabilityGuestUIAndroidResources.swift` | Reservation-owned reconciler/exchange/ticket/render state, checked transient aliases, synchronous leased inner helpers and sealed cleanup evidence. |
| `CapabilityGuestUIAndroidProgress.swift` | Sixteen permanent progress cells and fixed C exports `mxuit_drain`, `mxuit_complete`, `mxuit_progress`. |

The lane also owns a new `native/android/signed-guest-ui/binding/include/` header
and module map importing the **unchanged** transport header and declaring the
three already-frozen `mxis_*` methods. The stage 4 lane may not edit transport
sources/tests, existing runtime/control/worker files, installed modes, profiles,
JNI/Java, renderer or packet code. Root owns the shared changes in section 2.

Independently authored host fixtures, harness and command runner belong to a new
`verification/android-binding-stage4/` directory. They compile unchanged new
production Swift files, the exact C `transport.c`, real `MixerGuest`/`MixerUI`, and
root's common lifetime changes together. No replacement source, fake common
lifetime, stubbed Task join, generated fixture or imported implementation is
allowed. Any general-purpose dependency must be recorded in `THIRD_PARTY.yml`;
none is required by this proposal.

The normal package need not acquire a C transport dependency yet: root may approve
the private module-map import behind `canImport(CMixerUITransport)` while the
regular build continues its frozen unsupported path. Harness linkage supplies
that module and fixed host-platform symbols. There is no runtime selector,
Boolean, test flag, callback setter, injected driver or arbitrary closure that
turns unsupported Android into an admitted profile. A separate root-owned build
integration is required before a normal Android build can consume these files.

## 2. Minimum shared changes, root-owned and frozen before dependent work

The existing common lifetime is an Apple implementation: its lifetime receipt
has only a `fileprivate init(apple:...)`; facade cleanup construction is private;
`finish` awaits the actual optional Task, then weakly calls the Apple retirement
protocol returning `Bool`. The current gate retires the obligation after a retired
Apple lifetime. These facts are intentional stage 2 limits. **Do not** reuse the
Apple `Bool`/missing-weak-owner behavior for Android, expose raw receipt/permit
initializers, or let endpoint retirement alone retire Android resources.

Root must make these bounded changes, preserving the existing Apple branch:

1. In `CapabilityGuestUIPresentationLifetime.swift`, add a concrete Android
   backend case consuming a one-shot `CapabilityAndroidLifetimeCapsule`. The
   capsule is constructed only by the fixed registry/lifetime implementation,
   after the C owner and sole real Task have been published. It contains the
   exact facade/lifetime/endpoint IDs, actual `Task<Void,Never>`, and a resource-free
   concrete `CapabilityAndroidLifetimeControl`; its constructor is file-private
   to the Android lifetime source. Consumption invalidates the capsule. Existing
   installation and permit move cells remain the sole authority.
2. The Android branch of common `finish(using:)` admits that exact permit once,
   requests stop, **awaits the capsule's actual `task.value`**, and only then
   constructs `CapabilityPresentationTaskReturnEvidence`. Its initializer stays
   file-private in the common lifetime source; its fields are exact IDs, never a
   `joined: Bool`. It invokes the concrete control's
   `joinNative(after: CapabilityPresentationTaskReturnEvidence)` and validates its
   returned sealed evidence against all three IDs before constructing the
   private Android lifetime receipt. Android never returns `noTaskCreated`.
3. Add `CapabilityPresentationEvidenceScope` to Android receipts/results with
   disjoint `androidHostHarness` and `androidNative` cases. A fixed host linkage
   can issue only host evidence. Native cleanup uses a separate sealed native
   witness type, with no conversion from a host witness. No caller-selected
   scope parameter appears on any constructor or preparation API. Root's future
   native factory must reject the host capsule/evidence type before any profile
   admission. The current public and portable factories remain unsupported.
4. Keep `CapabilityFacadeCleanupReceipt` construction inside its trusted type.
   Add a narrow consuming factory accepting a sealed
   `CapabilityAndroidFacadeCleanupEvidence`, never scalars, `Bool`, `Result<Void>`
   or an arbitrary protocol implementation. The producer and checks are section
   5. Add finite Android transport/cleanup/invariant failure codes, retaining
   scalar-only diagnostics. Constructors remain inaccessible to ordinary and
   `@testable` clients.
5. In `CapabilityPreparedPresentation.swift`, add a concrete Android gate/final
   retirement branch. Android finalization must execute section 6 before calling
   `obligation.retire()`; its successful lifetime receipt alone cannot enter the
   existing Apple release path. The common setup guard still owns the initial
   permit until exact core acceptance and performs explicit async failure cleanup.
6. In `CapabilityGuestUIPresentation.swift`, reserve a private Android binding
   delegation seam without enabling normal `prepare`. A harness-only factory
   lives in the verification module, invokes the concrete Android engine, and
   returns host-scoped observations. The Apple MainActor class and public model
   behavior stay on their existing implementation. No other runtime/control/
   worker change is necessary for the stage 4 host slice.

These are proposed exact type/operation names; root may rename them before the
freeze. The ownership and evidence requirements are invariant. Root and the lane
must agree on the concrete capsule, task-return evidence, native-retirement
evidence and final-gate signatures before either edits a shared dependency.

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
one presentation Task. Existing coordinator consumer/timer and core cleanup Task
remain separately counted; no join-coalescing, detached cleanup, polling, timer,
per-owner thread/FD/Handler, dynamic dictionary or growing receipt history is added.
A suspended final joiner may indirectly retain its reservation through its closing
stack; that is a bounded reference, not a scalar or resource alias.

The weak box never means cleanup succeeded: after resources are published, failed
promotion is a typed invariant/quarantine. Only an exact acquired-empty stage may
retire without promotion. Setup must transfer the persistent resource reference to
the obligation and relinquish its local alias before transfer to core or awaiting
failure cleanup. A UI outer trampoline enters C first, checks Swift scalars, then
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

The sole common permit owner waits actual `Task.value` and passes its unforgeable
return evidence to `joinNative`. That method validates exact IDs and its one-shot
state, reads the terminal outcome, and calls `mxuit_consumer_joined` exactly once
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

A sealed cleanup evidence instance contains only:

- Exact facade, lifetime, endpoint, active UI-entry serial and checked cleanup
  serial; native bridge-slot generation/disposition and evidence scope.
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
real Swift clear and entry checks above. An attached/published slot requires the
sealed stage 5 native witness; until it exists, finalization remains pending or
quarantined. A null/missing weak reference cannot turn a published slot into a
never-published slot. Host fixtures may own and actually clear host tree/listener/
weak-owner resources, but can issue only a distinct host witness, never the JNI
witness. Their receipts explicitly carry `androidHostHarness` scope. Common
receipt constructors reject cross-scope/cross-ID evidence and remain private.

## 6. Final close, aliases and destruction

Final close first latches Swift close/revokes input/probe under its gate, then
unlocks, calls C facade close and signals the exact data-only stop record. It
promotes no resource and is safe during helper reentrancy and between attempts.
The ordinary/observation moves remain those frozen by stage 2. Final ownership is
setup before transfer or the existing core cleanup job after transfer; its
one-shot move bit prevents a second final joiner.

Final finish joins the current permit (or reads its exact completed receipt after
ordinary/observation ownership has moved). Nil plus an unfinished current lifetime
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
sources. C-only ASan/UBSan can supplement this; a missing Swift-compatible mode is
reported as pending, not a pass. Full activation builds and frozen Apple/core/
portable regressions remain required. Private-constructor negative compilation
must run with ordinary and `@testable` imports. Linux CI linkage is a separate
check; Android API30/Swift6.3.3 compile/link is scope-limited cross-compilation.
No host pump, host pthread or MainActor proves Android's Java main Looper.

Each run records command/argv, environment, tool version/hash, source revision and
complete source/dependency manifest, output hashes, binary hashes, cases executed,
instrumentation limits, skips and evidence scope. Root reviews exact source and
receipt bindings before committing. Host success cannot establish Java weak
global deletion, actual JNI/Java stack return, draw/Choreographer health, mobile
lifecycle, a published FieldLog consumer, release/signing/store/customer/operational
or accountable GA acceptance. Phones remain disconnected; no discovery, physical
runs or reconnection requests are permitted.
