# Private Swift control invocation contract proposal

Root should freeze one private control-operation slice on the accepted original
`FrameOperationPhase`. Generalize the existing literal control macro and share
the existing Frozen inline control arms, then invoke those sources from Swift.
Keep a complete fetch/dispatch loop, initializer, Ready state and public invoke
outside this slice. This is a proposal and host declaration prerequisite;
implementation and accounting acceptance are pending.

The binding requirements are `mixer-product-plan.md` Sections 7, 10, 20 and 25.
The commissioning lane is fresh-context Sol 6.1, `xhigh`. This lane owns only
this file and `verification/swift-control-invocation-contract/`; it changes no
product source, tracker, gate, dependency or prior acceptance. The metadata run
occurred under the computer-use/native-runtime pause; the user subsequently
resumed computer use, capture and simulator/emulator runtime. This bounded lane
remains host-only. Phones remain disconnected and final physical checks deferred.
Host compiler/metadata tests below started no native test instance.

## Accepted starting point

The active-frame acceptance binds the 119-file VM closure
`4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4`,
committed in `ff1bb262aa66c01790df4fbd1371c8ff33caabe8`. Current observed HEAD
was `f18ea41910bc06a95d04cc19081a73dc31b5a96e`; the collector confirmed the same
VM closure. The original cache, WASI, control and State own all authority.
`prepare_frames`, entry/rollback, finish, indexed terminal pin drain, retained
cleanup and fixed-storage completion are implemented and accepted. The
constructor still leaves the reactor Uninitialized. A retained frame is pin
storage and cannot become an execution frame again.

`experimental::execution::borrowed::frozen_control_methods!()` currently emits
exactly `SpanInstance::pop32`, `close_control` and `branch`. The literal
`Operation::Block/Else/End/Br/BrIf/BrTable/Return` arms remain in Frozen `run`.
The prior `ControlMode` design failed its unchanged Frozen accounting; do not
restore that extra fallible adapter layer. `AlgorithmMode` remains a historical
proposal. Numeric/value primitives and frame cleanup remain their accepted
implementations.

## One common algorithm and the minimum additive interface

Keep `Kind` and all `Control` fields at their existing private visibility. Add
only these crate-private, infallible scalar leaves to the **existing** Control:

```rust,ignore
Control::result(self) -> bool;
Control::height(self) -> usize;
Control::start(self) -> usize;
Control::end(self) -> usize;
Control::is_loop(self) -> bool;
Control::is_function(self) -> bool;
Control::is_if(self) -> bool;
Control::clear_result(&mut self); // only on the copied branch Control
Control::decoded(ControlKind, start: usize, end: usize,
                 height: usize, result: bool) -> Control;
```

Each getter reads its one original field, or compares its original Kind. The
constructor uses existing `ControlKind`; no public Kind, duplicated kind enum,
Control wrapper or second control arena is introduced. Put the existing struct
literal and kind mapping in one private record-expression macro used by both
Frozen's Block arm and `Control::decoded`; Frozen expands to the original
literal. The new leaves add real Swift call/scalar transfer roles and receive
positive accounting. They expose no pin, proof, owner, ledger or public API.

Generalize the current literal method macro with a failure type, hygienic
receiver/Control parameter, compile-time leaf macro and optional close prelude:

```rust,ignore
shared_control_methods!(self, FailureType, leaf_macro, control,
                        { /* mode-specific close guard, empty for Frozen */ });
// Leaf selectors: pop, push, invariant, values, controls, frame, floor,
// result, height, loop, function, clear, start, after_end,
// truncate_values, truncate_controls, observe, set_pc.
```

Frozen leaf expansion is the original direct owner expression, including
`self.work`, `self.pop/push/observe`, original invariant/unreachable fallback,
direct field reads and truncations. It adds no wrapper function, result layer,
runtime callback, mode object or check. Require compiler-expanded equality of
all three original method bodies before acceptance. Retain the current private
Frozen invocation; grant only the minimum crate-private re-export needed by the
actual sibling Swift module. Downstream access must remain rejected.

Swift leaves project `self.phase.parts` and call existing `phase.pop_value`,
`phase.push_value`, `FrameOperationPhase::work`, actual `RuntimeControl` and
actual accounted WASI. Copy only the current frame's scalar floors before a
mutable leaf call; retain no borrowed frame/pin across it. Use the common
Control getters above. Do not move close/branch arithmetic into these leaves.

Extract each existing Frozen control arm into one private statement/expression
macro body, with compile-time leaf substitutions at the same boundaries.
Invoke it in the existing Frozen match arm and the Swift method below. Rust
macros need not expand to match arms: expand **inside** each existing arm.
Keep every Frozen local binding, call depth, arithmetic, selected-target use and
effect/check order compiler-expanded identical. Do not introduce a Frozen
`execute_control` helper. A sharing change that fails that identity or the
unchanged Frozen reservation stops for root review.

## Exact Swift owner route

```rust,ignore
// New private method on the existing original-owner phase.
FrameOperationPhase::control_operation(
    &mut self, operation: Operation, selected_target: Option<u32>,
) -> Result<bool, SwiftRunFailure>; // true asks the caller to invoke finish

// Existing concrete completion storage gains exactly one field:
FrameOperationStorage<'a> {
    preparation: Option<Result<FrameOperationPhase<'a>, SwiftRunFailure>>,
    entry: Option<Result<(), SwiftRunFailure>>,
    returned: Option<Result<FrameReturn, SwiftRunFailure>>,
    drained: Option<FrameDrainReport>,
    controlled: Option<Result<bool, SwiftRunFailure>>,
}
```

The accepted `prepare_frames` owns admission; do not relax zero-frame value
preparation or add another phase/owner. Implement the new methods in a child
`control_operations` module of `frame_operations`, permitting short reborrows of
the existing private phase fields without widening those fields. The new method
accepts only Block, Else, End, Br, BrIf, BrTable and Return. Other operations fail
closed with UnsupportedEnvironment before mutation. Their actual `Operation`
must come from the current pinned decoded function. BrTable receives only the
one selected depth, copied from that view before dispatch. No full branch-table
copy, new scratch Vec, cache phase or cache mutation is allowed here.

This boundary starts **after** the future caller has selected the instruction,
set the exact `Cursor { stage, function, offset }`, debited instruction fuel/count
once, charged outer dispatch work 1, and advanced pc once. This slice implements
none of those caller responsibilities, and debits no fuel or instruction count.
Tests may hand-step real decoded instructions with a bounded host harness;
that harness is not a product dispatcher or target execution receipt.

Before the operation, run existing `active()` and require a real current frame.
Check `base <= operands <= values.len()` and a present Function sentinel at
`frame.controls`, with sentinel height equal to `frame.operands`. All indices
and any `end + 1` used by Swift must be checked. Use the sentinel's decoded end
as the function bound; no new retained FunctionView is needed. For a new Block,
validate end/alternative against that bound and the already advanced pc before
publishing anything. Else requires the current If Control and its matching end.
These are Swift guards; they insert no Frozen checks.

The close prelude checks the copied Control height is between the **current**
frame operand floor and actual value length. A result-bearing close requires an
actual value above that height. Branch's selected index must be at or above the
current frame control floor. End must have a top Control at or above that floor
before popping it. These boundaries protect caller locals, operands, controls
and pins even when live counts still happen to agree. A function-completing
operation returns true; it does not release or pop the frame. The caller must
invoke accepted `finish` before any further control operation on that frame.

## Order, live accounting and terminal failure

Preserve the literal common schedules:

| Operation | Helper schedule after the outer caller boundary |
| --- | --- |
| Block/Loop/If | If alone pops i32 first. Preflight aggregate room, charge work 1, check function-inclusive depth, predebit one Control, publish it using current pc/value height. False If sets pc to alternative+1 or end; observe agreement. |
| Else | Set pc to matching end; no helper work/fuel debit. |
| End | Charge work 1, pop exactly one Control, remove its live count immediately, shared close, return Function flag, observe. A later failure does not restore the removed Control. |
| Br | Check target index/floor, copy one Control, charge `controls.len()-index`; clear result on a loop copy; shared close; truncate controls to index+1 for loop or index otherwise; set loop start/end+1 pc; observe; return Function flag. |
| BrIf | Pop the condition even when false. Invoke shared branch only when nonzero. |
| BrTable | Require the preselected depth, pop i32 selector, invoke shared branch. Selection itself belongs to the future fetch boundary. |
| Return | Return true; accepted finish handles result and frame cleanup. |
| shared close/pop32 | Close saves at most one popped result; charges `remaining_values-height+1`; truncates values; observes; pushes saved result through existing accounted push. pop32 consumes one value before reporting a non-i32 invariant. |

Swift's capacity and function-inclusive 512 ceiling remain distinct from Frozen
Limits. Before a Block publication require aggregate fixed capacity, checked
current depth `controls.len()-frame.controls`, and next depth <= the sealed
decode policy (512 maximum). The existing Function sentinel counts toward it.
Predebit with `add_live_with_wasi(Live::Controls, 1, cursor, actual_usage)` as
the last fallible admission, then perform the known-room push immediately.
No value/control arena can allocate, reserve or grow during these operations.

For every successful pop/truncation, remove **exact actual** Values/Controls
after the effect using `remove_live_with_wasi`, with no intervening cancellation,
deadline, work, admission or cache check. A removal rejection sets existing
`cleanup.live_unreconciled` and returns its actual failure. Observation uses
existing agreement checks; it never debits a second time or repairs live counts.
Retain accepted push/pop work/limit ordering, including work before pop effects
and saved-result push failures after close truncation. Never refund work.

Every control-operation error calls existing `terminal()` and returns the first
failure observed by the original control with the real WASI usage/cursor. No
Ready transition, retry, control rollback or replacement diagnostic is allowed.
Accepted `drain` clears actual residual arenas and attempts every real frame pin
deepest first despite failure/cancellation/work exhaustion. Rejected releases,
unpublished guard authority, sticky mismatch and nested/outer restore debt retain
their existing State slots, charges and explicit cleanup-only reacquisition.
The new Result slot must be empty and passed through fixed completion before
restoring the envelope; retained diagnostic copies need permanent attribution.

## Positive reservation change to freeze before product execution

Do not spend the original value/frame inventories twice or widen public budget
ceilings. Introduce exactly `control_operations::PERMANENT_BYTES` and
`control_operations::ACTIVE_BYTES`, each the checked fixed size of a named typed
inventory. Checked-add PERMANENT to `EXECUTION_HEADER_BYTES`; checked-add ACTIVE
to the existing `FRAME_OPERATION_BYTES`. Preparation records the resulting exact
bound in existing `FrameCleanupState.bound`; resume and completion use that same
formula and retain rejection debt. This adds no State cleanup field or ticket.

The added `controlled` field enlarges every actual FrameOperationStorage,
completion drop tuple, return wrapper and typed existing inventory containing
that storage. Recompute those existing sizes as well as adding new positions;
the slot is not covered by an old entry/returned slot. Require exact production
and unit typed-field/MIR inventory review, as for accepted active frames. Do not
copy an old receipt, use an optimizer alias or choose a rounded byte allowance.

The closed new role set is:

| Reservation | Newly named roles; each actual source/argument/return/caller/Try placement is separate |
| --- | --- |
| Permanent, before phase admission/after completion | New fixed caller slot and retained bool/failure copies; added slot's prepare/complete/storage/drop-tuple transfers; checked bound/error and header construction/cleanup changes caused by their enlarged concrete types. |
| Active, while the recorded frame bound lives | control_operation receiver/Operation/target and Result<bool>; common pop32/close/branch caller chain, copied Control and optional result; current frame scalar floors, indices/depth/pc/condition/checked Options; Control accessor/constructor transfers; work/admission/removal/observation and guard failures, actual WASI observations; source/returned/caller, closure and Try/residual positions. |

Derive exact counts from the chosen **actual** source and compiler inventory
once, freeze the complete disjoint map, and include unchanged nested value/frame
components positively. The current declaration probe does not supply that map or
a complete new byte total. Product entry is blocked until root accepts that
accounting preflight; a measured slot delta alone cannot authorize it.

## Bounded implementation ownership and executable acceptance matrix

Root should assign one coordinated implementation lane the existing
`vm/src/experimental/execution/{mod,borrowed}.rs`,
`vm/src/experimental_swift_reactor/{execution,frame_operations,frame_operations_tests}.rs`,
new `control_operations.rs`/`control_operations_tests.rs`, and the corresponding
new control verification packet. Common macros and fixed storage are one
integration unit. The existing public control regression file remains the
Frozen parity oracle. No compiler, WASI, cache, memory, public API, dependency
or unrelated tracker change is needed by the implementer.

Use independently authored small modules through the real validated proof,
original constructor/cache pin and accepted frame preparation. No forged pin,
shadow ledger or copied reference interpreter. Add exactly these twelve named
control tests, each with a finite case table:

| ID | Required cases/assertions |
| --- | --- |
| SC01 decoded block/loop/if | Real decoded empty/result blocks and loops; If true, false+Else and false without Else. Exact pc/height/result/control peak. |
| SC02 end/else/return | Nested End; function End; Else skip; Return with open blocks. True only for function completion; accepted finish produces the hand-authored result and releases the original pin. |
| SC03 branch targets | br to block, loop and Function; br_if true/false; br_table selected first/last/default, unsigned selector. Loop label discards result and retains its Control. |
| SC04 current-frame floors | Nested real frames; depth at frame floor and one beyond; empty operand stack, malformed height below operands, missing result above height, End without own Control. Caller locals/operands/controls/pins remain intact at rejection. |
| SC05 control limits | Inclusive depth 511->512 succeeds, 512->513 rejects; aggregate capacity exact and one over; separately narrowed valid Controls budget. No allocation/reallocation or publication on failed predebit. |
| SC06 value limits/types | Saved-result close push limit/capacity rejection, empty operand and wrong-i32 condition; verify exact already-consumed/popped/truncated effects and sticky failure. |
| SC07 exact work prefixes | For each successful SC01-03 trace with work W, execute each budget 0..=W. Compare exact failure boundary, partial arenas, pc, work and live counts; zero helper fuel/instruction increments. |
| SC08 cancellation/first failure | Cancel before operation and at each identified work/predebit boundary; retain actual cursor/WASI usage. Existing terminal failure wins over later cancellation or cleanup faults. Zero-work arms rely on their explicit precharged caller boundary. |
| SC09 defensive/live faults | Active-count mismatch, checked pc/depth/height failure, wrong original-owner pairing, and after-effect live-removal rejection. Rejection terminalizes; mismatch never repairs itself; unsupported Operation mutates nothing. |
| SC10 retained cleanup | After each selected partial failure, cancel/exhaust work and drain. Inject two real rejected pin releases at distinct depths; each authority remains in its indexed real frame, no implicit retry, explicit reacquisition/completion preserves debts. |
| SC11 completion/accounting | New fixed slot moved out and supplied empty; exact header/phase bound one-byte-below/at boundary, admission rejection, dropped phase, retained and restore-rejected outcomes. All containing inventories match actual source; old zero-frame preparation and consuming cleanup barriers still reject active/retained state. |
| SC12 allocation/shared source | Warm decoded control interval has zero allocations under first-request refusal; cold decode is separately counted. Confirm actual sibling invocation and original common Control; Frozen compiler expansion and public parity unchanged. |

Execute SC01-12 under Swift-only/all-features x Debug/Release, serial allocation
observation (`--test-threads=1`). Run existing six
`--test span_control_extraction` tests under span/all-features x Debug/Release,
and the existing Swift frame/value suites under Swift/all x Debug/Release.
Run default/span/Swift/all library checks and formatting on the changed files.
Broad baseline Clippy limitations must remain explicit; do not quietly accept
new findings. Layout/accounting probes cover production/unit in all four Swift
configurations. This is the complete next-slice matrix; full-target differential,
native runtime and physical phone matrices belong to later integration gates.

## Observed packet and remaining gaps

Run `python3 -B verification/swift-control-invocation-contract/collect.py` to
reproduce the declaration packet. `probe.rs` invokes the generalized literal
helper source on the **actual** FrameOperationPhase from a child module and
type-checks uncalled short borrows through actual cache, control, WASI and value
APIs. It does not create a substitute phase. Scalar accessors are additive only
in the isolated copy; Kind and fields remain private. Guard/truncation/operation
bodies intentionally panic if called and are never executed. The metadata test
only binds method pointers and prints concrete type sizes.

The qualifying run is recorded by `summary.json`. Rust/Cargo 1.99.0,
aarch64-apple-darwin, Swift-only/all-features x Debug/Release executed one
metadata test each with identical 17-row tables. Control/SwiftFrame/phase are
32/64/128 bytes. Failure and the new bool Result/optional slot are 1,096 bytes.
The proposed flat five-field storage witness is 6,232 bytes versus 5,136;
that **1,096-byte positive delta** is a signature/layout observation, not a
complete completion inventory, stack bound or resource proof. The preliminary
four-configuration witness used nested existing-storage-plus-slot storage;
the qualifying run repeats all four against the exact proposed flat shape.

The collector retained failed preparation attempts (Cursor shape and function
pointer lifetime annotations, then a first-row output parser), corrected them,
and ran all four configurations fresh. Each receipt binds source revision/tree,
tool versions, command argv/cwd/target, stdout/stderr and scope. Isolated build
directories were removed; no simulator/emulator/frontend or other project
process was touched. The live accepted VM closure stayed identical.

Still pending: exact inline-arm/generalized-Frozen expansion verification,
actual guard/after-effect/control bodies, full positive actual-source accounting,
SC01-12 and regression execution, and independent root acceptance. The probe
cannot satisfy any of them. Full instruction selection/dispatch, calls/host and
memory/growth execution, initialized/Ready/public invocation, full Swift target,
immutable separate-repository FieldLog packages, native/device, signing/store,
customer, operational and GA qualification remain separate work.
