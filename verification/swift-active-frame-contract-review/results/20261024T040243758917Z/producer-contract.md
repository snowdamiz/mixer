# Private Swift active-frame contract proposal

This is a review proposal for the next complete W08 entry/return/unwind slice,
under `mixer-product-plan.md` Sections 10.2–10.4. It adds no product execution
path. The source archive binds the accepted literal Frozen control extraction,
tree SHA-256 `5d1da3fedb28804ed8ddc271ce78461b58b06b8475b5cc8eb411226626bc199f`.
Root's subsequent test-observer serialization repair is separate from this
captured baseline. The collector reports live drift instead of silently changing
its archived baseline. Root acceptance of the macro does not accept this proposal.

The controlling agent commissioned this bounded fresh-context task for
`gpt-6.1-sol`, `xhigh`. Owned outputs are this document and
`verification/swift-active-frame-contract/`. No VM, tracker, gate, dependency,
release, native app or other lane source is modified. Computer use, capture,
simulators/emulators and physical-device work remain paused. Compilation and
layout probes below are host-only. Their declarations and uncalled lifetime
witnesses are not active-frame runtime acceptance.

## The chosen ownership solution

Keep every actual `SwiftFrame` in the original fixed-capacity State frame arena
until its owned pin releases successfully. A rejected release returns the same
pin inside `SwiftReleaseFailure`; extract it before ending that wrapper and put
it back into the same actual frame at the same index. Move its original scalar
fields; do not clone a pin, manufacture a token, build a new owner, or copy cache
metadata. Several release rejections therefore retain several actual frames and
their frame/pin charges simultaneously. There is no `Option<Pin>` accumulator
that can overwrite another frame's authority.

An unpublished entry has no published frame slot. Add exactly one inline owned
`FrameCleanupState` to the original `SwiftExecutionState`. It has:

```rust,ignore
struct FrameCleanupState {
    disposition: FrameDisposition, // Idle / Active / Draining / Retained / RestorePending
    bound: Option<FrameBound>,      // exact outer previous and admitted bounds
    unvisited: usize,              // original unprocessed prefix during drain
    nested_restore: Option<usize>, // exact frame bound after rejected cache completion
    live_unreconciled: bool,       // sticky mismatch or after-effect live-removal failure
    entry_attempted: bool,       // retained entry already attempted in this pass
    entry: Option<EntryGuard>,    // at most one unpublished guard, with its actual pin
}
```

The guard slot is a permanent State field, with its own positive reservation and
all State/owner transfer growth measured. It remains owned after a phase is
dropped or completion rejects. Its pin may coexist with every retained frame pin.
It is not a new heap allocation, authority vector, extra execution arena, public
type or an alternative cache. `FrameCleanupState` is empty only when Idle,
bound/nested_restore/entry absent, unvisited zero, entry_attempted false and
live_unreconciled false. A new guard always starts with entry_attempted false.

Frame scalars inside a retained frame may refer to values/controls already
removed by terminal drain. They are then move-only historical scalars. No value
operation, finish, reentry, numeric/control operation or fetch may interpret
them. Only the terminal indexed pin-retirement path can move such frames.

## Private types, phase and caller storage

`verification/swift-active-frame-contract/proposed.rs` freezes the compiled type
shapes. `FrameOperationPhase` borrows the original `ExecutionOperationPhase`,
the State cleanup field, and the original lifecycle. Its parts still reference
the actual cache, memory, table, globals, values, controls and frames. The
`SwiftExecutionOperation` still references the original control and accounted
WASI. No reconstructed RuntimeControl/WASI/cache/state, shadow ledger, callback,
trait object, stored mode, dispatch loop, arbitrary invoke or initializer exists.

The proposed method signatures are:

```rust,ignore
SwiftReactorInstance::prepare_frames(&mut self, Cursor)
    -> Result<FrameOperationPhase<'_>, SwiftRunFailure>;
SwiftReactorInstance::resume_frame_cleanup(&mut self)
    -> Result<FrameOperationPhase<'_>, SwiftRunFailure>;
FrameOperationPhase::enter(&mut self, function: u32) -> Result<(), SwiftRunFailure>;
FrameOperationPhase::finish(&mut self) -> Result<FrameReturn, SwiftRunFailure>;
FrameOperationPhase::drain(&mut self) -> FrameDrainReport;
FrameOperationPhase::complete(self, FrameOperationStorage<'a>) -> FrameCompletion;
```

These bodies intentionally remain unimplemented in the isolated contract module.
Their signatures do not constitute implementation evidence. Compile-only bodies
separately check actual original-field borrowing, cache-phase/pin transfer and
indexed frame release/reinsertion using the real owner APIs.

`FrameReturn` is `CallerContinues | Outermost(Option<Value>)`. Nested finish
publishes its value into the caller and returns only CallerContinues; only an
outermost copied Value may escape. `FrameOperationStorage` has exactly four
concrete fields: possible returned preparation slot, entry Result slot, finish
Result slot, and drain-report slot. Completion takes this exact type, never
generic arbitrary `T` and never `ValueOperationStorage`.

`FrameCompletion` is Completed, Retained(report), or RestoreRejected(report).
Reports contain copied failure/current usage/cache/bound observations and counts;
they contain no pin, guard or frame authority. The actual State owns all such
authority. Completed means that this envelope closed after verified cleanup; it
does not replace or erase the control's original operation failure. Retained and
RestoreRejected explicitly leave the original owners and bound charged.

## Prepare and dropped-phase state

1. Borrow the original WASI/control and call `checked_usage`; check actual cache
   pairing and every State execution-header/arena ticket. All of this precedes
   envelope enlargement. Preserve the actual WASI observation at every failure.
2. Require the State cleanup field to be empty/Idle, lifecycle not Terminal, all
   three stack arenas empty, active cache pins zero, and the corresponding actual
   live counts zero. Also verify memory page/arena length and capacity agreement
   with the retained State tickets. No owner moves on rejection. This initial
   frame phase starts empty; nested/recursive entries occur within this phase.
   It does not relax the existing zero-frame preparation contract.
3. Compute the additional frame-operation inventory by const evaluation. Check
   `previous + frame_operation_bytes` and call the actual observed ordinary
   `enlarge_construction_with_wasi` once. Cancellation/deadline/previous terminal
   cause may reject here without changing the previous bound.
4. Record `FrameBound{previous,admitted}` and Active in the actual State immediately
   after enlargement, then return the original-owner phase. No further fallible
   action lies between enlargement and recording/return. Preserve Uninitialized;
   this phase cannot produce Ready. A dropped phase does not clear this record
   or refund its scratch. A later preparation/value operation rejects it.

`resume_frame_cleanup` is a distinct cleanup-only reacquisition of that same
recorded phase. It validates original ticket/WASI/cache provenance through
cleanup-independent checks; it neither enlarges, admits, checks cancellation/
deadline/work nor allows enter/finish. It changes Active to terminal Draining
before touching arenas. Retained frames are never reinterpreted as active frames.
Malformed/missing provenance rejects intact and preserves the bound record.

## Pin acquisition and nested completion

Before acquiring a pin require known room in the fixed frame arena and the
sealed runtime frame ceiling (default/max 64, narrowed by SwiftRunBudget). Charge
entry work 1 before signature/pin lookup, as on the original entry path. Read
the original execution signature through a short proof borrow; copy parameter
count/result scalars and end that borrow before a mutable cache operation. Check
caller parameters exist above its current operand base and match the validated
signature, using short per-parameter type reads; parameters are already admitted.

Prepare the actual cache operation phase, using the original control/WASI and
cursor. Move its Result out of its caller Option slot. Invoke its `pin` exactly
once. Move the pin Result out of its caller Option. Consume both now-empty return
slots through that phase's `complete`, ending the cache phase before returning
to any frame/value/host operation.

`PinAttempt { pin: Option<SwiftFunctionPin>, failure: Option<SwiftRunFailure>,
nested_restore: Option<usize> }` represents a successful acquired pin and a cache
completion failure at the same time. Do not use `?` after acquisition in a way
that drops the pin. Keep the earlier pin/operation failure if completion also
fails. If completion rejects, retain the exact expected frame bound in
nested_restore; no successful restore is inferred from a destroyed wrapper.
Immediately move both the pin (if present) into State.entry and any restoration
obligation into State before propagating failure. Entry never continues after a
failed nested completion.

Only cleanup may retry restoring that nested bound after its empty cache wrappers
have ended. It calls the existing cleanup-independent restoration API with exact
recorded bytes. A failure remains explicit; never shrink the outer envelope
past a failed nested obligation. Invalid construction owner/ticket/bound cannot
be repaired by ledger assignment. Real acquired pins still drain despite the
completion error.

## Entry and rejection

Every enter first rejects an occupied entry slot, non-Active disposition, pending
nested restoration or unreconciled live state before acquiring a pin. With the
pin now owned in State.entry, inspect a short pinned FunctionView for
locals count and the checked final instruction index. End the view. Check
`parameters + declared_locals <= 256`, fixed Values/Controls/Frames capacity,
aggregate values/controls/frame ceilings, and function-inclusive control depth
512. The aggregate control budget remains 4,096 maximum. Do not widen frozen
Limits or borrow their scratch. Parameters contribute to locals but are not
appended or debited again. The function control consumes one real control slot.

Compute base from the existing admitted parameter suffix, preserving caller
operands, and charge the original entry's second work amount `locals + 1` once.
For each declared local: check the original observed operation, fetch only that
local's Type with a short `get(index).copied()` view borrow, end the view, create
one `Value::zero(Type)`, then predebit Live::Values immediately before its
allocation-free push into known room. Both Option<&Type> and Option<Type> are
named in the inventory. No borrowed locals slice/iterator spans a debit or
publication. Each successful debit belongs to the actual guard until publication
of the frame. Every local initialization is checked; no bulk resize bypasses
those boundaries.

Predebit the one function Control and immediately publish the common real
Control. Set operands to the new actual values length and controls to the
previous actual control length. Predebit Live::Frames last, then infallibly move
the guard pin and scalar metadata into one actual SwiftFrame in known room.
There is no fallible checkpoint between a successful debit and its matching
publication. Clear the guard debit ownership and empty State.entry only after
the actual frame owns them. Reconcile actual/live counts without double debit.

On any rejection, first mark lifecycle Terminal and enter cleanup disposition;
retain the first failure. Remove only successfully appended locals and this
entry's function control, using captured pre-entry lengths while they remain
valid. Never remove caller parameters, values, controls or frames, and never
refund work. Remove each corresponding successful guard debit after the actual
effect, using cleanup-independent removal. Remove an unpublished frame debit
only if it was acquired. Update guard counters only after successful removal;
they are acquired debits, never inferred from requested or appended lengths.
Any mismatch/removal failure latches live_unreconciled. Release this guard's pin
once. If release rejects, extract its pin and keep it in the same State.entry;
do not clear its active-pin charge. A guard with outstanding debit obligations
also remains even if its pin successfully released.

## Return and release rejection

Finish is legal only in Active with exact current live/arena agreement, no entry
guard, and no pending nested restore. Read current top-frame scalar metadata
without copying a frame/pin. If it returns one result, pop through the original
preflighted/accounted value boundary first. Save at most one Option<Value>.
Read base/control lengths after that pop and compute the checked original work
amount `(actual_values_len - base) + (actual_controls_len - controls) + 1`.
Charge that amount before frame/arena removal. Retain original failure/effects
when this work charge rejects; no trap-wide rollback restores the popped value.

Move the actual top frame, truncate actual values/controls to its captured bases,
and remove their exact live reductions after each effect. Do not refund a frame
debit while its pin is unresolved: keep that debit through the release attempt.
On successful pin release, retire the frame and remove Live::Frames after the
actual effect. The cache itself removes ActivePins before its infallible record/
usage effects; do not remove that pin count a second time.

On release rejection the shared cache release has changed neither pin records
nor the pin live count: all its fallible checks precede those effects. Copy the
failure diagnostic, extract the owned pin, reconstruct this same frame from its
moved original scalars and pin, and reinsert it into the vacancy. Keep frame/pin
counts and pinned/resident reservation charges. Mark terminal; do not push the
saved result into the caller and do not resume finish with stale arena offsets.
The failed wrapper ends only after authority is back in State.

After successful retirement, use the caller's actual operands and sealed 128
operand ceiling with the existing push boundary. A failed result push occurs
after callee removal/release and preserves that failure/effect order. Drain
remaining caller frames. An outermost result is copied into its explicit
permanent output position before supplied result wrappers end.

## Deepest-first drain and several rejected releases

Drain is terminal and runs independently of cancellation, deadlines, fuel and
work exhaustion. It executes no guest instruction or host call, no ordinary
checkpoint, admission, reserve or allocation. The actual WASI owner remains
alive; its observation is passed to every cleanup/failure boundary. The
control's sticky first failure is never replaced by a default usage or later
cleanup diagnosis. `record_cleanup` records after-cleanup separately.

First roll back the unpublished guard's actual successful publications using
the still-valid captured entry lengths, if entry itself is failing. Then clear
the actual values/controls arenas globally and remove actual reductions. On a
resumed terminal drain they are simply already empty: never apply stale retained
frame offsets. Any actual/live disagreement or rejected live removal sets the
sticky live_unreconciled flag even if underflow happens to leave ledger zero.

Freeze the frame iteration invariant. On a fresh drain before any frame release,
`u = frames.len()`. If finish already attempted and reinserted the rejected top
frame, initialize `u = frames.len() - 1`, placing it in the processed suffix. The
prefix `[0,u)` contains all not-yet-attempted frames, in original order; the
suffix `[u,len)` contains only already-attempted rejected frames. For each
iteration decrement u first and remove exactly index u. On success, the retained
suffix shifts left one place and the next prefix `[0,u)` is untouched. On failure,
reinsert the same frame at index u; that frame joins the retained suffix and the
next prefix is again untouched. Thus every original frame is attempted exactly
once, deepest first, even for mixed success/rejection or all failures. The fixed
Vec had room before remove, so insertion cannot allocate. Do not use swap_remove,
restart at last(), overwrite one pending token, or stop on the first invariant.

Attempt a rejected guard release before published caller frames because it is
the deepest unpublished entry. A release already attempted by entry/finish is
marked processed when joining terminal drain: the failed finish top frame joins
the suffix described above, while State.entry_attempted records an already
attempted guard. Do not immediately retry the same pin in that drain pass.
Clear entry_attempted only when the entry slot becomes empty or an explicit
cleanup-only resume starts a new pass. Explicit later cleanup-only resume may retry retained
pins in descending original order. The unvisited prefix is held in State while
in progress, so a returned/dropped phase cannot reset or skip it. On a completed
pass set Retained if any frame/guard/nested-bound/live obligation remains.
The existing cache's header validation/release remains the only pin-release
algorithm. No direct PinRecord clearing, alternate numeric/control semantics,
cache teardown, or token-sized refund is allowed.

## Completion and consuming owner barrier

Completion first verifies that the actual arenas, frames and guard are empty,
cache active_pins and all stack/frame/pin live counts are zero, unvisited is zero,
the nested restore succeeded, and live_unreconciled is false. A recorded cleanup
underflow cannot pass merely because all observed counts now read zero. Do not
clear that latch on resume or invent a ledger-repair API. Such a state remains
explicit terminal retained evidence until a separately reviewed recovery exists.

If authority or obligations remain, consume/end the fixed return/phase wrappers
but keep State's original bound and retained objects, then return Retained(report).
If clean, destroy the exact returned phase/result/guard/frame/release/diagnostic
storage before calling the original construction-phase restoration with the
exact saved previous bound. If restoration rejects, keep State.bound and
RestorePending, return RestoreRejected(report), and retain the conservative
envelope. On success clear the State record to Idle; Uninitialized remains
Uninitialized unless an earlier error made lifecycle Terminal. Completed allows
the existing consuming component/header cleanup only through the barrier below.

The later coherent implementation must extend **both** prepare_value_operation
and cleanup_owned before this new State field can become product state. They
must reject nonempty disposition/bound/nested_restore/entry/unvisited/entry_attempted/latch and
every nonzero live values/controls/frames/active-pins count **before taking any
owner**. The current cleanup_owned checks arena/cache emptiness but lacks the
full live barrier; this proposal does not claim that source already enforces it.
Cache cleanup can otherwise clear PinRecords without receiving all external
tokens, so it must remain unreachable while retained authority or obligations
exist. A retained phase cannot be passed through generic component cleanup to
make it appear complete. Empty failure/result/report storage is subsequently
supplied to existing consuming header cleanup under its permanent reservation.

## Positive accounting and compiler evidence

The isolated candidate only adds the inline State field, a private module with
chosen declarations/uncalled witnesses, the existing value-operation constant
visibility leaf and its unit fixture field initialization, and one common crate-private constructor
`Control::function_entry(end,height,result)`. Kind and Control fields stay
private. Frozen methods/macro invocations, owner layout, public Limits/C ABI and
the exact 2,912-byte frozen formula stay unchanged. No second control algorithm
or Swift invocation of the Frozen macro is introduced.

`inventory.py` emits separate concrete Rust fields for every proposed binding's
source/argument/return/caller position. All windows reserve simultaneously; no
window aliasing lowers the bound. It includes the original owners/State changes,
phase/parts/operation borrows, nested cache returned slots, pin and PinAttempt,
guard and all debits, short descriptor/view/type Option positions, common
Control, frame/scalar transfers, saved result/pop/push, release rejection wrapper
and returned pin, actual before/after live/cache/WASI/usage observations,
descending cursor/report, exact fixed completion storage and retained results,
and Rust Try branch/residual/closure positions. Accepted value/declaration/cache
internal rows remain occupied and supply no credit for these new call edges.
No old scratch, 512-byte Frozen reserve, owner padding or equal-size alias is
spent again. Arithmetic/layout calculations run as constants before admission.

The additional permanent inventory is added positively to the execution header;
the active inventory is an entirely new frame-operation enlargement:

```rust,ignore
const FRAME_OPERATION_BYTES: Option<usize> = match VALUE_OPERATION_BYTES {
    Some(nested) => ACTIVE_BYTES.checked_add(nested),
    None => None,
};
// prepare subsequently checks previous.checked_add(FRAME_OPERATION_BYTES?).
```

The full accepted value-operation component is added as a **fresh positive
nested reservation**, simultaneously with every new frame edge/guard/result/
pin/WASI position. Its original sealed map/source/formula are referenced by
exact hashes in nested-value-component.json; the measured component remains
119,576 bytes on this host. No existing bound supplies any of this amount. Do
not narrow it to selected push/pop rows without another proof. The overlay only
widens the existing constant to pub(super), preserving its initializer and all
value algorithms. Exactly one nested push/pop may be active at once, through
the original inner ExecutionOperationPhase; every cache view/phase ends before
the call and the synchronous value call ends before any later call. The
compiler witnesses/checks establish ordinary original-owner reborrowing; actual
future enter/finish source must separately show these scopes. Never call
complete_values as frame completion. The
collector also records propagation of the larger private State/owner sizes
through existing formulas; those automatic deltas are not credited against the
new fields. Value-operation scratch has its old meaning; it does not authorize
frame calls. Complete binding positions, offsets, sizes and containing padding
are saved for independent accounting review. A table of declarations is not a
proof that absent implementation bindings are complete: actual code must match
this inventory or return for a new freeze before admission.

The collector runs stable ordinary checks (default/span/Swift/all × Debug/
Release), compares compiler-expanded Frozen enter/finish/cleanup/pop32/close/
branch methods, compares exported C names against the archived baseline, and
checks negative downstream imports for the private phase/constructor/owner.
Bootstrap is restricted to compiler expansion diagnostics. Baseline/candidate
metadata runs use fresh targets and production/unit layouts for minimal Swift
and all features in Debug/Release. Only the named metadata test is executed;
no full VM or guest execution is claimed. Exact command/tool/source/archive/
output/binary records and failed attempts are preserved under the verification
directory. Saved evidence is independently checkable with `verify.py`.

The final collector packet is
`verification/swift-active-frame-contract/results/20261024T035815017174Z/`.
Its 80 commands pass with Rust/Cargo 1.99.0 and Python 3.14.8. The archived
accepted source closure contains 117 files; its exact digest above is the source
binding. `sourceRevision` is the observed root HEAD at collection, while the
archive deliberately predates root's concurrent test-only observer repair.
`coordinatedLiveChangedPaths` names only `tests/span_control_extraction.rs`;
the VM implementation closure remains identical to the accepted macro tree.

| aarch64 Apple compiled proposal layout | Baseline | Candidate |
| --- | ---: | ---: |
| Original State inline bytes | 312 | 424 |
| New owned FrameCleanupState | absent | 112 |
| Production execution header | 289,536 | 449,568 |
| Unit execution header | 290,496 | 450,720 |
| Fresh permanent frame positions (production / unit) | absent | 157,680 / 157,872 |
| Production construction envelope | 1,062,312 | 1,069,144 |
| Unit construction envelope | 1,065,072 | 1,071,904 |
| Existing value-operation scratch | 119,576 | 119,576 |
| Fresh active frame-edge positions | absent | 240,616 |
| Fresh nested full value component | absent | 119,576 |
| New frame-operation enlargement | absent | 360,192 |
| Frozen fixed reservation | 2,912 | 2,912 |

There are 956 individually named added fields: 252 permanent and 704 active.
Each containing inventory has four additional alignment bytes, included
positively; its interior padding pays for no other object. The header has an
additional 2,352 bytes of measured existing-owner/State transfer growth beyond
the new permanent fields; the construction formula grows by 6,832 bytes. These
are positive propagated deltas, never reductions credited against new rows.
Production/unit and minimal/all × Debug/Release layouts are individually saved.
`binding-map.json` binds exact declarations, offsets, widths and alignments to
their source roles; `verified-summary.json` reconstructs them from raw logs.

All sixteen qualifying metadata executables and eight matching ABI dylibs are
retained in the compact `qualifying-artifacts.tar.gz` beside that receipt.
`qualifying-artifacts.json` binds each archive member to its exact source closure,
configuration, compile/run/list/export commands, original path and SHA-256. The
offline verifier resolves this archive even after Cargo targets are absent. The
original targets remain under the lane's ignored build directory for active
independent review; no scratch is removed while that review is running. A prior
seal is preserved as seal-before-portable-artifacts.json; the current seal binds
the final portable artifact packet and verifier.

The first shell environment attempt could not resolve rustc until the existing
toolchain directory was added to PATH. Collector attempt 1 preserves an E0583
explicit-module-path mistake. Attempts 2 and 3 preserve an E0425 name-resolution
mistake in the baseline-only metadata printer. Attempt 4 preserves an E0063
missing new field in the original unit layout fixture. Attempt 5 passed an
intermediate declaration map; attempt 6 passed its scalar/full-nested-component
refinement; attempt 7 passed the short cache-view/value-call witness and additional exact
shared guard/pin borrow fields. Attempt 8 is the final passing packet: it adds
the exact FunctionView/SignatureView Try branches, SignatureView Result and
optional original-owner borrow wrappers requested by independent review. All attempts retain their own
source archives, inputs, command output and failed/successful receipts. No failed
or intermediate packet supplies final accounting/runtime acceptance.

## Required later executable acceptance

`future-matrix.json` specifies bounded meaningful tests on real constructed
owners, actual cached functions and real entry-created recursive/nested frames.
Private fault hooks must operate at exact real boundaries while preserving
original tokens; fabricated pins/frames are not original-owner execution evidence.
The control boundary fixture uses at most nine actual entry-created frames and
a cfg(test)-only helper publishing actual common Controls with exact live
predebits from decoded block metadata. This tests aggregate/function control
admission without claiming a Swift block dispatcher or depending on one.
The matrix covers exact work prefixes, locals/parameter/control/frame/value
ceilings, predebit failures without publication, local initialization checks,
pin plus phase-completion failure, nested and outer return, failed result push,
several rejected releases with mixed outcomes, all rejected releases, retained
guard plus several rejected frames, underflow that reads zero, cleanup-only
resume/dropped phases, provenance rejection, prior real WASI effects and sticky
first failures, allocation refusal, and the consuming-cleanup barrier.

Before product access, root must accept this complete contract and independently
review its accounting. Before implementation acceptance, run that matrix against
actual code and verify no allocation within warm admitted paths. Every newly
unrun native/simulator/emulator/physical check remains pending under the pause.
Swift initialize/invoke/dispatcher, host/memory/growth/control joins, complete
target qualification, immutable published FieldLog consumption from its separate
repository, final physical-phone matrix, signing/store/customer/operations and
all specified GA review evidence remain pending.
