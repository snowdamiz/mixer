# Private Swift imported-host operation contract

This is a selected contract and uncalled compiler feasibility packet. It adds no
live VM implementation or runtime acceptance. The binding product scope remains
`mixer-product-plan.md` section 10; full dispatch, ordinary call/indirect-call
choreography, Ready, public invocation, the full Swift payload, native joins,
physical phones, release and GA remain pending.

The baseline is Git `a1f78d1e88d6e1e934a08cdb85ce90f87f6ff343` with the exact
125-file VM closure
`96c945a817c81be17fb526067d87cc667a21cdaf5a47be18179e10fe5ed8de0d`.
The uncalled candidate closure is
`cec112c3e53391cc0961547aea4e323807780e5b0d6e6fed167cf8377bd4165e`.
Only a private child module appended to `frame_operations.rs` differs in that
snapshot. [The packet](../verification/swift-host-dispatch-contract/receipt.json)
binds actual commands, compiler output, source archives, layouts and limitations.
It is independent of the active isolated memory-growth lane and grants no
acceptance to that lane.

## Smallest original-owner seam

The proposed private method is:

```rust,ignore
FrameOperationPhase::host_operation(
    &mut self,
    absolute_import: u32,
    returned: &mut Option<Result<(), SwiftRunFailure>>,
) -> Result<(), SwiftRunFailure>;
```

The witness uses `host_contract_operation` to distinguish its uncalled status.
It publishes into the actual `FrameOperationStorage.entry` type, as existing
memory operations do. Outer Ok means publication only; the caller must inspect
the stored operation result. An occupied slot is preserved, terminalizes the
phase, and returns before fetching, work, PC mutation or host entry. A failed
stored outcome remains available through terminal drain/completion. A successful
outcome is taken before reuse. There is no second host outcome field, new owner,
ticket, host frame, host pin, argument vector, callback or guest reentry.

The operation borrows the existing phase. Its original `ExecutionParts` holds
the actual State values and memory arenas, cache, caller frames and controls;
its `SwiftExecutionOperation` holds the actual mutable WASI/control pair and
cursor. It neither borrows the whole instance while split nor borrows the
memory reservation ticket. The caller's existing pin remains in the actual
frame throughout host execution and later ordinary return/terminal unwind.

The original `prepare_frames` first calls `original_owners`: actual WASI
`checked_usage`, cache owner/header, construction owner, State header/layout and
all six backing tickets/live memory layout are checked before phase admission.
The exclusive phase borrows prevent replacing those owners while it exists.
Existing phase `active`/agreement checks consume that established pairing. The
new inner boundary additionally invokes actual `checked_usage` and
`cache.check_owner` before its first work or argument effect. No copied usage
authorizes admission or serves as a meter. Every later fallible existing work,
dispatch, live-removal and push boundary samples the same context anew.

The absolute index selects only
`cache.proof().execution_imports().get(absolute_import as usize).copied()`.
The proof seals the complete ordered 34-descriptor table. It also provides the
actual execution signature; the witness checks complete parameter/result
equality with that descriptor before copying only the descriptor and parameter
count. Names are never reparsed and no user context is injected. Non-import
indices fail closed. This seam does not implement ordinary defined-function
entry or an indirect table dispatcher.

## Exact work and lifetime ordering

Frozen's existing `call` looks up its signature, charges `work(params)`, computes
the checked argument base, checks the current frame operand floor, then chooses
its import/defined-function path. Frozen `import` checks control, charges work
1, checks/increments its original host counter, resolves its existing `mixer`
checkpoint/abort import and executes that behavior. All those Frozen bodies
remain unchanged. Its ABI is different from Swift's accounted Preview1 ABI;
this slice introduces no generalized import macro or runtime mode adapter.
Ordinary shared call choreography remains a later separately coordinated slice.

The private Swift imported-host operation has this explicit order:

1. Reject occupied caller storage; validate the active phase and paired actual
   owners as above. Read/copy the sealed descriptor and signature scalars.
2. Charge execution work equal to `params`, before computing the checked
   `values.len() - params` base. Reject underflow, a missing frame, invalid
   frame floor/control base, or arguments below the caller's operand floor.
   Check every actual argument type against the sealed descriptor. There is
   no argument mutation or extra type-scan charge hidden in this step.
3. End all signature, frame and parameter-type views. Charge host execution
   work 1 with a fresh actual WASI observation.
4. Borrow `&values[base..]` and disjoint mutable `memory.as_mut_slice()` directly
   from the actual State arenas. Call the actual `AccountedWasi::dispatch` once
   with the original control, copied descriptor and current invocation cursor.
   No cache `FunctionView`, cache operation phase or immutable WASI phase borrow
   survives this boundary.
5. `AccountedWasi::dispatch` checks its actual header owner and control, then
   calls `enter_host_with_wasi` immediately before actual context dispatch.
   That is the sole executor host-entry debit. The new method never calls
   `enter_host` itself. Actual `WasiContext` remains the sole call/work/transfer/
   randomness/log meter, with its existing admission, rollback and OS behavior.
6. Adapter failure and `proc_exit(u32)` latch their original typed fault before
   AccountedWasi's postcheck. A later cancellation/deadline cannot replace that
   first cause. `proc_exit`, including code 0, has no successful result and
   never exits the native process. The witness rejects an impossible returned
   errno for that descriptor rather than creating a success value.
7. On successful errno only, end the argument/memory borrows, truncate values
   to `base` once and remove exactly `params` live values once. A rejected
   removal sets the existing `frame_cleanup.live_unreconciled` flag and retains
   that debt for ordinary terminal cleanup. Convert official errno through
   `u16` to i32 and push through the actual existing `phase.push_value` path,
   including its work 1, capacity/operand checks and final live predebit.

The pinned one-step compiler witness copies one instruction while viewing the
actual pinned caller and then ends that view. It sets the invocation cursor,
accepts only `Operation::Call`, charges instruction/fuel once, charges caller
work 1, checked-increments the caller PC once, and invokes the imported-host
inner method. The host operation itself assumes that prefix has already run;
it does not duplicate instruction/fuel/PC effects. A rejected non-import target
is not evidence of defined-call support. The witness is uncalled and supplies
no instruction-loop or guest execution receipt.

All original caller frame/control/pin storage remains in place on host success
and failure. Imported indirect calls must eventually use this same host rule
after full structural signature equality and selector removal; that indirect
choreography is outside this slice and remains unimplemented here.

## Failure effects and first observations

| Boundary | Host-entry/adapter-call effect | Arguments and other effects |
| --- | --- | --- |
| Occupied slot, owner/floor/type/import rejection, caller fuel/work/PC failure | No new actual host entry or adapter call | Preserve the actual prefix effects already reached; no host argument mutation. |
| Host work or actual control host-limit/cancel/deadline rejection | No entry debit when entry admission rejects; adapter calls unchanged | Arguments remain for terminal drain; exact latest attributable WASI usage reaches first failure. |
| Adapter call-budget rejection after admitted host entry | One host entry; adapter call counter does not increment | Actual adapter terminal failure and its counters remain authoritative. |
| Actual adapter failure or post-dispatch control failure | Exactly one admitted entry; adapter counters reflect actual entered behavior | Arguments remain; current memory/output effects remain as produced by the unchanged adapter. The executor adds no rollback. |
| Successful non-success errno | One entry and one adapter call | Remove arguments once, push the official errno as unsigned i32, and continue if all later boundaries succeed. |
| `proc_exit(code)` | One entry; actual adapter counter/failure behavior retained | Exact GuestExit code, no errno result, arguments retained for terminal drain. |
| Live removal fails after truncate | Original host effects and counters retained | Truncation has occurred; existing sticky live debt is set. No result is pushed. |
| Result push fails | Original host effects and counters retained | Arguments have been removed/reconciled; actual push publication/debit behavior is retained. No rollback or fabricated room. |

`RuntimeControl::fail` remains the sole first-failure authority. Preserve exact
kind/code/resource/attempted/limit/capacity, cursor, deadline origin,
`wasi_failure`, GuestExit and immutable `at_failure`; `after_cleanup` remains
separate. No terminal cleanup completes the frame envelope until original
pins/guards/live debt and fixed caller return storage satisfy existing rules.
The future full dispatcher must also retain the frame envelope whenever a
separately implemented growth operation retains replacement/old ticket or
refund/live debt; this host seam adds no alternative completion shortcut.

## Positive proposed accounting

The uncalled compiler probe introduces no live reservation formula changes.
Before a runtime candidate is authorized, add its complete fixed caller/
completion class to the original execution header and its active class to the
existing frame-operation envelope, before their first corresponding object is
created. The existing header and construction owner remain the authorities;
no new ticket is needed. Rebase and remeasure after any accepted growth source
is integrated; the figures below are explicitly against the pre-growth closure.

The inventory contains 4,768 disjoint positive fields: 2,324 production MIR,
2,400 additional unit MIR and 44 fixed caller/completion placements. It retains
every typed argument, return/local, authored alias, direct typed literal,
Try/residual, closure capture and promoted descriptor body for the new seam,
actual AccountedWasi dispatch/checked-usage/usage and descriptor parameter/result
bodies. Each has separate source, argument, returned and caller fields. Existing
frame/control/value/cache/adapter internals keep their accepted reservation
classes; the complete additional dispatch MIR is charged afresh. The six
foundation optional-observation positions supply no credit to these additions.
The fixed class includes real storage/slot/result/publication/first-failure,
completion tuple/report and after-cleanup observation placements.

Sixteen actual paired metadata builds cover baseline/candidate × Swift/all
features × Debug/Release × production/unit. Every positive field is aligned,
lies inside its measured containing class and occupies a disjoint interval.
All original measured owner types/offsets and prior bound expressions agree.

| Logical reservation against this baseline | Production bytes | Unit bytes |
| --- | ---: | ---: |
| New header permanent class | 113,760 | 113,760 |
| New frame active class | 457,016 | 914,312 |
| Original execution header | 1,758,216 | 2,652,896 |
| Proposed execution header | 1,871,976 | 2,766,656 |
| Original frame operation bound | 3,478,968 | 6,299,432 |
| Proposed frame operation bound | 3,935,984 | 7,213,744 |

All 4,800 accepted memory and 4,324 bulk positions remain exact. There is no
peak subtraction, padding credit, equal-size alias credit or reassignment of
existing rows. Ticket maximum 86, State 128 MiB and Combined 256 MiB remain
unchanged in every layout. These are logical authored/canonical object bounds;
they make no physical stack, optimizer temporary, allocator overhead or RSS
claim. The existing absent-cursor cleanup diagnostic remains an open G08 limit.

## Compiler evidence and pending runtime matrix

Rust 1.99.0 (`b940084d7`, LLVM 23.1.1), Cargo 1.99.0 and the actual
`aarch64-apple-darwin` host compile the uncalled seam in Swift/all ×
Debug/Release. Production and unit MIR are retained. Actual compiler expansion
reproduces all 39 Frozen methods, fourteen containing owner declarations and
unchanged Frozen reservation source (the accepted bound remains 2,912 bytes).
No new Frozen runtime trace is claimed; its complete source is unchanged.

Three deliberately invalid exact-source probes fail as required: argument
borrows across truncation (E0502), a retained pinned cache view across host phase
mutation (E0502), and a live cache operation phase overlapping actual WASI/
control dispatch (E0499/E0502). The passing witness therefore demonstrates the
selected Rust borrow boundary. Typing/layout/negative borrowing do not prove
host semantics, counters, allocations or cleanup behavior.

Every runtime group remains pending:

| Group | Required actual host/runtime evidence |
| --- | --- |
| H01 sealed descriptors | All 34 original descriptors, exact argument/result ABI, no name resolution or callback; non-import rejection. |
| H02 original authority | Missing/foreign WASI, cache, State header/backing tickets rejected at their original owner boundary before work/effects; attributable observations only. |
| H03 argument boundary | Underflow, caller locals/operand floor, full ordered type checks, malformed frame floor and parameter work ordering. |
| H04 pinned prefix | Actual pin/view fetch, occupied slot, cursor, instruction/fuel/work failures and checked PC increment; no later fetch after failed stored outcome. |
| H05 sole host entry | Host limit zero/exact/overflow, cancellation/deadline admission; assert exactly one debit only on actual dispatch entry. |
| H06 adapter budgets | Exhausted adapter calls/work/transfer/iovec/log budgets and exact host/adapter counter distinction. |
| H07 cancellation | Before adapter entry, inside bounded adapter work and after real dispatch; retain actual memory/output/counters and first cause. |
| H08 deadline | Actual executor/WASI deadline origins, both sides of real OS calls and postcheck precedence. |
| H09 errno | Success and each exercised official non-success errno push exact zero-extended i32 and preserve caller pin. |
| H10 exit | `proc_exit(0)`, nonzero and high unsigned codes latch exact GuestExit with no result or native process exit. |
| H11 typed WASI fault | Exact `wasi_failure`, adapter rollback where specified, failed OS work counters and later postcheck cannot replace first failure. |
| H12 arena publication | Truncate/reconcile exactly once; existing result push work, operand/capacity rejection and live predebit with no implicit Vec growth. |
| H13 cleanup debt | Rejected post-truncate live removal sets existing sticky flag; retained first failure and explicit terminal drain/completion outcomes. |
| H14 pin/cache lifetime | Actual recursive caller pin stays live, import creates no pin/frame, no view/phase survives host; normal/failed drain preserves authority. |
| H15 allocation/storage | Warm host interval requests no executor allocation, fixed slot stays sole outcome, no refund/envelope restoration while relevant returned storage/debt remains. |
| H16 regression/scope | Frozen runtime parity and existing suites, all-feature/Swift Debug/Release host checks, native/device/full-Swift/Ready/public routes remain separately pending. |

Only root can select runtime implementation after reviewing this packet. No
interpreter/WASI operation, native UI, simulator/emulator, phone, published
FieldLog package, signing, store, customer, operational or GA check executes or
passes in this contract lane.
