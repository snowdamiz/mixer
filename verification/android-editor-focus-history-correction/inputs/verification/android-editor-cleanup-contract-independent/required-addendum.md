# Required independent correction to the editor cleanup design

This addendum accompanies producer seal
`060347101b96ecb7a5ee180828cf3437d47179fbb82e8c8ba8457a96859023b7`.
Accept the producer contract **together with this correction for isolated candidate
preparation only**. No complete editor implementation, Android runtime behavior,
API28–35 admission, OTA or GA gate is accepted. The producer packet stays frozen.

## Standalone lifecycle entry must own its platform suffix

The producer describes a lifecycle continuation but does not order its acquisition
relative to scalar retirement. That ordering is binding:

1. Check main before field reads, scalar retirement or any platform super call.
   Capture exact field/Record/View/available Editable and the current attempt or
   its precise absent/consumed disposition. Enter the counted lifecycle call
   lease **before** revoking the attempt. This also applies when no adapter call
   is on the stack. Do not create native connection authority to obtain the lease.
2. Record the actual loss as a local denial and revoke the attempt permanently.
   Block feature events and interaction before querying `input.open`. New adapter
   dispatch, creation, replacement/bind and incompatible preparation remain blocked.
3. Invoke the matching native super once under that same exact lifecycle lease.
   Known platform callbacks on the exact old tuple may join its continuation.
   Keep the lease through post-super checks. An already-entered live selection
   callback keeps its original callback lease after retirement; a later cleanup
   Mutation alone cannot repair its captured live Mutation postcheck.
4. In outermost finally, record any native failure before cleanup. After the native
   suffix returns/throws, drain the exact target once if eligible. Keep the cleanup
   executing busy scalar through close, scope restoration, failure bookkeeping and
   terminal reporting. Clear the busy scalar last. Do not call owner `settle`,
   `closePending`, coordinator `leave`, or any new resumption callback after this
   final clear. Only the existing accepted asynchronous Handler Work resumes
   pending owner disposal. Rejected/throwing posts may remain pending.

Lifecycle loss must remain a denial after a public hook returns. In exact API36
`View.dispatchDetachedFromWindow`, window-visibility and aggregated-visibility
hooks precede public detach, which precedes hidden TextView internal detach. View
attachment/window getters can still reflect the earlier state during this outer
algorithm. An IDLE close disposition therefore does not alone admit a successor.
Clear a loss denial only after its corresponding actual gain/attach and existing
current input facts permit it. A gain cannot revive an old adapter or release
CREATING/DRAINING/CLOSING/QUARANTINED. These are additional refusal facts, never
an independent readiness token. An authoritative gain while busy cannot create a
connection from inside that same native frame.

The public-hook lease covers its matching super and callbacks, not the whole
package-private `View.dispatchDetachedFromWindow` or hidden
`TextView.onDetachedFromWindowInternal` after the public hook returns. A permanently
retired field has no new feature events or successor, but native detach/service
suffixes can still execute on the retained View. If they enter an authored callback
without a known exact captured continuation, fail closed and record uncertainty;
do not grant a fence-wide cleanup Mutation merely because the owner is terminal.
Normal accepted owner Handler work queued while a public hook is busy runs after
the Java stack unwinds. No native-quiescence or complete platform-dispatch lease
is inferred from public-hook depth reaching zero. Direct coordinator disposal must
remain centrally guarded while an actual editor call/drain is executing.

## Construction and callbacks without an admitted target

Superclass construction may invoke virtual selection/drawable/lifecycle callbacks
before `NativeField.record`, `Record.view`, its binding or an Editable exists.
No field initializer or ACTIVE phase can be assumed to have run at that point.
The implementation must distinguish this constructor bootstrap from a later
sealed callback. Main checks still happen first. Bootstrap calls only the matching
required platform super; it performs no Record/Input/Editable lookup, feature
event, interaction, close, or connection creation. It cannot supply a cleanup
lease to any later callback. Once the Record exists but construction/binding is
unfinished, use the existing strict construction transaction scope, suppress
events, and refuse connection creation until construction is complete. Do not
use an allocating owner/core query or normal live input lookup to initialize it.

Later lifecycle callbacks with no active target may use an exact field/View and
available Editable lifecycle lease to run the matching platform super; absent or
already-consumed target is explicit and grants no native target dispatch. Require
the exact construction/retained roster relationship appropriate to that phase.
An unavailable Editable is not a successful exact-target close.

`getHandler()` remains the only selected bootstrap exception to main-first:
constant null on any thread, with no field, target, Record, phase, Handler or
native read. Off-main lifecycle/creation/adapter calls refuse or throw before
native effects. Constructor bootstrap must not turn an off-main lifecycle call
into a native super call.

## Unrequested native failures still retire the field

Distinguish validation/entry refusal before a native call from uncertain partial
native execution. A no-call rejection does not fabricate a cleanup failure.

For a creator/delegate/widget/lifecycle-super throw, observe the original ordinary
failure or Error before any cleanup/report callback. A thrown delegate, widget or
lifecycle super can leave a native batch/selection/composition prefix unfinished
even when no retirement was previously requested. Immediately revoke scalar,
block successors and report terminal uncertainty through the existing sink. Let
the known native frame unwind; attempt one exact target close in the outermost
finally when safe, or retain its precise DEFERRED/FAILED_UNCERTAIN disposition.
A coordinator operation/commit-finish block still prevents that native close.
Quarantine forbids successor admission but does not itself suppress the one
later eligible close of a known retained target whose close was never attempted.

A creator throw can hide an allocated native target that was never returned.
Record FAILED_UNCERTAIN, quarantine, propagate the original failure and never
invent a target, native close, reclamation or retry. On a normal native creator
return that was revoked meanwhile, close its known exact target before any
successor; the original attempt guard also covers EditorInfo output scrubbing.

Every entered frame balances exactly once in finally. Keep bounded recursion:
arbitrary nested adapter/input calls refuse; same-hook recursion cannot run an
unbounded chain of native supers; known nested callbacks join only the captured
exact tuple and have a finite implementation limit/guard. Overflow/unbalanced
exit retires terminally. The authored model's bound is finite test scope, not an
Android recursion measurement or a mandated product constant.

Retain the first observed primary (ordinary or fatal) and first fatal Error in
observation order.
Attempt bounded eligible cleanup even when an earlier native fatal exists. The
first fatal escapes over any ordinary primary and later cleanup failure; a later
fatal never replaces it. Preserve and surface ordinary native failures through
the terminal/disposal outcome rather than returning a rejected keystroke as if
cleanup had succeeded. A returned exact close records only RETURNED; it does not
prove all native batches/services reclaimed.

## Implementation entry point and ownership

The next isolated implementation can own a new private editor adapter plus
`NativeAppearanceViewsV2.java`, `NativeRenderer.java`, and exactly the two selected
coordinator disposal edits. Leave owner/core and both SDK<36 admission guards
unchanged. Coordinate the field/Record/Input contract before dependent edits.
Use fresh private field/owner targets; do not graft over existing native monitoring.
Do not add a hook, getter, allocation, callback or native cleanup to the successful
`commitV2`→`finishV2` interval. The outstanding editor-native-call predicate must
not be added to ordinary coordinator entry/publication or confuse temporary seals
with permanent editor retirement.

Actual complete-source controls must cover every InputConnection descriptor,
construction, lifecycle first/inside/after-super reentry, output/EditorInfo null and
throw scrubbing, no-call rejection, plain native throw, exact callback postcheck,
cleanup fatal ordering, retained-roster disappearance, depth/serial exhaustion,
central disposal, Handler rejection and strict preservation of compatible Binding
echoes/Editable/selection/composition. The current host models are design evidence;
these implementation controls and pinned-SDK cross-compilation still must run.
