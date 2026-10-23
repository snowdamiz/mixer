# Private Swift executor/composition stage contract

Proposal for root review, 2026-10-23; implementation and all implementation tests
are pending. This refines the accepted
`docs/swift-reactor-execution-stage-design.md` and the v2 cache contract; it does
not authorize implementation or execution. `mixer-product-plan.md` remains the
full binding scope. The artifact checker below checks this proposal only.

<!-- C01: authority -->
## Authority, dependencies and ownership

Checkpoint `45852204fbcced037d8e530876b619d9ed1c2ce1` accepted the borrowed
descriptors and observed control prerequisites recorded in
`verification/swift-cache-stage-acceptance.json`. Accepted accounted WASI and
runtime-control receipts are prerequisites. The cache lane's evolving code is
**unaccepted**; depend on its v2 contract and subsequent root implementation
acceptance, never on an agent's progress report. No source is changed here.

Before assigning implementation root freezes the helper signatures, measured
layout model and observed instruction/fuel delta below. Then root assigns
`experimental/execution/{mod,borrowed,tests}.rs` and new
`experimental_swift_reactor/{execution,execution_tests}.rs` (paths proposed).
Root owns control, proof, module/Cargo/public wiring and integration acceptance.
The executor lane may not edit cache/WASI/validator owners or another active lane.
The lane uses independently authored engine code and same-ABI fixtures, with no
Patch/Skip source, generated source, tests, fixtures, dependencies or alternate
production engine. No new dependency is proposed.

Complete validation is historical evidence, not execution evidence: the actual
53,777,114-byte target, SHA-256
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`, passed all
79,832 defined bodies, 6,505,659 instructions, 188,428,924 work credits, with
54,827,522 internal peak bytes in the canonical validation receipt. Its 493
types, 4,105 parameter entries, 5,273 globals, 20 data segments, one element
segment, maximum 181 parameters-plus-locals, 67 operands and 379 controls do not
predict execution's call depth, cache locality, memory, fuel, duration or result.
No new full validation, instantiation, `_initialize` or corpus invocation occurs
in this contract task. **Full target execution remains forbidden until separate
root approval of one exact bounded runner.** No device discovery/runs or requests
to reconnect phones; physical iOS/Android, immutable published FieldLog consumer,
store, performance, delivery size and all GA gates remain pending.

<!-- C02: frozen owners -->
## Frozen owners and private static reuse

Preserve literal stored layouts/fields of `ValidatedSpans`,
`ValidatedSwiftReactor`, `FunctionCache`, `FunctionPin`, legacy slot/pin/decoded
types, `SpanInstance`, `Frame`, `Control`, execution budget/usage/failure,
`WasiContext`, `RuntimeControl` and adopted proof/tickets. Keep every old Rust/C
API, header/export, feature policy, identity/revision, requested allocation,
work/fuel/error order and usage formula. No stored mode enum, policy/deadline/
ledger pointer, callback, trait object, replacement legacy wrapper or widened
`Limits`. `FrozenMode` uses original fields through ephemeral borrows.

Use a sealed private `ExecutionMode` with associated `Cache`, `Pin`, `Frame`,
`Operation<'a>` and `Failure`; only frozen and Swift implementations exist.
Adapters below are proposed concrete helper boundaries; exact Rust lifetime
spelling is frozen by root before implementation, not represented as compiling
code here. No downstream implementation or runtime host choice is exposed.

```rust,ignore
ExecutionParts<'a, M: ExecutionMode> {
    cache: &'a mut M::Cache,
    memory: &'a mut Vec<u8>, table: &'a mut Vec<Option<u32>>,
    globals: &'a mut Vec<Value>, values: &'a mut Vec<Value>,
    controls: &'a mut Vec<Control>, frames: &'a mut Vec<M::Frame>,
}
SwiftExecutionOperation<'a> {
    control: &'a mut RuntimeControl, wasi: &'a mut AccountedWasi,
}
initialize_state<M: ExecutionMode>(parts: &mut ExecutionParts<'_, M>,
    operation: &mut M::Operation<'_>) -> Result<(), M::Failure>;
enter<M: ExecutionMode>(parts: &mut ExecutionParts<'_, M>, absolute: u32,
    operation: &mut M::Operation<'_>) -> Result<(), M::Failure>;
run<M: ExecutionMode>(parts: &mut ExecutionParts<'_, M>,
    operation: &mut M::Operation<'_>) -> Result<Option<Value>, M::Failure>;
finish<M: ExecutionMode>(parts: &mut ExecutionParts<'_, M>,
    operation: &mut M::Operation<'_>) -> Result<Option<Value>, M::Failure>;
unwind<M: ExecutionMode>(parts: &mut ExecutionParts<'_, M>,
    operation: &mut M::Operation<'_>); // release all frame pins despite failures
```

The mode statically supplies proof descriptors, limits, frame scalar access/
owned-pin extraction, pin/view/release, work/fuel/live accounting and host
dispatch. Frozen operation borrows the original budget/cancellation/usage/cursor;
Swift operation borrows the single control and actual WASI owner. Its mutable
WASI borrow permits shorter immutable reborrows during cache operations and
excludes concurrent dispatch. Parts/operations are created only after their
named temporary reservation is enlarged. Shared algorithms may be factored in
steps, but no duplicate Swift numeric/branch/memory interpreter is accepted.

<!-- C03: phase and arena ownership -->
## Construction phases, fixed arenas and exact reservations

Private composed storage owns one cache, one `AccountedWasi`, one control and
six fixed-capacity State vectors: values, controls, frames, memory, table and
globals. A Swift frame retains the legacy scalar meanings (`function`, `pc`,
`base`, `operands`, `controls`, `result`) and exactly one `SwiftFunctionPin`.
Its layout is new and measured; the old `Frame` is untouched. Vec lengths change
inside admitted capacities; ordinary pushes never allocate or grow capacities.
Value arena counts parameters, locals and operands together; each defined
frame's implicit function control counts toward the aggregate control arena.
No host frame/pin is created for an import. No allocation per frame/control.

```rust,ignore
SwiftExecutionState::prepare(control: &mut RuntimeControl,
    cache: &SwiftFunctionCache, wasi: &AccountedWasi, cursor: Cursor)
    -> Result<ExecutionConstructionPhase<'_>, SwiftRunFailure>;
phase.construct() -> Result<SwiftExecutionState, SwiftRunFailure>; // once
phase.complete<T>(self, returned_phase_storage: T)
    -> Result<(), SwiftRunFailure>;
SwiftReactorInstance::prepare_operation(&mut self, cursor: Cursor)
    -> Result<ExecutionOperationPhase<'_>, SwiftRunFailure>;
phase.initialize_once() -> Result<(), SwiftRunFailure>; // private sealed 35
phase.invoke_corpus_once() -> Result<i32, SwiftRunFailure>; // sealed 62
phase.complete<T>(self, returned_phase_storage: T)
    -> Result<(), SwiftRunFailure>;
```

These names do not grant a new public constructor. State preparation first
validates actual WASI/control pairing, then intact cache/control ownership,
before checks/admission/enlargement. Construction borrows descriptors from that
same cache; it never consumes/re-adopts/duplicates the proof. The outer composed
construction envelope is enlarged before cache, WASI, state and instance move/
Result/Option/partial-builder wrappers coexist. Cache and WASI nested phases
restore their **exact previous bound**, inside-out. Each phase is one-shot,
borrows the same authority, and completes only after its function returned and
all named temporary storage drops or is supplied for drop. Omitting completion
conservatively retains the enlarged charge. The operation phase encloses the
entire init/invoke return; nested cache-operation phases complete before it.

For checked capacity C and size S, reserve `C.checked_mul(S)` before the first
`try_reserve_exact(C)`. Zero capacity requests allocate nothing. Actual logical
capacity must equal requested, including all six vectors; unexpected capacity is
typed allocation failure with requested/observed fields, never post-admitted.
Default/max runtime caps remain: 64 frames, 16,384 values, 4,096 controls, 768
memory pages, 128 MiB State, 256 MiB Combined; cache 64 entries/pins, 16 MiB total,
8 MiB entry and 64,000,000 work; fuel 100,000,000, execution work 1,000,000,000,
host entries 32,768 and 30,000 ms lifetime. Every zero/narrowed dimension is real
exhaustion; widening is rejected by the foundation, never a target workaround.

Let `B(n)=n*65,536`, `F/V/K` be narrowed frame/value/control capacities, `G/T`
be retained global count/table minimum, `E=SwiftExecutionState`, `I` the actual
composed instance, and `X` the named permanent execution cleanup objects. Use
checked arithmetic for this disjoint model:

| State reservation | Requested bytes; exact measured type required |
| --- | --- |
| values / controls / frames | `V*size_of::<Value>()` / `K*size_of::<Control>()` / `F*size_of::<SwiftFrame>()` |
| memory / table / globals | `B(memory.minimum)` / `T*size_of::<Option<u32>>()` / `G*size_of::<Value>()` |
| exclusive execution header | actual `size_of::<E>()` plus the part of `size_of::<I>()` excluding nested E/cache/WASI/control, plus checked named `X`; count each header once |
| growth overlap | complete `B(next)` alongside the old `B(old)` until replacement drop |
| ordinary construction/operation scratch | additional named simultaneous objects in the existing Construction ticket; never in a second ticket |

Freeze actual chosen wrapper/header nesting before accepting the formula; no
negative subtraction, duplicated E, assumed padding credit or copied legacy
520-byte estimate. Cache header excludes only its already-counted proof header;
ticket/Option/Vec handles remain in their containing owners. Source/meta,
cache/pinned subset, WASI and Shared remain disjoint. Category sums must equal
Combined at every observation, with simultaneous peaks rather than peak sums.

The finite bound is **86 authoritative tickets**:
`2 proof + 3 cache fixed + 64 resident-or-incoming entries + 6 state buffers +
1 replacement memory + 4 WASI buffers + 1 cancellation backing + 4 exclusive
headers + 1 construction`. Execution adds exactly seven permanent State tickets
(six vectors and header), at most one temporary replacement ticket, and no
ticket per pin or operation. Eviction precedes incoming construction. Inline
ticket ownership never allocates a registry or points back into the ledger.

`acceptance.json` holds a pending measured layout map: every actual type's size,
alignment, field offsets, feature/target/toolchain and simultaneous object count
for construction, operation, pin-return, error return, growth and cleanup must
be recorded by executable probes. Include E/I/SwiftFrame/Control/Value, all
Vec/Option/Result shapes, phase/parts/operation readers, selected instruction/
target/scalars, partial owners/tickets, cache release failures/tails, WASI cleanup
results, Fault/Cursor/failure/usage and cancellation handle/backing attribution.
Counts are not guessed here. Missing measured map blocks implementation
acceptance; reservations are requested logical/named-object accounting, not RSS,
allocator overhead or compiler-stack measurements.

<!-- C04: exact descriptor initialization -->
## Initialization from retained descriptors

Use the same accepted complete proof: 34 ordered Preview1 descriptors, no start,
memory minimum 584, no declared maximum, effective host maximum 768; fixed table
46,713/46,713 (effective maximum 46,713, not policy ceiling 65,536); exactly memory
0, `_initialize` 35 `()->()` and corpus 62 `()->i32`. Same-ABI synthetic fixtures
need at least 29 definitions. Small source does not reduce their real memory or
table initialization. No relaxed policy, fabricated proof or alternate exports.

Allocate the six State vectors in legacy order: values, controls, frames,
memory, table, globals. Initialize memory to zero in <=4,096-byte chunks, table
entries to None, globals in source order. Read `execution_global(i)` with its
`execution_global_initializer_offset(i)` and exact borrowed slice; decode only
the validated numeric constant expression and its ending `end`, check full
consumption/type, retain float bits, and report absolute first offending byte.
No copied initializer metadata or rescan from module start. Frozen initializer
helper behavior remains literal; Swift's checked reader cannot alter it.

Preflight *all* data ranges, then *all* element ranges before copying any active
payload. Each uses checked `destination + count`; zero-length at the boundary
is valid, overflow/out-of-range traps at its descriptor's absolute payload cursor.
Then apply data segments in retained order and element segments in retained
order, preserving last-writer overlap semantics. Data count must equal borrowed
payload length; chunked copies use `payload_offset + consumed`. Element reader
starts at exact payload offset (after count), decodes exactly count u32 LEBs,
checks each absolute function/signature is present and consumes the exact slice;
no allocation or whole-module parse. Globals/constants/elements use bounded
readers with actual control checks in every byte/LEB loop.

Initial memory live pages are debited before publication. If a narrowed memory
budget is below minimum, fail before allocating memory. After state construction
and exactly one accounted context, call sealed initialize once. State machine:
`Constructing -> Initializing -> Ready -> Exited/Failed`; Ready requires empty
initializer result and zero frames/values/controls/pins. A trap, exit (even zero),
limit, capacity, cancel/deadline or WASI failure returns no Ready owner; no retry,
new context or reset. Preserve memory/globals/table/capture and lifetime counters
across later corpus calls. Nonzero corpus i32 is a real result, not a fabricated
trap; qualification fails separately. No arbitrary index/name invocation escapes.

<!-- C05: per-frame pins -->
## Per-frame cache authority and interpreter behavior

Coordinate with cache owner through its accepted contract. Proposed consumer:
`prepare_operation(control, Some(&wasi), cursor)` then phase `pin(&mut cache,
absolute)`; view borrows immutable cache with direct control/WASI pairing;
`release` consumes the pin and returns it on rejection. Exact signatures await
cache implementation review. No cache type/accessor is made public for executor
convenience; only the minimum immutable adopted-proof borrow is needed.

Cache owner reports these candidate signatures, consistent with the frozen v2
contract; they are coordination inputs, **not accepted cache code**:
```rust,ignore
cache.proof() -> &ValidatedSwiftReactor;
cache.view<'a>(&'a self, pin: &SwiftFunctionPin, control: &mut RuntimeControl,
    wasi: Option<&AccountedWasi>) -> Result<FunctionView<'a>, SwiftRunFailure>;
cache.release(&mut self, pin: SwiftFunctionPin, control: &mut RuntimeControl,
    wasi: Option<&AccountedWasi>) -> Result<(), SwiftReleaseFailure>;
release_failure.into_pin() -> SwiftFunctionPin;
```

For a defined call preflight frame limit, charge enter work, read its sealed
signature, acquire exactly one pin, inspect locals/instruction end, preflight
remaining aggregate values/control and checked parameters-plus-locals <=256.
Count parameters already in the value arena; append only declared locals. Every
local initialization checks control. Keep newly acquired pin in a local owned
guard until publishing frame/function control and their exact live debits; if
any intervening check fails, remove only acquired debits and release that pin
once. The return wrapper/guard fits the operation envelope. Recursive calls each
acquire their own pin even for one resident entry; no shared frame pin/copy.

Fetch exactly one copied `DecodedInstruction` and, for br_table, only its selected
u32 target while borrowing the pinned entry; end that borrow before pc/state
mutation, dispatch, callee pin/decode/eviction or release. No borrowed code view
survives mutation. Cache residency cannot move a live frame's code. Direct,
recursive and imported indirect calls compare full structural signatures (all
ordered parameter types and result), not type-index identity or hash alone.
Absent slot/null/signature mismatch retain their distinct existing traps.

Function return moves its owned frame out, saves at most one result scalar,
truncates values/controls to the frame bases, releases pin once, removes live
counts after effects, and pushes result into caller within preflighted capacity.
The outermost result escapes only as copied Value/i32. A release rejection keeps
the owned pin for terminal unwinding; never discard an error wrapper containing
authority. Terminal unwind drains deepest-first including partially built frame
guard and every recursive pin, clears values/controls, then records cleanup;
unwind continues after a cleanup invariant and never replaces first cause.
An import has no frame/pin: its caller's pin remains live through dispatch and
is released on normal return/terminal unwind. Imported indirect calls follow the
same rule. No guest reentry from a host call.

Reuse every current `Operation` semantic: integer/float/saturating helpers,
locals/globals, block/if/loop/end/return/branches/br_table, table calls, loads/
stores, memory size/grow/copy/fill. Numeric helper push is permitted only after
proving it consumes >=1 and emits exactly one within the existing arena; no
implicit Vec growth. Structural control has both aggregate 4,096 and sealed
function-inclusive 512 limits; frame entry contributes one. No unsupported
operation, type or environment is silently approximated.

<!-- C06: actual WASI dispatch -->
## Actual WASI dispatch and first-failure observations

Use `execution_imports()[absolute]` as the sealed `WasiFunction`; never reparse
names, choose a callback, or inject a context. Borrow the exact typed argument
slice in values and disjoint mutable memory; no scratch argument Vec or guest
pointer escapes. Charge call instruction once, then parameter movement/host work.
Pair actual WASI/control/cache before dispatch. `AccountedWasi::dispatch` already
checks control, charges **the single executor host-entry counter** immediately
before actual context dispatch, enters the real adapter, latches terminal
adapter outcome, and performs its postcheck. Executor must not charge host again.
WASI's unchanged context remains sole call/work/transfer/log meter. Host refusal
does not increment adapter calls; adapter failure/errno does reflect its actual
entered-call behavior. Assert exact counters at each rejection boundary.

Map successful errno to one official unsigned i32 result and normal control
flow, truncating arguments and preserving caller frame/pin. `proc_exit(u32)`,
including 0, latches GuestExit with exact code and never pushes success or exits
the native process. Adapter failure retains exact typed `wasi_failure`. Explicit
qualification grants only random, realtime, monotonic and stdout/stderr; paths,
sockets, environment and filesystem remain denied. Test all 34 descriptors,
real OS clocks/random, fd close/capture and default denial. Existing standalone
adapter precedence, rollback and storage/layout remain unchanged.

After actual context construction every potentially failing execution/cache/
cleanup boundary supplies current attributable WASI usage. First use
`AccountedWasi::checked_usage(control,cursor)` (no admission/work/time checks),
then sample the actual context anew at each boundary; synchronous borrow excludes
dispatch meanwhile. Foreign/missing WASI header contributes None; same-owner
accounting invariant contributes actual usage. Check intact cache/header/state
ownership before effects. No copied usage authorizes admission or persists as
the meter. Local trap/invariant `control.fail` also receives actual observation.

Root prerequisite, **not accepted by this proposal**:
```rust,ignore
RuntimeControl::instruction_with_wasi(cursor: Cursor, wasi: Option<WasiUsage>)
    -> Result<(), SwiftRunFailure>;
RuntimeControl::charge_fuel_with_wasi(credits: u64, cursor: Cursor,
    wasi: Option<WasiUsage>) -> Result<(), SwiftRunFailure>;
```
Both internal check/fuel failure and instruction-count overflow must retain it.
Existing `instruction`/`charge_fuel` delegate None preserving layout/counter/
failure semantics. Current checkpoint's unobserved methods would lose actual
WASI counters on a later fuel failure; never call one and repair the latched
snapshot afterward. All existing observed work/live/admission/capacity/phase/
drop/remove paths must likewise be used, including `work_with_wasi`,
`add_live_with_wasi`, `admit_with_wasi`, `exact_capacity_with_wasi`,
`enlarge_construction_with_wasi`, `end_construction_phase_with_wasi`,
`drop_reserved_with_wasi`, `drop_proof_with_wasi` and `remove_live_with_wasi`.
Carrying the WASI deadline before a
context exists legitimately has None. Root review/receipt for this delta is a
hard prerequisite to executor acceptance.

Root has since reported an implemented candidate in
`verification/swift-instruction-observation/isolated-1/receipt.json`: 319+9 checks
per Debug/Release, 72 minimal-Swift library checks per mode, lint and formatting.
It exercises actual ArgsSizesGet before eleven success/fault cases, including
fuel-before-instruction-overflow ordering. Independent review is pending; this
proposal records that candidate, not accepted prerequisite completion.

<!-- C07: cumulative counters and interruption -->
## Work, fuel, memory growth and interruption ordering

Preserve the frozen algorithm trace exactly. For Swift, check terminal then
cancellation then earliest carried deadline before each charged boundary;
first previously latched cause wins. Before instruction effects, copy selected
instruction/target, set its absolute function/source cursor, charge one
instruction fuel/instruction count, charge one execution work, then advance pc
and dispatch. A failed charge makes no instruction effect. Imported call is
already charged by its Call/CallIndirect instruction. No counter is reset at
initialize/Ready/invoke completion, and rejected work is never refunded/refilled.

Freeze this Swift base work schedule to current shared behavior: initialize
`memory_bytes + table_entries + globals`; 16/global constant; 1/range descriptor;
data payload length and element encoded length before copying/decoding; enter
1 plus declared-locals+1; push/pop 1; call parameter count; structural signature
sum of parameter lengths; control close/truncate/return actual moved/discarded
counts plus current fixed scalar credits; load/store width; bulk length;
growth new_bytes+old_bytes. Preserve every existing extra branch/end/tee/control
credit in shared code. Document any necessary additional Swift descriptor/live
work as a separate checked term before root freeze, never silently changing
legacy work. No expensive scan is free simply because a getter is O(1).

Charge bulk extra fuel `ceil(length/64)` after range validation and before first
copy/fill. Copy overlap selects backward/forward chunks as existing memmove
semantics, with <=4,096 bytes/chunk. Check inside each zero/table/global/segment/
element/LEB/local/signature/value-control-movement/bulk/growth loop and after its
last chunk before publication or successful return; scalar scans also remain
bounded. Truncation only drops Copy scalars except frames, whose pins unwind
explicitly. A long bounded precharge does not replace inside-loop checks.

Growth checks declared/effective host maximum and narrowed 768-page cap. A
declared/host maximum denial returns Wasm -1; zero delta returns old pages.
Allocation, State/Combined, cancellation, deadline or invariant failure is
terminal. Admit full new memory while old ticket/storage stays live; preflight
page live count, zero/copy under checks, final check, replace/drop old storage,
then refund old ticket and commit new pages. Roll back only newly acquired live
debits on precommit failure. At 767->768 pages memory overlap alone is
100,597,760 bytes; all cache/state/WASI/Shared/Construction still count. Do not
misclassify resource failure as -1 or claim trap-wide rollback of previous writes.

The lifetime starts before any runtime construction. WASI uses the earliest
run/WASI deadline inside its accepted staging/service/commit loops. Cancelled+
expired chooses cancellation unless prior terminal cause exists. Cooperative
checks cannot preempt a single allocator/platform service: check both sides and
retain origin/overshoot. Tests pause only with cfg(test) hooks at real loop
boundaries, then cancel the actual shared token or expire the actual deadline;
no product clock callback, sleep-only inference or unbounded retry.

<!-- C08: cleanup and diagnostic authority -->
## Cleanup phases and immutable first failure

`RuntimeControl::fail` is the only terminal authority. Preserve exact kind/code/
resource/attempted/limit/capacity, function/offset, deadline origin, underlying
WASI cause and `at_failure` counters/ledger/peaks. Later calls return that cause
without decode, work, allocation, services or guest effects. `after_cleanup` is
a separate observation, never a replacement. Invocation terminalization drains
all frame/guard pins and live values/controls/frames while keeping owned fixed
arenas/cache/memory/context until consuming cleanup. Constructor failure returns
no owner and drops all acquired storage/tickets in the same accounting model.

```rust,ignore
cleanup_owned(owned: &mut Option<SwiftReactorInstance>)
    -> Result<ExecutionCleanupTail, SwiftRunFailure>;
tail.complete<T>(self, returned_phase_storage: T,
    outcome: &mut Option<SwiftRunFailure>, usage: &mut Option<SwiftRunUsage>)
    -> (); // same header, no new ticket
```

The new composed owner stores its control/cache/WASI/state in private Options,
allowing safe owned take after preflight; these extra Option shapes are included
in the measured header/transfer model. This changes no legacy owner. The tail
owns the original control, same execution-header ticket, copied final WASI usage
and copied first failure; it cannot receive a replacement control. Do not borrow
an embedded control alongside ownership of its parent. All old/new wrappers
are reserved before moves; no self-reference, unsafe extraction or cleanup
enlargement is needed. Root must freeze concrete chosen field shapes and sizes.

Permanent **same execution header** reservation contains the named worst-case
cleanup envelope from construction onward. Preflight actual WASI/cache/state/
control ownership while the caller slot is intact. A rejected pair leaves exact
Some(owner) with no drop/refund/live mutation/work/admission; original control
can still drain. After successful preflight take once; deepest-first frame/pin
drain, State vectors drop-before-refund, cache owned-slot cleanup and its
same-header tail completion while actual WASI lives, WASI cleanup, execution
header tail and finally control consumption. Cache/WASI can be drained in the
chosen frozen order only after all pins/borrows are gone; retain actual final
WASI usage before destroying context. Continue every later component cleanup
despite errors and preserve immutable first failure/independent cleanup invariant.

Complete ordinary operation/construction phases before cleanup. Cleanup may
not prepare/enlarge a phase, allocate, spend work, call services, or check time/
cancellation. Partial constructor cleanup before permanent header admission is
covered by its already live construction envelope. The successful destructive
path returns Ok(tail) even if cleanup latched failure, leaves owner slot None,
and retains the same header ticket through Result/Option/return transfers.
The tail exclusively owns control, is non-Clone/must-use, and completion
drops supplied empty slot/large wrappers before observed header refund, consumes
control via `finish_owned_cleanup`, writes copied outcome/final usage and returns
unit. Omitted completion conservatively retains the recorded charge. No large
possible-owner Result/Option survives refund. Map the final small refund/output
active values explicitly to foundation's 4 failure/4 usage/6 ticket/2 WASI-usage
allowances; never assume spare space, reuse cache's envelope for another live
phase, fabricate zero counters or refund while corresponding owner still lives.
After full valid-owner cleanup combined current/tickets and all live counts are
zero. Corrupt/lost ownership conservatively retains charges and reports invariant.

<!-- C09: executable acceptance -->
## Acceptance functions and artifact boundary

`verification/swift-executor-stage-contract/acceptance.json` freezes 20 exact
synthetic function names and assertion matrices. Every function must execute
at least once in Debug **and** Release after implementation, with actual test
counts; zero-test filter success is failure. All are pending now. Fixtures use
the unchanged public complete validator and exact ABI above. No execution is
performed by the contract checker or collector. Tests isolate allocation/work
observation from fixture construction, validation and harness storage; use
existing per-thread observers and cfg(test) hooks, never another global
allocator or public test authority.

Run `python3 -B verification/swift-executor-stage-contract/check_contract.py`
for artifact consistency and `--mutation-checks` for deliberately invalid
artifact copies. The checker verifies fields/required boundaries; it cannot
prove memory safety, runtime semantics, acceptance or OTA eligibility. Future
engine commands and the required frozen-route matrix are listed as **pending**
in the manifest; this checker intentionally has no engine-run option.

Root then obtains independent adversarial source review, exact layout/
allocation/work/error/privacy parity, complete synthetic/fault evidence and
combined regression receipts. Only a later separately approved exact-target
runner may hash/validate the immutable target, drop external input, construct
once and invoke twice on one owner. That future runner must compare all 11
typed fields of two actual captured duplicate-free JSON objects and both real
zero returns against native reference, retain first failure and never raise
caps to get a pass. No such runner or execution approval is created here.

Receipts record source revision plus dirty state, source hashes/tree digest,
tool versions, command/output hashes, scope and limits. Artifact success changes
no implementation or GA gate. Physical devices, published separate-repository
consumer, mobile/API/signing, performance, delivery-size, stores, customers and
operations remain explicitly pending.
