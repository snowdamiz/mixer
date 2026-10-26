# Private Android owner integration candidate

This implements the selected private owner contract, correction, roster amendment
and dirty/result clarification. It is a candidate for independent source/behavior
review and exact profile selection. It does not select public V2 routing, qualify
Android runtime behavior or accept a release. `MixerActivity` and public V1 routing
are unchanged. No signing, publication, UI/capture, native instance or phone work
was performed.

`NativeOwnerV2` owns the exact moved `OwnerLifecycleV2`, one prepublished observer,
one coordinator opening/adoption and one Handler slot. The core moved once into
`app/src` with SHA256
`4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6`
(12,473 bytes); its former path is absent. Tokens come only from that core.

The owner closes the shared draw/input fence and current/pending gate scalars
before invoking cancellation or lifecycle/core work. It maps actual root window
focus explicitly. Input first retains its admitted real presentation, seals, then
reads fresh focus. Terminal/current-reference checks and the unchanged core's
`admitsInput` decide admission; intentionally closed `inputAllowed` cannot grant
or reject replacement authority. Every core SEAL decision synchronously closes
shared/current/pending scalar gates, including nonterminal dirty focus decisions.
Processing that decision does not repeat cancellation or advance the seal serial.
Ordinary input is synchronous through its sink, carries engine
operation 1 and leaves no owner packet/event byte field. Environment refresh uses
the exact retained committed array, with no prepare/commit/abort/exchange or
revision advancement.

Observer construction resolves targets without registering listeners. The owner
stores the observer before `register()`. Eight existing acquisition/removal slots
retain their accepted identities and uncertainty. An owner UNREGISTER decision
immediately retires the observer with a scalar assignment; registration's
`completed()` guard then prevents another add. Disposal remains deferred while an
add is active, so the late current slot is removed exactly once by unwind. The
same scalar retirement occurs in emergency fallback without inventing a cleanup
token. Typed reports bind one READY observer to the exact renderer, retain the
specific cause and independent first fatal, ignore stale reports after main-thread
checking, and defer active renderer/session disposition to the owned idle/tail path.

C1 cancellation snapshots fixed current, pending target and pending detached
rosters, each bounded to 4,096 records. Claims consume duplicate record identities
before callbacks. Recursive newer seals are consumed by the active pass. Native
Switch policy/parent ownership clears before setPressed/invalidate/release; each
release is attempted independently, retaining first ordinary and first fatal.
Serial exhaustion closes the owner without wrapping or manufacturing an exception.

Transaction mutations capture an exact non-null operation token. Native live
callbacks capture the current presentation and require open draw/input admission
as appropriate. Native constructors, defaults, setters, hierarchy loops, rollback,
IME acquisition/forwarding, normal scroll and draw bodies execute guarded scopes.
Superclass virtual entry before Record assignment remains inert. No stale scope
can acquire replacement authority. A completed boolean delegate result can return
after a live successor only through direct scalar/reference checks and immediate
return, as selected in the clarification. Closed/terminal/dirty authority rejects;
the old captured scope still rejects a later mutation. Refusal-only IME overrides
never call a native delegate.

The successful JNI commit → renderer finish path contains only its scalar status
branch, direct finish invocation and prepared reference/scalar swaps. Finish has no
native call, capture, callback, allocation or main-check call on its success path.
Successful finish adopts the prepared state while leaving `v2Open` and the actual
current Gate.open false. The completion-bookkeeping hook therefore observes closed
concrete gates before `core.complete`, including reentrant dirtiness, retirement
and failure. After actual core completion, owner publication requires LIVE/clean,
no operation/drain, a non-null actual presentation and the exact current resource.
Trusted renderer/coordinator scalar helpers then publish that exact presentation
outside the commit/finish interval. Dirty completion stays successfully committed
with closed concrete gates before its one Handler.post and follow-up refresh.
The native renderer-only fixture likewise publishes only after its own real clean
core completion; that fixture change remains cross-compilation-only.
Invalid/replayed arguments reject separately. A genuine terminal finish records a
scalar deferred cause; reporting occurs only after the interval flag is cleared.
The retained class files and javap output supplement executed controls; source
text alone is not Android runtime or release proof.

The package-private three-argument owner constructor accepts a host-only
`completionFault` Runnable. The production two-argument constructor supplies null.
It runs after the coordinator returned and before `core.complete`, outside the
commit/finish interval. Initial/input/refresh controls throw a selected fatal at
that boundary and verify emergency disposal, `coreCompletionUnreported`, and the
same still-active real core operation. No successful completion is fabricated.
Registration fallback separately executes exact core pause/close calls with a
controlled fatal from an A-only mechanical Looper getter callback. This proves
the boundary catch/fallback behavior; VM allocation exhaustion was not induced.

A coordinator can internally retire after a failed transaction and dispose after
its active native call returned. The outer owner subsequently processes the
retained disposition rather than releasing it again, consistent with proposal
lines 305–316. Earlier operation primary/fatal identities remain separate from
renderer/engine release outcomes. `closeFromOwner()` no longer throws an earlier
ordinary operation primary when both release slots returned. Abort, rollback and
discard have separate retained outcomes/failures. An uncertain abort prevents
rollback, status 2 remains terminal without rollback, and a throwing attachment's
own consumption is not repeated by coordinator discard/rollback.

The input cleanup outcome uses main-checked cancellation-only status. Active
operations and renderer report frames independently defer coordinator disposal;
they do not make an already returned cancellation IN_PROGRESS. Genuine recursive
cancellation remains IN_PROGRESS until the outer pass returns and overwrites it.
The immutable candidate-2 witness fails both the active-operation and report-frame
cases; the repaired actual-owner cases pass while retaining separate DEFERRED
disposal and final resource results.

`Work` retains a posting flag, one pending cancellation flag and the actual core
CANCEL_QUEUED token only while its own Handler.post is active. Cancellation first
consumes the single owner slot. Before post unwinds, its outcome is DEFERRED;
afterward the exact potentially enqueued Work is removed and the real cleanup
token completes once. The token/flag clear before that removal callback. This
also handles false/throwing post, including enqueue then throw, and terminal
reentry before enqueue. Removal never consumes a newer Work identity. Failed
removal remains FAILED_UNCERTAIN with separate primary/fatal identities. Tests
use explicit controlled early delivery; production does not assume inline post.

After scalar sealing/cancellation, start/resume/drain stop ordinary focus/readiness
work when terminal. Actual Gate.invalidate reentry closes the owner during the
resume/drain seal and verifies zero subsequent seedFocus/probeWindow native reads.
Initial registration-terminal reentry separately covers start without inventing
an already-open coordinator before its first start.

All seven formerly implicit constructor/bind/measure/list/children/root-layout/
layout scope parameters now receive the caller's captured Mutation explicitly.
Recursive measurement, layout and Group title/layout forwarding pass that same
object. Synchronous measure/layout callbacks save and restore Record.scoped in
finally; constructor/bind do likewise. Normal Group framework entry captures once;
NativeScroll supplies its already captured live scope to the explicit overload.
CLEANUP can authorize only dedicated consumed release/hide paths. All thirteen
ordinary helper families refuse sealed CLEANUP and stale captured scope before
any native leaf; actual transaction and normal recursive live layout remain positive.

Candidate 2 is retained as a held proposal. The same actual fourteen-subject IME
`commitText` → Editable/TextWatcher → renderer event → owner witness flips root
focus after the final captured getter result. Candidate 2 reaches the fresh owner
getter and Handler.post with shared/current gates open while the exact core is
dirty/unfocused. Repaired bytes close them at both entries and perform no new
engine transaction. A separate real core focusChanged decision proves nonterminal
SEAL closure without serial/cancellation effects. Dirty/terminal/fatal callbacks
at the fresh getter and recovered completed-successor input have explicit controls.
The independent immutable reproduction is retained in the root review's
`independent-review/implementation-review-1/targeted-2`; the producer's identical
before/after controls are in `focus-repair-control`.

| Evidence | Executed scope |
| --- | --- |
| `publication-repair-A-3` | Actual owner/core/coordinator/observer; 216 cases, 1,101 assertions, 173 explicit migrated vectors; declared renderer/platform/JNI orchestration leaves |
| `publication-repair-B-full-1` | Mandatory actual fourteen subjects and exact selected 73 substitute FQCNs plus probe; 184 baseline + 5 introduced sites × 7 = 1,323 rows; 14,477 assertions including focused controls |
| `observer-final-1` | Preserved eight-slot fault/unwind coverage and two-phase/binding controls; 162 actual-observer cases |
| `core-regression/attempts/exact-final-1` | Exact moved core, 22 cases and 45,841 assertions |
| `publication-repair-crosscompile-1` | Complete current Java/native fixture sources, official SDK 37, Java17 target and D8 min28 |
| `crosscompile-final-1` | Ordinary app-owned Swift 6.3.3 Android engine, NDK JNI link and ELF inspection; its Swift/JNI/SDK inputs match the final candidate |

Every host compile uses official OpenJDK 27 with `--release 17 -Xlint:all -Werror
-proc:none`, explicit source lists, empty implicit class/source paths and stripped
JVM options. This is target-17 bytecode executed on JDK27, not a Java17 runtime
receipt. Runners retain inputs, class identities/bytes, command/tool identities,
streams, bounded child/time/output evidence and owned scratch cleanup. Earlier
failed/provisional attempts remain separate; the original line-only and first
lower-return proxy counts are not final coverage evidence.
`ledger-repair-control` and `focus-repair-control` retain identical witnesses
compiled against immutable candidate-2 and repaired class bytes, with expected
old failures, after successes and bounded scratch/child cleanup. The first full
ledger rerun's stale-map race and the first focus hook's overlapping frame count
remain failed attempts, not counted coverage.
`publication-repair-control` runs the identical real fourteen-subject witness
against immutable candidate-3 and final repaired class bytes: prepare-dirty,
completion-hook-dirty and passive clean-completion cases fail the old boundary
and pass the correction. Eighteen concrete controls cover initial/input/refresh
with clean, prepare-dirty, hook-dirty, hook-retirement, ordinary throw and fatal
throw. Clean native successors and exact retained-packet dirty refresh remain
positive. A failed new driver assertion about dirty initial adoption is retained
separately; it does not replace the independent targeted-6 failing trace.

`barrier-map.json` retains each old source ID, exact invocation, current location
and phase-specific native anchors. Driver-owned synchronous StackWalker evidence
retains class, method descriptor and bytecode index. Clean cases require one exact
caller frame and distinct source-site identities, including same-line original
calls. Helpers retain the full native sequence of the chosen invocation, final
return anchor and a source/bytecode-bound pure tail. Consecutive `new Record` loop
invocations are distinguished by concrete receiver identity. The high-level
navigation `group.onLayout` return anchors on the final list Group.layout after
all rows, not the first lower measure. `closeConnection` anchors on the existing
BaseInputConnection hook; InputConnectionWrapper's remaining tail is direct return.

The four new IME C3 calls are `super.beginBatchEdit`, `super.endBatchEdit`,
`super.clearMetaKeyStates` and `super.closeConnection`. A fifth introduced boundary
is Group framework onLayout forwarding its one captured Mutation to the scoped
overload. Its selected root-vStack branch retains the complete native sequence
through the final section Group View.layout return, with pure scope/loop/return
tail. The four old helper invocations whose spelling adds a Mutation argument
retain their original source IDs and explicit old-to-new argument mapping.
The remaining new calls in
those regions are direct scalar helpers/authority checks, typed report/cancellation
routing and fixed-ledger work, not omitted native forwarding mutations. Existing
constructor/setter/hierarchy/draw calls retain their old 184 IDs. New owner/core/
observer/coordinator effect boundaries are covered separately by Closure A and
focused C1/C2 controls; they do not substitute for C3's matrix. The five historical
V1 children calls run positively through unchanged actual apply/children code;
the two setLayoutParams branches retain different bytecode indices.

Focused B controls cover native callback operation-null scrolling, actual IME
Editable/TextWatcher → owner → commit/finish successor behavior, current/terminal/
dirty/stale/fatal forwarding families and refusal zero-forward behavior. Actual
observer notifications are labeled separately: before capture can coalesce, a
stale capture encountered by later validation retires, and notification inside
commit after the final concrete validation can complete then refresh. No capture
was added into commit/finish. Failed native edit buffers are not synthesized back.
C1 controls include first/middle/last faults, independent parent release, duplicate
identities across all real rosters, recursive serials, active disposal deferral and
exhaustion. C2 controls cover all six causes, installed/environment capture,
current-fatal propagation through actual draw and input, foreign/stale/repeated
reports, false/throw tail posts and deferred reporting after commit.

`legacy-vector-map.json` enumerates all 133 historical coordinator cases and maps
them to current cases, source assertions and the selected changed expectations.
All 141 vectors from the first migrated suite remain in the final 173-vector set.
The historical Java fixture remains preserved; no active runner invokes its old
constructor/close interface. Pure finish cannot receive synthetic callbacks; its
old before/after model faults are explicitly replaced by real commit-leaf terminal
reentry and post-return completion-bookkeeping controls, without claiming literal
VM allocation exhaustion. No other old case is silently omitted.

The proposed profile is exactly `mixer.android-source-pair.3`, 22 adapter members
and the unchanged 22 SDK members. The candidate proposal includes the new owner
and moved core once, unchanged default descriptor fixture and wire identity.
Compiled CLI literals remain profile 2 until root selects the frozen exact map.
CLI export/common/driver/preaccess/copied consumer qualification is a separate next
step after that selection, not a host acceptance inferred here.

Independent product source/behavior review, selected CLI migration/consumer checks,
actual Android framework/JNI/native IME/draw/lifecycle runs, physical-phone matrix
and all release/GA gates remain pending. Native Activity/instrumentation sources
were migrated and cross-compiled; none was run during the pause. The private
RendererFixture constructor and factory now independently unwind a
registered observer, acquired renderer and actual core, and detach a dedicated
nonprimary root if later construction/tracking fails. First primary and first
fatal are retained separately by the fixture owner. Those native-only failure
paths were cross-compiled and source-reviewed here; their runtime fault injection
is pending, and host controls do not claim to execute them. In particular,
mechanical leaves cannot qualify Android dispatch timing, rendering fidelity or
OS/JNI reclamation. This candidate makes no OTA, public V2, simulator/emulator,
phone, signing, store, live-VM or GA acceptance claim.
