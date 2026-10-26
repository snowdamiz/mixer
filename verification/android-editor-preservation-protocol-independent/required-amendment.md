# Minimal private-protocol amendment for root selection

This is an independent recommendation against frozen protocol seal
`e575641c10d690bf4b6e02843355a60d5b3077233c94fc5cb443be7f490584bd`.
It grants no implementation authority until root selects it. Existing original
Mutation identity, native restoration eligibility, failure policy and two precise
coordinator hooks remain as proposed. No owner/core change is requested.

## PC-P01: separate progress from replay and release

Replace the ambiguous shared completion claim with distinct primitive facts:

- Candidate/journal completion progress distinguishes OPEN,
  SUCCESS_IN_PROGRESS, SUCCESS_DONE, FAILED_IN_PROGRESS and FAILED_DONE.
- The failed endpoint has its own once-only invocation claim. Success preparation
  or scope ending does not consume this failed-endpoint claim.
- Each scope's counted/released disposition records whether its exact count was
  actually released. An ended or success-preclaimed scope may still hold a count.
  End is consumed only with the successful matching decrement; it is never
  inferred from candidate.used, journal.complete, scope.ended or callback removal.

Success validates the entire cohort before every success-side effect. All
supported synchronous rejection/throw decisions precede callback revocation,
prepared swaps and the first release. After that preflight, the complete success
tail must be direct nonthrowing scalar/reference work through the final release:
no callable predicate, Input endpoint, per-scope throwing guard, reporter,
allocation, native/main query, iterator, callback or owner resumption. Fixed
journal membership/size is prevalidated and cannot change during that tail.
SUCCESS_DONE is set only after all represented preservation holds are released.

An unsuccessful scalar finish that rejects at its preflight leaves scopes
available to the ordinary post-interval failure endpoint. SUCCESS_IN_PROGRESS
is not itself a failed-endpoint replay claim. If a bounded hostile fixture
constructs a partial-release state, the first failed-endpoint invocation processes
remaining exact counted holds, leaves already released scopes unchanged, and
never decrements them twice. A completed successful candidate, repeated failed
endpoint invocation, or repeated successful finish refuses before all effects.
An imbalanced hold is retained; replay is not a repair/retry mechanism.

Do not claim this supplies recovery from arbitrary asynchronous VM interruption
between scalar writes. A partial-release fixture is a state-invariant control,
not a reachable ordinary synchronous product failure. Actual bytecode/callgraph
review must establish the nonthrowing healthy tail; no new interval fault callback
is selected to manufacture an execution boundary.

## PC-P02: no scope, unentered scope, and counted scope are separate cases

The entry/completion predicate is factored into exact captured identity and
phase-specific custody checks. The entered-and-counted requirement applies only
to decrementing a represented preservation hold, not to every possible failed
candidate or registration cleanup.

1. For the exact renderer-owned candidate and immutable candidate.journal with no
   captured scope and no preservation hold, failed completion may consume its
   own failed-endpoint claim and return. originalMutation may be absent because
   attach never entered or failed before capturing it. No Mutation, scope, native
   authority, count, field error or restoration is fabricated. This also covers
   candidates whose journal contains native states but no preservation scopes.
2. For a CAPTURED exact owned scope whose Begin refused before entry, require all
   captured renderer/Input/Record/View/fence/original/candidate/journal/NativeState
   identities, plus !entered, !counted, zero callbacks/hooks/checking, and exact
   registration-or-already-unregistered disposition. Revoke only that exact
   registration and mark it ended/uncounted-complete. Perform no decrement or
   native restore and do not report a native-prefix failure when no native work
   was entered. The coordinator still retains its actual operation failure and
   existing terminal policy. A foreign registration remains untouched.
3. Exact Begin performs all callable validation and possible refusal first.
   Its final no-throw scalar tail publishes entered, counted, phase, cohort total
   and shared increment together before returning. Remove the caller's separate
   post-return entered assignment. There is no ordinary supported throwing step
   after count acquisition but before entered publication.
4. An actually entered-and-counted scope follows the proposed retained lifetime
   and exact scalar end. A counted-but-not-entered or entered-but-not-counted
   hostile state is inconsistent, never repaired by inventing the missing flag
   or borrowing another count. Report while actual custody remains held and
   preserve other exact balanced scopes' eligible cleanup.

Add explicit complete-source tests for pre-attach/no-original failure, attach
failure before the first scope, a constructor failure before registration,
CAPTURED registered scope whose Begin refuses, one entered A followed by refused
C, a no-preservation success/refresh/failure, zero-count ordinary Begin admission,
and malformed entered/count combinations. Preserve both owners on all foreign
and replay controls. These supplement the frozen test plan's existing matrix.

## Required proof details retained from the proposal

Before any cleanup reporter can throw, retain its original native/engine failure
in the appropriate existing ledger. Later coordinator cleanup fatal transport
must not outrank an earlier renderer/field fatal. Prove actual chronology with
first native fatal F, restoration/report fatal G, later abort/report fatal H;
surface F by identity after every eligible balanced scope releases. A fixed
ledger visitation order alone is insufficient evidence of observation order.
No new global owner/core ordering service is selected.

During failure completion, discover/report all required per-field/cohort failures
while all releasable applicable holds are still held, then enter a no-reporter
scalar release phase. A failed per-scope release check must not introduce a
report after another scope performed the final clear. If aggregate count is
underfunded, retain the represented custody rather than deciding that an
unrelated positive count funds a particular scope.
