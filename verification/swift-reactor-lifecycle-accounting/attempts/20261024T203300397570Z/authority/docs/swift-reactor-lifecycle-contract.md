# Private Swift reactor lifecycle and target-runner contract

Proposal for root review, October 24, 2026. **selected=false; runtime=false.**
This packet prepares a private exactly-once initializer and repeated corpus-call
boundary over the accepted V7 dispatcher. It implements no product route, runs
no VM or native application, reads no retained full reactor, and accepts no gate.
The binding scope remains `mixer-product-plan.md`, especially sections 7, 10,
20–25, W07/W08, G07/G08 and D3. The complete commercial product remains required.

## Baseline authority and the next missing behavior

The live baseline is the root's 130-file manifest at
`verification/swift-calls-dispatch-root-review/live-v7-integration-retry/final-live-manifest.json`,
closure `3dee84f70c852c2a26572c1d6e3463e45e56760a6bba403fabfb9c355ccb1cd3`.
The immutable qualified V7 candidate remains closure
`78e2586b41f698c60e1bcd4cdd4abb33fbf98d747d1ee183a793988dea7b5237`.
Root's `formatting-normalization.json` binds the sole difference: spaces removed
from seven otherwise-empty `experimental/execution/borrowed.rs` lines, with every
other byte and line count preserved. Its complete 27-command qualification and
fresh 342-test live replay ran the original V7 bytes before normalization.
Those are root's historical results, not runs by this packet. Final normalized
source compilation here is uncalled composition evidence only.

The V7 checkpoint accepts defined/indirect calls and complete private dispatch.
Do not assign those again because older tracker prose still calls them pending.
`SwiftReactorInstance::construct` returns `Lifecycle::Uninitialized`. Existing
dispatch tests manually prepare/enter/run/complete and assert the owner is never
Ready. No current product body publishes Ready or implements initialization.

The next behavior is fixed: execute `_initialize` absolute function 35 `()->()`
once, then execute `mixer_fieldlog_corpus_v1` absolute function 62 `()->i32` twice
on the same original owner. The complete validator already seals these exports,
all 34 ordered WASI descriptors, no start, memory minimum 584/effective maximum
768 and fixed table 46,713. No caller-selected function/name, custom policy,
second proof/cache/WASI/context, eager Module conversion or alternate executor is
introduced. Public arbitrary invocation remains a later API/security decision.

## Proposed private request and rejection contract

The only request variants are `Initialize` and `Corpus`. Product spelling may
change together; their target/stage/signature may not. They carry no u32 target,
name, guest arguments, budgets, deadline override or capability negotiation.

| Current lifecycle | Request | Nonexecuting decision or permitted action |
| --- | --- | --- |
| Uninitialized | Initialize | Attempt fixed function 35 with Initialization stage. |
| Ready | Corpus | Attempt fixed function 62 with Invocation stage. |
| Ready | Initialize | `Rejected(AlreadyInitialized)`; preserve Ready exactly. |
| Uninitialized | Corpus | `Rejected(NotInitialized)`; preserve Uninitialized exactly. |
| Terminal | Either | `BlockedTerminal`; preserve terminal state and original authority. |

The two ordinary misuse rejections inspect lifecycle only and return a small
copied enum. They call no `RuntimeControl` method: no `fail`, `check_with_wasi`,
`record_cleanup`, prepare, work, usage snapshot, allocation, service or guest
instruction. They neither latch nor replace first failure. Counter/reservation
snapshots, memory, globals, table, cache and output remain byte-for-byte unchanged.
A duplicate initialization is not successful initialization or an idempotent
reexecution. A preinitialization call is not a terminal runtime failure. This
remains true if cancellation/deadline has become pending: the refused request
does not execute or probe the runtime. The next permitted attempt observes it.

`BlockedTerminal` is a distinct marker, not an ordinary misuse and not a new
failure. It copies no diagnostic and does not call `record_cleanup` to fabricate
an after-cleanup observation. The actual first attempt's failure and original
RuntimeControl remain authoritative. A corrupt Terminal state without a recorded
failure stays blocked; this precondition path does not invent a replacement.
This avoids a new control accessor solely for repeated terminal calls.

After a request is admitted, provenance, header/ticket, clean-state, budget,
cancellation/deadline and preparation failures are runtime failures. Latch the
actual first cause and terminalize the owner; no initialization retry or Ready
reactivation is permitted. Missing/foreign owners and malformed state are not
ordinary lifecycle misuse. Preserve a rejected preparation's actual ownership
and prior envelope; do not pretend a phase was admitted or call cleanup twice.

An exclusive synchronous original-owner borrow prevents concurrent entry; no
new lifecycle field or in-progress owner is proposed. Host reentry remains denied.
No background task, callback, lock, thread or new cancellation backing is added.

## One execution attempt and publication barrier

For each permitted request, create the fixed stage/function cursor, use actual
`prepare_growth`, then actual `enter(35)` or `enter(62)`. The target has no
parameters; do not add an outer parameter/instruction debit. Entry retains its
original checks/work/pin/local/control rules. Invoke `call_dispatch::run` exactly
once. Inspect both its outer publication Result and stored `returned` outcome;
outer Ok alone never indicates guest success.

The initializer's successful outcome is exactly
`Some(Ok(FrameReturn::Outermost(None)))`. CallerContinues, missing outcome, a value,
an error, any GuestExit including zero, or a terminal lifecycle is ineligible.
The invocation's successful outcome is exactly `Outermost(Some(Value::I32(n)))`;
the private VM preserves n. The exact FieldLog runner separately requires n=0;
a valid nonzero Wasm result is not relabeled a VM trap. Wrong/missing shape fails
closed before Ready or a successful result is published.

After an otherwise successful run, while the actual phase still exists and
before entering consuming completion, perform one final observed
`check_with_wasi` with that attempt's stage/cursor. This is a newly specified
lifecycle checkpoint, with no fuel/work debit. It observes any existing sticky
cause and pending cancellation/deadline before eligibility is committed. Its
failure terminalizes and follows actual cleanup; do not add ordinary checks
inside terminal drain. Together with the actual successful outcome and nonterminal
lifecycle it establishes the absent-first-cause prerequisite without a new
diagnostic accessor. The original completion's restore can still fail, in which
case no publication occurs. Cooperative checks do not promise hard realtime.

Use the existing pending-growth release and deepest-first drain on failure,
without work, allocation, service or cancellation/deadline admission during
cleanup. Preserve first cause, actual effects and retained pin/restore/live debt.
`proc_exit` remains the actual sticky GuestExit, never native process termination.
No later failure or successful cleanup may replace it.

Ready may be published only when **all** conditions hold simultaneously:

1. This attempt was admitted as Initialize from Uninitialized, entered fixed 35
   and produced the exact successful void outermost outcome above.
2. Actual state frames/values/controls are empty; actual cache pins and live
   frames/values/controls/pins are zero; original frame cleanup has no retained
   entry, unvisited suffix, live debt, nested restore or unfinished bound.
3. Growth replacement/old storage capacities are zero, both tickets absent,
   uncommitted page debit zero, no growth live debt, and preparation vacant.
4. Every growth/preparation wrapper has been explicitly consumed while covered.
   The actual inner result is `FrameCompletion::Completed`, after the original
   frame completion destroys its supplied fixed storage and restores its bound.
5. The first cause is still absent and lifecycle has not become Terminal.
   No fallible operation remains between that completion and the Ready write.

`GrowthCompletion::Completed(FrameCompletion::Retained(_))` and
`...RestoreRejected(_)` are failures, not completion. Every
`GrowthCompletion::Retained` keeps its actual phase, ticket borrow, transfer,
fixed storage and preparation. Do not drop it as an acceptance shortcut. Cleanup
retry may use only the original retaining route and cannot execute another call.
An after-cleanup success cannot turn a failed initializer into Ready.

Successful corpus completion leaves Ready and preserves state. Each operation
must finish its full barrier before another request. The one original control,
cache, WASI, memory/globals/table, reservation tickets, absolute deadline, fuel,
execution/cache/WASI work, host counters, capture lengths and peaks accumulate
through initialization and both calls. No reset or replacement occurs at a phase
boundary. Cleanup snapshots do not become admission authority.

## Required completion seam and design tradeoff

The isolated uncalled witness demonstrates a concrete borrow constraint. A naive
caller cannot recover whole-instance mutation to set Ready while a returned
`GrowthCompletion<'owner>` may still own that instance's split borrow. Both this
case and whole-owner mutation during an active growth split fail compilation.
Do not solve it with unsafe pointers, forgotten wrappers, extra lifecycle owners
or an early Ready write.

A short reborrow of the actual phase's `&mut Lifecycle` **inside** the consuming
barrier compiles: destructure its original fields, call the existing
`FrameOperationPhase::complete` with the short reborrow and exact fixed storage,
then publish Ready only after its copied `FrameCompletion::Completed` result.
The retained branch returns the original phase before that short reborrow.

The proposed production seam places `lifecycle.rs` as a private child of
`memory_growth_operations.rs`. That child can use the original private vacancy
predicate and frame fields without widening visibility. Select one shared
publication-aware growth completion helper: existing `complete_growth` delegates
with a closed `Preserve` goal; the lifecycle route uses a closed `Initialize`
goal. The helper derives eligibility from the actual fixed returned outcome and
lifecycle, performs the original vacancy/drop sequence, and calls original frame
completion exactly once. No public bool/callback/continuation authorizes Ready.
Existing `call_dispatch::complete` and all ordinary callers retain their existing
surface and Preserve behavior. Keep original frame completion byte-identical.

This is a **required scoped expansion for root selection before implementation**:
the growth completion body/wiring gains the common helper and new accounting.
It is not authorized by the old V7 receipt or this compiler witness. The witness
copies the vacancy predicate only to typecheck against the unchanged baseline
and accepts a boolean solely to prove the shorter borrow; neither is the proposed
product API. It is deliberately incomplete as a lifecycle implementation.
No full owner-entry/runner borrow route or accounting is accepted by its success.
The implementation lane's first compiler task must therefore cover the complete
precondition → preparation → fixed entry/run → terminal preparation rejection or
retained/completed return route, before generating broad accounting. In
particular, the witness does not prove whole-owner lifecycle mutation after a
failed `prepare_growth` while another branch may return its borrowed phase. If
that needs a publication-aware preparation helper or any additional source seam,
freeze the exact amendment with root before proceeding. Do not infer it from
the successful phase-only completion witness.

## Bounded future file ownership

| Owner/file | Permitted product work after root selection |
| --- | --- |
| Lifecycle lane: new `vm/src/experimental_swift_reactor/lifecycle.rs`, `lifecycle_tests.rs` | Closed request/rejection, original-owner attempt choreography, actual result checks, fixed result storage and lifecycle matrix. Child of growth module. |
| Same lane: `memory_growth_operations.rs` | Private child wiring, one shared consuming completion/publication helper, additive accounting. Preserve original vacancy semantics, retaining carrier, transfer/ticket ownership and Preserve callers. |
| Same lane: `execution.rs` | Positively additive lifecycle permanent/header term only; retain owner fields, six buffers and lifecycle enum. Coordinate any actual extra need before edits. |
| Same lane: new lifecycle evidence directory | Exact candidate sources, new carriers, compiler/layout/behavior/allocation/cleanup evidence. Do not append to this sealed contract attempt. |
| Root | Selection, any further ownership amendment, independent review, exact-target authorization/runner selection, trackers/gates, integration, commits/pushes/CI. |

No edits to control/cache/WASI/validator/shared Frozen files, public Rust/C ABI,
Cargo features, native/SDK/compiler wrappers or the retained reactor are proposed.
If the complete entry route needs a new accessor/owner/field or cannot preserve
the common completion contract, return to root with the exact required seam.
Do not silently broaden scope or revisit accepted V7 accounting absent a defect.

## New carrier and accounting contract

No new numeric byte total is approved here. The declaration witness does not
inventory compiler storage or supply reservation credit. Before product runtime,
freeze actual full compiler bodies, source bindings and phase-appropriate exact
types for every new/changed lifecycle and common-completion position.

| Lifetime/class | New positions that need disjoint positive accounting |
| --- | --- |
| Permanent execution-header addition | Request/rejection/terminal markers, final scalar result and first-failure/usage copies that outlive frame completion, their Option/Result/argument/return/caller transfers, final cleanup caller storage. |
| Active frame-operation addition | Prepared Result/Option, actual phase/context borrows, pending growth and fixed storage transfers, enter/run/publication/cleanup outcomes, saved outermost result, init eligibility, closed completion goal, short lifecycle reborrow, inner/outer completion variants, drain report and every error/Try/residual/closure transfer. |
| Entry/bootstrap before frame admission | Lifecycle precondition request/decision/caller copies, target/stage/cursor and allowed-request preparation errors. Reserve these before existence through a specifically named permanent or admitted bootstrap position; do not claim later frame storage covers them. |
| Completion and retention | Simultaneously live saved result/failure, original storage, phase/context/growth/preparation, goal/eligibility, original completion report, moved retained carrier, returned/caller copies, and any wrapper surviving a failed restore. |
| Target runner, separate from runtime ledger | Input allocation/hash workspace/validation overlap, owned stdout comparison/parsing/receipt buffers and phase observations. Bound these explicitly and report them separately; a borrowed runtime cannot measure arbitrary caller allocations. |

Retain all prior accepted V7 roles/finite positions and their named header/frame
terms. No peak subtraction, optimizer elision, padding, equal-size surrogate,
reuse of existing diagnostic slots without accounting, or silent header credit.
No new ticket, new ledger or per-invocation allocation is proposed. The finite
86-ticket maximum, existing State/Combined ceilings and frozen 2,912-byte bound
remain unchanged. If full positive additions exceed a ceiling, preserve that
specific failure and request a scoped decision rather than widen budgets.

Require fresh production/unit MIR for Swift/all × Debug/Release, exact added and
changed function/closure/promoted identities, and baseline/candidate paired owner
layouts in all sixteen contexts. Original owner declarations/fields and all 39
Frozen expanded methods remain unchanged. Audit actual lifecycle caller and
common-helper transfers; do not reopen already accepted V7 rows merely to recount
them. Distinguish logical named-object bounds from physical stack or RSS.

## Planned executable lifecycle matrix

`verification/swift-reactor-lifecycle-contract/matrix.json` defines SL01–SL24.
Every runtime row is planned, never passed by this packet. It includes exact
proposed test prefixes, independent fixtures, assertions and future command
templates. A filtered command must bind its concrete binary test identities and
select a nonzero exact set; listing/compilation is not execution.

Synthetic fixtures retain the existing complete sealed ABI and validator,
including initial memory/table and all 34 descriptors; no relaxed fixture policy.
Use hand-authored expected state/effect/counter traces, not implementation-derived
expectations. Existing dispatch helpers remain the single interpreter semantics.
Test real persistent memory/global/table changes across calls: the retained real
corpus creates a new local Workspace each invocation, so its repeated equality
does not establish persistent feature state.

Run all lifecycle cases in Swift/all × Debug/Release, independent adversarial
cases, new accounting/layout acceptance, old full libraries/Frozen regressions,
default/span checks, scoped production Clippy and formatting. Allocation refusal
must prove the lifecycle wrapper allocates nothing; admitted cache miss/growth
allocations remain separately measured. Exact source/commands/tools/output,
original failures and cleanup are required. No test run is performed here.

## Separate exact-target selection after lifecycle acceptance

Root must first select the completed lifecycle candidate, independently reproduce
its behavior/accounting and inspect complete source isolation. Only then select
one bounded host runner attempt. This proposal grants no exact-target execution.

The retained target identity from existing evidence is 53,777,114 bytes, SHA-256
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`.
It was not read or hashed by this packet. The later runner must reverify its actual
immutable bytes, complete proof, signatures/imports/no-start/memory/table,
environment float support and original native/source/tool closure before entry.
Keep the runner's external input allocation alive through validation, record
input-plus-internal overlap, then drop that input before adopting the proof.

Use actual OS secure randomness, explicit realtime/monotonic grants and bounded
capture sinks, no preopens/paths/sockets. Construct once, initialize 35 once, call
62 twice, finish each barrier, then perform consuming cleanup. Capture actual
phase suffixes without resetting WASI. Parse exactly two complete duplicate-free
11-field objects from actual output, reject extra/missing/wrong-type fields, and
compare to the retained native reference. Require both i32 results zero and the
unchanged observations: codableRoundTrip=true, committedEntries=1,
completionBasisPoints=5000, emptyTitleRejected=true, pendingChanges=1503,
reordered=true, repeatedCommitRejected=true, reportIncludesEntry=true,
status="passed", taskCount=1000 and unicodePreserved=true.

Record construction/init/call1/call2/failure/final-cleanup counters, category and
combined current/peak, memory pages, depths/values/controls/pins, cache entries/work,
fuel, execution/WASI work/host/transfer/random/log and deadline origin/overshoot.
Node counts/pages are reference observations, not exact requirements for a
different bounded fd sink. On exhaustion retain the first failed dimension and
do not retry with blanket cap increases, skip bodies/imports or replace app logic.

Even a passing host attempt leaves full D3/G07/G08, async/actors, source maps and
debugger, standards/fuzzing, physical/device/performance, the compressed-size
failure, immutable published separate-repository FieldLog consumption, signed
updates/recovery, stores, customers/operations and every GA gate open. Simulator/
emulator work is authorized for later development joins; none is needed here.
Phones remain disconnected and deferred until final acceptance. No publication,
customer message, migration, credential or provider action is implied.

## Actual uncalled evidence and replay

Attempt `20261024T194625118230Z` preserves an exact 130-file baseline and a 131-file
uncalled witness, closure
`92c13f227da0b4f9c3d7ec8c7d922e8ee4bc38340c90c30d11b5d19949ffea8a`.
Only the new probe and one private child declaration appended to the isolated
frame source differ. Live VM is unchanged and all 130 hashes were rechecked.

Official pinned Rust/Cargo 1.99.0, LLVM 23.1.1 and Python 3.14.8 on
aarch64-apple-darwin produce nine recorded commands: three versions, four fresh
production cargo-check configurations and two expected borrow rejections.
All four positive contexts pass; both negatives reject. No unit binary, VM,
native process, simulator/emulator or retained reactor executes. No MIR/layout,
complete owner-entry route, full lifecycle semantics or accounting is accepted.
The positive witness has no runtime root and must not be copied as product code.

Cleanup records all nine command groups empty, no open scratch holders and the
owned 185-file / 102,853,322-logical-byte temporary tree removed. No unrelated
project process or device was touched. Installed compiler provenance pins the
executables, not a complete platform-toolchain supply-chain attestation.

Recheck the saved packet without compiling or running guest code:

```sh
python3 -B verification/swift-reactor-lifecycle-contract/verify.py --live
```

Archive-only replay omits `--live`. A fresh typecheck may run `collect.py` from a
separately owned new reproduction directory at the same depth; never append to
this sealed packet or mutate its old attempt. Neither command
selects this contract or authorizes runtime. Root's selection must be a separate
review artifact before dependent implementation.
