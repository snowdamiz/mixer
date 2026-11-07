# Private Swift calls and complete dispatch contract

Proposed next implementation unit for root selection, October 24, 2026. Implement
**defined and indirect calls together with the complete private instruction loop**
over the accepted original-owner primitives. The result must execute meaningful
multi-function, control, numeric, memory, growth and imported-host programs through
one loop. A call-only mock, more one-instruction callers, a second interpreter, or
another syntax inventory does not complete this unit.

This document is a preimplementation contract. Its isolated compiler witness is
uncalled, has no runtime acceptance and supplies no reservation credit. Product
code, trackers, Git state and predecessor evidence are untouched. The binding
scope remains `mixer-product-plan.md`, especially sections 7, 10, 20–25, W07/W08,
G07/G08 and D3. Full native/guest parity, async/actors, source diagnostics, immutable
separate-repository FieldLog consumption, updates/recovery, signing/store,
customers/operations and G01–G38 remain required product work.

## Exact authority and present implementation

The authoritative baseline is the root's contextual cleanup integration:
`verification/swift-cleanup-diagnostic-root-integration/integration.json` and its
128-file source archive/manifest, closure
`1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c`.
The receipt records 282 all-feature Release library tests, 16 Frozen Release
integration tests and Swift Clippy. Those are root's previous executions, not new
executions by this contract lane. The packet retains an immutable copy of that
receipt and archive; its integrity verifier does not call the historical
host-operation verifier against the later cleanup source. Git is contextual;
source bytes govern. Later documentation cannot silently redefine this baseline.

| Existing source | Actual reusable authority or behavior |
| --- | --- |
| `experimental/execution/mod.rs` | Original cached/Frozen interpreter: run, call, indirect signature comparison, import, finish, work/fuel; eager `execute.rs` is a separate reference path. |
| `experimental/execution/borrowed.rs` | Closed modes, borrowed parts, one numeric primitive body and literal shared control/load/store/bulk/growth bodies. |
| `experimental_swift_reactor/execution.rs` | One original instance/control/cache/WASI/State, six vectors/tickets, selected-instruction and transfer types, Uninitialized constructor and consuming cleanup. No instruction loop or invocation route. |
| `frame_operations.rs` | Original frame envelope, entry guard, per-frame move-only pin, cache-phase completion debt, live debt, normal return, deepest-first cleanup and fixed caller storage. |
| `value_operations.rs` | Actual value push/pop/numeric, floor/room/live checks and contextual active removal. No instruction debit. |
| `control_operations.rs` | Actual shared structural control; `control_operation` returns whether the current function finished. It neither fetches nor calls finish. |
| `memory_operations.rs`, `bulk_memory_operations.rs` | Actual scalar/bulk/MemorySize operations publish into fixed `entry`; outer Ok means publication only. |
| `memory_growth_operations.rs` | Original `buffers[3]` borrow, old/new memory tickets and storage, page/refund debt, `prepare_growth`, `release_growth_pending`, retaining `GrowthCompletion` and `complete_growth`. |
| `frame_operations.rs` host section | Actual sealed 34-descriptor AccountedWasi dispatch, parameter and host work, sole host-entry in adapter, errno/exit/failure semantics, same fixed `entry` outcome. |
| `control.rs`, `cache.rs`, `experimental_wasi/accounted.rs` | Sole first-cause, budgets/reservations/live counters, retained proof/cache pins, actual WASI context and adapter counters. No copied usage becomes authority. |

Existing helpers contain deliberately bounded one-step callers. The full loop
must use their **inner operation boundary**, never call these pinned callers and
thereby refetch, recharge or advance PC twice. Existing Ready enum syntax is not
an implemented Ready transition. This unit leaves initialization and public
invocation unavailable.

## Ownership and selected interfaces

Assign one implementation lane to the following coordinated unit; assign an
independent read-only review lane after freezing its exact packet. Other active
lanes must not edit these files concurrently. Root owns selection, trackers,
integration, commits/pushes and CI.

| Owned candidate files | Required change |
| --- | --- |
| New `vm/src/experimental_swift_reactor/call_dispatch.rs` and focused `call_dispatch_tests.rs` | Full private call/indirect/fetch/dispatch/run choreography, fixed-slot caller, result/floor/type defenses and executed matrix. Wire as a private child of `frame_operations.rs`, allowing access to actual fields without widening visibility. |
| `vm/src/experimental_swift_reactor/frame_operations.rs` | Private child wiring, positively additive call/dispatch header/frame reservation terms; coordinate any small wrappers on original methods. Preserve original frame/guard/debt ownership and completion. |
| `vm/src/experimental_swift_reactor/memory_growth_operations.rs` | Reuse the original prepare/growth/retaining completion path for every full-loop phase; only change it if an actual compiler/accounting or cleanup defect requires a separately identified correction. |
| `vm/src/experimental/execution/{mod,borrowed}.rs` | Extract literal common instruction-arm orchestration where needed, preserving all 39 Frozen expanded methods and its original bound/trace. Existing shared numeric/control/memory algorithms remain the single implementation. |
| `vm/src/experimental_swift_reactor/execution.rs` | Add the new permanent accounting term through the original checked header formula. No owner field, new cache/proof/WASI context, public export or lifecycle transition. |
| `verification/swift-calls-dispatch/**` | Exact sources, fixtures, commands, tools, allocation/counter traces, complete accounting and cleanup evidence. |

Do not duplicate numeric, branch/control, load/store, copy/fill or growth
algorithms. Prefer literal static arm extraction and Swift leaves which delegate
to accepted primitives; no trait object, dynamic callback, mode enum, boxed frame,
argument vector, second ledger or eager `Module` conversion. The complete shared
run/call extraction must preserve Frozen expansion/behavior. If exact extraction
is infeasible, obtain a concrete root amendment before accepting duplicated
semantics or changing Frozen. This packet proves the original-owner composition
seam, not feasibility of that separate literal extraction.

Selected private API shape (names may be adjusted together, meanings may not):

```rust,ignore
// Existing original-owner preparation; use even if this program never grows.
instance.prepare_growth(cursor)
    -> Result<(FrameOperationPhase<'_>, SwiftGrowthContext<'_>), SwiftRunFailure>;

// A caller first enters the admitted defined function through actual enter.
// Outer Ok publishes final outcome into storage.returned; it is not execution
// success. Occupied caller storage is preserved and returns Err before fetch.
run(phase: &mut FrameOperationPhase<'a>,
    growth_context: &mut SwiftGrowthContext<'a>,
    growth: &mut SwiftGrowthStorage,
    storage: &mut FrameOperationStorage<'a>) -> Result<(), SwiftRunFailure>;

// Same actual retaining completion, after explicit pending-growth cleanup.
complete_growth(phase, growth_context, growth, storage, preparation)
    -> GrowthCompletion<'a>;
```

Use the existing `entry: Option<Result<(), Failure>>` for operation publications,
`controlled` for retained control outcomes if necessary, and `returned` for final
`Result<FrameReturn, Failure>`. Do not add a second stored host/growth outcome or
new owner field. Account all temporary Result/Option/copy/closure transfers even
when existing fixed slots are reused. `drained` retains the actual report only
when drain ran. All successful intermediate outcomes end before slot reuse;
failed outcomes remain through drain/completion. Any occupied preparation,
entry/returned/controlled/drained slot rejects before another fetch. No implicit
clearing of a failure authorizes progress. Final outermost Value is copied to
caller diagnostics before fixed storage is consumed, under the original header.

The uncalled `composition_probe.rs` supplies a concrete compiling full-loop
shape using these current APIs. It deliberately uses simple invariant diagnostic
codes, fixed Invocation stage and fewer defensive checks than the selected
runtime contract. It does not implement the shared Frozen extraction, accounting,
all floor/type guards, cleanup runner or runtime matrix; copying it wholesale
cannot qualify an implementation.

## Fetch and the single instruction prefix

For each iteration: establish active phase and actual live agreement; reject
occupied outcome storage; validate current frame floors and its retained pin;
borrow exactly that pin's cache view, copy one `DecodedInstruction` and only the
selected `br_table` u32 target, then end every frame/view/metadata borrow. Never
retain a reference into resident payload across cache mutation, callee entry,
host dispatch, growth, PC/value mutation or release.

`br_table` selection uses the actual top i32, interpreted as u32, without popping
it during fetch. Validate the selector belongs to the current operand region,
checked `first + selector` and target bound. A selector outside the count chooses
the copied default. The control helper later removes the selector once. Invalid
fetch/selector metadata fails before the instruction prefix; its code/offset
must identify the attempted current frame/instruction when available.

Set the cursor to the actual absolute function and decoded byte offset, retaining
the prepared execution stage (Invocation now; Initialization only under its
future lifecycle contract). Invoke `instruction_with_wasi` once: one instruction
fuel debit and one instruction count on its actual accepted ordering. Then
`work(1)` once, checked-increment the current frame PC once, then dispatch. Fuel
rejection has no later work/PC/op effect; work rejection retains the accepted
instruction debit but no PC/op effect; PC overflow retains prior prefix debits
but executes no arm. Preserve RuntimeControl's actual no-refund semantics. A
callee does not debit another instruction until its own first fetch. Import
entry never charges another instruction. Bulk extra fuel remains distinct.

Match all **27 current Operation variants** exhaustively, without a successful
wildcard fallback. New decoder variants must fail compilation until coordinated;
unsupported encodings still reject in complete validation/cache decoding before
execution. Unknown numeric/subopcode values fail before partial shape helpers.

## Direct and indirect calls

For a direct target, resolve only the retained proof. An invalid absolute index
fails before pin acquisition or host entry. Imported and defined calls share the
same parameter semantics but **not a duplicate parameter work debit**:

1. An import delegates to existing `host_operation`, which already charges
   `work(params)`, checks checked base, caller floor, ordered types, host work 1
   and actual adapter entry. Do not add an outer parameter debit.
2. A defined call copies the sealed parameter count, charges `work(params)`
   once, checks `values.len() - params`, actual caller frame
   `base <= operands <= values.len()` and valid control floor/sentinel, then
   delegates to original `enter`. Its existing entry work 1, signature/type
   recheck, limit/capacity, cache phase, locals work `locals + 1`, local checks,
   live predebits, frame/control publication and rollback remain authoritative.
3. Parameters remain in their existing arena positions and become callee locals;
   append only declared zero locals. Never clone arguments, split_off, allocate
   per-frame vectors or debit parameters as new live values. Frame base is the
   checked argument start; operands is the first position after parameters and
   added locals; controls is the caller control length before function sentinel.
4. Every recursive entry acquires its own move-only pin, even when sharing one
   resident function. A successful pin plus failed cache-phase completion keeps
   both pin and nested restore debt in original State before returning error.
   Reuse current bounded entry/rollback/cleanup rather than a simpler Result pin.

For `CallIndirect(type_index)`, the prefix runs first; pop the selector once
through an actual pop with its work/live observation, mark existing frame debt
if a post-effect removal fails, and require i32. Interpret it as u32. Distinguish
`table_out_of_bounds`, `indirect_call_null`, unavailable validated descriptor
(invariant), and `indirect_call_type_mismatch` (guest trap). Selector consumption
is retained on later failure. Do not fetch a callee, create a pin or enter host
for these rejected cases.

Resolve expected type and actual selected function signature from the same
retained proof; checked-add both parameter counts, charge that scan work, then
compare all ordered parameter types **and** optional result type structurally.
Type-index identity, parameter count alone, hash or pointer equality is
insufficient. Two different type indices with equal structure must work;
same arity with different scalar/result types must reject. End views, then use
the exact same direct-target import/defined choreography. Imports in the table
create no callee frame or pin and keep the actual caller pin throughout dispatch.

## Arm mapping, results and failure effects

| Operations | Required existing leaf and observable rule |
| --- | --- |
| Unreachable / Nop | Typed guest trap / no arm effect after prefix. |
| Const / Drop | Original push / original pop; no additional instruction debit. |
| Select | Original pop32, pop b, pop a, push chosen scalar in that order; protect operand floor and require condition i32 and equal selected types. |
| LocalGet | Checked base+index in declared parameter/local region; copy one scalar, original push. |
| LocalSet / LocalTee | Original pop / tee work 1 and peek; actual source must be above operand floor; checked local index and sealed declared type before write; preserve Frozen successful order. |
| GlobalGet / GlobalSet | Retained global declaration and actual State slot; copy/push or pop then mutability/type check and write. Invalid slot/type/mutability fails closed. |
| Block / Else / End / Br / BrIf / BrTable / Return | Existing `control_operation`; no second control implementation. A true finished result invokes original finish once. |
| Call / CallIndirect | Choreography above; no one-step pinned caller. |
| Load / Store | Existing `memory_operation` publication, actual ranges/types/work/live semantics. |
| MemorySize / MemoryCopy / MemoryFill | Existing `bulk_memory_operation`; retain overlap, range, chunk, extra-fuel and post-effect behavior. |
| MemoryGrow | Existing `growth_operation` with the actual borrowed State memory ticket and caller-owned growth storage. |
| Numeric / Saturating | Original `numeric_value`; reconcile actual post-trap lengths without fabricating a result or repairing counts. |

New local/signature/result guards must use short retained proof/cache views,
never a second metadata owner. Bounds/types are checked before unchecked indexing
or partial shape helpers. Newly introduced scans and loops need bounded ordinary
control checks and an explicit work term if they add work; document any required
amendment to the accepted base schedule before freeze. Audit earlier parameter
loops as a full-run interruption prerequisite rather than assuming historical
primitive acceptance proves every full-target interruption interval. Never alter
Frozen error/work order silently to make an extra Swift guard convenient.

On a finished function, validate its actual result against the sealed optional
result type, then call original `finish` exactly once. It saves/pops at most one
scalar, charges actual truncation work, removes frame, truncates/reconciles
values/controls, releases pin and removes frame live count. Nested result push
uses existing work/room/live ordering; `CallerContinues` resumes the already
advanced caller PC without a second return value. `Outermost(None/Some(value))`
is retained in the one final returned slot and stops fetching. Wrong/missing
result fails closed and never produces Ready. A rejected pin release remains
owned at its original frame slot; its processed suffix is not retried during the
same drain pass.

After any failing primitive, inspect both outer publication Result and stored
operation Result. Mark terminal and stop; a successful publication is never
interpreted as a successful operation. Post-effect pop/numeric/control/host/
finish live-removal failures retain exact contextual cursor, resource,
attempted/available, sticky invariant/debt and original first failure. Do not
convert these into generic wrapper diagnostics. Numeric's existing direct
primitive distinction remains: there is no new numeric debt field, and terminal
drain must still observe actual arena/count disagreement.

Actual WASI continues to own call/work/transfer/random/log counters and fault
semantics. Keep errno zero-extended from official u16 to i32, actual committed
output/memory effects, exact GuestExit including zero, typed `wasi_failure`,
deadline origin and immutable `at_failure`. A later cancellation/deadline,
cleanup invariant, refund failure or source-wrapper error cannot replace the
first cause. Invocation-attributed removals use the selected contextual entry;
rollback, drain, pending-growth refund and genuine cleanup keep their original
cursorless cleanup entry. G08 original Swift source mapping remains open: a
correct Wasm cursor is only one diagnostic prerequisite.

## One completion barrier, including growth

Use `prepare_growth` for the complete run. It splits actual State arenas and
`&mut buffers[3]`; no whole-instance access survives the split. A run which did
not grow still uses empty original growth storage and the same completion rule.
No second memory ticket/context is constructed for host or nested calls.

On terminal failure, release pending growth through its existing cleanup-only
rule and drain frames through original deepest-first pass, regardless of fuel,
work, cancellation or deadline exhaustion. Observe both outcomes. A committed
growth whose old-ticket refund rejects is not rolled back: State owns its new
memory/ticket and old refund debt remains in the original growth carrier.
Uncommitted replacement is dropped before refund; rejected page reconciliation
or ticket provenance stays retained. Growth debt does not disappear because all
pins were released.

Only `complete_growth` (or a root-reviewed equivalent consuming exactly those
same original fields) may consume this full-loop phase. Calling `phase.complete`
directly is forbidden while a growth context, transfer, page debit/refund debt or
preparation wrapper remains. Retained completion owns phase, ticket borrow,
transfer, original fixed storage and preparation; dropping it does not refund
its admitted envelope. Original frame completion independently checks pins,
entry guard, live debt, nested restore, frame/value/control emptiness and fixed
controlled storage. Retained drain/restore reports cannot be relabeled Completed.
Explicit cleanup reacquisition, not another executable run, is the only retry.

Positive execution-header accounting covers copied final failure/result/usage
through consuming final owner cleanup. Never refund the header or restore the
outer construction bound while returned wrappers or authority are still live.
No Drop implementation becomes an unreviewed cleanup/acceptance shortcut.

## Required accounting prerequisite

Do not reuse this uncalled witness's unchanged formula or historical numeric
host proposals as approval. Freeze a new exact candidate after the baseline
above. Before its runtime qualification, inventory the **complete added/changed
compiler bodies**, including free/bare functions, impl methods, every closure,
promoted body, typed argument/return/local, authored literal/alias/reborrow,
Result/Try/residual, selected instruction/target, index/signature/result copy,
slot transfer, caller guard, completion and retained carrier. Select full compiler
headers with explicit expected body identities. Substring-only selection of a
module/namespace is insufficient: Rust emits these free bodies as `fn run`,
`fn fetch`, etc. The first witness inventory reproduced exactly that omission;
its incomplete artifacts remain historical, and fresh corrected selection is
required in the final packet.

Charge every new canonical role positively in disjoint named original-header
permanent and frame active classes, before that role can exist. Retain all prior
positions, including 4,800 memory, 4,324 bulk, 10,356 growth, 4,876 host and 5,516
contextual diagnostic positions. No existing row, padding, phase reuse, equal-size
alias, peak subtraction, optimizer elision or ticket-sized placeholder supplies
credit. Existing State/Combined ceilings and ticket maximum 86 stay unchanged;
if a positive complete bound exceeds them, retain the actual rejection and
request an explicit scoped decision rather than widening all budgets.

Require separate fresh compiler contexts: baseline/candidate × Swift/all ×
Debug/Release × production/unit (16 layouts), with production/unit MIR in all
four candidate feature/build configurations. Archive raw MIR, full headers,
compiler expansions and type/layout/offset/interval inventories. Verify all
original owner declaration/layout fields and all 39 expanded Frozen methods,
original 2,912-byte Frozen bound and existing reservation expressions. A changed
owner type is a coordinated contract change, not a harmless layout refresh.
Record complete field sizes, alignment, offsets, class totals and source binding.
These are logical named-object bounds; they do not claim physical stack/RSS.

## Executable acceptance matrix

The machine-readable `verification/swift-calls-dispatch-contract/matrix.json`
contains CD01–CD24, exact fixture cases and assertions. Every runtime row is
pending. The sealed compiler packet checks type/borrow composition only.
Implement each group as actual production-path tests whose names begin with the
recorded prefix. List and bind binary test identities before execution; a filter
which selects zero tests is a failure. Assertions compare independently authored
expected values, exact counters/events/cursors, memory bits and pin/ticket/debt
inventories, rather than reading an expected result back from implementation.

Require all four Swift-only/all-feature × Debug/Release runs; selected independent
adversarial tests; full library suites; Frozen integration/allocation traces;
default/span/Swift/all library checks; Swift CI Clippy; formatting/whitespace.
Use source/config-specific fresh targets for product, baseline, derived layout
and negative compiler runs. Archive failures and any normalization explicitly.
An allocator refusing its first request must see zero executor requests on warm
non-growth/non-cache-miss dispatch; separately qualify admitted cache decoding
and growth allocation. No new owner or per-call allocation is allowed.

## Next route to real Swift and remaining gates

After independent/root acceptance of this coherent dispatcher candidate, implement
one separately reviewed **private lifecycle/target-runner** unit: `_initialize`
35 `()->()` once, then two corpus 62 `()->i32` calls through this same dispatcher
and the same instance/cache/WASI, preserving memory/globals/table and cumulative
fuel/work/host/cache counters. Ready requires actual initializer success with
zero result/frames/values/controls/pins and successful completion; any failure or
GuestExit returns no Ready owner. Do not reset context/budgets or replace business
logic to obtain parity. Public arbitrary-index/name invocation is a later API
security/lifecycle decision, not implied by successful private execution.

The retained full Swift target identity is
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`
(53,777,114 bytes). This contract does not read/validate/run it. Before the real
runner, independently verify its current immutable bytes, complete proof/profile,
all 34 exact descriptors, no start, memory minimum 584/effective maximum 768,
fixed table 46,713, initializer/corpus signatures, environment float support,
actual secure randomness, original native 11-field observations and source/tool
closure. Historical reference execution is not current owned execution. Dynamic
call/value/control/cache/work/fuel/memory demands, interruption intervals,
resource overlap and deadline origin must be measured, not inferred from counts.
A budget exhaustion remains a failed exact dimension, not permission to raise
all limits or skip bodies. The full artifact's compressed-size failure, performance
and source mapping stay independent requirements.

The current packet creates no native/simulator/emulator/phone instance and
attempts no discovery. Simulator/emulator verification is authorized for later
development joins; final physical iOS/Android remains deferred while phones are
disconnected. Compiler/layout/host proof does not close a native, FieldLog,
signing/store/customer/operational/OTA/GA gate. Root must select this contract
before dependent implementation begins.

## Retained preimplementation proof

The selected attempt is
`verification/swift-calls-dispatch-contract/attempts/20261024T150134948097Z/`.
Its original 128-file baseline is byte-equal to root integration. Its uncalled
129-file witness closure is
`5d07262597a096afc2b0fb57a269387c005907724a82b4703e1b9afacfa7519c`:
only a private child-module declaration appended to `frame_operations.rs` and
the isolated probe source are added. All prior product files remain exact.

Rust/Cargo 1.99.0, LLVM 23.1.1 and Python 3.14.8 on the actual
`aarch64-apple-darwin` host execute 17 selected commands: five provenance/version
commands, eight fresh MIR compilations, and four expected borrow rejections.
Each compiler context retains the complete MIR and 24 selected full function
headers: ten actual free bodies and fourteen closures. Production/unit compiler
qualification changes which names require namespace disambiguation; selection
accepts both explicit full forms and verifies all ten bodies. No selected
promoted body exists in this witness; the verifier rejects a newly introduced
one until explicitly inventoried.

The four negative inputs reject a cache view across callee entry, argument slice
across truncation, whole-instance access while the original growth split lives,
and a borrowed memory ticket across mutable growth dispatch. These are compiler
borrow results, not runtime tests. The original twelve E0500 errors and the
incomplete/overstrict historical MIR selectors remain retained among five
attempts/43 recorded commands. Only the final eight contexts and four negative
inputs supply this selected composition proof. All five owned scratch directories
are removed after empty holder checks, with no remaining recorded command group
and no native instance created. Final scratch removed 560,377,092 logical bytes.

`receipt.json`, `input-bindings.json`, `seal.json` and the independent read-only
`verify.py` bind the current contract, 25 immutable input snapshots, source
archives, commands/outputs, MIR, matrix and cleanup. Reproduce saved-proof checks:

```sh
python3 -B verification/swift-calls-dispatch-contract/verify.py --live
```

This checks the current live VM against the exact baseline without compiling,
executing a VM, modifying files or discovering devices. Omit `--live` for
archive-only checks. A fresh compiler reproduction must run `collect.py` from a
new separately owned copy at the same verification-directory depth; do not append
to this sealed historical packet. The collector requires the pinned local Rust
installation at `/opt/homebrew/opt/rustup/bin`, uses no downloaded dependency and
removes only its own temporary tree and process groups.
