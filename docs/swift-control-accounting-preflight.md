# Swift shared control accounting preflight

This packet supplies an actual, isolated implementation draft and exact logical
ownership accounting for root review. It does not accept the implementation or
execute its control behavior. Live VM source remains the accepted 119-file
closure `4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4`.
The ready overlay has 120 files and closure
`6d9e1b3f5aec1bedf2a8dc773a23c1731ee05e094d69d646ab4db8d397381156`.
No dependency, tracker, gate, root configuration, commit or push is part of this
lane. The original RuntimeControl, cache, proof, pin, WASI and FrameOperationPhase
remain the only authority.

The qualifying packet is
`verification/swift-control-accounting-preflight/results/20261024T062441792011Z/`.
Use `verification/swift-control-accounting-preflight/verify.py` for its offline
manifest/hash/layout audit. `overlay/` and `source.patch` contain the concrete
six-file change; the patch is applied with `patch -p1` from an isolated `vm/`.
Root must review the preflight before applying it to live VM or running SC01–SC12.

## Actual source and shared Frozen identity

The draft shares literal pop32/close/branch methods and Block, Else, End, Br,
BrIf, BrTable and Return bodies through compile-time macros. The original Frozen
methods and the entire `run` method compare byte-for-byte equal after compiler
expansion. This covers its original calls, local bindings, selected target,
closures, check/effect order, caller cursor/fuel/outer-work/pc boundary and call
depth. Frozen has no new runtime adapter or execute helper. Its measured fixed
reservation remains exactly 2,912 bytes. The original inclusive-depth behavior
and all limits are unchanged.

Rustfmt wraps long match expression macros in an extra block. A method-level
`rustfmt::skip` preserves the original Frozen `run` arm AST, while formatting
checks pass. Macro diagnostic source spans now refer to the shared macro source;
those actual spans are retained as provenance. This does not claim identical
compiler-debug file/line locations. The expanded guest cursor and offset
assignments are identical.

Kind and all five Control fields remain private. Exactly nine infallible scalar
leaves are added to the existing Control. One private record-expression macro
supplies Frozen's original literal and the new decoded constructor. Actual
constructor/getter MIR contains Kind temporaries: their typed inventory resides
inside the existing execution owner, where Kind is nameable. Its fields stay
private, it contains no authority and it is embedded once in the active inventory.
The successful sibling probe binds the real control method and all nine leaves
from `value_operations`; it calls none. The original kind/field and downstream
macro/Control access probes are rejected by the compiler.

The private `control_operations` child implements actual current-frame and
Function-sentinel guards, checked control bounds/pc/depth, current operand floors,
else matching, aggregate capacity, inclusive depth, last-fallible predebit,
immediate exact live removal after every mutation, mismatch latching and terminal
first failure. It calls the existing accounted value operations, frame work and
cleanup methods. The new flat `controlled: Option<Result<bool, SwiftRunFailure>>`
slot is checked empty before completion can restore the existing recorded bound.
No fetch loop, instruction selection, fuel/count debit, initialized lifecycle,
Ready transition or public invoke is added. A future caller must supply the real
pinned decoded operation/selected target, exact cursor and precharged boundary,
and call accepted finish immediately after a true result.

## Exact positive ownership map

Root clarified that the accepted active-frame accounting is logical ownership
accounting, not an optimizer machine-stack bound. The bound map therefore uses
actual authored source plus canonical unoptimized production/unit MIR positions.
It retains 7,520 distinct positive fields: 3,700 canonical production, 3,700 unit,
and 120 permanent fixed-result lifecycle roles. Source aliases, argument/return/
caller transfers, closure captures, literals and Try/residual positions remain
separate. Every role is bound to actual source spans and the qualifying source
closure in `bound-inventory-schema.json`; `canonical-function-manifest.json` and the spanned
MIR retain their compiler provenance. No original value/frame position is reused
to pay for the additions, and no padding/rounded allowance is selected.

All eight Swift/all × Debug/Release × production/unit MIR builds succeeded.
Optimized Release MIR is retained as source/call coverage evidence. Inlining
introduces private compiler types such as
`core::num::niche_types::UsizeNoHighBit`; no usize mirror or optimizer alias is
invented, and these optimizer-created temporaries are excluded from the logical
ownership census. This follows root's clarification and the accepted active-frame
review's explicit limitation.

| Exact measured bytes | Production | Unit |
| --- | ---: | ---: |
| New permanent inventory | 105,280 | 105,312 |
| New active inventory, including private scalar transfers | 1,153,424 | 2,306,832 |
| Enlarged existing permanent inventories | +30,688 | +48,224 |
| Enlarged existing active inventories | 0 | 0 |
| Execution header before | 1,378,536 | 2,238,504 |
| Execution header after | 1,514,504 | 2,392,040 |
| Frame-operation bound before | 1,049,448 | 1,624,872 |
| Frame-operation bound after | 2,202,872 | 3,931,704 |
| Unchanged nested value bound, included once | 119,576 | 119,576 |

The storage itself grows 5,136 → 6,232 bytes, exactly +1,096, as does every
containing fixed storage/drop tuple. Four original frozen and 24 production
implementation inventory fields enlarge: 28 × 1,096 = 30,688. Unit has 16 more
containing positions: 44 × 1,096 = 48,224. These changes occur in the existing
types; the new control map does not re-add whole old frame/value inventories.
`all-enlarged-containing-positions.json` names all 44 positions.

Both permanent and active inventories are named concrete structs. Their measured
field offsets, exact sizes and alignment are checked for occupation/non-overlap
in every configuration. PERMANENT is checked-added to the header after the
recomputed existing frame permanent inventory. ACTIVE is checked-added to the
existing frame active plus value bound. Preparation records exactly
`previous + FRAME_OPERATION_BYTES` in the existing cleanup bound; resume uses the
same formula. Existing completion passes the enlarged storage/parts through
fixed completion before restoration. A rejected restore keeps the original debt;
there is no new cleanup owner, State field, ticket, ceiling increase or refund.

## Boundaries and usable budgets

The corrected arithmetic receipt is `corrected-boundary-comparisons.json`.
The raw collector receipt mistakenly added the separately released constructor
bootstrap to its displayed phase boundary. Runtime source was correct throughout;
the audit explicitly corrects the metadata arithmetic rather than rewriting its
historical command receipt. For a recorded previous construction bound P:

- Permanent header: 1,514,503 bytes is one below; 1,514,504 is exact (production).
- Phase admission: P + 2,202,871 is one below; P + 2,202,872 is exact.
- Unit equivalents are header 2,392,039/2,392,040 and phase P + 3,931,703/3,931,704.

These are exact arithmetic boundaries, not claimed runtime admission results;
SC11 will exercise rejection, admission, drop, retained and restore-rejected debt.
The constructor bootstrap remains 1,069,144 production / 1,071,904 unit and ends
before normal frame preparation. It must not be counted again as P.

The unchanged public state ceiling is 134,217,728 and combined ceiling is
268,435,456. Production header plus active frame bound is 3,717,376 bytes;
unit is 6,323,744. Subtracting only those claims leaves 264,718,080 and 262,111,712
combined bytes respectively. Other source/metadata/cache/WASI/arena reservations
still consume their own actual amounts, so this arithmetic is not a promise that
every maximum-sized module fits. The header alone leaves 132,703,224 production
state bytes. The positive accounting adds 1,289,392 production bytes over the
accepted header-plus-frame claims, without changing any user budget ceiling.

## Observed verification and limits

Rust/Cargo 1.99.0 on aarch64-apple-darwin performed 41 qualifying commands,
including eight default/span/Swift/all library checks, formatting, two Frozen
expansions, eight source MIR builds and sixteen baseline/candidate metadata
runs. Eight unit metadata tests and eight production metadata binaries ran only
size/offset arithmetic, prints and uncalled pointer binding. Debug/Release and
Swift/all layouts agree for each production/unit mode. Eight further metadata runs measure the private nested inventory component
offset/size/alignment. Four additional privacy commands prove actual sibling callability, all five original private fields,
private Kind and downstream rejection. Full logs, argv/cwd/tool versions, source
manifests, outputs and SHA-256 bindings are retained. The two failed collector
attempts and earlier rejected contract evidence remain intact.

No control method, guest, native frontend, simulator, emulator or physical phone
ran in this lane. Owned scratch/build directories are removed and bulky compiler
evidence is losslessly compressed with uncompressed digest bindings. Other
projects' processes and data are untouched. Phones remain disconnected and final
physical checks deferred. No GA or product implementation gate is passed.

## Next bounded ownership and acceptance

After root accepts source/accounting/expansion, assign one fresh-context Sol 6.1
xhigh implementation lane the six overlay files plus a new
`control_operations_tests.rs` and its dedicated control verification packet.
Common macros, scalar leaves and fixed completion storage remain one integration
unit. That lane applies the exact overlay, implements finite SC01–SC12 tables
through real validated proofs/original pins and runs the contract's serial
Swift/all × Debug/Release control, frame/value and allocation matrix. The six
Frozen control extraction tests run under span/all × Debug/Release. Recheck
formatting and default/span/Swift/all library checks, inspect baseline Clippy
limitations without silently accepting new findings, and collect exact runtime
boundary and retained-cleanup evidence. Root owns independent review and any
coherent validated commit/push; no other active lane's files are swept in.

SC01–SC12 and all behavior regressions are pending. Full instruction dispatch,
calls/hosts/memory execution, initialized/Ready/public invocation, complete Swift
support, separate-repository immutable FieldLog packages, native/device, signing,
store/customer/operational and GA qualification remain pending product scope.
