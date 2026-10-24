# Proposed private frozen control macro extraction

Root review is pending. This alternative emits the literal existing private
`SpanInstance::pop32`, `close_control` and `branch` methods from one macro source.
The compiler expands each method identically to its original definition. No
product source has changed. The earlier static-trait freeze and rejected
fallible-adapter evidence remain unchanged; this proposal supersedes neither.

This is a W08 source-extraction prerequisite under the binding product plan.
It implements no shared Swift control execution, active frame, interpreter loop,
target run or GA gate. The no-argument `self.fields` macro cannot currently be
invoked on `ExecutionOperationPhase`, whose original storage is in `parts` and
whose live accounting is separate. Any later Swift use needs the further
contract described below. All evidence is headless native macOS host tooling;
computer use, screen capture and simulator/emulator/device runtime remain paused.

## Exact proposed definition and invocation

The complete proposed definition is
`verification/swift-control-macro-extraction/frozen_control_methods.rs`.
It contains one `macro_rules! frozen_control_methods` with no metavariables,
callback, function pointer, new trait, mode value, adapter or runtime wrapper.
It emits only the three existing private methods with their original signatures
and bodies. Definition and re-export are both gated by
`experimental-span-execution`; the re-export is exactly:

```rust,ignore
#[cfg(feature = "experimental-span-execution")]
pub(super) use frozen_control_methods;
```

In the proposed overlay only, append that definition to
`vm/src/experimental/execution/borrowed.rs`. Inside the original span-enabled
`impl SpanInstance`, replace the original `pop32` definition with:

```rust,ignore
borrowed::frozen_control_methods!();
```

Remove the original `close_control` and `branch` definitions because the macro
emits them at this invocation. No other owner code or callsite changes. The
methods retain their original inherent owner identity and private visibility.
The source ordering of the three definitions changes; the call graph does not.
The helper names never become public Rust/C entry points.

Only the parent `execution` module can name the re-export. No `#[macro_export]`
attribute exists. All identifiers originate in the literal definition; there
are no invocation arguments to capture. The receiver and each local are declared
inside the same emitted method. Its existing type, enum and fallback names
resolve in the original owner context. Actual stable-mode compilation and exact
expanded-method comparison check that resolution rather than assuming hygiene
from the macro spelling alone.

Compiler privacy probes independently reject:

- downstream `mixer_vm::frozen_control_methods!()` with **E0433**;
- downstream access to `SpanInstance::branch` with **E0624**;
- a crate sibling importing the `pub(super)` macro re-export with **E0603**.

The third case is in `verification/swift-control-macro-extraction/privacy-sibling/`.
These are expected compile failures, not product failures or new runtime tests.

## Compiler expansion, types and layout evidence

The final proposal receipt is
`verification/swift-control-macro-extraction/results/20261024T030849261537Z/receipt.json`.
It inherits the exact archived source, successful compiler outputs and metadata
binaries from `results/20261024T030635088702Z/`, whose collector stopped at its
row-parser assertion. All inherited inputs, outputs, source closures and binaries
remain independently bound; finalization does not replace their contents.

The real VM closure has 116 files and SHA-256
`96b16d4886b9218e132a2a1255c0ce4e66c60879ed7bb5f1ea1185b0ca08b8c7`,
matching the accepted value-operation source. Observed HEAD is
`6341a5633b98f8c698c1234e533d0387cc01e81a`. The immutable baseline and proposed
source are extracted into distinct directories with complete manifests.
Every expansion, check and metadata command has a distinct fresh Cargo target;
every source closure is checked before and after execution.

Rust/Cargo **1.99.0**, aarch64-apple-darwin:

| Check | Observed scope |
| --- | --- |
| rustc-expanded method comparison | All three original methods match byte-for-byte after compiler pretty printing, in span/all-features × Debug/Release: 12 method comparisons. |
| Ordinary library type checks | Default/span/Swift-only/all-features × Debug/Release: eight successful checks. |
| Production/unit layouts | Baseline/candidate × span/all-features × Debug/Release × production/unit: 16 metadata binaries, each with the same 66 records. |
| Private access | Three expected compiler rejections with the codes above. |

Expansion uses `cargo rustc ... -- -Zunpretty=expanded` with process-local
`RUSTC_BOOTSTRAP=1` solely to obtain compiler diagnostics from the installed
compiler. This is recorded in each command. Ordinary type checks, metadata
builds and privacy checks explicitly remove that environment flag and use the
normal compiler. No bootstrap-based build is presented as product qualification.

The 66 records measure 27 actual types, 38 owner/borrow field offsets and the
reservation formula. Frame, Control and SpanInstance remain 64, 32 and 1,496
bytes respectively. ExecutionFailure and each measured large Result remain
392 bytes. The fixed formula remains **2,912 bytes**. No chosen layout, field,
budget, feature association, public API or formula is modified to get a fit.

Production metadata runs a small probe-only example; unit metadata executes
exactly `experimental::execution::control_macro_layout_only`. Neither constructs
an owner, pins/decodes a function, executes an opcode or invokes a platform.
Probe-only wrappers and type-printing code are isolated from the expansion and
ordinary-check source variants. Metadata sources are distinct from those source
variants; production/unit metadata targets are also distinct from each other
and from any future product verification.

Two collector faults are retained. The first expected 62 rows when the initial
probe emitted 59. The next probe added seven missing original Try/result types,
correctly emitted 66 rows, then its parser mistakenly included the unit test
name in the first row. Finalization reconstructs rows using complete
`control_macro_type`, `control_macro_offset` and `control_macro_reservation`
markers from the sealed raw logs. All 16 reconstructed tables match. The failed
receipts remain failed; the correction changes no source, build, binary or raw
output from the inherited complete run. The fresh-run collector now uses that
correct parser.

## Named unchanged transient map

`verification/swift-control-macro-extraction/named-transient-map.json` records
26 source-binding groups and all nine original Try sites: one in pop32, three
in close_control and five in branch. Each group names the original receiver,
argument, scalar/value/control, Option/Result, closure capture, source/returned/
caller and residual-transfer roles relevant to its exact source expression.
The compiler-expanded source at each group is unchanged.

This is a **zero-addition delta map**, not a new claim that a measured layout
alone proves the entire historical baseline reservation complete. The source
extraction introduces zero runtime objects, call boundaries or failure-transfer
positions. The original failure source/return/caller positions remain on their
original inherent method boundaries. There is no intermediate ControlMode work,
pop, push, truncate, observe or pc-setting call to produce the rejected new
Result layers.

The original receiver borrows, saved `Option<Value>`, copied Control, frame
reference, checked index/pc, invariant closures, Result wrappers and Try
branch/residual positions remain exactly those of the original bodies. Their
leaf calls still invoke the original owner work/pop/push/observe directly.
Callers including run's copied instruction/target, End's Control, branch's
completion flag and all existing pop32 users remain unchanged. Expanding a macro
at compile time creates no runtime macro object or additional receiver borrow.

The original owner, three explicit ExecutionFailure positions, two CacheFailure
positions, DecodedInstruction, Control, ScalarReader and 512-byte scalar term
retain their existing meanings. No numeric scratch, source/return alias, owner
padding or same-sized object is reassigned as free capacity. The rejected
1,176-byte fallible-adapter transfer subset is absent because that additional
boundary is absent. This delta argument still requires independent root review;
the current receipt accepts neither accounting completeness nor semantics.

## Concrete later Swift sharing path and its dependencies

The present form shares one source for frozen method definitions only. It has
no Swift invocation and does not establish a usable cross-mode execution seam.
Future Swift sharing must occur by editing this **one macro body**, not copying
its control arithmetic or branch/close schedule into a second interpreter.

The required future contract is a parameterized failure type plus compile-time
leaf substitutions. A later proposal must provide exact token definitions for
the following projections/effects while keeping one control algorithm source:

| Algorithm leaf | Frozen expansion must remain | Swift side must use after its own freeze |
| --- | --- | --- |
| Arena/frame projection | Original `self.values`, `self.controls`, `self.frames` | Actual `self.parts.values/controls/frames`; no cloned or reconstructed owner. |
| Failure return type | `ExecutionFailure` | `SwiftRunFailure`. |
| Pop/push | Original direct `self.pop`/`self.push` | Original accounted phase operations, with exact operand boundaries and predebit-before-publication. |
| Work | Original direct `self.work` | Original observed execution-work method on actual control/WASI/cursor. |
| Value/control truncation | Original direct Vec truncation | Actual arena shrink followed by exact cleanup-independent live removal; no cancellation/work/admission between the effect and its removal. |
| Observation | Original direct `self.observe` | Actual live/arena agreement and WASI observation without double-debiting. |
| Invariant/absent frame | Original invariant and `unreachable_failure` behavior | Actual Swift cursor/first-failure route; no default usage replacement. |

These are **compile-time token substitutions**, not runtime callbacks, function
pointers or a new owner wrapper. The exact future macro signature and token
hygiene are not compiled or frozen here. Such a generalization is acceptable
only if Frozen still expands to its identical original methods. Swift-specific
leaf adapters may introduce real fallible/transient boundaries; they need their
own positive Swift operation/permanent reservations and independent review,
rather than borrowing the frozen delta map or accepted value-operation rows.

Before a Swift invocation, root must also accept complete original-owner frame
preparation, pin acquisition/phase completion, entry, return and terminal unwind,
including several release failures each retaining its pin. Existing zero-frame
preparation/completion and consuming cleanup cannot authorize active frames.
The common Control/Kind fields currently have private ownership boundaries;
any minimum crate-private accessors/visibility required by Swift leaf selection
need a separate contract. Never copy those types or encode alternate control
semantics to work around access. Function-inclusive control ceilings, per-frame
operand boundaries, live checks and actual WASI observations must remain real.

No Swift macro invocation, parameterization, visibility widening, frame wrapper,
new account, shortened guard lifetime or release outcome is implemented by the
present proposal. If the future leaf contract cannot retain a single algorithm
source and the Frozen expansion guarantee, stop and review the contract again.

## Root freeze and later executable acceptance

For a separate bounded root freeze, review the exact macro file/invocation,
compiler expansion equality, ordinary compilation, privacy results and 26-group
delta map. Only then apply the two-file source move and execute the product
verification packet. Preserve the former freeze/rejection as historical input.

`verification/swift-control-macro-extraction/later-implementation-matrix.json`
retains all six meaningful proposed cases and their actual work/fuel/failure/
allocation/cancellation/limit requirements. It binds the immutable earlier test
matrix. Baseline/candidate product builds, exact runtime test lists, public
control traces, all attainable bounded work prefixes, sticky failures, warm-cache
allocator refusal, cold cache allocation ordinals and relevant frozen/Swift
regressions remain required. Code-token equality supports the change; it does
not replace executable evidence. No full product suite is rerun for planning.

Run `python3 -B verification/swift-control-macro-extraction/verify.py` to inspect
the saved proposal packet, or `collect.py` for a fresh isolated preflight.
`finalize.py` retains the exact reconstruction and missing privacy probe steps
for the current saved run. Semantic tests, independent accounting review, root
implementation acceptance, Swift execution, full target, final physical phones,
immutable published FieldLog consumption, signing/store/operational and GA gates
remain pending. No product edit, commit, push, publication or device action was
performed.
