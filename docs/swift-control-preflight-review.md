# Independent Swift control preflight review

Decision: **revision required; preflight is not accepted**. This review binds the
119-file live VM closure
`4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4` and isolated
120-file candidate closure
`6d9e1b3f5aec1bedf2a8dc773a23c1731ee05e094d69d646ab4db8d397381156`.
It reviews source, logical positive accounting and compiler-expanded Frozen
identity only. Root must review a corrected packet before authorizing control
execution. The producer packet and live VM were not modified.

## Required revision: rejected value-pop removal does not latch the frame

P2, `control_operations.rs:7-10`: the Swift `pop` leaf calls
`self.phase.pop_value()` directly. The existing value primitive pops its actual
arena at `value_operations.rs:557`, then propagates a rejected
`remove_live_with_wasi(Live::Values, 1, ...)` at line 560. That path cannot access
or set `FrameCleanupState.live_unreconciled`. The new `control_remove` correctly
sets that field for its control-pop and truncation paths, but condition pops and
saved-result pops bypass it. The outer control wrapper calls `terminal()`, which
changes lifecycle/disposition without setting the latch or checking agreement.

The frozen invocation contract, lines 175-180, explicitly requires a removal
rejection to set the existing latch and return its actual failure. The original
primitive's equality guard makes normal underflow unreachable while counts are
uncorrupted; this is a missing required defensive/fault-injection path, not an
observed normal-execution failure. This review does not claim that debt is
refunded, that the original RuntimeControl loses its sticky failure, or that a
clean completion has been demonstrated.

Keep using the accepted value primitive and preserve its work/effect/failure
order. Add the necessary phase-level reconciliation on its failing return so an
actual after-effect mismatch becomes sticky without a second live debit,
cancellation/work check, failure replacement or repair. Regenerate the exact
source/MIR/typed inventories and layout packet for all added wrapper, scalar,
failure, receiver and lifecycle positions. The revised SC09 plan must exercise
the actual rejected-removal path after root accepts the revised preflight; no
SC operation was executed by this review.

## Source and accounting evidence that passed

The independent audit validated the producer seal, all four source archives and
source manifests, the exact six-file patch, and all 7,520 disjoint positive field
declarations. An independent canonical MIR census checked all 37 selected
functions and closures in each production/unit configuration, including every
declared argument/local/return place and direct source alias. It covers the new
guards, common pop32/close/branch chain, copied controls, typed failures,
Try/residual positions, and private scalar transfers. The 120 separately named
fixed lifecycle roles remain positively reserved; they do not spend old fields.
This is the root-clarified logical authored/canonical unoptimized ownership map,
not a bound on optimizer temporaries, physical machine stacks or total RSS.
Optimized MIR is retained as coverage only; no private compiler core type is
replaced by a guessed alias.

Direct source review confirms one shared compile-time helper/arm source,
private Kind and original Control fields, exactly nine infallible scalar leaves,
one private Kind inventory embedded in the active map, current-frame/sentinel
guards, inclusive decoded control depth, last-fallible control predebit,
immediate control-pop/truncation live removal, original terminal failure and
original completion/cleanup authority. The value-pop latch gap above remains.
No new pin, proof, cache, control arena, lifecycle owner, fetch loop, instruction
selection, fuel/count debit, Ready transition, public invoke, runtime adapter or
budget ceiling is introduced. Producer sealed compiler privacy probes and
actual sibling signature witnesses were reviewed against the source.

Fresh compiler expansions of the archived baseline and candidate reproduce
byte-for-byte equality for Frozen `pop32`, `close_control`, `branch`, and the
entire `run` method, including original bindings, closures, selected target,
caller cursor/fuel/pc boundary and call depth. Macro diagnostic source spans
change as disclosed. The independent isolated patch application exactly
recreates every candidate file.

Fresh independently authored metadata probes ran Swift/all × Debug/Release ×
production/unit, eight configurations. They measure every new field offset,
class size/alignment, the nested private component and all 44 existing containing
storage/drop positions (28 in production). They reproduce:

| Exact bytes | Production | Unit |
| --- | ---: | ---: |
| New permanent | 105,280 | 105,312 |
| New active | 1,153,424 | 2,306,832 |
| Existing permanent enlargement | 30,688 | 48,224 |
| Existing active enlargement | 0 | 0 |
| Header | 1,514,504 | 2,392,040 |
| Frame-operation bound | 2,202,872 | 3,931,704 |
| Original nested value bound, once | 119,576 | 119,576 |

Storage grows from 5,136 to 6,232 bytes, +1,096 per containing position. All
measured positive fields fit their real classes without overlap, including the
private nested component. Frozen's reservation remains 2,912 bytes. Header
construction checked-adds the new permanent amount after the enlarged existing
inventory. Frame preparation/resume use checked `previous + FRAME_OPERATION_BYTES`;
completion consumes the enlarged fixed storage before restoring the same
recorded bound and retains rejection debt. The new controlled slot must be empty.
The corrected arithmetic excludes the separately released constructor bootstrap;
the original collector metadata remains retained. State/combined ceilings stay
134,217,728/268,435,456 bytes. These arithmetic boundaries are not runtime
admission results.

## Reproduction and limits

Run `python3 -B verification/swift-control-preflight-review/review.py` for the
independent audit/compiler/metadata probes and
`python3 -B verification/swift-control-preflight-review/verify.py` for the sealed
offline review audit. The packet retains exact command argv/cwd/environment,
Rust/Cargo/Python/host versions, source manifests/archives, stdout/stderr hashes,
independent Frozen bodies, all metadata outputs, input bindings, review findings
and cleanup. The qualifying independent run used Rust/Cargo 1.99.0,
aarch64-apple-darwin, Python 3.14.8, at source revision
`bc45a20298533b70808607b8228473b1d1efa81d`. Three reviewer harness preparation/
parser attempts are retained separately; none ran a control operation.

The eight metadata programs/tests execute only size/alignment/offset prints and
metadata arithmetic. No control body, SC01-SC12 case, guest, native frontend,
simulator, emulator or physical phone ran. The live VM stayed at its baseline
closure; all owned scratch/build trees were removed and no other project
process was touched. Phones remain disconnected. Behavioral, product, native,
physical, signing, store, customer, operational, FieldLog release and GA
acceptance remain pending.
