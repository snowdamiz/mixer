# Private shared executor algorithm contract

Proposal for root review, 2026-10-23, based on
`df97e3ff71391d27492d1dfdbafde4a175868f01`. The final collector observed
`82d520cf555fe965ab5bb759177840369bd52710`; its VM tree is unchanged from
that accepted construction checkpoint. This is a design and compiling
borrow/type prerequisite only. The product source is unchanged. The accepted
Uninitialized constructor and zero-frame cleanup remain the only implemented
Swift execution slice. This document authorizes no interpreter, target run,
public constructor, activation, device run, OTA release or GA state change.
`mixer-product-plan.md` remains binding. Phones remain disconnected.

## Scope and source authority

Read together with the accepted executor-stage contract, reactor execution stage
design, v2 executor-stage acceptance, and construction acceptance. Their frozen
owner/layout, first-failure, accounting, work/fuel, host and lifetime requirements
continue to apply. Historical acceptance JSON saying cache acceptance or
construction is pending is not rewritten by this proposal; construction's later
acceptance is the current authority for that slice.

The actual sources examined are `vm/src/experimental/execution/{mod,borrowed,tests}.rs`,
`vm/src/experimental/cache/{mod,borrowed}.rs`, the frozen descriptor and numeric
helpers, `vm/src/experimental_swift_reactor/{execution,cache,control}.rs`,
`vm/src/experimental_wasi/accounted.rs` and the complete Swift proof descriptors.
The verification closure binds their bytes and the complete compilable VM
library/test source closure. The supplied 53,777,114-byte target is never read,
validated, instantiated or invoked here.

The existing `ExecutionMode` has only Cache/Pin/Frame/Operation/Failure
associations. Keep those associations, all existing fields, old Rust/C APIs,
public `Limits`, feature behavior, identities, reservation formulas and error,
work, allocation and fuel ordering unchanged. All new adapters are ephemeral.
No trait object, stored mode enum, callback, ledger pointer, new shared authority,
engine dependency or alternate interpreter is proposed.

## Smallest implementation slice

Extract **numeric dispatch first**, into the existing borrowed execution module,
then move push/pop/room helpers, then branch/control helpers, then memory helpers,
and finally shared call/run/return/unwind orchestration. The first slice runs only
through the frozen route. It must have executed parity tests and allocation/work
receipts before Swift uses it. Every later extraction similarly keeps only one
implementation of its instruction semantics. Swift may not introduce duplicate
numeric, branch, load/store, bulk-memory or growth algorithms while waiting for
this sequence.

The first numeric extraction is a literal move of the existing `numeric` method,
with field access replaced by static adapters. Keep this exact trace:

1. Obtain numeric shape from the existing float/saturating/integer shape helpers.
2. Read current frame operand base; reject insufficient operands or wrong types.
   This preserves the original invariant's cursor and usage. Numeric helpers
   consume at least one operand and emit at most one; existing arena capacity
   covers the only possible push. Trap paths can emit **zero**, so accounting
   must use actual before/after lengths, never `count - 1` unconditionally.
3. Charge `count + 1` execution work, with exactly the existing frozen check and
   error precedence. Add no new fuel debit or check to the frozen route.
4. Invoke the existing `float::saturating`, `float::numeric` or
   `execute::numeric` implementation on the existing value arena. Preserve bits,
   NaN behavior, integer traps and saturating semantics.
5. Observe actual resulting lengths even on a numeric trap, then map the actual
   helper error to the mode's guest-trap failure. Frozen observation cannot fail
   and preserves its existing usage update order. Swift's later adapter removes
   exactly the actual value-count reduction, without work/time/cancellation or
   admission, and carries the actual attributable WASI observation. Corrupt live
   accounting fails closed; first failure is never repaired after latching.

The numeric API below is implementation-ready in shape. Its full algorithm,
observation/trap adapters and behavior tests are **pending**; the current probe
only compiles the frame/value/operation borrowing and the associated common
helper signatures. It does not execute an opcode or validate this trace.

## Compiled static core

Add a private sealed extension `AlgorithmMode: ExecutionMode + Sized`; it inherits
`ExecutionMode`'s existing closed mode family. Both mode types stay zero sized.
Its implemented type-probe subset is exactly:

```rust,ignore
trait AlgorithmMode: ExecutionMode + Sized {
    type ReleaseFailure;
    type Growth<'a>;
    fn frame(frame: &Self::Frame) -> FrameScalars;
    fn frame_pin(frame: &Self::Frame) -> &Self::Pin;
    fn set_pc(frame: &mut Self::Frame, pc: usize);
    fn view<'cache>(cache: &'cache Self::Cache, pin: &Self::Pin,
        operation: &mut Self::Operation<'_>)
        -> Result<FunctionView<'cache>, Self::Failure>;
    fn check(operation: &mut Self::Operation<'_>) -> Result<(), Self::Failure>;
    fn work(operation: &mut Self::Operation<'_>, credits: usize)
        -> Result<(), Self::Failure>;
    fn invariant(operation: &mut Self::Operation<'_>) -> Self::Failure;
    fn release(cache: &mut Self::Cache, pin: Self::Pin,
        operation: &mut Self::Operation<'_>) -> Result<(), Self::ReleaseFailure>;
    fn split_release(error: Self::ReleaseFailure,
        operation: &mut Self::Operation<'_>) -> (Self::Failure, Self::Pin);
}
struct FrameScalars {
    function: u32, pc: usize, base: usize, operands: usize,
    controls: usize, result: bool,
}
struct PinAttempt<M: AlgorithmMode> {
    pin: Option<M::Pin>, failure: Option<M::Failure>,
}
```

Exact Rust bodies/signatures and mode implementations are retained in
`verification/swift-shared-executor-algorithm-contract/{common_probe,swift_probe}.rs`.
These are isolated verification overlays, not product source or an executable
interpreter. The association `Operation<'owner>` retains its owner lifetime;
`&'short mut Operation<'owner>` is independent. Never require a temporary borrow
to live for the whole owner lifetime. `view` returns a borrow tied **only** to the
cache, not to the pin or operation reborrow. A returned view cannot survive cache
mutation. `frame_pin` borrows the frame; it never clones or copies the pin.

`FrameScalars` copies six existing scalar meanings and owns no authority. This
projection is additional named temporary storage; it is not a new stored frame
or a same-size alias of an already reserved object. `set_pc` is infallible after
the shared helper performs the original checked arithmetic/invariant boundary.
Frozen and Swift `ReleaseFailure` remain their actual different wrapper types;
`split_release` preserves the returned pin and maps frozen diagnostics using the
actual operation, never zero/default usage.

A successful cache `pin` can be followed by failed phase completion. Therefore
`Result<Pin, Failure>` is insufficient for the adapter boundary: `PinAttempt`
allows `Some(pin)` **and** `Some(failure)`. The caller holds that pin in the
entry/unwind guard until released, even though the operation is terminal.
`PinAttempt` is an internal transient, never an owner field or public authority.

## Growth borrow missing from the accepted parts

`ExecutionParts` borrows the cache and six vectors. The accepted
`SwiftExecutionOperation` borrows control/WASI and stores a cursor. Neither
contains the state memory-ticket slot. A generic growth implementation cannot
safely recover it through these types. Add a separate ephemeral argument:

```rust,ignore
// No new stored field in any accepted owner, phase or operation.
FrozenMode::Growth<'a> = ();
struct SwiftGrowthContext<'a> {
    memory_ticket: &'a mut Option<ReservationTicket>, // state.buffers[3]
}
SwiftMode::Growth<'a> = SwiftGrowthContext<'a>;

fn run<M: AlgorithmMode>(parts: &mut ExecutionParts<'_, M>,
    operation: &mut M::Operation<'_>, growth: &mut M::Growth<'_>)
    -> Result<Option<Value>, M::Failure>;
fn grow<M: AlgorithmMode>(parts: &mut ExecutionParts<'_, M>,
    operation: &mut M::Operation<'_>, growth: &mut M::Growth<'_>)
    -> Result<(), M::Failure>;
```

Destructure `SwiftExecutionState` once into its six vectors and `buffers`, then
borrow `&mut buffers[3]` separately from the six vector references. The compiler
accepts this exact split. Keep `ExecutionOperationPhase` and existing
`with_cache_operation` unchanged; the future root-owned operation preparation
returns/retains the growth borrow alongside that phase. It completes/drops the
growth wrapper before ending the outer operation envelope. Whole-instance access
is unavailable while those borrows are live.

Swift growth retains the actual original ticket while admitting complete new
storage and obeys old/new overlap, checked zero/copy loops, final check,
replace/drop-before-refund and live-page ordering from the accepted contract.
Frozen growth retains its original reserve/refund and maximum-denial ordering.
The ephemeral capability is only the ownership route; growth allocation,
transfer, failure and cleanup algorithms remain pending.

## Remaining mandatory static methods and helper boundaries

The following signatures specify the intended full seam; unlike the core above,
their mode adapter bodies and callsite type probes are not yet compiled here.
Root must freeze each before its corresponding extraction. Returning borrowed
metadata never retains a second proof or copies source/metadata.

```rust,ignore
// Proposed additions to AlgorithmMode, not currently implemented.
fn signature<'cache>(cache: &'cache Self::Cache, absolute: u32)
    -> Option<SignatureView<'cache>>;
fn type_signature<'cache>(cache: &'cache Self::Cache, index: u32)
    -> Option<SignatureView<'cache>>;
fn global<'cache>(cache: &'cache Self::Cache, index: usize)
    -> Option<GlobalView<'cache>>;
fn call_depth(cache: &Self::Cache, operation: &Self::Operation<'_>) -> usize;
fn operand_limit(cache: &Self::Cache) -> usize;
fn function_control_limit(cache: &Self::Cache) -> usize;
fn room_values(parts: &ExecutionParts<'_, Self>, additional: usize,
    operation: &mut Self::Operation<'_>) -> Result<(), Self::Failure>;
fn room_control(parts: &ExecutionParts<'_, Self>,
    operation: &mut Self::Operation<'_>) -> Result<(), Self::Failure>;
fn observe(parts: &ExecutionParts<'_, Self>, before_values: usize,
    before_controls: usize, before_frames: usize,
    operation: &mut Self::Operation<'_>) -> Result<(), Self::Failure>;
fn trap(operation: &mut Self::Operation<'_>, code: &'static str) -> Self::Failure;
fn set_cursor(operation: &mut Self::Operation<'_>, function: u32, offset: usize);
fn charge_instruction(cache: &Self::Cache, operation: &mut Self::Operation<'_>)
    -> Result<(), Self::Failure>;
fn charge_bulk(cache: &Self::Cache, credits: u64,
    operation: &mut Self::Operation<'_>) -> Result<(), Self::Failure>;
fn acquire_pin(cache: &mut Self::Cache, function: u32,
    operation: &mut Self::Operation<'_>) -> PinAttempt<Self>;
fn make_frame(scalars: FrameScalars, pin: Self::Pin) -> Self::Frame;
fn take_frame(frame: Self::Frame) -> (FrameScalars, Self::Pin);
fn is_import(cache: &Self::Cache, absolute: u32) -> bool;
fn dispatch_host(cache: &Self::Cache, absolute: u32, arguments: &[Value],
    memory: &mut [u8], operation: &mut Self::Operation<'_>)
    -> Result<Option<Value>, Self::Failure>;
```

`room_*` only preflight; actual Swift live debits occur immediately before their
corresponding successful arena publication, with rollback for partial entry.
A generic observation method cannot silently add work/checks to FrozenMode;
its frozen body is the literal old `observe`. The Swift body observes/removes
known actual deltas after effects and uses the existing observed live APIs.
Entry growth of live counts needs the explicit observed pre-debit boundary,
separate from after-effect removal. Root must extend `observe` with that exact
boundary before adapting push/control/entry; this proposal does not claim that
an after-effect callback alone safely admits increased live counts.

No generic copied `Limits` or policy object is created. Frozen mode reads the
original narrowed frozen fields. Swift reads sealed grammar ceilings and its
own narrowed run budget separately. In particular frozen default controls 128,
operand stack 4,096, memory pages 64, fuel 1,000,000 and host calls 1,024 remain
unchanged; Swift's function-inclusive 512 controls, 768 pages, 100,000,000 fuel
and 32,768 host entries never pass through widened frozen `Limits`.

Shared free helpers use `&mut ExecutionParts<'_, M>` and
`&mut M::Operation<'_>` throughout. `numeric(opcode,saturating)`,
`push(value)`, `pop()->Value`, `pop32()->i32`, `close_control(Control)`,
`branch(depth)->bool`, `range(address,len)->Range<usize>`, `bulk(len)`,
`copy()`, `fill()`, `load(opcode,offset)` and `store(opcode,offset)` retain their
current argument/result meanings. They are generic free functions, not default
trait methods that a mode can replace. This keeps arithmetic/branch/memory
semantics in one body. `width` and existing numeric/float helpers remain shared.
`enter(parts,absolute,operation)->Result<()>`,
`finish(parts,operation)->Result<Option<Value>>` and
`unwind(parts,operation,pending_pin:&mut Option<M::Pin>)->()` have compiled
function signatures in the probe; their divergent bodies are intentionally
unimplemented. `run` additionally receives growth as above.

Initialization stays in the separately accepted constructors. This extraction
must not re-run initialization or replace Swift's checked constant/segment
readers with the frozen initializer's weaker consumption behavior. Public
invoke/export resolution and sticky frozen terminal diagnostics stay in the
original owner wrapper until separately proven extraction; Swift stays sealed
to initialize 35 and corpus 62 and has no public route.

## Fetch, cache, host and return lifetimes

Select a copied `DecodedInstruction` plus only the chosen br_table scalar while
borrowing `M::view`. Compute the actual selector before the charge, as current
frozen run does. End the entire view before changing pc, cache residency,
pinning/releasing or host dispatch. Then set the exact function/offset, charge
instruction fuel/count, charge work 1, increment pc and dispatch. The probe uses
arbitrary first copied scalars only as a lifetime witness; it does not implement
actual br_table selection or instruction dispatch.

`SwiftMode::view/release` makes short disjoint reborrows of the actual
`operation.control` and immutable `operation.wasi`. A cache operation phase
borrows control and an immutable WASI reference only until completion; no
actual WASI dispatch can overlap it. `acquire_pin` must:

1. Prepare the cache phase with actual operation cursor and WASI owner.
2. Execute `phase.pin(cache,absolute)` exactly once into
   `Option<Result<SwiftFunctionPin,SwiftRunFailure>>`.
3. Move its owned pin/failure into the separately charged `PinAttempt`, leaving
   the returned Option empty.
4. Consume that empty returned storage through `phase.complete` before returning.
   Preserve an earlier pin failure over completion failure. Retain a successfully
   acquired pin alongside a completion failure; do not use `?` to discard it.

The exact operation's `previous_bound` is restored inside-out by accepted cache
completion; do not substitute zero, subtract an estimated allowance, complete
before returned storage drops or retain a phase-owned borrow across dispatch.
The compiler accepts this concrete cache phase choreography and the existing
higher-ranked `with_cache_operation` reborrow.

The host adapter receives a typed argument slice directly from `parts.values`
and disjoint mutable `parts.memory`; no scratch argument vector. Its Swift body
indexes only sealed `execution_imports()`, invokes actual `AccountedWasi::dispatch`
with original control/cursor, and maps errno to `u16` then i32. AccountedWasi
already debits host entry exactly once; no executor debit is added. Frozen body
keeps check, work 1, old host limit/increment, import lookup and checkpoint/abort
ordering. Shared call choreography moves arguments at its current call work
boundary, imports create no frame/pin, indirect calls use complete structural
signature equality and preserve distinct null/bounds/mismatch traps.

Finish moves one owned frame, saves at most one copied result, charges and
truncates at the current bases/order, then releases that exact pin. A failed
release wrapper remains owned until moved into pending unwind authority; retain
first failure and drain remaining frames deepest first despite cleanup errors.
Frozen public terminal's historical after-cleanup diagnostic rewrite remains
frozen behavior; Swift control's immutable `at_failure` plus `after_cleanup`
semantics are separate mode behavior. A shared body must not make one imitate
the other. Existing zero-frame consuming owner cleanup must not be used for an
active frame until the pin/guard drain and accounting extension is accepted.

## Positive accounting obligations

These are additional named classes, not guessed byte totals or credits from
same-sized existing aliases. Before any product implementation, compile actual
chosen shapes/counts on all required layout configurations, build a disjoint
simultaneous binding map and enlarge the proper existing phase/permanent
execution envelope before first creation. Current host type sizes measure only
the named probe shapes; they are not complete operation bounds.

| Window | New/transferred shapes requiring explicit positive attribution |
| --- | --- |
| Frozen borrowed wrapper | Actual `ExecutionParts`, `FrozenOperation` and tuple/return/Option/Result wrappers. Existing frozen fixed scratch formula cannot silently increase; prove coverage with named original classes or defer extraction. |
| Scalar numeric | `FrameScalars`, frame/value reborrows, shape/type/count/result bindings, actual pre/post lengths, work parameters, failure/observation copies and helper return wrappers. Probe's zero-work witness is not a work schedule. |
| Selected instruction | Actual copied `DecodedInstruction`, selected `Option<u32>`, Cursor, frame projection, FunctionView, checked-access Options/Results and adapter arguments. Existing selected-instruction storage covers only its actual previously mapped bindings. |
| Nested pin | Actual `CacheOperationPhase`, prepare Result and match transfers, returned `Option<Result<Pin,Failure>>`, consumed match Result, both PinAttempt placements/return transfers, completion Result, by-value failure/pin parameters, entry guard and release error wrappers. A live pin plus failure occupies both payloads. |
| Memory growth | Actual `SwiftGrowthContext`, tuple with parts/phase if used, mutable ticket borrow, actual GrowthTransfer and pin-safe error/return wrappers, both memory/ticket lifetimes. A reference cannot substitute for ticket/owner storage. |
| Host | Actual WASI descriptor scalar, argument slice and memory reborrows, dispatch return/errno/Value shapes and observation/failure copies. Foundation's six optional observations are already allocated to its named simultaneous chain; new retained caller observations need disjoint charge. |
| Return/unwind | Owned frame and scalar projection, optional saved result, release wrapper/pin/failure transfers, pending pin, deepest-first loop state and live removals. No refund or header completion while any corresponding authority-bearing wrapper lives. |

The current frozen allocation at `vm/src/experimental/execution/mod.rs:342-352`
reserves exactly
`size_of::<SpanInstance>() - size_of::<FunctionCache>() +
3*size_of::<ExecutionFailure>() + 2*size_of::<CacheFailure>() +
size_of::<DecodedInstruction>() + size_of::<Control>() +
size_of::<ScalarReader>() + 512`. The 512-byte component is explicitly described
as scalar/initializer/copy temporary scratch; it is not an unassigned new
executor allowance. The first numeric extraction must name and count every
actual new wrapper, argument, reference, shape/result and return slot against
that **unchanged** formula, including coexistence with its other named terms.
Existing adapter declarations and equal-size references are not proof that
those positions have already been attributed. No owner field, requested
reservation, budget, work or failure ordering change may be used to make the
map fit. If a narrower internal numeric borrow seam is needed to avoid unused
whole-parts/projection storage, root must review and compile that concrete seam
before implementation; this proposal selects no alternate public contract.
The actual first extraction stays on FrozenMode only until numeric semantic,
trap, live-length, work and allocation parity is accepted.

No previous constructor total, measured alignment or padding is free allowance.
The accepted construction/permanent-header maps are not recomputed or silently
increased here. If literal frozen scratch cannot cover newly named adapter
positions without a reservation/usage change, stop that extraction at root
review; a frozen accounting change is not authorized by this document.

## Verification and acceptance boundary

Run `python3 -B verification/swift-shared-executor-algorithm-contract/collect.py`
from the repository. The collector requires a fresh results directory, snapshots
an explicit source closure into an archive, records SHA-256 manifest/tree digest,
versions, commands, outputs and base revision, and verifies derived closures
before/after every command. Each source variant/profile has its own fresh target
directory. It never compiles product and instrumented sources into one target.
Historical failed attempts remain separate.

Positive variants compile both real mode associations against current source,
with all features and minimal Swift feature, Debug/Release. Only explicitly
filtered function-binding/layout tests execute; none calls an algorithm witness,
constructor, guest opcode, target or platform service. Counterfactual source
variants must fail compiler borrow checking for cache mutation with a live view,
returning a view as static, and dispatch while the cache phase still owns its
control/WASI borrows. Error-code checks classify actual compiler failures; they
are not syntax-only acceptance.

The final results contain fourteen executed function-binding/layout probe tests
(four all-feature and three minimal-Swift per Debug/Release), two separately
filtered frozen-layout tests, and three expected compiler rejections. The
unmodified baseline and derived minimal-Swift layout probes produced the same
41 layout/offset lines for Frame, Control, SpanInstance, ExecutionParts and
FrozenOperation. This comparison concerns the host build only. Named new host
sizes/alignments are FrameScalars 40/8, PinAttempt<FrozenMode> 424/8,
SwiftGrowthContext 8/8, PinAttempt<SwiftMode> 1128/8 and
Result<(),SwiftReleaseFailure> 1120/8. They supply no phase total or positive
simultaneous-count acceptance.

Run `python3 -B verification/swift-shared-executor-algorithm-contract/verify.py`
to independently reconstruct all six source variants from the exact archive and
retained overlay inputs, check the compiler output bindings, and obtain runtime
test lists and SHA-256 for all four executed probe binaries. This supplements
the collector; it does not add a semantics test. `results/receipt.json` and
`results/artifact-check.json` retain the evidence. Failed `attempt-1` through
`attempt-3` and earlier `draft-1` are nonqualifying historical collector attempts.

This evidence proves the chosen static signatures, source-bound compiler borrow
splits and host shape measurements only. It does not prove opcode semantics,
work/fuel parity, allocation freedom, phase byte coverage, runtime cleanup,
Swift initialization/invocation or frozen API regressions. Implementation,
independent adversarial review, all executor-stage synthetic assertions/layouts,
a separately accepted exact bounded target runner, physical iOS/Android,
immutable published FieldLog consumption and external GA evidence remain pending.
