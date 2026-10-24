# Private Swift value operations

This candidate implements actual, accounted operations on the original Swift
reactor value arena. `SwiftReactorInstance::prepare_value_operation` returns the
existing private `ExecutionOperationPhase`; `push_value`, `pop_value` and
`numeric_value` execute through that phase. `complete_values` clears the actual
zero-frame value arena and closes its reservation envelope. The reactor remains
Uninitialized. No interpreter loop, initialize, invoke or activation route exists.

Root approved this bounded implementation seam and its additive accounting
approach before product application. The host receipts below pass; independent
coverage review and root acceptance of the candidate accounting remain pending.
They do not supersede the prior construction/primitive acceptance documents or
qualify a full Swift target, published package, native device or GA gate.

## Original owners and operation ordering

Preparation borrows the original control, cache, WASI and State. It checks the
actual WASI pairing, original cache owner and every State ticket. Populated
values, controls, frames, pins, or nonzero live stack/frame counts reject the
zero-frame slice intact. The ordinary check in construction-envelope enlargement
preserves an earlier terminal cause and prevents admission on cancellation or
deadline. No owner moves on rejection. The exact previous construction bound is
retained before creating a phase.

Push charges one execution-work credit, checks actual/live value agreement and
the private operand base, reads the sealed proof's **128** operand ceiling, and
checks existing arena room. It predebits `Live::Values` immediately before its
infallible, allocation-free publication. Pop charges one work credit, validates
the same actual/live and operand boundary, removes the real value, and then
removes its live count. Capacity and operand denials publish no value.

Numeric operations reject unsupported scalar/subopcode values before calling
partial shape helpers. They validate the actual live count, operand base, shape
and types, charge `count + 1` work, then call the single accepted shared primitive
dispatcher. `SwiftMode::NumericState` is exactly the original `Vec<Value>`; its
adapter only returns a shorter arena borrow. The raw helper result stays live
through actual before/after reconciliation. An integer or conversion trap can
consume every operand and emit zero values. The exact actual reduction is
removed without an ordinary check/admission/work debit before the original trap
code is latched with the actual WASI observation. Corrupt accounting fails
closed, with the first cause preserved.

These primitive operations charge no instruction fuel or instruction count. A
future instruction dispatcher must charge those exactly once at its separately
reviewed dispatch boundary. Work, cancellation and deadline failures leave
operands intact when the primitive has not started.

Completion clears actual values even after cancellation, work exhaustion or a
guest trap. It reconciles/removes their count through cleanup-independent APIs,
then passes the actual parts and fixed `ValueOperationStorage` into the original
`end_construction_phase_with_wasi`. That method destroys supplied storage before
restoring the exact previous bound. `ValueOperationStorage` names both possible
returned phase and operation-outcome `Option<Result>` slots. It accepts no
arbitrary additional storage type. Completion reports its cleanup/restore
result; the caller retains the original operation outcome separately. Retained
diagnostics must subsequently be supplied to the existing consuming final owner
cleanup before the same execution header is refunded. The new failure tests do
so explicitly. Dropping an uncompleted phase retains its scratch charge.

## Positive accounting candidate

All existing owner fields, layout meanings and the accepted construction formula
are unchanged. The new module defines additional concrete `PermanentPositions`
and `ActivePositions`. Complete sizes of their named fields, including containing
padding, add positively to the corresponding envelope. No old declaration row,
alias, interior padding or frozen scratch supplies credit.

| Observed aarch64 Apple layout | Baseline | Candidate |
| --- | ---: | ---: |
| Production execution header | 207,352 | 289,536 |
| Unit execution header | 208,312 | 290,496 |
| Additional permanent positions | 0 | 82,184 |
| Existing declaration operation rows | 16,328 | 16,328 |
| Additional active operation positions | 0 | 103,248 |
| Admitted value-operation scratch | absent | 119,576 |
| Production construction envelope | 1,062,312 | 1,062,312 |
| Unit construction envelope | 1,065,072 | 1,065,072 |

Permanent positions cover preparation arguments/owner/ticket borrows, actual
cache/live/usage observations, pre-enlargement errors and phase returns,
completion's parts/operation/fixed returned storage, clear/restore/return results,
and diagnostics retained after restoration through final cleanup. Active
positions cover operation/arena/control/WASI reborrows, all primitive
arguments/results, shape/type/count/boundary state, work/live callsites, actual
observation and failure transfers, and the shared primitive's typed scalar,
pop/conversion/push/return windows. The sum is conservative across helper
windows; the values describe logical requested/named storage, not stack or RSS.

The compiled map has **227 named fields** and **561 typed positions**.
`binding-map.json` expands arrays into their individual typed positions and
records declarations, actual offsets, sizes and alignment. The eight candidate
configurations are minimal Swift/all
features × Debug/Release × production/unit layouts. Matching baseline probes
confirm every measured accepted Swift/Frozen owner size and offset. Compiler
measurements establish those chosen shapes and disjoint fields; completeness of
the association with actual simultaneous implementation bindings still requires
independent accounting review. This document does not call that pending review
a pass.

The preceding candidate at `results/20261024T011018226684Z/` is retained
as rejected accounting evidence. Independent review identified missing exact
conversion/division results, range and borrow roles, nested shape and NaN
positions, preflight wrappers, and Rust Try branch/residual transfers. The
corrected inventory adds each actual type positively; unused i128/u128 and the
incorrect conversion-result type supply no credit. Phase size is now a const
evaluation, so its named-row traversal does not run before admission. The
correction leaves the operation behavior and original owner layouts unchanged.

Raw unit layout logs prefix their first output with the test name. The original
collector matched `value_` in that name rather than the full layout marker.
All sixteen layout records were reconstructed from the sealed raw logs; eight
first rows were corrected. `receipt-before-layout-parse-repair.json` preserves
the original receipt, and the current receipt binds that repair explicitly.
No source, command output, compiled binary or test execution changed. The
verifier now checks every parsed layout record against the raw log.

The coordinated shared-module change only widens `NumericMode`/`numeric` to
crate-private Swift-or-span compilation. The Frozen implementation remains
span-only. Its primitive body and entire original `SpanInstance` source are
literal baseline bytes. The frozen 2,912-byte formula, public Limits, work,
fuel, allocation and error behavior remain unchanged.

## Executed host evidence

The final receipt is
`verification/swift-executor-operations/results/20261024T013344529137Z/receipt.json`.
`verified-summary.json` and `binding-map.json`
retain the independently reconstructed source/layout/binary evidence. The exact
candidate VM closure is 116 Cargo/source/test/include files with tree SHA-256
`96b16d4886b9218e132a2a1255c0ce4e66c60879ed7bb5f1ea1185b0ca08b8c7`.
Rust and Cargo are 1.99.0. All 131 commands retain argv, cwd and output hashes;
tool-version commands are included. Every product/derived command checks its
exact source closure before and after execution. Every product feature/profile build,
Clippy/check build, and derived metadata configuration has a separate fresh
target. Product and metadata sources never share a target.

The twelve new production-path tests pass in each minimal-Swift/all-feature
Debug/Release run. They execute 128 admitted scalar shapes and eight saturating
shapes; independently expected native arithmetic, signed division, saturation
and floating bit identities; trap consumption; invalid opcode/type/underflow;
work/cancellation; operand/capacity denials without publication or allocation;
actual live corruption and sticky cleanup; exact envelope restore; and real
original-control admission rejection retaining all owners.

These are selected library and numeric integration targets, not the complete
product suite. Per profile the baseline/candidate counts are:

| Features | Baseline passed | Candidate passed | Existing ignored |
| --- | ---: | ---: | ---: |
| Swift reactor only | 137 | 149 | 6 |
| All features | 185 | 197 | 6 |

There are exactly twelve added listed test identities and no removed identities
in each comparison. Forty-eight actual product binaries have SHA-256 and runtime
test lists checked independently. Each all-feature profile matches all 454
frozen public numeric traces, including result/trap/work/fuel/cache/allocation
observations. Allocation observers refusing their first request see zero
requests during the selected new operation paths. These observations cover the
executed paths, not every possible asynchronous cancellation instant.

Default/span/Swift/all library checks, formatting and all-feature library Clippy
pass. Broad all-target/all-feature Clippy still fails on the same **26 actual
diagnostic identities**, matched by title, primary source path, line and column
against the baseline. The six existing ignored development oracles were not
executed by this collector; their earlier accepted evidence is not replaced.

Reproduce with `python3 -B verification/swift-executor-operations/collect.py` and
check saved evidence with `python3 -B
verification/swift-executor-operations/verify.py <results-directory>`. The first
collector attempt stopped because ordinary Cargo CLI artifacts were counted as
test artifacts; its failed receipt/archive remain under
`results/20261024T010924911811Z/`. The successful collector selects actual
`profile.test` artifacts before binding executable lists. The unlinked
`proposed-values.rs` file is historical proposal material, superseded by the
archived product implementation.

## Required subsequent inventories and implementation

Function entry/run/finish/unwind remain absent. They require a separately
reviewed shared algorithm seam and positive selected-instruction, entry-guard,
cache-phase, `PinAttempt`, frame-transfer, saved-result, release-error and
deepest-first unwind positions. A successfully acquired pin must survive a
failed cache-phase completion; no `Result<Pin, Failure>` simplification may drop
that authority. The original terminal cause must survive every later drain.
The current zero-frame completion cannot qualify active-frame cleanup.

Growth remains absent. A future `SwiftGrowthContext` must separately borrow the
actual `state.buffers[3]` memory ticket while six State arenas are borrowed. Its
positive inventory must include the context, complete old/new memory overlap,
both tickets, `GrowthTransfer`, reserve/allocation/return/failure wrappers,
checked zero/copy iteration, replacement drop/refund, and page publication.
Neither a ticket-sized alias nor a reference to unrelated storage supplies
growth ownership or reservation.

Branch/control, memory load/store/copy/fill/grow, calls, indirect structural
signature checking, host dispatch and initialized/Ready lifecycle transitions
remain unimplemented. Future host dispatch must use the actual accounted WASI,
exclude live cache borrows/phases and debit the host entry exactly once.
Initialize/invoke, a separately accepted exact bounded full-target runner,
simulator/emulator execution of later native joins, final physical iOS/Android,
immutable published FieldLog packages from a separate repository, signing,
store/customer/operational evidence and GA acceptance remain pending. No device,
target, publication, commit, push or tracker change was performed by this lane.
