# Private Android owner integration: correction 1

This versioned source-only correction resolves C1–C3 from
[the independent contract review](android-private-owner-effect-contract-review.md).
It supersedes only the affected seams and acceptance rows of
[the original proposal](android-private-owner-effect-integration-proposal.md).
All original sealed files remain byte-for-byte unchanged. Root has not selected
implementation or a successor source profile. No product tests, cross-compilation
or native execution are asserted here.

The read revision is `b45963c03816112972499bd60073039f36916272`. Observer/profile 2
is separately accepted at this revision. The actual observer remains 14,318 bytes,
SHA-256 `814b00b91b458c1287cb9c924c099fc2e647e42501b09e09acd711fbe5b54dac`;
the accepted core remains 12,473 bytes,
`4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6`.
[The correction packet](../verification/android-private-owner-effect-integration-proposal/correction-1/receipt.json)
binds current sources, predecessor/review manifests, tool identities and source-only
results. Prior acceptance does not cover the proposed two-phase observer or join.

## Frozen surface and ownership

Keep one owner, one stored-before-registration observer, one bound renderer and
one held opening/adopted coordinator. Move the exact core into the export closure
once with no behavioral change. Keep the V1 renderer constructor and public
`MixerActivity` routing/padding unchanged. The following package-private surface
is the coordinated implementation contract; none exists yet unless already in
the accepted source. Types nested under `NativeEnvironmentV2` below are explicit.

```java
final class NativeOwnerV2 implements AutoCloseable, NativeEnvironmentV2.Sink {
    NativeOwnerV2(Activity activity, FrameLayout root); // bookkeeping only
    void start();                                    // exactly once
    void onResume(); void onPause(); void onStop();
    @Override public void close();                   // main first, idempotent
    @Override public void changed(NativeEnvironmentV2.Observer source,
        NativeEnvironmentV2.Change change,
        NativeEnvironmentV2.RendererCause rendererCause, Throwable primary,
        Error firstFatal);
    boolean hasCommittedPresentation();
    CleanupLedger cleanupLedger();                   // fixed borrowed ledger

    static final class Fence {
        boolean terminal, drawAllowed, inputAllowed, commitFinish;
        boolean rendererReportActive;
        long sealSerial;                             // starts at 1; no wrap
        OwnerLifecycleV2.Token operation, presentation;
    }
    private void nativeInput(byte[] envelope);        // synchronous stack only
    private OwnerLifecycleV2.WindowFacts probeWindow();
}

// NativeEnvironmentV2 nested types:
enum Change { INVALIDATED, DETACHED, EPOCH_EXHAUSTED,
              REGISTRATION_FAILED, RENDERER_TERMINAL }
enum RendererCause { INTERACTION_EXHAUSTED, CAPTURE_FAILED, ROLLBACK_FAILED,
    CURRENT_CHECK_FATAL, CANCELLATION_FAILED, TERMINAL_VALIDATION_FAILED }
interface Sink {
    void changed(Observer source, Change change,
                 RendererCause rendererCause, Throwable primary, Error firstFatal);
}
// Replace the current observer constructor; retain eight exact registration slots:
Observer(Activity activity, FrameLayout root, Sink sink);
void register();                                     // one shot
void bindRenderer(NativeRenderer renderer);           // READY only, once
void rendererTerminal(NativeRenderer source, RendererCause cause,
                      Throwable primary, Error firstFatal); // single report route
NativeEnvironmentV2 capture();
void invalidate();
CleanupLedger cleanupLedger();

// Coordinator loses AutoCloseable/old close(); only owner disposes it.
NativeCoordinatorV2(Activity activity, FrameLayout root,
    NativeEnvironmentV2.Observer observer, NativeOwnerV2.Fence fence,
    NativeRenderer.Events nativeInput);               // inert binding only
void renderInitial();                                // creates session here
void dispatchInput(byte[] envelope);
void refreshEnvironment();
void sealGatesScalar();                              // trusted direct writes
void cancelInputFromOwner(long sealSerial);           // C1: active-safe bridge
boolean busyForOwnerDisposal();                      // active/cancel/report
void closeFromOwner();                               // idle; disposition once
CleanupLedger cleanupLedger();

// Existing V1 constructor remains exclusive to V1; no lazy V2 acquisition.
NativeRenderer(Context context, Events events,
    NativeEnvironmentV2.Observer observer, NativeOwnerV2.Fence fence);
void sealScalarV2();
void cancelInputV2(long sealSerial);                  // real bounded records
void reportDeferredTerminalV2();                     // after commitFinish false
void disposeV2();                                    // no observer close/report loop
```

`CleanupLedger` denotes component-specific final preallocated objects with fixed
fields and borrowed read access, not a general mutable log. Owner retains first
primary, first fatal, exact terminal cause, and independent Handler cancellation,
input cancellation, unregister and coordinator disposition outcomes. Keep input
cancellation distinct from core `CANCEL_QUEUED`. Observer retains eight slots;
coordinator retains renderer/session disposition outcomes; renderer retains first
ordinary cancellation failure and first fatal, attempt counts and in-progress/
consumed serials. No result means actual OS/JNI/parent reclamation.

All public/package entries check actual main Looper before stale/retired guards.
Scalar sealing methods are trusted internal bodies called after that check, with
no injected checker or callback. All ordinary input uses the owner sink. No owner
field holds packet or event bytes. Two-phase registration, exact context/identity
binding, concrete tuple rereads and source-profile preaccess remain as previously
specified. No additional readiness listener set is introduced.
The owner stores the observer before one-shot `NEW -> REGISTERING -> READY`;
all callback fields precede the first add. Preserve all eight accepted slots,
before-add ownership, exact removal targets and uncertain failing acquisition.
Terminal reentry unwinds acquisition and never continues registration. Owner
unregister completion remains deferred until active registration unwinds; bind
is READY-only, exact-context/renderer and one-shot. Exhaustion never wraps.

## C1: active-safe cancellation with consumed ownership

On dirty or terminal entry, first close shared draw/input authority and actual
current/pending gate flags using direct scalar writes. On terminal entry set
`fence.terminal` first. Advance `sealSerial` before any callback, except that
`Long.MAX_VALUE` never increments: exhaustion terminally seals, records
`SEAL_SERIAL_EXHAUSTED` in the owner ledger, requests unchanged core close and
continues best-effort cleanup without wrap/reset. No cleanup callback can reopen
or reset serial state. A coordinator acquired later is sealed at the current
serial before exposure to any operation.

The owner invokes `cancelInputFromOwner(fence.sealSerial)` on each distinct held
coordinator (opening/adopted may be the same identity). This bridge requires main,
checks the exact shared fence serial and closed flags, and may run while `active`.
It never calls `enter()`, creates/destroys a session, commits/finishes, unregisters,
or disposes the renderer. It calls only that coordinator's bound renderer.

Coordinator and renderer publish an in-progress claim before entering the next
component/native callback. Renderer publishes `consumedSerial` before scanning;
repeated calls for that serial return the retained ledger. A recursive call while
in progress records only the latest requested serial and returns; it cannot reset
counts, rebuild a roster, restart at index zero, recursively cancel or dispose.
The outer pass consumes each record before its callback. It may absorb a newer
dirty serial after the pass because no native input can acquire a gesture while
the fence remains shut. The core still receives that invalidation and retains
the later dirty epoch/drain. A later distinct, nonrecursive seal may run a new
pass; only normal monotonic serial advancement authorizes it.

The native packet limit is 4,096 nodes. Maintain fixed indexed record rosters for
current, pending targets and pending detached records, at most 12,288 references.
Populate them as those concrete sets are built/published, outside the commit/finish
interval. Candidate publication must not expose a map without its roster. Do not
allocate an iterator, grow a list or infer a roster from a diagnostic model during
cancellation. A per-record last-claimed pass/serial prevents duplicate cancellation
of the same identity appearing in several sets. Newly constructing unpublished
records cannot own a live gesture: shared input is already sealed before preparation,
and construction/defaults/overrides are guarded as described in C3. They remain
subject to immediate transaction barriers even before joining the pending roster.
At pass entry capture the three roster references and counts into local fixed
slots. Reentry cannot replace, append to or republish those arrays until the pass
returns; no nested transaction is admitted. Keep the pass cursor/record claims
consumed before callbacks. This is a stable bounded pass, not iteration over a
live mutable collection. Serial exhaustion cannot reset any claim or cursor.

For each actual `Record.cancelToggleInput`, consume the record claim before calls.
Within `NativeSwitch.clearTouch`, consume touch/retained-parent ownership before
`setPressed(false)`, `invalidate()` and parent interception release. Attempt those
three independently even if an earlier one fails; continue every remaining record
despite RuntimeException or Error. Record the first ordinary and first fatal in
fixed fields before best-effort suppression. Retained parent release is attempted
once; return does not prove release. Cleanup may clear gesture/paint/native parent
ownership only and must never bind/layout, generate input, reopen a gate or start
an operation. `drawableStateChanged` and related callbacks must not resume normal
paint/mutation while cleanup/terminal authority is active.

After all bounded attempts, any cancellation failure follows C2 once with cause
`CANCELLATION_FAILED`. The owner terminally seals and preserves its real ordinary/
fatal values. Independent Handler cancellation and observer unregister still run;
coordinator disposition waits for operation/cancellation/report frames to unwind.
The fatal escapes after best-effort independent cleanup. A bridge return while
recursively claimed means `in-progress`, not a completed attempt or parent release.
An operation that never returns may have completed cancellation/unregister while
its coordinator disposition remains explicitly deferred.

## C2: one exact-renderer terminal report

The only renderer self-retirement route is
`observer.rendererTerminal(this, cause, primary, firstFatal)`, delivered as
`sink.changed(observer, RENDERER_TERMINAL, cause, primary, firstFatal)`. Do not use native input
events, ordinary invalidation, an untyped predicate, or an additional owner listener
for terminal reporting. Renderer and observer bind once to the same exact renderer.

`rendererTerminal` checks main first, then ignores retired/stale/repeated reports.
While live, it validates exact bound renderer identity and non-null allowed cause
before mutation; a foreign report rejects without changing owner authority. Record
the first cause/primary/fatal in fixed slots, claim the terminal report and retire
the observer before dispatch. The renderer has already closed shared terminal,
draw/input and current/pending scalar flags before calling this method. The owner
checks exact observer identity and a separate `terminalProcessed` claim; it must
not confuse the already-set shared terminal flag with an already-processed core
transition. It claims processing before any callback/core allocation, retains the
exact cause, and calls unchanged `core.close(lifetime)` if no accepted specific
entry applies. The core's `CLOSED` remains `CLOSED`; the adapter ledger preserves
the detailed renderer reason. The fatal is an explicit independent argument from
the retained component slot; propagation must not depend on successful exception
suppression or an allocating traversal of a primary RuntimeException. Observer
notices use the same primary/fatal arguments and a null renderer cause. No core
source edit or fabricated token is allowed.

Self-retirement sites are mandatory: interaction exhaustion retains
`INTERACTION_EXHAUSTED` with no manufactured exception; installed/environment
capture RuntimeException/Error retains `CAPTURE_FAILED`; rollback/restore failure
retains `ROLLBACK_FAILED` and both original/cleanup failures; Error from any concrete
current/presentation/draw/input capture check retains `CURRENT_CHECK_FATAL`.
Direct terminal validation of a transaction uses `TERMINAL_VALIDATION_FAILED`.
Ordinary tuple mismatch still seals first and calls the same observer's `invalidate`
to dirty/schedule; it is not a terminal report. Every caught Error is retained as
fatal and rethrown after cleanup; a false current check must not swallow it.

Renderer claims its report before calling the observer. Observer cleanup invoked
by owner unregister cannot report back again. `disposeV2` performs already-requested
cleanup and records its own failures without recursively reporting self-retirement;
coordinator/owner collect those retained outcomes. Later reports are inert after
main checking, but an actual newly thrown cleanup Error still escapes its calling
cleanup path and is retained in that component's ledger. Repeated reports never
retry consumed resource dispositions or replace the first terminal cause.
An accepted live report processes the transition without automatically throwing
its reported ordinary primary; the originating capture/rollback API preserves
its own ordinary throw policy. It throws the retained first fatal after cleanup.
A retired/stale report returns without acting on its supplied failure arguments;
the originating product catch must still rethrow any Error it actually observed.
Foreign live reports reject before accepting any supplied diagnostic arguments.

Set `fence.rendererReportActive` around the single reporting call and clear it in
finally. `busyForOwnerDisposal` includes active transaction, coordinator cancellation
bridge and report frames. `closeFromOwner` checks that condition before actual
disposal. If the owner initiated the current external effect, retain any `CLOSE`
decision until that effect returns. An active core operation already defers close
until its matching completion. A renderer report from an ordinary draw/input/native
callback outside an owner-initiated effect has no such completion: post one terminal
disposition tail on the main Handler so disposal runs after that stack unwinds.
Use the same single owned-work slot, tagged `DRAIN` or `TERMINAL_CLOSE`; consume the
ordinary drain slot before terminal posting. The tail carries the exact core close
token/resource or an explicitly unreported fallback disposition, never an input or
ordinary drain token. No second concurrent owned runnable, polling or retry is added.
Stale deliveries cannot steal a newer slot or repeat close. False/throwing post is
a retained terminal scheduling failure; do other independent cleanup and report
close pending if no safe unwind/entry can execute it. Do not call nonreentrant
disposal to make a report appear complete. Main Handler posts do not run inline;
the host queue must model that contract explicitly.

The successful engine commit/finish path remains callback/capture/allocation/native
mutation free. Surround it only with scalar `fence.commitFinish=true` and finally
false. `finishV2` reads trusted scalar/reference fields directly, including exact
operation, and never reports. If an in-interval failure detects terminal state,
record first deferred cause/fatal in preallocated fields, seal scalar flags and
fail closed; do not invoke the route there. After the interval's finally clears
the flag, the coordinator catch/failure path invokes `reportDeferredTerminalV2`
once before completing normal failure cleanup. Successful completion/presentation
publication remains after finish and `active=false`. Supplemental source/bytecode
guards check this interval; they do not replace C3 behavior tests.

## Exact lifecycle, focus and mutation mapping

`WindowFacts` has no focus member. Start, every actual observer invalidation and
every fresh delivered drain probe read `root.hasWindowFocus()`. Before admitting
input, call `core.focusChanged(lifetime, actualFocus)` on initial seeding and each
changed focus value; maintain an explicit `focusKnown` bit and last focus value.
Apply its decisions with scalar sealing already done. A focus notification whose
value is unchanged still calls ordinary `core.invalidate` for the environment
event, without inventing a second focus transition. Then send concrete Window/
token/geometry/inset facts to `core.windowChanged` or `core.drain` as appropriate.
Queued delivery checks focus as well as readiness; reading it into unused state
is forbidden. The sole observer remains the window-focus listener owner.

Activity `onResume` calls owner `onResume` -> scalar seal -> `core.resume` plus
fresh focus/window probe; `onPause` and `onStop` seal -> `core.pause`/`core.stop`.
Destroy calls owner close -> terminal scalar seal -> unchanged `core.close`.
Observer detach -> `core.detached`; registration failure ->
`core.registrationFailed`; observer epoch exhaustion/renderer terminal/adapter
scheduling failure -> unchanged core close with detailed outer cause. Re-check
each returned decision's exact token/lifetime/owned slot after reentrant effects.
No Activity duplicate configuration/inset observer is introduced.

Transaction guard and normal callback guard are different:

| Context | Direct authority and behavior |
| --- | --- |
| Opening/refresh/input preparation, bind, attach, layout, rollback | Exact captured non-null operation token equals `fence.operation`, and `!fence.terminal`. Draw/input flags are deliberately false. A dirty tuple/capture may independently reject. Never fall back to a new live token after an old operation becomes stale. |
| Normal draw/layout/scroll/IME/key/accessibility/toggle callback outside a transaction | Capture the exact live presentation token and require its identity remains `fence.presentation`, `!terminal`, and appropriate draw/input authority. Preserve existing concrete current-record/capture/focus/toggle checks. No operation token is required or fabricated. Normal valid navigation scrolling must continue with `fence.operation == null`. |
| Transaction-generated native callbacks | Use the captured transaction mutation scope for necessary guarded framework/layout work; never treat programmatic setters as ordinary feature input. |
| Cancellation/disposal | Explicit bounded cleanup scope permits only consumed best-effort release/hide calls. It has no authority to reopen, bind/layout or send input. |

For source implementation, add nested `NativeAppearanceViewsV2.Mutation` with
immutable `Mode { TRANSACTION, LIVE_PRESENTATION, CLEANUP }`, exact fence/token and
direct `require()` checks. Factories capture the appropriate token before native
work. Add the explicit scope parameter to `Record` construction, `Record.bind`,
`defaults`, `text`, `bindTitle`, `installChildren`, `measure`, `title`, `measureList`,
`layoutRoot` and `layout`; recursive helpers pass the same scope, never recapture
a newer token. `Record` retains its fence before constructing any View, and stores
the current scoped mutation only while synchronous native callbacks need it;
save/restore in finally. `Group.onLayout/titleLayout` use that exact scope; normal
`NativeScroll.onScrollChanged` captures its own live-presentation scope before
interaction/title/child relayout. Cleanup scopes cannot masquerade as transactions.

Guard before and after every selected callback-capable call, including each call
inside constructors/defaults/text/title helpers, not merely after `Record.bind`.
For initialized `NativeSwitch.setEnabled` and `setFrame`, cancel touch first,
then revalidate the captured scope before the `super` mutation. Native superclass
constructors can call an override before subclass fields exist: an override with
no assigned Record must be inert (return/return false), without product callbacks
or a subsequent superclass mutator. After each opaque constructor returns,
validate the original scope before any next Mixer setter or child add. This
controls Mixer-originated work; it cannot promise to interrupt framework internals
inside an already-entered native call. Constructor/native semantics remain pending
real Android qualification. The host leaves deliberately exercise these early
virtual entries and after-callback barriers.

## C3: mandatory executable production subjects and substitute roster

The actual class is `NativeRenderer` in `NativeRenderer.java`; “renderer V2” means
its actual V2 methods, not a new substitute `NativeRendererV2` implementation.
Two closures are mandatory after selection. Closure A keeps actual owner/core/
coordinator/observer with the narrow renderer leaf for orchestration faults.
Closure B executes **all fourteen actual production subjects** listed below and
the actual concrete `Gate`, `Input`, `Record`, native control subclasses and helper
bodies. Compiling these methods without executing them cannot satisfy Closure B.

The machine-readable [mandatory roster](../verification/android-private-owner-effect-integration-proposal/correction-1/required-host-roster.json)
freezes both closures, explicit source paths and substitute FQCN/file identities.
Closure B subjects are new `NativeOwnerV2`, moved exact `OwnerLifecycleV2`,
`NativeCoordinatorV2`, `NativeRenderer`, `NativeEnvironmentV2`,
`NativeAppearanceViewsV2`, `InstalledAppearanceV2`, `UiPacket`, `Json`,
`AppearanceDescriptorV2`, `AppearanceGeometryV2`, `AppearanceResolverV2`,
`AppearanceNativePathsV2` and `AuthoredToggleInputV2`. No product subject may be
copied, reduced, translated, overlaid or replaced in Closure B. Tests load a valid
independently authored descriptor/packet through actual decoder/capture; fault
leaves cannot mint installed/environment/current authority. JDK standard library
remains real. Only the enumerated Android FQCNs and `NativeBridge` are substitutes.
JNI leaves count actual calls/bytes/tokens; they provide no Swift/JNI qualification.

Use new `NativeOwnerV2ConcreteHostTests.java`, a closed
`NativeOwnerV2ConcreteHostLeaves/` file list and bounded explicit-source runner.
The roster includes complete Android class FQCNs because the complete real view
source compiles, including untouched V1 methods in the same renderer file. Nested
Android listener/layout/enum types belong to their enumerated owning source file;
no broad Android jar or implicit sourcepath may replace those controlled leaves.
`ConcreteHostProbe` is test instrumentation only, never a product subject.
Any added leaf/source needs an explicit root-reviewed roster amendment rather
than a wildcard. Use official JDK, `--release 17 -Xlint:all -Werror -proc:none`,
empty class/source paths, stripped implicit JVM options, bounded child/time/output
and scratch cleanup. Full selected Android SDK compilation/D8/ordinary Swift-JNI
cross-compilation remains an additional signature check, never a behavior substitute.

The frozen [baseline barrier inventory](../verification/android-private-owner-effect-integration-proposal/correction-1/required-host-roster.json)
identifies concrete selected calls by file/line/source text and required enclosing
regions. It is an inventory, not a parser-based proof. Implementation must retain
every selected barrier and give newly introduced calls in these same regions
equally mandatory IDs; no discretionary subset or coarse `faultV2()` replacement.
For every selected call, execute a clean control plus terminal and dirty reentry
at leaf entry and before return, and ordinary/fatal throw after the selected
callback. Assert actual shared/current/pending gate flags at callback entry.
Terminal/fatal reentry stops the next forbidden Mixer mutation/commit/event;
dirty reentry preserves closed live authority, concrete transaction validation
and one later drain without inventing terminal retirement. Injecting at a method
name without identifying the reached production call site is insufficient.

Required regions, all executed with actual product bodies, are:

- Prepublication `Record`/native subclass construction, Android superclass early
  virtual entry, Record defaults, text/title setters and nested child adds;
  preparation before `v2Pending` exists and gate construction/setters.
- `Record.bind`, `defaults/text/bindTitle`, `installChildren`, intrinsic/title/list
  measurement, root/group/title layout and all native hierarchy mutations in
  renderer attach/restore. Reentry stops before each subsequent setter.
- NativeSwitch cancellation before `super.setEnabled`/`super.setFrame`, every
  lifecycle/focus/visibility/RTL override that cancels, gesture parent release,
  `performClick` finally/reconciliation and callback-driven navigation relayout.
- Actual Gate draw/touch/key checks, actual renderer `Input.open/event/interaction`,
  and fatal concrete `current()` propagation through both draw and input.
- New IME connection refusal before superclass acquisition; an already-retained
  connection rejects every mutating forwarding method when sealed. Exercise actual
  InputConnectionWrapper overrides, key/accessibility and text-change callbacks.
- Real C1 bridge and all-record cancellation with first/middle/last ordinary/fatal
  leaf failures, duplicates across rosters, serial exhaustion, recursive newer
  dirty/terminal notices, in-progress/consumed attempts and active/deferred disposal.
- Real C2 interaction exhaustion, installed/environment capture failure, rollback
  failure and fatal current checks; exact source/foreign/stale/repeated reports,
  core terminal state, retained primary/fatal, one pending/idle/tail disposition,
  and no report callback between successful commit and finish.
- Positive normal scroll/navigation/gesture/IME controls with no operation token;
  transaction reentry cannot gain live authority; focus/resume/pause/stop mapping
  drives actual core admission; dirty during operations retains one later drain.

Leaves record primitive/native calls and invoke controlled callbacks; assertions
inspect actual product fields and call effects independently of expected core
decision logs. Scope all fourteen actual subjects in the result; do not count
Closure A's scripted renderer flags as Closure B observations. Independent source
guards/bytecode review supplement this execution. Neither closure proves real
Android/JNI behavior, successful physical reclamation, public V2, OTA or GA.

## Correction evidence and remaining boundaries

Retained original boundaries are explicit: owner publishes the exact core
operation into the shared fence before coordinator entry; Candidate retains it.
Complete only that operation/coordinator after finish and the active-operation
finally. Core allocation/completion failure uses preallocated independent cleanup
without invented tokens; never-returned work stays pending. Fresh Window/token/
size/inset probes wait for notifications without polling. Ordinary input remains
synchronous and unbuffered. Refresh uses the same coordinator's exact retained
packet reference/bytes with zero engine create/prepare/commit/abort/dispatch/effects
or Swift revision advance. Synchronous tuple mismatch seals then invalidates the
bound observer; dirty during any operation/cancellation coalesces one later drain.

Private Activity/instrumentation migrates to owner readiness/lifecycle/input;
renderer-only fixtures use the real core for tokens, distinct dedicated roots,
one inset setter and explicit replacement/finally cleanup. Public V1 stays V1.
Only root selects future fixed source-profile ID/hashes. Preserve the 22 SDK
members, descriptor and wire identities by exact comparison, and export the new
owner plus the moved unchanged core once through the sole compiled policy (22
adapter members if no extra source is selected). Reject old/edited/recomputed
locks without silent refresh; retain the rendered driver's projection of that
same authority. These remain mandatory implementation checks, not new passes.

This correction's verifier checks source custody, the exact original 36 manifest
members, independently sealed review members, accepted predecessor identities,
roster/barrier inventory and correction coverage only. It does not execute product
code or claim the required new host fixtures have passed. No dependency is added.
Root selection, implementation, both host closures, independent review, cross-build,
profile migration and full SDK signatures remain pending.

The original `seal.py` uses an exact recursive directory closure. Its bytes are
preserved, so adding this authorized `correction-1/` subtree makes its old whole-
directory check unsuitable. The correction-owned verifier checks original entries
byte-for-byte and checks original packet membership while excluding **only** this
new subtree; it does not silently weaken or rewrite the original manifest/verifier.
Correction files have their own manifest and digest. No other extra original
packet member is allowed.

All computer use, capture and native simulator/emulator runs remain paused; phones
remain disconnected. No native test was started or process queried/changed. Keep
the concrete native fixtures authored/compiled but unrun until authorized. Final
device/accessibility/performance, immutable separate-repository published FieldLog,
signing/store/operational and accountable GA requirements remain open. Source-only
preparation authorizes none of those gates or a product/profile edit.
