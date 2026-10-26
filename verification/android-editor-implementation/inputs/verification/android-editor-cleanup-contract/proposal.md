# Exact native Android editor cleanup contract — design for independent review

Recommendation: accept this contract for **candidate preparation only**. Do not
select a usable editor implementation from the identity/signature packets. No
canonical product, owner, coordinator, root metadata or Git change is made here.
The proposed amendment needs `NativeAppearanceViewsV2`, `NativeRenderer`, and
two bounded coordinator disposal guards. The owner/core remain unchanged.

The binding product remains native text input, selection, composition, platform
accessibility and keyboard behavior (`mixer-product-plan.md:322–346`). The private
limitations below do not satisfy that eventual scope or authorize GA/OTA release.

## Verified premises and correction to the earlier design

The proposal index SHA256 is
`4ad1b8edebf913308484c4600282c5d8af0af00efbc67fa4f75962967b4cc08e`
(95 members); the audit seal is
`c7fa78e51d301418479c0d2eab214211ac653800a9c747126e89a0b3b7756e82`
(108 members). Every member was rehashed before reuse. Canonical views SHA256 is
`a217d0b178869f3e5c3fc2d80f30f559a22c76a303195e62bfcb73d3cce91cce`;
renderer is
`fa523aa1c9cd2f11a77022b008a5e983c8fda697a93e2a76585c01f79f50d725`.
`collection.json` identifies the bounded source tree and copied exact inputs.
No frozen packet was imported, executed or changed.

Actual API36 `EditableInputConnection.getEditable()` reads its retained TextView's
**current** Editable. Its close calls Base close first, then drains its own
`mBatchEditNesting` and sets that nesting negative. Base close first finishes
composition, then resets IME consumption. Native close therefore cannot be safely
postponed until after a successor is usable. A returned close establishes the
call's disposition, not physical reclamation or cancellation of every native
service/subscription. Official sources are pinned to `android-16.0.0_r1` and
listed with URLs/hashes in `official/collection.json` and `source-map.json`.

The earlier assumption that `renderer.cancellationInProgressV2()` alone would
defer owner disposal was wrong. Actual coordinator `busyForOwnerDisposal()` uses
only `active || cancellation || fence.rendererReportActive`; its different
`inputCancellationInProgress()` consults renderer cancellation. Root explicitly
expanded this proposed contract to a coordinator predicate and central guard:

```java
boolean busyForOwnerDisposal() {
    requireMain();
    return active || cancellation || fence.rendererReportActive
        || renderer.editorDisposalBusyV2();
}
private void disposeOnce() {
    if (disposed || busyForOwnerDisposal()) return;
    // Existing disposition/session consumption and cleanup follow unchanged.
}
```

Do not repurpose `rendererReportActive`. Do not add editor busy to coordinator
`enter()`, input dispatch, ordinary presentation publication, or core generation.
The renderer predicate is only a scalar report of an already-entered exact native
editor call/creator/close or an unfinished synchronous cleanup drain. It neither
mints permission nor grants any dispatch authority. Its state must clear in a
finally block on every finite return/throw path. `disposal_probe.py` compiles
unchanged actual owner methods and actual coordinator `enter()` plus this explicit
candidate predicate. It witnesses the old predicate's premature disposal and
checks that healthy synchronous feature events can still enter the coordinator.
Actual `leave()` directly invokes `disposeOnce()` after retirement; changing only
the busy predicate leaves that disposal bypass unprotected. The central guard
must run before setting disposed or consuming the engine session. Actual
`closeFromOwner()` already checks busy and throws before calling retire/dispose,
so the new no-op is a deferral on the direct leave path, not a successful owner
return after clearing its pending resource. Main confinement and the intervening
scalar-only retire helper prevent busy state changing between those checks.

## Local state and the narrow public contract

Each NativeField owns one attempt object and one exact immutable target/Editable
pair. The state is `IDLE`, `CREATING`, `ACTIVE`, `DRAINING`, `CLOSING`, or
`QUARANTINED`. Each attempt retains its permanent revocation and close disposition
(`NOT_REQUESTED`, `DEFERRED`, `ATTEMPTED`, `RETURNED`, `FAILED_UNCERTAIN`, `NO_TARGET`).
There is no numeric generation, observer slot, readiness token, global registry,
new queue, retry, or delayed edit. Native batch ownership is not inferred from
`begin/endBatchEdit` boolean returns.

The views-to-renderer Input amendment needs four package-private operations:

1. Enter/leave an exact editor native call, with Record/view/attempt/target and
   Editable identity. Renderer retains a bounded scalar outstanding-call count
   and executing-drain flag for the disposal predicate; native state stays field owned.
   Mere pending DEFERRED or FAILED_UNCERTAIN records are **not busy**: they block
   successors, but must allow owner disposal to perform/record cleanup. Holding
   busy for inactive pending work would deadlock that cleanup. Overflow/unbalanced
   exit fails terminally. No allocating lifecycle-core call.
2. Supply an `EditorCloseScope` for that retained exact tuple, from an already
   authorized direct live/transaction Mutation, or from `Mutation.cleanup(fence)`
   when sealed. It is field/tuple scoped; the existing fence-wide cleanup Mutation
   alone is insufficient. Never call ordinary `input.open()` to reopen cleanup.
3. Report exact-target cleanup failure/quarantine through existing
   `terminalV2(CANCELLATION_FAILED, primary, firstFatal)` and existing ledgers.
   No new owner sink, observer lifecycle, or terminal implementation.
4. Query scalar editor availability before renderer native preparation/attachment
   and before Record bind. No successor-replacing preparation is permitted while
   a retained field is creating/draining/closing/quarantined. Check captures before
   their first native access too. Healthy active native calls may continue the
   existing strictly compatible editor-preserving echo path.

`Record` gains a separate exact editor callback lease; do not overload `changing`
or replace its existing bind `scoped` Mutation. Cleanup callback lookup has
priority over the ordinary `record.mutation()` path. A lease does not authorize
bind/layout or grant an operation to another record. Its exact tuple is verified
before/after native calls and callbacks, including same actual Editable. A native
getter throwing or a mismatch is a failure, not evidence that cleanup succeeded.

## Serialized creator and EditorInfo

First close the admitted predecessor to a returned disposition, then reserve a
fresh attempt and enter `CREATING` **before** `super.onCreateInputConnection`.
Reentrant creates while CREATING return null before super and do not steal or
clear that attempt. They must not mutate their nested caller's EditorInfo.
CREATING also refuses rebind/replacement/new edits. This supersedes the frozen
proposal's newest-nested-native-creator-wins rule. The old identity-only model is
historical: a late outer native target cannot be closed after an inner target
starts editing the same TextView.

Use the actual caller EditorInfo for the one native creator, preserving native
private fields and framework identity. Do not use hidden `createCopyInternal`,
invent a partial success copy, or round-trip arbitrary caller data through Parcel.
Retain that exact output object with the attempt until return. Before returning a
usable adapter verify the original Mutation strictly (no accepted-successor rule
for creation), exact field/Record/view/attempt/Editable, focus/input, valid buffer,
actual selection and native `initialSelStart/End`, and the expected input type and
configured Done action. Clear the already-refused handwriting gesture and preview
advertisements on that same object with empty public lists/sets; remove advertised
NEXT/PREVIOUS navigation flags. Set the extraction/fullscreen refusal hints for
the selected nonmonitor policy. Keep generic stylus text-input enablement intact.
Recheck after those potentially reentrant public setters. The successfully returned
adapter and metadata describe the same attempt and unchanged editor snapshot.

On native null return, mark `NO_TARGET` only for this attempt; it admits no adapter.
On a nonnull return invalidated during creation, retain and close that exact target
before any successor. Focus loss during creator execution marks revoked/draining
immediately; it never recursively closes an as-yet-unreturned target. A creator
throw may have constructed an inaccessible target: quarantine permanently,
record `FAILED_UNCERTAIN`, propagate the original failure, and do not retry.

On every null/failure return after native population, clear app-populated public
payload fields on the exact caller output while the attempt guard is still held:
input type/IME options/action and label/hint metadata/extras/content MIME/locales,
initial selection to -1, caps to zero, and `setInitialSurroundingText("")` **after**
invalidating selection. API36 source confirms that this clears the private
surrounding payload for invalid selection. Clear gesture advertisements too.
Retain framework package/autofill/field identity. No hidden fields are accessed.
This scrub is output cleanup only, grants no editor scope, and must preserve first
fatal precedence if a hostile setter throws/reenters. A failed scrub is recorded
as uncertain and cannot yield an adapter. Implementation controls must test the
real EditorInfo output on null/throw/late invalidation, including setter reentry;
this packet does not claim those controls already ran on Android.

## Retirement, native unwind and exact close

Retire on explicit current close, field/window focus loss, window/view/ancestor
visibility loss, aggregated visibility loss, detach, actual Editable replacement,
record/field replacement and permanent owner retirement. The bounded NativeField
overrides revoke **before super**. Exact View detach first calls window visibility,
then aggregated visibility, then public detach, then TextView's internal detach;
so all three public hooks are needed. The hooks must still call their native
super under the exact lifecycle continuation scope, including when input is sealed.
Reentry uses the same local retirement claim; repeated callbacks do not duplicate
native close. No connection revocation on compatible Binding acknowledgements,
temporary owner seals, or presentation-token succession alone.

Every native delegate entry captures an exact call lease and its original Mutation
before target work. This includes the adapter context-menu call before its native
batch prefix, plus field key/accessibility/menu native entries. A known widget
callback belonging to that native call may join its lease; arbitrary nested adapter
or external mutating dispatch refuses. A selection callback begun before retirement
retains the **same** callback lease through super and its postcheck. After scalar
revocation, the lease changes only to cleanup-only continuation; it does not acquire
a new normal Mutation or a successor's presentation authority.

If retirement occurs during an entered native edit:

1. Immediately revoke adapter dispatch and mark DRAINING; suppress feature events
   and interaction accounting. Block create, successor edit, Record bind, unsafe
   candidate preparation/attachment and Editable replacement before native work.
2. Permit only the already-entered native algorithm's exact old-field suffix and
   its callbacks to unwind. Same target/Editable and original call identity remain
   mandatory. This can include old selection/composition changes, error-state
   cleanup, batch end, platform invalidation/accessibility/IME reports. It is not
   a promise of zero platform side effects or permission for new feature events.
3. The outermost delegate finally, after the delegate has returned or thrown,
   captures any failure **before cleanup**, reaches call depth zero and closes
   the exact retained target under CLOSING. Never recursively close from the
   TextWatcher/selection/lifecycle callback inside that unfinished edit.
4. If coordinator operation or commit/finish is still active, do not close there.
   Quarantine/report terminal and retain DEFERRED exact cleanup for later owner
   disposal. No native call is inserted in the successful commit→finish interval.

When close is eligible, verify retained roster membership (current or retained
pending/disposal roster), exact Record/view/target/attempt/Editable and no successor;
enter CLOSING and consume the one native close disposition **before** any callback.
Set the Record's exact no-feature-event cleanup scope for the one direct target
`closeConnection()` call, restoring callback scope in finally. Selection,
drawable/paint, watcher, focus/window/visibility/detach callbacks must consult it
before ordinary Mutation lookup; no cleanup callback may reacquire a live scope.
Record bind/layout remain forbidden. Event suppression happens before `input.open`
or event/interaction forwarding. Keep owner/observer invalidation fully operative.

During CLOSING all create/adapter/field native input and candidate bind/prepare
routes refuse before native work. A close callback cannot close twice. Only a
normal return and valid exact postconditions mark RETURNED and release the target
for successor admission. Loss/throw/mismatch/scope failure means QUARANTINED and
terminal owner reporting. Retain target and precise attempted/returned/uncertain
facts; no retry and no claim of reclaimed batches. A stale already-returned
adapter close is local only: no successor revocation, native close or composition
change. Known failures feed the existing ordinary primary/first Error ledgers in
observation order; first fatal escapes over an ordinary primary/cleanup failure.

Renderer permanent cancellation sweeps editor retirement separately from the
   existing toggle/serial claim before the serial early-return, using retained fixed
rosters and attempt-local once-only claims. This covers seal-serial exhaustion
without allocating a new serial or closing healthy connections on temporary seals.
`disposeV2` must retire/drain exact editor targets before visibility cleanup and
preserve all existing failure accounting. A target already failed uncertain is
retained as such and never retried by disposal. Its retained ordinary/fatal cleanup
failure must still propagate from disposal even if the old cancellation serial
was consumed, so the owner cannot record RETURNED for unresolved native cleanup.

## Existing owner disposal resumption and its limit

With the proposed coordinator predicate and central guard, owner `closePending` leaves the
same resource/token pending while a native editor stack or cleanup drain is busy.
Owner `settle` posts its existing TERMINAL_CLOSE Work. Normal Android main Handler
acceptance is asynchronous: after outer native finally closes/drains and clears
the scalar busy count, Work.run verifies the exact pending resource/token and
calls closePending; its finally calls settle again. No new handler, queue, wakeup
or owner/core byte changes are needed on this accepted-scheduling path. The probe
executes these actual extracted owner methods and demonstrates finite resumption,
active-operation deferral, exact-token mismatch handling and cleanup-drain deferral.

There is an existing scheduler-failure limit. If TERMINAL_CLOSE Handler.post
rejects or throws, owner.post retains the exact pending resource/token and DEFERRED
status but clears queued; depth reaching zero does not itself invoke owner.settle.
No autonomous retry/resumption is proven on that branch. A later owner entry can
settle the retained work. Preserve this pending/uncertain operational limitation;
do not call disposal complete or repurpose rendererReportActive to trigger it.
Guaranteed completion under scheduler rejection needs a separately selected owner
amendment. Nonreturning native code likewise has no demonstrated finite unwind.

## Selected private compatibility limits and still-supported behavior

Root selected nonmonitored extraction only, zero-mode/zero-filter cursor disabling
only, explicit spell-check false, text-bounds unsupported completion, existing
handwriting gesture refusals with accurate empty advertisements, sendKeyEvent false,
and configured `IME_ACTION_DONE` only. Unknown/nonzero cursor requests and arbitrary
editor actions refuse before target work. Required unsupported callbacks carry
constant unsupported results only and preserve caller executor/fatal behavior;
they carry no editor payload or native permission. `getHandler()` is constant null
on any thread with no field/target read or main assertion. Exact IMM bootstrap
normally switches to the View hierarchy's thread before creating the connection
and calling getHandler; fixed null preserves native scheduling without making this
bootstrap query depend on local editor validity. This corrects the old proposal's
blanket main-first row; it is not evidence of a presently leaked native Handler.

Base sendKeyEvent queues work through IMM and ViewRootImpl, so an outer synchronous
lease cannot bind its later edit to the old connection. TextView's arbitrary
editor actions can queue Enter or move focus. Do not fabricate a key editing
algorithm or substitute another view-dispatch route without separate ownership.
The configured Done path retains its existing submit listener or native hide-IME
behavior under the captured continuation. Generic stylus-origin commit/composing
text remains allowed under the normal text rules; gesture rejection alone is not
a reason to disable stylus input globally.

New losses include IMEs depending on key-event transport, arbitrary IME action and
focus navigation, monitored/fullscreen extraction UI, cursor subscriptions and
candidate placement, explicit spelling requests and text geometry callbacks. The
limits do not claim automatic platform spelling, blink/layout/accessibility/native
service continuations are all disabled or owned. Candidate adoption requires a
fresh private field/owner, not grafting the adapter over an old already-subscribed
native target. Ordinary native commit/composition/delete/selection, supported plain
completion, bounded synchronous reads/snapshot and configured Done remain intended.
Keep both SDK<36 guards; API28–35/public support remains closed.

## Evidence, acceptance boundary and cleanup

`scripts/transitions.py` passed 24 authored transition tests; its fake target uses
the actual shared-current-Editable hazard shape. `scripts/disposal_probe.py`
compiled unchanged bounded owner fragments and actual/candidate coordinator
predicates/central disposal with JDK 27: two actual-source failure witnesses and
20 candidate host checks passed. The initial 15 checks covered owner scheduling
only; they did not include the subsequently discovered direct coordinator leave
bypass. The final probe supersedes that limited coverage. This is contract-model/
scheduling evidence, not complete adapter,
Android TextView, native batch reclamation, IME lifecycle, device or GA evidence.
`scripts/check_packet.py` validates hashes, exact source anchors, contract choices
and negative controls. No regex/syntax inventory authorizes release.

The complete actual adapter/views implementation, all-descriptor adversarial
host/cross-compilation and independent actual-source review remain prerequisites.
Native runtime cleanup/composition/batch/window/visibility/EditorInfo/IME tests,
TalkBack/design parity, physical phones, signing/store/OTA, separate immutable
FieldLog and accountable GA gates remain pending. Computer use, capture, UI
automation, native simulator/emulator/phone runs and process inventories stayed
paused. No native/capture process was started; no cleanup of other projects was
attempted. Host subprocesses were reaped; disposable compiler directories were
removed. Initial collection metadata-shape and host-leaf compilation failures are
retained separately and are not passes.
