# Independent Swift control candidate 2 preflight review

Recommendation: **accept candidate 2 for source/accounting preflight only**.
SCPR-01 is resolved in the reviewed source. Root owns acceptance and any later
authorization to execute or integrate the overlay. This review grants neither.

The review binds the unchanged live 119-file VM closure
`4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4`, candidate 1
closure `6d9e1b3f5aec1bedf2a8dc773a23c1731ee05e094d69d646ab4db8d397381156`,
candidate 2's 120-file closure
`e1b88be22eb683c40bfe53cd32f5b48d391b475b6097bab233aaf00b5303453d`, and producer
seal SHA-256 `4550cb63df539164c2c58cac12d15215311720ee199d7f1d2bb06b5695d622b1`.
The qualifying producer result is `20261024T065629251176Z`. Candidate 1 and its
revision-required review remain frozen historical evidence.

## Source finding and narrow repair

The common Swift pop leaf now calls `control_pop_value`. This one private phase
method records actual value length, calls the accepted `phase.pop_value()` once,
sets the existing `cleanup.live_unreconciled` latch only when that exact Result
is an error and actual length changed, and returns the same Result.

Direct inspection of the unchanged `primitive_pop` establishes the distinction:
its work debit, live agreement and operand-floor checks precede its single pop;
the only fallible action after that pop is its original
`remove_live_with_wasi(Live::Values, 1, actual_wasi_usage)`. Every shared
condition pop (If, BrIf, BrTable) passes through pop32 and the changed leaf;
shared close's saved-result pop uses that same leaf. Thus every rejected
after-effect removal in this control slice latches the original frame. A
pre-effect error leaves length unchanged. A non-i32 pop32 rejection follows a
successful primitive removal and does not falsely add this latch.

There is no second debit, work/cancellation/deadline/cache check, diagnostic
replacement, count repair, refund or rollback. The original outer wrapper still
terminalizes any error and returns it unchanged. Existing active/completion
guards and drain/reacquisition debt remain the original authority. The ordinary
equality guard prevents this underflow with uncorrupted counts; this is a
source-level resolution of the required defensive path, not an executed fault
test or an observed normal-execution failure.

The independently reproduced candidate 1-to-2 non-inventory patch exactly equals
`behavior-delta.patch`. Of all 120 candidate files, only
`control_operations.rs` changes. The original value primitive, fixed completion
storage, common algorithms, scalar leaves, private Kind and five original
Control fields, cache/control/WASI ownership and budget ceilings remain bound
to the already reviewed source. Fresh compiler expansions reproduce identical
Frozen pop32, close_control, branch and the complete run method, including
bindings, selected-target use, work/effect order and call depth. No fetch loop,
Ready transition, public invoke, runtime adapter or new authority is introduced.

## Independent positive map and compiler measurements

The independent census reads actual canonical MIR declarations at every scope,
arguments, return place, repeated source aliases, direct typed literals and
actual closure capture projections. It compares each four-position ownership
role, exact MIR type and corresponding real inventory declaration. Fresh
uninstrumented production and unit MIR independently reproduce all 38 selected
functions/closures per configuration. The same checks bind the archived
canonical source/MIR map and all 7,640 disjoint positive declarations.

The exact delta is 136 wrapper fields (68 per configuration) minus 16 obsolete
ExecutionOperationPhase reborrow fields at pop32/close_control, for net +120.
The 120 separately occupied lifecycle transfer fields are preserved. No old
value/frame allowance funds the new wrapper. The private scalar inventory is
one actual nested active component, measured once with non-overlapping fields.

Fresh independently instrumented metadata probes run Swift/all features by
Debug/Release by production/unit: eight configurations. They measure every
field's offset, size and alignment, each class, the private nested component,
all 28 production/44 unit existing containing positions and the actual fixed
storage. They reproduce these exact values:

| Bytes | Production | Unit |
| --- | ---: | ---: |
| New permanent | 105,280 | 105,312 |
| New active | 1,162,520 | 2,325,032 |
| Existing permanent enlargement | 30,688 | 48,224 |
| Execution header | 1,514,504 | 2,392,040 |
| Frame-operation bound | 2,211,968 | 3,949,904 |
| Original nested value bound, once | 119,576 | 119,576 |

The actual storage remains 6,232 bytes, +1,096 over baseline at each containing
position. Existing active inventories have no containing-storage enlargement.
Fresh measurements agree with every sealed field's source-bound layout and
the original accepted reservation formulas. Header construction checked-adds
the new permanent amount after enlarged existing types. Frame preparation and
resume checked-add the same recorded frame bound, and completion consumes the
fixed storage before restoration while retaining rejection debt. The separate
constructor bootstrap is excluded from the phase boundary. State/combined
ceilings stay 134,217,728/268,435,456 bytes.

This is the root-clarified logical authored/canonical unoptimized ownership map.
Optimized Release MIR is coverage evidence only. No compiler-private core type
is replaced with a guessed alias. These measurements assert neither exact
physical stack/RSS nor an optimizer-temporary census or runtime admission pass.

## Reproduction and remaining acceptance

Run `python3 -B verification/swift-control-candidate-2-review/verify.py` for the
sealed offline audit. To repeat compiler probes, copy `review.py` and
`supplement.py` into a fresh sibling verification directory and run them in
that order; the sealed harness refuses to overwrite this historical review.
The packet retains commands, tool versions,
source revision/tree bindings, manifests/archives, outputs and hashes,
independent source/type/delta/layout results, preparation attempts and cleanup.
The producer seal, all four source archives/manifests, exact six-file patch and
producer offline verifier pass. Source identity justifies retaining the prior
privacy/authority review; this packet does not present it as a fresh privacy run.

The metadata binaries/tests execute only size/alignment/offset printing and
arithmetic. No control body, SC01–SC12 case, fault behavior, guest, native
frontend, simulator, emulator or physical phone runs. All owned scratch/build
trees are removed; the live VM and both prior packets remain unchanged.

SC09 must still exercise the actual original rejected live-removal call after
the pop through a root-reviewed positively accounted test hook, separately for
condition and saved-result paths, with the specified negative controls. All
SC01–SC12 behavior, allocation/regression, native/final physical, immutable
separate-repository FieldLog release, signing, store, customer, operational and
GA gates remain pending. Phones remain disconnected.
