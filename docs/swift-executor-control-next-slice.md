# Proposed next shared executor control slice

This is a bounded W08 contract proposal for root review, observed from
`ebd73243ec139dabaabca5f6cba86d163a519161`. It changes no production source,
accepted contract, tracker, receipt or gate. Its recommendation is to extract
the existing frozen `pop32`, `close_control` and `branch` algorithms into one
private static helper body each. Exercise them through the existing frozen
interpreter before adapting Swift. Root must freeze the exact seam and accept
its accounting before product implementation.

The binding scope remains `mixer-product-plan.md`, especially Sections 10.2–10.4
and W08. This small extraction advances that scope; it does not redefine it.
The user's pause of computer use, captures and native simulator/emulator runtime
work remains in force. All proposed commands below are host-only. No target
reactor, native app, simulator, emulator or physical phone was run for this plan.

## Current authority and the choice of boundary

`verification/swift-value-operations-root-review/acceptance.json` accepts the
private original-owner zero-frame route against VM tree SHA-256
`96b16d4886b9218e132a2a1255c0ce4e66c60879ed7bb5f1ea1185b0ca08b8c7`.
Its source revision is `a739aa694f5270604fddf5362b0beb04fd409880`; the later live
HEAD is not evidence that any larger scope passed. The planning collector checks
the complete current VM source closure against the accepted source bindings.

The executable sharing is narrower than the earlier generic algorithm sketch:
`NumericMode` shares only raw scalar primitive dispatch. Original frozen
validation, work and observation remain in `SpanInstance::numeric`; original
Swift push/pop/numeric metering remain in `value_operations.rs`. Swift preparation
rejects nonempty frames/controls/values or active pins, and consuming owner
cleanup independently rejects nonempty state. `SwiftFrame`, `EntryGuard` and
`SelectedInstruction` are chosen layouts, not active executor implementations.
No `AlgorithmMode` implementation exists in product source.

Control close and branch form a useful next shared unit because they can execute
on the existing frozen owner without admitting a Swift frame or creating a new
pin lifetime. Branch returns whether the current function finished; the existing
frozen loop still calls its existing `finish`. Sharing only a Swift fetch loop
would immediately require correctly admitted frames, pin ownership and unwind.
The accepted zero-frame completion cannot provide that drain.

The earlier shared algorithm proposal sequences stack helpers before control.
This proposal requests an explicit narrower root decision: reuse the already
accepted owner-specific push/pop/work primitives as adapters, and share the
control semantics above them. It introduces no second push/pop implementation.
A general shared stack algorithm remains subsequent work if needed; this choice
does not freeze unimplemented adapters from the earlier sketch.

## Proposed private helper contract

The narrow owner-state association follows the accepted `NumericMode` pattern.
It avoids constructing `ExecutionParts`, `FrozenOperation` or `FrameScalars` in
the frozen run loop. These are proposed signatures, not compiled evidence:

```rust,ignore
// Within experimental::execution::borrowed; sealed by ExecutionMode.
trait ControlMode: ExecutionMode + Sized {
    type ControlState<'owner>;

    fn work(state: &mut Self::ControlState<'_>, amount: usize)
        -> Result<(), Self::Failure>;
    fn pop(state: &mut Self::ControlState<'_>)
        -> Result<Value, Self::Failure>;
    fn push(state: &mut Self::ControlState<'_>, value: Value)
        -> Result<(), Self::Failure>;
    fn invariant(state: &Self::ControlState<'_>) -> Self::Failure;
    fn values_len(state: &Self::ControlState<'_>) -> usize;
    fn controls_len(state: &Self::ControlState<'_>) -> usize;
    fn frame_control_base(state: &Self::ControlState<'_>) -> Option<usize>;
    fn control_at(state: &Self::ControlState<'_>, index: usize) -> Control;
    fn truncate_values(state: &mut Self::ControlState<'_>, height: usize)
        -> Result<(), Self::Failure>;
    fn truncate_controls(state: &mut Self::ControlState<'_>, height: usize)
        -> Result<(), Self::Failure>;
    fn set_pc(state: &mut Self::ControlState<'_>, pc: usize)
        -> Result<(), Self::Failure>;
    fn observe(state: &mut Self::ControlState<'_>)
        -> Result<(), Self::Failure>;
}

fn pop32<M: ControlMode>(state: &mut M::ControlState<'_>)
    -> Result<i32, M::Failure>;
fn close_control<M: ControlMode>(state: &mut M::ControlState<'_>, control: Control)
    -> Result<(), M::Failure>;
fn branch<M: ControlMode>(state: &mut M::ControlState<'_>, depth: u32)
    -> Result<bool, M::Failure>;
```

`FrozenMode::ControlState<'owner>` is exactly `SpanInstance`. Only FrozenMode
implements the trait in this slice. The existing three owner methods become
delegating wrappers so existing callsites and visibility stay intact. The trait
contains leaf storage/metering adapters; a mode cannot replace the three shared
control algorithms. The adapter `pop` delegates to the existing owner `pop`,
never to the new `pop32` wrapper; this prevents accidental recursion.

`control_at` returns one Copy `Control` after the shared checked index has been
established. It creates no authority, metadata copy, cache view or collection.
`frame_control_base` copies only the top frame's existing `controls` scalar. It
does not clone/copy the frame or pin. No borrow survives any adapter call.
`set_pc` uses the original frozen last-frame error behavior, including the
existing `unreachable_failure` fallback rather than substituting a new cursor
or diagnosis. All these additional Option/Result returns still need accounting.

Frozen truncate adapters perform only their literal Vec truncation and return
Ok. Frozen `observe` calls the literal existing observer and returns Ok. They
add no cancellation, deadline, work, allocation or live admission. Fallible
adapter return types reserve the future after-effect accounting boundary; they
do not authorize a Swift implementation now. A compiler probe must demonstrate
ordinary short reborrows; no mutable borrow may be tied unnecessarily to the
entire owner lifetime.

## Exact semantic and work trace

1. `pop32`: call the existing pop once, including its work and observation;
   return the i32 payload, or the original invariant after a non-i32 pop. A type
   failure therefore preserves the already completed pop, not its old operand.
2. `close_control`: if `control.result`, pop and retain exactly one Value first.
   Then reject `control.height > actual_values_len`. Charge
   `actual_values_len - control.height + 1`, truncate to height, observe, and
   push the retained value if present through the existing owner push. The
   close-work charge uses length after the result pop. Any push charge/limit
   failure happens after truncation; no trap-wide rollback is introduced.
3. `branch`: first require a top frame. Compute the original checked control
   index from current control length, depth and the top frame's control base;
   reject an out-of-frame or unavailable depth before branch work. Copy that
   control and charge `controls_len - index`. For a loop clear only the copied
   control's `result` flag. Run shared close. Only after successful close,
   truncate controls to `index + 1` for a loop or `index` otherwise. Set pc to
   loop start or the original `end + 1`, observe, and return whether the copied
   kind is Function. Do not change the arithmetic or add a new frozen check in
   the extraction; any proposed arithmetic hardening needs separate review.

No instruction count or fuel is charged by these helpers. The existing run
loop retains its exact fetch, selector peek, cursor, fuel, work, pc-increment,
Block/Else/End and finish order. In particular `End` still charges its extra
one credit and removes its Control before calling close; a later close failure
does not put that Control back. `BrIf` still pops its condition even when false.
`BrTable` still selects its target under the cache view before instruction
charging, then pops the selector and calls branch after the view ends.

The shared control helpers perform no cache operation, pin acquisition/release,
frame push/pop, host call, memory operation or lifecycle transition. They mutate
only the original values/controls arenas and the current frame pc. Frame-local
operands remain protected by existing owner pop/push boundaries.

## Ownership, allocation and accounting invariants

- Keep Frame, Control, SpanInstance, SwiftFrame, SwiftExecutionState,
  SwiftExecutionOperation, ExecutionOperationPhase and owner layouts unchanged.
  Keep public Rust/C APIs, Limits, budgets, error identities, reservation formulas
  and feature behavior unchanged. No new owner/authority, trait object, callback,
  stored mode, dependency or alternate interpreter is introduced.
- Vec capacities are unchanged. No reserve, grow, scratch argument Vec or
  allocation can occur within the shared helper interval. Warm-cache public
  dispatch must still succeed when the first allocation request is refused.
  Cold decode allocations are separately observed rather than called zero.
- Frozen uses its existing aggregate and operand limits in the original order.
  Never route sealed Swift ceilings through widened public frozen Limits.
  No Swift live debit is authorized by the control extraction.
- Name each new helper state reference, Control parameter/copy, optional saved
  Value, Result<Value/Value-payload/unit/bool>, frame-base Option, depth/index/pc,
  bool, error, adapter source/return/caller slot, closure capture and Rust Try
  branch/residual transfer. Include the still-live caller, run-loop selected
  instruction, End's copied Control and nested close/pop/push/work windows.
  A separate failure/result payload is not covered merely by equal byte size.
- The frozen fixed reservation remains
  `size_of::<SpanInstance>() - size_of::<FunctionCache>() +
  3*size_of::<ExecutionFailure>() + 2*size_of::<CacheFailure>() +
  size_of::<DecodedInstruction>() + size_of::<Control>() +
  size_of::<ScalarReader>() + 512`, observed as 2,912 bytes on this host.
  Existing numeric scratch attribution is already occupied. Prove disjoint
  simultaneous coverage; do not reuse the whole 512 bytes or owner padding.
  If the narrow seam cannot fit without changing this formula or observations,
  return to root with the exact map before product acceptance.
- The existing Swift permanent 82,184-byte addition and active 103,248-byte
  value-operation inventory belong to their accepted named positions. They
  supply no unused credit for control, selected instruction, frame or cleanup
  objects. Production execution header 289,536 and value scratch 119,576 are
  historical host values to compare, not budgets available to spend twice.

The binding map and compiler layout probes are required before root acceptance;
no byte total for this new slice is claimed by this planning document.

## Following active-frame ownership slice

After control extraction acceptance, freeze one complete private entry/finish/
unwind slice before any Swift dispatch route. It must borrow the original owners
and fixed arenas, retain Uninitialized lifecycle unless the separately defined
initializer actually succeeds, and offer no arbitrary public invoke.

The proposed existing shared-function shape remains the previously compiled
`enter(parts, function, operation)`, `finish(parts, operation)` and
`unwind(parts, operation, pending_pin)` family. Their bodies are unimplemented.
The following details need an exact new compile/accounting freeze, not an
assumption that those signatures alone are sufficient:

| Boundary | Required concrete behavior and ownership |
| --- | --- |
| Prepare | Check actual WASI/cache/state ticket provenance and current live/arena agreement before enlarging the operation envelope. Preserve every original owner and previous bound on rejection. A distinct frame-operation preparation is required; do not relax the zero-frame preparation contract. |
| Acquire pin | Prepare the actual cache phase, pin once, move the returned payload out, consume the empty phase-return slot through completion, and restore the exact nested bound. `PinAttempt` must represent both an acquired pin and a completion failure simultaneously. No `?` may discard that pin. |
| Entry | Enforce frame/call-depth and fixed capacity ceilings; enter work is 1 plus declared-locals+1. Parameters are already in the arena, so append only locals. Inspect the pinned view for locals/end, end the borrow, check each local initialization, and predebit exact Values/Controls/Frames immediately before their corresponding publication. Count the Function control against sealed function-inclusive 512 and aggregate 4,096; enforce checked parameters+locals <=256. EntryGuard retains only acquired debits and its one pin until frame publication. |
| Entry rejection | Remove only successful unpublished debits, discard appended locals/controls after effects, and return the acquired pin exactly once. Never remove caller values/controls or refund work. Keep the first failure and actual WASI observation through guard cleanup. |
| Return | Save at most one result, use current base/control lengths and work order, move one actual owned frame, truncate actual arenas and remove exact live counts after effects. Release that frame's pin once, then push the result through the caller's existing preflighted boundary; only outermost copied result may escape. |
| Release rejection | `SwiftReleaseFailure` contains authority. Extract and retain its pin before ending the wrapper. Freeze how each rejected frame/guard pin remains owned if more than one release rejects. A lone pending Option cannot silently hold several pins; bounded retained storage must be existing owned slots or separately admitted explicit storage. Do not discard a token or claim a live refund because a release was attempted. |
| Unwind | Drain deepest-first despite cancellation/deadline/work exhaustion; process all remaining frames after a cleanup invariant, preserve original failure, and record after-cleanup separately. No guest instruction/host work, allocation, admission or ordinary checkpoint during drain. Reconcile actual values/controls/frames/pins after each effect. If invalid provenance makes a token genuinely unreleasable, retain that authority and its charges in an explicit outcome rather than pretending cleanup completed. |
| Completion | Destroy returned phase, guard/frame/pin/release wrappers and retained diagnostic slots before shrinking their operation envelope; only empty, authority-free state can reach the existing consuming component/header cleanup. A new fixed frame-operation returned-storage contract is required; ValueOperationStorage cannot authorize arbitrary extra caller storage. |

The multiple-rejected-pin outcome and its completion route are unresolved design
dependencies, not an observed cache bug. Valid same-owner pins release without
ordinary checks, but the contract requires failure-safe ownership under the
invariant cases it promises to test. Do not fabricate a pin fixture and call it
an original-owner frame execution receipt.

This ownership slice needs tests for nested/recursive frame pin counts, exact
locals/parameter and function-control admission, every selected failed boundary,
pin plus phase-completion failure, normal nested return, result-push rejection,
repeated release rejection and deepest-first cleanup after real prior WASI work.
All frame/guard/cache-phase/PinAttempt/saved-result/release/unwind positions need
positive operation/permanent inventory before becoming product paths.

## Instruction selection and dispatch dependency

Only after the frame ownership slice can the original-owner Swift dispatcher
join the shared loop. Selection must copy one DecodedInstruction, chosen
br_table Option<u32> and actual cursor from a pinned FunctionView. Read only the
chosen branch-table scalar, with the current selector interpretation. End every
cache view/phase before pc mutation, callee pinning, eviction, release or host
dispatch. Then set exact function/source cursor, call the observed instruction
debit exactly once, charge execution work 1, advance pc, and dispatch. Fuel can
already be charged when an instruction-count overflow fails; retain the accepted
control method's order. Work failure can occur after instruction debit; pc and
guest effect still stay unchanged. No helper below this boundary debits the
same instruction again.

A finite single-step dispatcher must return an explicit unsupported error for
every not-yet-implemented operation; it cannot mark a Swift module runnable or
skip an opcode. Do not add a second Swift branch/numeric/memory implementation
while waiting for extraction. Full run acceptance additionally requires the
shared semantics for Block/Else/End/Return, local/global access, direct/indirect
calls with complete structural signatures, scalar numeric operations, all
admitted loads/stores, memory size/grow/copy/fill, and actual accounted WASI.
The host adapter uses disjoint actual argument/memory borrows and charges host
entry once through AccountedWasi. The growth adapter separately borrows the
actual memory ticket at `state.buffers[3]` and accounts for old/new overlap.

The selected-instruction, frame/scalar, argument, checked-access Option/Result,
pc, charge/work/observation, nested call and completion transfers each need their
own simultaneous accounting map. Compiling their types is not opcode execution.

## Executable verification and acceptance order

`verification/swift-executor-control-next-slice/matrix.json` supplies exact
existing regression commands, proposed new test identities, configurations and
required assertions. Every product row is planned, with no test pass attributed
to this proposal. `collect.py` records only versions, revision and source
bindings. `verify.py` checks that planning packet; it does not accept semantics,
prove the completeness of accounting, or authorize a target run.

1. Root reviews and freezes the helper API, exact trace, file ownership and
   frozen simultaneous map. Compile the actual chosen signatures against real
   types before extracting. Keep product/layout/invalid variants in separate
   fresh Cargo targets, with complete source closures checked before/after.
2. Implement only the three helpers and static Frozen adapters. Add independent
   hand-authored structured-control fixtures and execute public frozen paths.
   Compare baseline/candidate values, distinct traps, cursor, full failure and
   usage/cache observations, reservations and allocation observations. Exercise
   successful and partial-effect failures, exact work prefixes and fuel edges.
3. Run span-only/all-features Debug/Release control and existing relevant frozen
   tests. Run minimal Swift Debug/Release accepted value tests and library
   default/span/Swift/all compile checks. Run format and scoped library Clippy.
   Broad existing warnings are separately classified if broad lint is attempted.
4. Compile production/unit layout probes across minimal Swift/all-features and
   Debug/Release. Compare all accepted owner layouts and exact existing formulas;
   independently review the new binding map against each actual source binding.
5. Independent review and root acceptance close only this extraction. Root then
   assigns the active-frame ownership freeze and implementation as a coherent
   slice. Tracker/GA status remains root-owned and evidence-driven.

No full suites were rerun just to write a plan. Later initialization 35/corpus
62, complete executor-stage assertions, approved bounded full-target runner,
native simulator/emulator execution after the pause ends, final physical
iOS/Android, immutable published FieldLog consumption from a separate repository,
performance/size, fuzzing/standards/differential coverage, debugging, signing,
store/customer/operational and GA evidence remain pending. Source inspection or
syntax checks alone never authorize OTA publication.
