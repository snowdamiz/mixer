# Private Android owner integration: proposed Slice B seam

This is a preparation proposal for root selection, not an implementation or an
acceptance receipt. It refines Slice B of
[the existing boundary](android-owner-effect-contract.md), rather than replacing
its observer repair, public-routing prerequisites, or full acceptance matrix.
The read context is `4e48ac1a3c1593d46c0dcbaf207053ff5e1b6d5d`, with the frozen
Slice A candidate observer identified in
[this packet](../verification/android-private-owner-effect-integration-proposal/receipt.json).
Slice A's independent review was running at that read boundary; this proposal
does not accept it or authorize editing its frozen files. Root must first accept
Slice A and explicitly select the following coherent implementation closure.

The binding W05 work remains native lifecycle, interaction and accessibility
qualification. Product plan sections 7.4, 8.1–8.3 and W05 require Swift state
ownership, concrete native validation and shared observable behavior. This
private integration supplies a missing lifecycle adapter; public `MixerActivity`
remains V1, API 28–35 remains unsupported by private V2, and native runtime,
physical, separate-repository published FieldLog, signing/store and GA evidence
remain pending. No dependencies are proposed.

## Choices to select together

Use one `NativeOwnerV2` per private Activity/root lifetime, the accepted
`OwnerLifecycleV2` without behavioral edits, one concrete observer, one bound
renderer, and one coordinator. Register before any session creation. Replace
the lazy renderer-owned registration path entirely for V2. Preserve the existing
two-argument `NativeRenderer(Context, Events)` exclusively for V1; it must reject
V2 capture/prepare calls without the explicit V2 binding.

Two source-grounded choices make this workable:

1. Split observer allocation from registration. The outer owner must hold the
   observer before registration can synchronously deliver detach or throw.
   The current constructor registers all eight sites, so its caller cannot yet
   store that instance when such a callback arrives. Add one-shot `register()`;
   retain Slice A's same slots, exact removal targets and unwind algorithm.
2. Make coordinator construction an inert allocation/binding step. Move
   `NativeBridge.create()` from its constructor to `renderInitial()`. A returned
   coordinator can then be held locally before acquisition callbacks and can be
   completed/disposed after a terminal callback. Construction must not acquire
   an engine session, register listeners, attach views or perform capture.

Both changes alter private seams and require fresh tests against actual changed
sources. Neither is claimed to be covered by Slice A or the accepted core's
earlier tests. Keeping registration inside the observer constructor is possible
only with a separate acquisition/report protocol; it adds a second partial
publication problem. The two-phase observer is the recommended choice.

## Exact proposed package-private surface

These signatures are a contract for a later implementation, not available APIs.
`OwnerLifecycleV2.Token` remains opaque and package-private.

```java
final class NativeOwnerV2 implements AutoCloseable, NativeEnvironmentV2.Sink {
    // Construct all bookkeeping; do not register or create a session here.
    NativeOwnerV2(Activity activity, FrameLayout root);
    void start();                    // exactly once; registers then probes
    void onResume();
    void onPause();
    void onStop();
    @Override public void close();   // Activity onDestroy; terminal, idempotent
    boolean hasCommittedPresentation();
    CleanupLedger cleanupLedger();   // borrowed bounded diagnostic object
    @Override public void changed(NativeEnvironmentV2.Observer source,
        NativeEnvironmentV2.Change change, Throwable failure);

    // Same concrete instance is shared by owner, coordinator and renderer.
    static final class Fence {
        boolean terminal;
        boolean drawAllowed;
        boolean inputAllowed;
        OwnerLifecycleV2.Token operation; // direct terminal-operation identity
    }
}

// Inside NativeEnvironmentV2:
enum Change { INVALIDATED, DETACHED, EPOCH_EXHAUSTED, REGISTRATION_FAILED }
interface Sink {
    void changed(Observer source, Change change, Throwable failure);
}
// Replace Observer(NativeRenderer, Activity, FrameLayout):
Observer(Activity activity, FrameLayout root, Sink sink);
void register();                     // NEW -> REGISTERING -> READY or RETIRED
void bindRenderer(NativeRenderer renderer); // once, READY only
NativeEnvironmentV2 capture();       // READY + bound renderer only
CleanupLedger cleanupLedger();       // existing eight slots, borrowed

// Replace NativeCoordinatorV2(Activity, FrameLayout):
NativeCoordinatorV2(Activity activity, FrameLayout root,
    NativeEnvironmentV2.Observer observer, NativeOwnerV2.Fence fence,
    NativeRenderer.Events nativeInput);
void renderInitial();               // create one session, then operation 0
void dispatchInput(byte[] envelope); // operation 1; synchronous caller only
void refreshEnvironment();          // unchanged retained-packet ownership
void sealGatesScalar();             // no Android calls/callbacks/allocations
void closeFromOwner();              // idle only; at most one real disposal
CleanupLedger cleanupLedger();      // retained renderer/destroy outcomes

// Preserve V1 constructor and add an explicit V2 constructor:
NativeRenderer(Context context, Events events,
    NativeEnvironmentV2.Observer observer, NativeOwnerV2.Fence fence);
void sealScalarV2();                // close current + pending flags only
void cancelInputV2();               // separate, callback-capable cleanup
```

`CleanupLedger` above denotes each component's own preallocated, fixed-field
diagnostic type; it is not a shared mutable log. Expose read access, not setters.
The owner ledger retains a first primary `Throwable`, first fatal `Error`, an
owner terminal cause, and independent cancel/unregister/coordinator disposition
slots. Observer retains its eight acquisition/removal slots. Coordinator retains
renderer-dispose and engine-destroy slots. Each slot distinguishes not requested,
deferred, attempted, returned and failed/uncertain as applicable. A dead observer
target remains dead/uncertain. Returned means the call returned, never that the
OS or JNI resource was reclaimed. Repeated observation allocates no new report.

The owner holds fixed fields for Activity, root, Handler, core, lifetime token,
fence, observer, one owned drain runnable/token, one active operation/kind,
in-flight opening coordinator, adopted coordinator, presentation token, window
identity, registration-in-progress, pending unregister token and cleanup ledger.
It retains no input bytes, packet bytes, event backlog, retry queue or history.
The runnable carries its exact drain token; it cannot borrow the newest token
from an owner field when delivered. One queued runnable plus one executing
operation is sufficient. Test-only factories/queues must be confined to the
closed host harness or package-private injection; production always uses the
real observer/coordinator and main Handler.
Remove `AutoCloseable` and the old `close()` entry from the package-private
coordinator; the outer owner is the sole disposition caller through
`closeFromOwner()`. Migrate coordinator-only tests to that explicit entry. The
coordinator remains responsible for its own failure retirement and retained
cleanup ledger.

## Registration, binding and readiness

`start()` enforces the real main Looper first, allocates/stores the one observer,
marks registration in progress, calls `register()`, and clears that marker in a
`finally`. Every callback field and sink must be assigned before the first add.
The observer constructor may resolve its fixed targets but acquires no listener.
`register()` retains Slice A's before-add ownership and after-add terminal checks;
it never resumes acquisition after retirement. `capture()` and `read()` continue
to reject incomplete registration. `bindRenderer` rejects null, foreign-context,
retired, incomplete and any second binding, including the same identity. Capture
authority is assigned once and is never supplied by caller-created environments.
`NativeEnvironmentV2.current(renderer)` still checks that exact bound identity,
generation, window token and second concrete tuple read.

There is one `Sink` implementation: the outer owner. Observer notifications no
longer call the renderer directly. Ordinary notifications advance the observer
generation before calling the sink; terminal notifications set observer retirement
before the sink. During `REGISTERING`, notifications may dirty/seal the owner but
cannot open. A registration failure calls the sink terminally before removal
callbacks. A terminal callback while registration is active defers the owner's
`UNREGISTER` effect until `register()` unwinds; the observer's own slot algorithm
still cleans the uncertain acquiring slot after its add returns/throws. Report
that ledger, then complete the exact core cleanup token. Do not report an
unregister pass merely because the outer `close()` call returned reentrantly.

The same observer owns layout, attachment, focus, insets, configuration, contrast,
high contrast and animator notifications. No second readiness listener set is
added. Component callbacks already reach this observer; Activity must not also
forward configuration into a competing observer path. Activity forwards only
resume/pause/stop/destroy. Insets remain dedicated-private-root, single-setter
ownership; V1's separate padding listener is untouched.

`probeWindow()` reads the actual bound Activity/root: destroyed state, attachment,
`Activity.getWindow()`, root window token, positive width/height, root insets and
window focus. Root context must be that exact Activity. A small retained
`WindowIdentity(Window, token)` has stable identity only while both actual values
are identical; this is the `WindowFacts.window` value, not a concrete capture.
Before the first ready observation its value is null. After binding, a changed
Window or token produces a different identity and the core rejects window loss.
Do not manufacture Activity/root identities to force a core reason.

Ready means registered, not destroyed, attached, actual Window and token present,
width/height positive and root insets non-null. A fresh probe on runnable delivery
is mandatory. An attached zero-size or inset-less root waits for a real observer
notification without polling or self-reposting. API/support/descriptor/contrast
checks remain in actual capture/prepare and can reject an otherwise ready core
operation. Foreground/focus affect input admission, not the readiness definition.
Every entry, including stale delivery, checks the real main Looper before state.

## Scalar sealing and transaction completion

The first terminal action is `fence.terminal = true`, followed by
`drawAllowed = inputAllowed = false` and direct closure of all current/pending
renderer gate `open` flags. Dirty notifications close the latter flags without
setting terminal. These operations must have no native call, collection walk,
thread-check callback, allocation, sink dispatch, cancellation or core call.
Only then may the owner probe, call the core, remove Handler work, unregister,
cancel toggles or dispose a coordinator. Initial gates start closed.

Split today's `environmentInvalidatedV2()` and `retireV2()`: their `invalidate()`,
`setVisibility()`, toggle `setPressed()` and parent interception callbacks belong
after the scalar barrier. `disposeV2()` must no longer close the observer. The
outer owner owns that single removal path. A renderer can retire itself, but must
close shared scalar authority first and notify its coordinator/owner outside the
commit/finish interval, so an internally retired renderer cannot leave live core
input authority. No fallback lazy registration path is retained.

`Gate.current()` first reads shared terminal/draw flags, then preserves concrete
presentation checks. `Input.open(record)` first reads shared input authority,
then preserves current-record identity, enabled/attached/shown/focus, capture
and toggle-binding checks. IME wrappers, keyboard and accessibility must keep
using that gate; acquiring a new input connection while sealed should return
null before calling the native superclass. Retained old connections must reject
edits. No stale IME/control callback may bypass the outer input sink.

`OPEN_INITIAL` retains a local coordinator identity before `renderInitial()`.
After every callback-capable preparation/attachment step, candidate/precommit
validation checks the shared terminal fence and exact operation identity in
addition to existing installed/environment/interaction/journal checks.
The owner sets `fence.operation` to the exact core operation before entering the
coordinator. `enter()` snapshots that non-null identity; `Candidate` retains the
same identity. Validation and finish compare those references directly. Clear
the field only after the coordinator returns and the completion is processed.
Do not use `drawAllowed` or `inputAllowed` to authorize attachment mutations;
they are deliberately false during a normal operation. Mutation requires a
nonterminal fence and that operation identity.
`Record.bind`, text/title helpers, hierarchy installation, layout and rollback
contain multiple native setters; checking only after an entire `bind` or loop
is insufficient. Insert direct shared-fence checks after callback-capable
setters and before the next mutation. No later mutation or rollback may reopen
gates after terminal reentry. Terminal rollback may fail closed and retire;
preserving an old live presentation is forbidden.

Before engine commit, perform all concrete captures and candidate checks,
including the direct fence check. Preserve this successful path literally:

```java
int status = NativeBridge.commitV2(session, token);
if (status == 0) {
    renderer.finishV2(candidate, journal); // prepared scalar/reference swaps only
    committedPacket = packet;
    return;
}
```

`finishV2` may read trusted shared fence fields directly along with existing
scalar/reference checks. Do not call `core.permits`, `core.complete`, a predicate,
the sink, capture, cleanup, native setter, user callback or an allocating helper
between commit and finish. Keep the existing failure path for invalid/unknown
outcomes terminal. JNI commit's existing scalar protocol is unchanged.

After finish and the coordinator's `active=false` finally, the owner completes
the exact operation with the exact coordinator identity. Only successful finish
sets `committed=true`. It then reads the core snapshot and publishes the new
presentation token and scalar draw/input flags. Draw opens only for a live clean
presentation; input additionally requires foreground and focus. If the epoch
changed during the operation, finish does not reopen authority: the dirty core
keeps scalar gates shut and issues one subsequent drain. A token-allocation or
completion failure after commit retires the whole lifetime; there is no retry.

A concrete tuple mismatch discovered synchronously by `presentationCurrentV2`
also seals scalar flags before work. Route its dirty notification through the
same bound observer's `invalidate()` and owner sink, so a delayed native listener
cannot leave the owner clean and unscheduled. Do not leave today's local-only
renderer invalidation as a second lifecycle route. Terminal observers remain
inert. Each effect dispatcher rechecks the scalar lifetime and token/owned slot
before applying a previously returned decision: reentrant cancellation can retire
the owner before an older `QUEUE_DRAIN` in that batch is reached.

## Input, refresh and the one drain

The renderer's V2 events target `NativeOwnerV2.nativeInput(byte[])`, replacing
`NativeCoordinatorV2::nativeInput`. The owner checks core `admitsInput` against
its exact presentation/lifetime, calls `dispatchInput`, immediately runs its
single `DISPATCH_INPUT` decision using that caller's bytes, and completes before
returning. Accepted bytes exist only on that stack. Rejected, reentrant,
background, unfocused, stale or dirty events are never buffered/replayed.
Ordinary rejected native edits may be contained only after both owners are
terminal, with the actual failure retained; a fatal `Error` always escapes.
Existing programmatic coordinator inputs in tests must use the selected owner
entry or an explicitly scoped coordinator-only fixture.

Execute `REFRESH_COMMITTED` only through the same coordinator's
`refreshEnvironment()`. The coordinator continues to own the exact retained
`byte[]`; owner receives neither its copy nor a replacement. No create, exchange,
prepare/commit/abort engine call, dispatch, Swift revision advance or effect is
permitted in a successful refresh. Capture/renderer work remains real. Assert
reference identity, bytes and engine call counts independently. Dirty during
refresh remains dirty and produces one later drain after completion.

Every `QUEUE_DRAIN` decision posts one token-carrying runnable to the main
Handler. Consume the owned queued slot before probing/delivering it; only its
exact token can start an operation. A stale runnable cannot consume the current
slot or invoke an effect. A false/throwing `Handler.post` is terminal, not a
retry. `CANCEL_QUEUED` consumes its owned runnable before `removeCallbacks` and
records attempted/returned/failed. Removal return alone cannot prove that no
delivery remains; lifetime and token checks make an ineffective cancellation
inert. Duplicate notifications may advance epochs but never add a second owned
queued drain.

## Disposal and failures

An owner terminal callback during any operation immediately seals, lets cancel
and unregister finish independently, and defers coordinator disposition until
that exact operation returns. Do not call current nonreentrant coordinator
`close()` inside a setter/JNI/render callback. A coordinator returned by an
opening factory after terminal state is never published as live; scalar-seal it,
complete the original opening with that acquired identity, and process the
core's one `CLOSE`. A never-returning operation retains deferred close, explicitly
pending. No timer invents completion.

`closeFromOwner()` enforces main/idle, records actual disposal attempts before
each call, and never repeats consumed renderer/session dispositions. If the
coordinator internally retired during a transaction, it returns its retained
ledger instead of invoking a second renderer disposal or engine destroy.
`session=0` and `committedPacket=null` still publish before cleanup. Observer
unregister, renderer dispose and engine destroy are independently attempted;
one throwing action cannot skip the other owners. Renderer cancellation should
attempt its bounded record set despite a leaf failure, retaining first failure
and first fatal rather than an unbounded list. All gates stay sealed throughout.

Core `cleanupComplete` means the runner processed that disposition, not resource
release. The owner ledger carries uncertainty separately. Keep exact core bytes:
for failures with no matching core operation (such as Handler post or observer
generation exhaustion), seal and request `core.close(lifetime)` while retaining
the exact adapter cause in the outer ledger. `CLOSED` then records the core
disposition request; do not relabel it as the adapter failure's detailed cause.
Detach and registration failure use the existing corresponding core entries.

The core allocates decision lists/tokens; it is not an allocation-free safety
barrier. If it or completion bookkeeping throws `Error`, scalar-seal first and
use the preallocated outer cleanup slots to attempt cancel/unregister and idle
coordinator disposition directly. Do not fabricate absent core cleanup tokens or
report their completion: record `core-completion-unreported` and terminate the
owner. If an operation is active, direct disposition remains deferred until its
finally returns. No subsequent entry may revive the core through its older
nonterminal state. Catch original failures through all independent cleanup,
retain first primary and first fatal, and throw the fatal after those attempts.
Suppression is best effort after cleanup; allocating graph traversal must not be
required to discover an already observed cleanup `Error`. This replaces the
current coordinator's allocating `rethrowNestedError` dependency in the joined
path. Failure handling cannot promise reclamation after OOM or a never-returning
native call.

## Migration and bounded ownership

Root should select one owner implementation lane for the mutually dependent
`NativeOwnerV2`, `NativeCoordinatorV2`, `NativeRenderer`, `NativeEnvironmentV2`
and needed `NativeAppearanceViewsV2` edits. Their sink/fence/registration signatures
must freeze together before another lane uses them. Separate profile/host-review
lanes can then consume exact frozen sources; no concurrent lane edits these files.

| Implementation surface | Coherent migration |
| --- | --- |
| `native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java` | Move once to `native/android/app/src/dev/mixer/android/OwnerLifecycleV2.java` with exact accepted bytes; delete former canonical path. Update `run-owner-core-host.py` source path and compile the moved source. Historical packet snapshots remain evidence only. |
| New `NativeOwnerV2.java`; five existing Java seams above | Implement this selected join; no V1 Activity/Swift/JNI/schema changes. Remove renderer-owned observer registration/removal and direct coordinator native callback. |
| `NativeCoordinatorV2IntegrationActivity.java` and instrumentation | Activity creates/starts owner after setting the private root, forwards resume/pause/stop/destroy, closes owner in finally. Instrumentation waits for real readiness/owner presentation and drives real controls; no direct manual `renderInitial` bypass. |
| `NativeAppearanceV2Instrumentation.java` | Replace every manual renderer create/recreate/dispose site with one nested renderer-only fixture owning its explicit observer/fence and the real accepted core for issuing operation tokens; register/bind before capture, close observer and renderer on replacement/finally. It uses real core operations for each prepare/finish, rather than forged tokens or a production bypass. This fixture proves renderer behavior, not the joined owner. Preserve foreign-owner tests using separately owned fixtures with distinct dedicated roots; never install two owned inset listeners on the same root. A foreign-root fixture need not capture/render to test candidate-owner rejection. |
| `NativeCoordinatorV2HostTests.java` and its fixed leaf set; observer host suite/leaves | Migrate constructor/capture/cleanup signatures and keep their fault assertions. Add actual one-shot registration and binding controls to observer suite. Leaf updates do not qualify Android behavior. |
| New `NativeOwnerV2HostTests.java`, closed `NativeOwnerV2HostLeaves/**`, bounded runner | Primary host join compiles actual owner + moved core + actual coordinator + actual observer, substituting only Android/JNI/renderer leaves. A separate concrete renderer closure is required for scalar/gate/source behavior. |
| `AndroidSDKCompatibility.swift`, focused Swift/Python admission tests | Root selects a new fixed profile only after frozen candidate bytes and path closure are known. Maintain the single compiled authority and its rendered-driver projection. Root coordinates metadata/delivery. |

The likely successor is source-pair.3, but this document selects no profile ID
or hash literals. Compared with profile 2, mapping adds `NativeOwnerV2.java` and
the moved `OwnerLifecycleV2.java` (20 to 22 adapter members if no extra source
files are selected), and changes coordinator/renderer/observer and possibly
native views identities. The 22 SDK members, default descriptor and wire contract
should remain identical; prove that claim against selected bytes. `AndroidProject`
already exports from the compiled map, so no second hardcoded export list is
needed. Explicit fresh-project recreation/migration must reject old profile-2,
edited and recomputed locks at common Swift and direct driver preaccess. Never
refresh profile 2's accepted map silently. The moved source must enter export
exactly once; reject extra/copied canonical owner sources.

## Executable acceptance required after selection

None of the following fixtures was run by this proposal. The packet's executable
checker verifies only custody, source anchors and proposal coverage.

| Future fixture | Actual production subjects and independent assertions |
| --- | --- |
| Owner join with manually drained Handler | Actual new owner, moved accepted core, real coordinator and real observer; closed Android, renderer and NativeBridge leaves. Assert real observer add/remove identities, one owned runnable, exact core tokens and coordinator engine calls, rather than replaying an expected decision log. |
| Readiness/registration/binding | Unattached/zero-size/no-insets waits; fresh queued probe; exact Window/token changes; registration callbacks before ready; every partial-add unwind; once-only bind and foreign/stale capture rejection. Preserve Slice A's complete eight-slot failure controls. |
| Reentry and late acquisition | Terminal/dirty at create return, capture, prepare, each attachment setter/hierarchy/layout seam, precommit, input/refresh and cancellation/removal. Assert actual current/pending gate flags before fault callback body; no reentrant close, later commit, reopened gate or live publication. Late acquired resource is disposed once only after return. |
| Actual coordinator refresh and input | Real methods with counted JNI leaves: exact retained reference/bytes and zero engine calls for refresh; input operation 1 synchronous once; no rejected input retention; presentation publication after finish/completion; dirty epoch requires later single drain. |
| Cleanup/fatal controls | Independent cancel, unregister, renderer dispose and engine destroy failures including fatal Error after ordinary primary; core allocation/completion fault; post false/throw; stale cancellation delivery; internally retired coordinator; repeated/foreign completion; operation-never-returned pending. Inspect attempted versus returned/uncertain, not just core closeDone. |
| Concrete renderer/native-view host or compile closure | Actual scalar sealing/gating methods plus independent callback-capable leaf hooks at setter boundaries. Source inspection guards supplement behavior; they cannot prove framework draw/IME/setter execution or JNI purity. |
| Commit/finish guard | Independent exact-source/compiled-bytecode review that successful commit-to-finish contains only existing branch, direct call and prepared swaps. Fault-hook methods belong outside that interval. A counted leaf test alone cannot prove absence of production callbacks/allocations. |
| Cross-compilation/profile migration | Actual selected fresh CLI export, complete Java 17 compile against pinned SDK, D8 min28, ordinary app-owned Swift/JNI unsigned build; fixed-map/default/wire checks and before-tool/output rejection controls. Do not invoke `native/android/build.py`. |

Retain exact source/tool/argv/streams/results and clean only owned bounded scratch.
Keep native Activity/instrumentation authored/compiled but **not run** during the
active pause. Later native qualification must exercise real draw, current/pending
gates, IME/key/accessibility, actual setters, detach/recreation and background
transitions; physical-phone and final product gates remain separate. A successful
host join or source guard does not qualify public V2, OTA release, or actual
Android reclamation.
