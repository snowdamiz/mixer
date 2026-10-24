# Swift control accounting candidate 2

Candidate 2 is an isolated source/accounting preflight repair for SCPR-01.
Root review is pending. No control operation, SC01–SC12 case, fault behavior,
guest, live VM integration, simulator, emulator or physical-phone test is
executed or accepted by this packet.

The binding contract remains `swift-control-invocation-contract.md` and root's
`verification/swift-control-invocation-root-review/{contract.json,accounting-scope-interpretation.json}`.
The accepted 119-file live VM closure remains
`4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4`.
Candidate 1's 120-file closure remains
`6d9e1b3f5aec1bedf2a8dc773a23c1731ee05e094d69d646ab4db8d397381156`.
Its qualifying producer result `20261024T062441792011Z`, verifier/seal and the
independent review's `frozen.json`, finding and seal remain unchanged historical
authority. Candidate 2's 120-file closure is
`e1b88be22eb683c40bfe53cd32f5b48d391b475b6097bab233aaf00b5303453d`.
Candidate 2 lives only in
`verification/swift-control-accounting-candidate-2/overlay/`; it does not replace
those packets or the live `vm/` tree.

## Narrow repair and unchanged authority

The Swift `pop` leaf now calls private `FrameOperationPhase::control_pop_value`.
The wrapper snapshots actual `values.len()`, invokes accepted
`phase.pop_value()` once, and sets the existing
`cleanup.live_unreconciled` latch when that exact Result is an error and the
actual length changed. It then returns that same Result. The existing outer
control wrapper calls `terminal()` as before. No error is copied into a replacement
diagnostic and no count, value, work or reservation is repaired or refunded.

Source review of the unchanged value primitive establishes why length change
identifies this path: work, value/live agreement and operand-floor checks precede
the single actual pop; its only fallible action after that effect is the original
`remove_live_with_wasi(Live::Values, 1, actual_wasi_usage)`. The wrapper performs
no second removal, admission, work, cancellation, deadline or cache check. Errors
before the pop leave length unchanged. A successful pop followed by pop32's
non-i32 failure already removed its live count and does not need this latch.
The normal equality guard makes underflow unreachable with ordinary uncorrupted
counts; the repair fulfills the required defensive path, without claiming an
observed normal-execution failure or an executed fault test.

`behavior-delta.patch` shows the complete non-inventory change from candidate 1.
The original value algorithm and its file remain byte-identical to the live
baseline. Frozen `pop32`, `close_control`, `branch` and the complete `run` remain
compiler-expanded identical, including call depth and work/effect ordering.
Kind and all five original Control fields stay private. The nine existing scalar
leaves, actual original phase/control/cache/WASI authority, fixed completion slot,
cleanup/restore debt and ceilings remain the contracted design. There is no new
runtime adapter, owner, fetch loop, instruction-selection/fuel responsibility,
Ready transition or public invocation.

## Complete positive map and measured bounds

The regenerated map contains 7,640 distinct positive fields: 3,760 canonical
production fields, 3,760 canonical unit fields and the same 120 separately named
fixed lifecycle transfer fields. Each configuration covers all 38 selected
functions/closures. The new wrapper contributes 68 actual typed positions in
each configuration, including its receiver and reborrows, actual length/scalars,
original Result/return and error-test paths. The old direct pop32 and
close_control call sites each lose one now-absent ExecutionOperationPhase
reborrow, with four positions per local per configuration. Thus the exact map
adds 136 wrapper fields and removes 16 obsolete call-site fields, a net +120.
These are changes to actual authored/canonical positions; no accepted nested
value/frame field or old allowance pays for the wrapper.

Every canonical field is rebound to qualifying unoptimized spanned MIR, source
span and candidate tree digest. The source lifecycle fields remain positively
occupied. The original private Kind inventory is one concrete nested active
component, measured separately exactly once. Optimized Release MIR is source/call
coverage only. No private compiler-core alias, optimizer-temporary bound,
physical-stack bound or total-RSS claim is made.

| Exact measured bytes | Production | Unit |
| --- | ---: | ---: |
| New permanent inventory | 105,280 | 105,312 |
| New active inventory, including private nested scalar positions | 1,162,520 | 2,325,032 |
| Active increase over candidate 1 | 9,096 | 18,200 |
| Enlarged existing permanent inventories | +30,688 | +48,224 |
| Enlarged existing active inventories | 0 | 0 |
| Execution header | 1,514,504 | 2,392,040 |
| Frame-operation bound | 2,211,968 | 3,949,904 |
| Header plus frame bound | 3,726,472 | 6,341,944 |
| Unchanged nested value bound, included once | 119,576 | 119,576 |

The header exact/below boundaries are 1,514,504/1,514,503 production and
2,392,040/2,392,039 unit. For an already recorded previous bound P, phase
exact/below boundaries are P + 2,211,968/P + 2,211,967 production and
P + 3,949,904/P + 3,949,903 unit.

All original enlarged containing positions are enumerated again: 28 production,
44 unit, each enlarged by the same 1,096-byte controlled slot. Existing
permanent inventories grow by 30,688/48,224 bytes; existing active inventories
have no containing-storage enlargement. All typed field offsets, sizes and
alignments, including the nested private component, are measured for
Swift/all × Debug/Release × production/unit and checked for occupation and
non-overlap. Candidate/base archives and the six-file source patch reproduce
all 120 candidate files exactly.

The permanent header formula checked-adds the new permanent inventory after
recomputing enlarged existing types. The frame formula checked-adds the new
active inventory to the existing frame inventory plus the unchanged 119,576-byte
nested value bound, once. Preparation/resume retain checked
`previous + FRAME_OPERATION_BYTES`; completion consumes enlarged concrete fixed
storage before restoration, with the same rejection debt. The separately released
constructor bootstrap is excluded from the phase-admission boundary. The sealed
arithmetic receipt gives exact/below boundaries; these are not executed runtime
admission tests. State and combined ceilings remain 134,217,728 and 268,435,456.
Other existing reservations still consume their actual amounts.

## Fresh verification and exact limits

The packet retains its bootstrap source/map commands; all eight library checks
(default/span/Swift/all × Debug/Release); baseline/candidate Frozen expansions;
eight uninstrumented source MIR builds; sixteen baseline/candidate metadata
runs; eight private-nested-component measurements; actual sibling callability,
private Kind/all-five-fields rejection and downstream rejection; exact patch
application; tool versions, revision/tree digests, argv/cwd, stdout/stderr,
archives/manifests and cleanup. Metadata programs/tests execute only
size/alignment/offset prints, arithmetic and uncalled signature bindings.
Failed attempts, if any, remain under this candidate's own result/attempt paths.
Owned build scratch is removed; compressed compiler evidence retains exact
uncompressed digest bindings. No other project's processes/data are touched.
Phones remain disconnected and final physical acceptance deferred.

Run `python3 -B verification/swift-control-accounting-candidate-2/verify.py` for
the sealed offline audit. `qualifying.json` names the fresh result directory.
`bootstrap.py`, `collect.py`, `postprocess.py`, `audit.py` and `nested_layout.py`
retain reproduction sources; rerunning producers creates new evidence requiring
a fresh seal, not permission to overwrite historical acceptance.

## Revised SC09 requirement after root accepts this preflight

The future behavioral lane must test the real original removal rejection,
separately for a condition pop (If/BrIf/BrTable) and a saved-result pop in shared
close. A root-reviewed, positively accounted test-only hook must intervene after
the primitive's equality guard and actual pop, before its original
`remove_live_with_wasi`, to force that real call's underflow. Returning a synthetic
Err from a wrapper, corrupting counts before the equality guard, or testing only
control truncation cannot witness SCPR-01. No such hook or test is implemented or
executed here.

Each case must assert exactly one actual value disappeared, the original
live-underflow failure/cursor/actual WASI usage survives, existing cleanup latch
is true, the frame terminalizes, and later operation/completion cannot clear or
repair the mismatch. Exercise accepted drain/reacquisition and retained debt
under existing cancellation/work/restore failure requirements. Also retain
negative controls: pre-effect work/guard/floor failures leave actual length
unchanged; successful removal followed by non-i32 pop32 failure has no false
unreconciled-pop latch. Preserve all original SC09 checked pc/depth/height,
owner-pairing, active-count, unsupported-operation and first-failure cases.

Root must independently review and accept this source/accounting/expansion
packet before any control execution or live overlay application. SC01–SC12 and
all required behavior/allocation/regression matrices remain pending. Full Swift
execution, separate-repository immutable FieldLog package dogfood, native/final
physical, signing, store/customer/operational and GA gates remain pending.
