# Frozen control extraction accounting preflight

The frozen `ControlMode` proposal is **not applied**. Its real-type preflight
compiled, but the chosen additional fallible-adapter transfer inventory does not
fit the unchanged reservation. Root's design freeze explicitly requires stopping
in this case. The full 116-file VM source closure remains identical to the
accepted original-owner value-operation source, SHA-256
`96b16d4886b9218e132a2a1255c0ce4e66c60879ed7bb5f1ea1185b0ca08b8c7`.
No production, existing test/helper, tracker, original planning packet or gate
was edited. No implementation acceptance is claimed.

The governing design freeze is
`verification/swift-executor-control-next-slice/root-freeze.json`. The preflight
receipt is
`verification/swift-control-extraction/results/20261024T025535989853Z/receipt.json`.
It retains the unmodified VM source archive, complete source manifest, exact
candidate overlay, copied freeze, four independent derived source manifests,
compiler output, runtime test lists, binary hashes, command argv/cwd/target,
versions and measurements. These are metadata/type/layout tests, not product
semantics tests. No candidate helper was called and no guest was instantiated.

## Measured transfer boundary

The isolated candidate implements the proposed signatures against actual
`SpanInstance`, `Control`, `Value`, `ExecutionFailure` and the existing owner leaf
methods. `ControlMode::ControlState<'owner>` is `SpanInstance`. It compiles the
three generic helper function bindings and the complete proposed static leaf
adapters. It uses no alternate owner, state wrapper or public route.

Rust/Cargo 1.99.0 on aarch64-apple-darwin produced these identical measurements
in minimal span/all-features × Debug/Release:

| Chosen actual type or role | Bytes | Offset within new transfer |
| --- | ---: | ---: |
| ExecutionFailure | 392 | — |
| Result<(), ExecutionFailure> | 392 | — |
| Result<Value, ExecutionFailure> | 392 | — |
| Result<bool, ExecutionFailure> | 392 | — |
| Result<i32, ExecutionFailure> | 392 | — |
| Work adapter source-result position | 392 | 0 |
| Work adapter returned-result position | 392 | 392 |
| Shared helper caller-result position | 392 | 784 |
| Complete additional transfer subset | **1,176** | 0 |

The concrete source association is the original `state.work(amount)` result
inside the new work adapter, that adapter's returned `Result`, and its caller
at `M::work(...)` inside shared close/branch. The chosen accounting convention
retains separate source, returned and caller positions, as the accepted numeric
preflight did. An optimizer, tail return or equal payload size supplies no
credit for merging these named positions.

The original frozen reservation protects three original ExecutionFailure
positions, 1,176 bytes, as well as its owner, two CacheFailure positions,
DecodedInstruction, Control, ScalarReader and 512-byte scalar component.
Reassigning those original diagnostic positions to new adapter transfers has
not been established and is not permitted as an assumed alias. Even granting
the new transfer subset the entire scalar component as a best-case ceiling:

```text
original explicit failure positions       1,176
new chosen adapter transfer subset        1,176
                                         -----
subtotal                                 2,352
original explicit failure + scalar limit  1,688
                                         -----
uncovered before other new scalar roles     664

unchanged complete frozen formula         2,912
formula minus 512 plus transfer subset     3,576
```

The 512-byte component is already attributed to named scalar windows; accepted
numeric windows peak at 464 bytes. This preflight does not borrow that occupied
numeric inventory or claim that all 512 bytes are actually free. The inequality
above is already sufficient to reject this chosen conservative map before
adding state reborrows, saved result/control/scalars, closure captures or Rust
Try branch/residual roles. It is a necessary subset, not a completed simultaneous
map or a measurement of physical stack/RSS. It does **not** prove that every
possible control-sharing design is impossible within 2,912 bytes.

The result also explains why changing only the infallible truncate/observe
adapter return types would be insufficient evidence: the genuine fallible work
adapter's transfer subset remains. No limit, reservation, owner field or formula
was widened to force acceptance.

## Minimal alternative requiring a new root freeze

Use one independently authored `macro_rules!` body in the existing private
borrowed module to emit the existing inherent `SpanInstance::pop32`,
`close_control` and `branch` methods directly. Replace those three original
method definitions with one private macro invocation inside the same owner
impl. Keep their signatures and literal bodies, including direct existing
`self.work`, `self.pop`, `self.push`, `self.observe`, truncation and pc assignment.
Do not insert ControlMode leaf adapters or delegating wrappers.

This alternative keeps a single source for the three algorithms while avoiding
the new fallible function boundary and its result transfers. It introduces no
callback, stored mode, new owner/state wrapper, changed layout/budget/formula or
additional helper call depth. It is **a proposal**, not a compiled alternative,
accepted accounting map or product implementation. The static-trait design
would be explicitly superseded only within this bounded extraction if root
freezes that change. Future Swift reuse still requires its separate ownership
and accounting contract; the macro proposal does not authorize Swift execution.

Before implementation, root must review the exact macro definition, hygiene,
private visibility and invocation, and the disjoint source/expanded-body map.
The candidate must then demonstrate that all original concrete method bodies,
typed temporaries, failure/error/observation ordering and formula are preserved.
Source-token or expansion equality is supporting evidence; executable public
parity and fault tests remain mandatory. No reduced semantics, synthesized
result, early failure latch in `SpanInstance.failure`, mutable out-parameter
failure channel, skipped work or fresh interpreter is proposed.

## Executed checks and still-unrun requirements

Four isolated derived metadata binaries compiled and each executed exactly one
named test, `control_adapter_transfer_accounting_probe`. Its assertions confirm
the actual function signatures, 2,912-byte frozen formula, 392-byte failure,
1,176-byte new transfer subset and inequality. A passing rejection probe means
the design does not fit; it is not an implementation pass. Source closures were
checked before and after every build/list/probe command. Each configuration has
its own fresh target directory and its runtime test identity/binary hash.

Because the accounting condition stopped implementation before product edits,
all six proposed product cases, baseline/candidate semantic traces, fault/work/
fuel/cancellation matrices, warm-dispatch allocation tests, existing frozen and
Swift value regressions, feature compile checks, product format/Clippy and full
production/unit owner layout comparisons remain **unrun** for this extraction.
The original acceptance evidence is unchanged; no redundant full suite was run
to disguise the failed prerequisite.

Run `python3 -B verification/swift-control-extraction/preflight.py` to create a
fresh retained preflight run. Run `python3 -B
verification/swift-control-extraction/verify.py` to verify the saved rejection
packet. The verification script checks packet and real binary/source bindings;
it cannot establish completeness of an unprovided accounting map.

Swift active frames, entry/finish/unwind including multiple rejected-release
pins, instruction dispatch, memory/growth/host execution, full target and GA
remain pending. Computer use, capture and simulator/emulator runtime remain
paused. No device, native app, publication, customer message, credential action,
commit or push occurred in this lane.
