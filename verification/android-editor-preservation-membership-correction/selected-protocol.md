# Proposed preservation outcome protocol

Status: design recommendation only. No dependent product change is selected by
this packet. Root and independent review must select the exact private contract
before a complete-source derivative is edited. Canonical integration, native
behavior, public V2, OTA and GA remain unselected.

The source is the frozen focus-history candidate sealed by
`2ebf7634886be778b06ecdfa0ab2a9ac69d14a473b88a7f6ea623ccddfcd5af8`,
product tree `2d0a89dac0c629b7257a75dfa42dee3794f021c558300f968fc4d8baaaecba01`.
The findings seal is
`a0cf5e8bff8ffee66f277b5e83c76b2778db13bd8eac558ae3ef65cdc007f5fd`.
`inputs/` contains byte-identical copies of the complete sixteen-file product
source, selected tests/findings and governing contracts. `input-custody.json`
records verification of all 5,325 producer and all 22 permitted finding members.
No other active independent actual-review directory is an input.

## Required behavior and source explanation

An otherwise-current original transaction, unchanged native field snapshot and
successful engine abort must permit the existing coordinator's ordinary status1
rejection path to restore the exact old compatible Binding and geometry. The
current source ends all FieldPreservation scopes in attachV2's finally, then
rollbackV2 constructs a new equivalent transaction Mutation. restoreV2 correctly
refuses the ended scope. Keeping that refusal while preserving the original scope
through the eligible outcome corrects the lifetime; constructing another
equivalent Mutation or another field scope does not.

fieldPreservationEnd currently checks the supplied Record/scope and the receiver's
positive shared count, but not their exact receiver ownership. The independently
reproduced two-renderer control therefore consumes the wrong renderer's count.
This is an internal invariant finding, not a public exploit claim.

## Bounded product ownership requested for selection

The prospective derivative may change NativeAppearanceViewsV2.java and
NativeRenderer.java. It also needs a narrowly selected NativeCoordinatorV2.java
change: call a renderer failed-outcome completion endpoint once in each of the
existing transact and refreshEnvironment catch paths. These calls follow the
existing abort/rollback/retirement/reporting work and precede rethrow. Existing
commit-result classification, abort eligibility, rollback eligibility, core,
owner, enter/publish/disposal predicates and outer leave control flow stay fixed.
This is a requested private hook, not authority already granted by the earlier
coordinator-unchanged focus-history selection.

No new owner/core slot, observer callback, asynchronous work, native operation,
SDK admission, cap, deadline, dependency or connection authority is requested.
The shared outstandingEditorNativeCalls count remains shared with EditorLease,
replacement and other accepted native custody. It is never globally reset.

## Exact private interface and retained objects

Keep these selected Input signatures:

```java
void fieldPreservationBegin(Record record, FieldPreservation preservation);
void fieldPreservationEnd(Record record, FieldPreservation preservation);
```

Both retain main-first entry outside the commit/finish interval, then use the
same private scalar ownership predicate. Neither a foreign nor replayed endpoint
may alter a scope, callback registration, candidate ledger or shared count.
Do not call either Input endpoint from finishV2: their main check calls Looper.

Select these private changes in the prospective derivative:

```java
// Added argument captures the actual immutable journal identity.
FieldPreservation(NativeField field, Mutation original, Binding selected,
                  Editable editable, NativeRenderer renderer,
                  NativeRenderer.Candidate candidate,
                  NativeRenderer.AttachmentJournal journal);

// Refined existing current-authority probe; callable, never used by finish.
boolean fieldPreservationCurrent(Candidate candidate, AttachmentJournal journal,
                                 Record record, FieldPreservation preservation);

// New coordinator-facing failure endpoint; only outside commitFinish.
void completeFailedV2(Candidate candidate, Throwable primary, Error firstFatal);
```

Candidate retains a reference originalMutation, assigned exactly once to the
existing Mutation.transaction result when attach enters. Every preservation's
original is that same object. attach's local v2Mutation, restoreV2 and rollbackV2
use that same reference. rollbackV2 must delete its Mutation.transaction factory
call; no fallback factory, successor token, CLEANUP conversion or new scope is
allowed. A missing or mismatched captured original refuses before native restore.
Preparing a candidate does not itself grant attach/rollback authority.

Candidate/journal also retain primitive phase, counted-preservation total and
completion-claimed bookkeeping. FieldPreservation retains the exact journal and
primitive phase/completion state. Existing NativeState.preservation and
forwardPreserved remain the authoritative journal membership. This needs no new
array, collection, ticket, Mutation, scope or callback allocation on completion.
Completion walks the already-owned journal ArrayList by integer index; a foreach
iterator/stream, lambda, boxing, list copy or new exception on the healthy path
is not permitted in the scalar success interval.

Conceptual states below may be represented by primitive constants. They must not
be implemented by a newly allocated state object on the healthy path.

| State | Callback authority | Count custody | Permitted next transitions |
| --- | --- | --- | --- |
| CAPTURED | none; begin not entered | absent until exact begin | ATTACHING, failed entry |
| ATTACHING | exact bounded field callbacks under the captured original | held | ATTACHED, RESTORING, FAILED_HELD |
| ATTACHED | exact bounded validation callbacks under the same original | held | PRECOMMIT_READY, RESTORING, FAILED_HELD |
| PRECOMMIT_READY | no new native entry from completion; retained scope is unended | held | scalar COMMITTED, RESTORING after eligible known rejection, FAILED_HELD |
| RESTORING | only exact existing field callbacks for restoration under the same current original | held | RESTORED_HELD, FAILED_HELD |
| RESTORED_HELD | callback registration removed, ended | held through coordinator reporting | RELEASED or FAILED_HELD on imbalance |
| FAILED_HELD | no new callback authority; ended, no revival | held until exact balanced end; imbalance stays held | RELEASED only if exact balanced endpoint was never consumed |
| COMMITTED | callback registration removed, ended | released by scalar finish after swaps | no transition |
| RELEASED | none, ended | absent | no transition |

PRECOMMIT_READY to RESTORING continues an unended scope; it does not revive an
ended scope or acquire successor authority. An actual ended scope may never
resume native work, including one whose matching count is deliberately retained.
An imbalance does not authorize an automatic retry. The sole held-count cleanup
endpoint can release an exact, otherwise balanced identity only if it was not
already consumed; synthetic repair in hostile tests is not a product retry policy.

## Scalar provenance before any endpoint effect

The private scalar predicate establishes all of the following before changing
any scope, Record registration, phase, counted total or shared count:

1. Receiver renderer is preservation.renderer and candidate.owner; the exact
   candidate owns the exact journal, journal.candidate is candidate, and scope
   candidate/journal references match both. The journal's existing NativeState
   belongs to this exact Record, forwardPreserved is true, and its preservation
   reference is this exact scope. A map key, equal value or nonzero count is not
   provenance.
2. scope.record is record, scope.field is record.view, scope.field.record is
   record, record.input is this renderer's already-created v2Input, and the
   invoked Input receiver is that exact Input for Input entry/end. Both
   record.editorFence and original.fence are this renderer's v2Fence.
3. original is candidate.originalMutation by reference. Its mode is TRANSACTION,
   its token is candidate.operation, and it has no editor, replacement or field
   continuation lease. The token must not be substituted even by an equal
   lifecycle token. Cleanup checks this captured identity without requiring that
   it still equals the fence's current operation.
4. Begin additionally requires the existing current original, exact retained
   candidate Record/View, no conflicting local scope or lease, compatible
   settled field, valid forward journal facts and all existing denial rules.
   Its count check admits only 0 <= outstanding < MAX and an unentered,
   uncounted, unended scope. The candidate's held-preservation total is checked
   against its fixed journal membership and bounded before increment. A
   legitimate active third-field EditorLease is allowed.
5. End/completion additionally requires its own entered and counted claim,
   expected phase, ended/unregistered state for terminal end, zero callbacks,
   empty existing hook stack, no checking evaluation and an unconsumed end.
   Shared count must be positive and at least the exact outstanding
   preservation cohort size. End cannot infer ownership from positivity.

End after terminal/current-operation loss uses only captured provenance and
balanced native-suffix bookkeeping. It must not call current(), exact(),
editorRetained(), lossObservation(), settledField(), field/native getters or an
owner/core probe after reporting. It does not require a valid native success
authority merely to release its own exact captured count. A foreign call or
replay refuses before all scalar effects, even if the receiver has an unrelated
active lease. An unchanged real owner/count must be observable after refusal.

For whole-cohort completion, preflight all ownership/count identities before
any success-side change. Revoke the exact callback registration, mark ended and
claim completion once; release its own counted claim last. A scope-local callback/hook imbalance
does not stop other exact owned scopes from reaching their eligible end. If the
shared aggregate count is below its exact held-preservation cohort or otherwise
cannot fund a represented decrement, no unfunded decrement is eligible; retain
that custody and report rather than borrowing another owner's count. Never
remove a foreign Record registration during error cleanup. Failure bookkeeping
remains while all applicable counts are held; no reporter follows a final clear.

## Attach, validation and scalar success

attachV2 retains current validation/preflight and native ordering. It captures
the original Mutation once and records each exact journal scope before entering
its native work. A failed attach records/restores/reports with the same captured
original while held, removes callback authority when its native suffix has
ended, and leaves scalar count release to the coordinator's failed-outcome
endpoint. It never relies on successful assignment of the caller's journal local.
An original fatal may propagate into the existing coordinator catch while
custody stays held; this transports the already-observed fatal before later
abort/report failures. It is not final completion. The completion endpoint must
visit and release every eligible exact owned scope before its own fatal throw.
Successful attach returns the journal with every captured field
scope still entered, counted and unended. Its finally restores only the previous
renderer v2Mutation. It does not end the scopes merely because attach returned.

validateAttachedV2 performs the existing candidate/environment/availability
validation outside commitFinish. After every callable validation bundle, check
the original reference/current token, pending candidate/journal, loss marker,
compatible before/selected Binding, exact native Editable/snapshot and settled
predecessor. The final callable validation is followed by scope.exact and a final
scalar ownership/count/zero-callback postcheck before PRECOMMIT_READY is set.
All snapshots/getSpans, environment observations and possible allocations remain
before commitV2. The existing snapshot checker allocates; the design requests
its final precommit use, never an allocation after commit. No new success ticket
or completion allocation is added. Root clarified that the allocation prohibition
applies to commit through finish/scalar completion; existing callable snapshot
helpers are allowed during bounded precommit validation.

The existing coordinator checkOperation remains between validation and engine
commit; it observes only scalar fence/token state. Successful engine commit to
finish does not call requireMain/Looper, current/exact, Input, snapshot validation,
native getter/setter/layout, JNI, callback, event, observer, owner/core or allocation.
The prevalidated candidate/journal/scope and final scalar checks are sufficient
only because there is no intervening callback or native mutation. A hostile
hook is not permission to add one to production.

finishV2 first checks its existing candidate/terminal/token facts and every
PRECOMMIT_READY scope's exact scalar provenance, current scalar loss serial,
the selected forward Binding reference (the old reference only belongs to
restoration completion), zero callbacks/hooks/checking, counted
ownership and cohort bound. It never recomputes a native fact. Validate the
entire cohort before swaps or ending any scope. Then remove callback authority,
mark the scopes ended and completion claimed, perform the existing prepared
presentation/reference swaps and candidate consumption, and release the
matching preservation counts last. A third field's entered EditorLease/count
remains untouched. Successful refreshEnvironment uses the same preparation and
scalar finish without a synthetic engine commit.

A failed scalar finish after commit success has an unknown committed outcome.
Keep existing terminal/deferred scalar failure behavior. Do not restore or end
through native observations in that interval. The outer failed-outcome endpoint
performs only permitted post-interval reporting and exact scalar end.

## Failure order and the narrow coordinator hook

The coordinator retains its original observation order: remember the thrown
failure, perform existing deferred reporting, classify unknown outcome, attempt
only the already-eligible engine abort, apply existing terminal-rejection policy,
and call rollback only under its current !terminal && !unknown policy. No status
classification or retry is changed. Pass its retained primary and firstFatal to
the new failure endpoint so later field bookkeeping cannot obscure an earlier
engine/coordinator failure. Renderer/field ledgers also retain their original
first primary and first fatal.

In transact catch, after its existing retireScalar and before the existing
firstFatal/rethrow selection, add exactly:

```java
if (candidate != null) {
    try { renderer.completeFailedV2(candidate, ledger.primary, ledger.firstFatal); }
    catch (RuntimeException | Error cleanup) { remember(cleanup); }
}
```

In refreshEnvironment catch, insert the same block after its existing
retireScalar and reportDeferredTerminalV2 handling and before firstFatal/rethrow.
The endpoint resolves the real immutable journal from the exact original
candidate, not from the nullable local journal that is assigned only after attach
returns. It therefore covers attach throws before returned-journal assignment,
including partially entered cohorts. The original journal local continues to
control the unchanged rollback/discard decisions. A pre-attach candidate has no
entered field scopes and completion releases no fabricated count.

completeFailedV2 requires main and !commitFinish before any new work. It claims
the exact failed candidate and its actual original candidate.journal completion
once using captured provenance,
even if c.used/journal.complete/pending have already changed because rollback
returned or attach failed. Current success authority is not required for scalar end. It records
the retained primary/fatal, revokes only its exact registered callback edges and
marks scopes ended, reports existing per-field/renderer uncertainty while each
applicable count remains held, observes reporting failures, then releases only
balanced exact counted scopes using the common scalar end predicate. No native
getter, Mutation factory, restore, new event or native suffix occurs here.

Completion uses a reporting phase followed by a scalar release phase. Collect
all retained component primary/fatal observations before later cleanup failures.
If a scope's callbacks/hooks/checking or count/provenance is inconsistent,
terminally report the imbalance while held and retain that scope's count. Visit
every remaining exact owned scope even if an earlier failure is fatal. All
eligible balanced scopes must end and release before this endpoint selects or
throws firstFatal; no loop iteration surfaces a retained fatal early. Preserve
the first fatal object by identity; a later reporting/end fatal never replaces it. No counter reset or
new asynchronous retry is introduced. After final count release this endpoint
has only scalar return/throw selection; it does not call settle, closePending,
leave, an owner callback or synchronous disposal. The existing outer coordinator
unwind remains unchanged; no extra resumption is attached to count clearing.

## Outcome matrix

| Outcome | Restoration and native scope | End/reporting disposition |
| --- | --- | --- |
| commit status0, valid finish | no native work after commit; scalar swap | scalar completion releases only own balanced scopes last |
| successful environment refresh | final native prevalidation, then scalar swap | same scalar completion |
| ordinary status1 (or other nonterminal known rejection), abort returns0 | unchanged coordinator policy calls rollback; restore with the identical captured original and retained journal scopes | native restore returns, callback edges end but counts remain; coordinator records rollback RETURNED, retires/reports, then failure endpoint releases balanced holds |
| known status2 or abort failure/throw | existing terminal policy; no newly authorized restore | report terminal uncertainty and release exact balanced holds without native getters; retain imbalanced holds |
| commit throws or status outside known range | existing unknown outcome; no abort/rollback invented | same terminal scalar completion after reporting |
| validation/checkOperation failure after attach | restore only if current original, native snapshot/loss/settled facts and existing coordinator policy permit | otherwise honest failed restoration/terminal result; exact scalar cleanup still works |
| attach fails before any scope | preserve original failure and existing restoration eligibility | no fabricated field count or returned journal |
| attach fails after one or more scopes | eligible restore uses identical original/scopes; report original failure before ending | retain exact candidate/journal/counts through the throw and coordinator cleanup; failed-outcome endpoint obtains the actual journal from candidate even when attach never returned |
| new own/foreign/repeated loss or original loss/successor | no scope revival or substitution, no successful restore from invalid native/current facts | exact already-entered super suffix only; uncertainty/reporting before matching scalar end |
| counter/callback imbalance | no success, no restored-claim fabrication and no shared reset | terminal first-fatal retained, foreign/replay calls inert, exact malformed held count remains busy |

rollbackV2 reuses candidate.originalMutation, temporarily installs that exact
reference as v2Mutation and keeps the existing restore ordering. Every forward
preserved state must hold its same unended scope and unchanged native snapshot;
its Binding/geometry restore uses preserve=true even when NativeState.active is
false. After successful restore and final exact check, remove callback authority
and mark ended while retaining counts, then perform its existing candidate/journal
consumption. It does not release counts before the coordinator records/reporting
outcome. Failed restoration reports while busy and leaves failure endpoint to
end only balanced exact custody; it never fabricates restored bindings or native
close success. No later terminal end grants native restoration authority.

## Limits and acceptance boundary

This design preserves all prior cleanup, replacement, focus-loss, event-reentry,
descriptor and SDK36 guard contracts. It does not make current unknown outcomes
recoverable or reopen an old connection after blur. RETURNED close still proves
only RETURNED. Existing Handler rejection may leave disposal pending. No
qualification of outer native dispatch quiescence is added.

Design checks and any model outputs establish only the protocol's own finite
logic and input custody. A selected derivative still needs complete-source JVM
positive/failure/hostile controls, pinned SDK37 javac/D8, independent actual-source
review and root selection. Native simulator/emulator/physical, UI/capture,
TalkBack/IME/OEM, API28–35 admission, immutable FieldLog release, signing/store,
OTA, operations and GA evidence remain pending. No process inventory is requested
or performed.
