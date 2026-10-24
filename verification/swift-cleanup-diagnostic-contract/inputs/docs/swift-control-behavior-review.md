# Independent private Swift control behavior review

The frozen 121-file candidate is recommended for root acceptance of this private
control slice. No product finding remains. This recommendation covers the
accepted caller contract and original-owner control behavior; implementation
acceptance and live application remain root decisions. It grants no Ready,
public invocation, full dispatcher, OTA release or GA qualification.

Review used a fresh isolated baseline and candidate, reconstructed twice:
the 119-file baseline plus `source.patch`, and the accepted 120-file candidate 2
plus `candidate-2-delta.patch`. Both produce closure
`241f7a6037100d29a4d277e1ec176fec55c0380b4283c17120bb8ace045318d5`,
which also matches the frozen implementation archive. The live baseline remains
`4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4`.
Producer seal and receipt hashes are respectively
`b5c7184b31f70c9361d769b5cf568be148985f6662bed56ddf130c9c86ac33b9` and
`42bd019420f161655213f2ae77cf986c7245dd6abae329ad4d45f6acb17e2d47`.
Exact inputs, manifests, commands, tool versions, outputs, independent probe
source, layout instrumentation and observations are retained in
`verification/swift-control-behavior-review/`.

Fresh runtime evidence includes all 46 original frame/value/control tests under
Swift-only/all features, Debug/Release, serial allocator observation; all six
Frozen parity tests in span/all features, Debug/Release; eight library checks;
formatting; and the complete Swift/all-feature library suites. Seven additional
independently authored groups execute in all four Swift configurations. These
are finite cases appended only to the review tree, reusing the real strict ABI
proof/owner fixture scaffold and actual cache/frame construction. There is no
product correction, reference interpreter, manufactured pin or shadow ledger.

The added probes cover nested result branches, a false result If with an inner
branch, Return through an open result loop, signed nonzero loop branches, three
genuinely distinct pinned branch-table depths including unsigned default to the
Function, six explicit branch work prefixes, four cancellation checkpoints,
four genuine after-pop failures, five-depth retained-pin cleanup, every bool
occupancy of the new completion slot, exact/below phase admission, dropped-phase
debt, and nested-frame floor/guard prefixes. A separate cold/warm run of each
new table fixture executes the complete warm interval under first-allocation
refusal with zero allocation/reallocation requests.

Source review confirmed the private helper starts after caller instruction/fuel,
work-1 and pc advancement. The original pin supplies each actual instruction and
the single selected branch depth. The helper neither selects a table target nor
adds another instruction/fuel charge. All function-completing operations return
the completion request; accepted `finish` owns frame result and original pin
release. Correct immediate finish and decoded provenance remain caller duties
until the future dispatcher exists.

The shared bodies retain result-saving/pop/close/push order. Loop branches clear
only the copied result flag and keep the original result-bearing loop Control;
End removes its Control before a later close failure. Function-inclusive depth,
aggregate capacity, last-fallible predebit, frame operand/control floors and
checked decoded end/alternative/depth boundaries retain the accepted behavior.
The independent malformed-floor cases preserve caller locals, operands, control
and pin authorities while asserting the exact already-visible condition-pop or
End-pop prefix. Work/cancellation failures retain those prefixes and the first
failure through later `finish`.

The after-pop hook consumes one real value in the original primitive, then makes
the original removal reject. The wrapper sets the existing mismatch latch and
returns that original failure. Its diagnostic remains Invariant,
`swift_run_live_underflow`, Cleanup, with absent function/offset/resource and the
actual nonzero WASI observation. No invocation cursor is invented. The original
failure and `at_failure` snapshot persist through cancellation, drain, fixed
completion and explicit cleanup reacquisition/`finish`; only the separately
defined `after_cleanup` observation changes. The latch remains set, new frame
and value phases reject, and consuming owner cleanup preserves the retained
owner. This does not close G08 diagnostic coverage.

The independent five-frame cleanup rejects the first and fifth real release
attempts, proves deepest-first visit order and the precise two retained pin
identities, then proves a second drain makes no implicit retry. Only explicit
cleanup reacquisition retries those two authorities. Existing retained guard,
nested restore, outer restore, zero-frame and consuming-owner barriers also
execute in the original suites.

AF22's updated formula adds the accepted control active inventory exactly once
to the existing frame and 119,576-byte nested value envelope. The review checks
an actual owner's exact combined bound and one byte below it; failure attempts
the exact bound without publishing a phase or changing construction charge.
At-bound admission records the same bound. Dropping that phase retains the debt
until explicit completion. `controlled: None` permits clean completion;
`Some(Ok(false))` and `Some(Ok(true))` each retain the complete envelope even
after arenas/pins are clear. The original producer retains the historical AF22
constructor-peak assumption failure; no production algorithm was changed.

Fresh compiler expansion reproduces complete Frozen `pop32`, `close_control`,
`branch` and `run` bodies byte-for-byte after extraction, with the 2,912-byte
reservation unchanged. Fresh uninstrumented production/unit MIR independently
replays all 38 canonical functions per configuration and their 3,752 roles each.
The separate hook recipe reproduces all 400 positive added fields, including
aliases, typed literals, calls, closures and changed reborrows. The hooks reuse
existing disabled-default scalar selectors/counters and add no owning field.

All eight fresh production/unit x Swift/all x Debug/Release metadata
configurations match every producer field offset, size, alignment, containing
inventory and total. The metadata source is archived separately and never used
as runtime behavior evidence.

| Exact logical bytes | Production | Unit |
| --- | ---: | ---: |
| Hook permanent supplement | 0 | 17,144 |
| Hook active supplement | 0 | 224 |
| Control permanent inventory | 105,280 | 122,456 |
| Control active inventory | 1,162,520 | 2,325,256 |
| Execution header | 1,514,504 | 2,409,184 |
| Frame envelope | 2,211,968 | 3,950,128 |
| Actual completion storage | 6,232 | 6,232 |

These are authored canonical logical ownership reservations. They establish no
optimized machine stack, optimizer temporary or RSS bound. State/combined
ceilings remain 128/256 MiB. Library Clippy passes; broad all-target/all-feature
Clippy independently reports the same 26 baseline diagnostic identities, matched
by code, message, path, column and source text. Those baseline failures remain
limitations.

Two review-only authoring/verification issues are retained and excluded from
qualifying evidence. The first six-group probe attempt compared the complete
failure against its pre-cleanup value; two assertions failed because original
`record_cleanup` adds `after_cleanup`. The corrected oracle requires every
original diagnostic/`at_failure` field unchanged and permits only that distinct
observation. Later optional full-library runs shared one Cargo target between
exact/probe source trees, allowing stale probe binaries to run under the exact
tree's cwd. Those four attempts are excluded. All final full-library runs and
seven-group probes use distinct target directories per source tree, with exact
test counts and retained executable hashes. No product source was corrected.

Run `python3 -B verification/swift-control-behavior-review/verify.py` for the
sealed offline audit. Fresh execution starts with `review.py setup`, then
`review.py matrix`, `review.py probes`, and `compiler_review.py metadata` /
`compiler_review.py sources`; the runner refuses a pre-existing scratch root.
Recorded command receipts supply exact argv, environments and source manifests.
The final receipt also records full-library commands, dependency bindings,
tool versions, failed/superseded attempts and cleanup. No dependency was added.

Only the named owned host scratch root was removed after evidence collection.
No simulator/emulator/phone, UI capture, other-project process, publication,
credential or live VM change occurred. Phones remain disconnected. Full Swift
dispatch, initialization/Ready/public invocation, immutable published packages
consumed by FieldLog in a separate repository, native/final physical,
signing/store/customer/operational and GA acceptance remain pending.
