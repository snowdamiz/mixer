# Independent review of the private frozen control macro extraction

This review concerns only the bounded W08 prerequisite that moves the existing
private `SpanInstance::pop32`, `close_control`, and `branch` method definitions
into one literal macro. It does not qualify Swift control execution, active Swift
frames, a new interpreter loop, native targets, FieldLog, OTA publication, or GA.
The final artifact hashes and independent replay result below bind the frozen
implementation packet. No blocking product defect remains within this scope.

## Source and accounting review

The two-file product change preserves each original private inherent method
signature and literal body. `SpanInstance` remains the owner. Its fields,
`Frame`, `Control`, budget types, dispatch call sites, work/fuel operations,
reservation calculation, and public API remain unchanged. The feature-gated
`pub(super)` macro re-export adds no external entry point; no callback, trait
adapter, function pointer, wrapper receiver, runtime macro object, or additional
fallible call boundary is introduced.

The macro still calls the original owner operations directly. `pop32` calls
`pop` before checking its type. `close_control` saves its result by popping,
checks height, charges work, truncates and observes, then pushes the saved value.
`branch` resolves the current frame and checked target, copies the selected
control, charges branch work, suppresses the copied loop result flag, closes,
truncates controls, writes the target pc, observes, and returns function status.
The `End` dispatch's own work charge and control removal remain outside the
macro and precede closing. No helper owns frame or pin release.

The 26-group map describes the same receiver, argument, `Option`, `Result`,
closure, copied control, saved value, Try branch/residual, and source/return/
caller positions. All nine Try sites stay at their original inherent-method
boundaries. The retained compiler expansion and 66-row layout evidence support
the zero-addition delta and unchanged 2,912-byte frozen reservation. This review
does not prove the complete historical baseline memory inventory, repurpose
padding or numeric/Swift-value capacity, or import the rejected adapter's
additional transfer positions.

## Executable test review

The six public tests contain 15 bounded successful fixtures with independently
specified expected results, plus an unreachable trap. They cover block,
function, and loop branches with and without results; both `br_if` paths;
chosen, default, and negative `br_table` selection; both `if` arms; normal
`End`; and a nested function. Success is asserted as well as comparing
baseline/candidate traces, so equal erroneous traces alone cannot satisfy the
ordinary parity case.

Work budgets include every integer credit from zero through one above each
fixture's successful total, and the unreachable fixture's terminal-error total;
fuel budgets include zero through one above its instruction total. These
fixtures have no bulk-memory fuel, so instruction count is a sufficient upper
bound for this bounded fuel sweep. Failure traces
include the complete failure/cursor, usage, cache accounting, construction and
cold allocation measurements. Every invocation error is re-invoked with the
first allocation denied: the exact first failure, usage, and cache state must
remain unchanged with zero allocation requests. The archived baseline comparison
is necessary evidence for the individual failure prefixes because the public
tests do not separately hardcode every intermediate failure record.

The allocator test warms each involved function, then denies the first request
and asserts zero requests, reallocations, and requested-byte peak delta. It
also checks unchanged state/cache reservations. Cold decode allocations are
counted separately; every observed ordinal is refused and separately cancelled,
with exact failure kinds and live-byte cleanup. This establishes bounded warm
dispatch evidence, rather than a universal no-allocation claim for arbitrary
programs. The observer's own opaque allocation probes check refusal,
cross-thread ownership transfer, unrelated background activity, and ledger
lifetime handling.

The cancellation/limits test explicitly asserts pre-invocation cancellation,
runtime aggregate live-value/live-control peaks and one-below failures, recursive
call-depth and cache-pin limits, and pin/frame cleanup. Its low per-function
operand/control profile limits are rejected by `validate_spans`; the emitted
`control_validation_ceiling` rows are validation evidence. They are not runtime
execution of the per-frame guards. Cancellation at cold allocation ordinals
and helper entry is deterministic. The tests make no timing-race or arbitrary
mid-instruction cancellation guarantee.

The two derived private probes append a test-only inline module to an archived
copy of the original execution owner file. Normal validation/cache construction
and `enter` acquire the real frames and pins. Deliberately invalid height,
selector type, and depth cases are labelled separately from public execution.
They directly assert result consumption before height/type invariants; all
attainable close/branch work refusal stages; truncation before a failed saved
push; `End` removal before close failure, including its stale observer state;
loop target retention and copied result suppression; block/function removal;
pc choice; caller-control exclusion after real recursive entry; and original
pin retention until explicit cleanup. These tests intentionally bypass public
terminal unwinding to observe helper partial states. They authorize no new
runtime access or malformed public module execution.

## Evidence corrections and limits

The producer retained an initial public-test failure caused by treating a
validation rejection as a runtime path, then corrected the assertion and label.
The first complete collector later stopped when its Swift-value test selector
expected nine identities but the runtime binary listed twelve. The qualifying
packet must preserve those failures and bind the corrected exact identities.
Initial private overlays also changed an archived library alias and added a
probe file; those attempts are excluded from the qualifying mod.rs-only probe
scope. A copied proposal-only comment in product source was corrected with
root coordination; the macro body and immutable proposal remain unchanged.

The independent review's first collector incorrectly compared the methods'
different indentation levels as source changes. Its failed receipt remains at
`verification/swift-control-macro-independent-review/results/20261024T032407728701Z/receipt.json`.
The corrected comparison ignores line indentation; the retained compiler
pretty-printed comparison still requires byte-for-byte equality. This was a
review-collector failure, not a product failure. The successful first selected
replay is retained separately, then rebound after the producer's final
unreachable-prefix refinement.

All new execution is headless macOS host Rust. Computer use, screenshots,
simulator/emulator/device discovery, native apps, and native runtime tests stay
paused. Phones remain disconnected. Physical qualification, immutable separately
published FieldLog packages, signing/store/customer/operational evidence, and
accountable GA review remain pending.

## Final independent receipt

The independent final result is
`verification/swift-control-macro-independent-review/results/20261024T032720299561Z/receipt.json`,
status **independent-host-review-passed-bounded-extraction**, SHA-256
`8c83a226d555f20bc56b8ea5aaf7d6531ffc82053accded9ebbbc521c4d10ee3`.
It binds the producer's final schema-2 receipt at
`verification/swift-control-macro-implementation/results/20261024T032530904964Z/receipt.json`
(SHA-256 `6690d34dcbe6ae6008552cc7ce3fe3d21de3827174bb81cdd9a53dd847268606`).
The final candidate closure has 117 files and SHA-256
`5d1da3fedb28804ed8ddc271ce78461b58b06b8475b5cc8eb411226626bc199f`.
Observed HEAD was `a8f203e7d4a46441b3a09391d2eb29a12c9c10c5`; the VM change
was uncommitted at review. Every source closure is checked before and after
the fresh host commands.

The review independently hashed retained command outputs, all 44 qualifying
binary identities and runtime lists, source archives/manifests, and the 229
immutable proposal-seal bindings. It compared all 795 control trace rows in
span/all-features × Debug/Release. It also checked unchanged regression runtime
identities, numerical traces, the two corrected private probes' 17 rows in each
configuration, twelve selected Swift-value identities in each of four
configurations, and the ordinary compilation/lint/format evidence. The initial
extra-file private overlays and superseded public traces are explicitly
excluded from final qualification.

Fresh independent all-features Release builds first replayed public parity,
work/fuel prefixes, warm allocator refusal/cold ordinals, cancellation/limits,
and both corrected private probes against the prior frozen closure. All six
selected tests passed. After only the integration test's prefix input changed,
the final review proved the source delta and replayed the changed prefix test
from the final candidate archive. It matched the final baseline exactly,
including 16 unreachable-prefix rows spanning `WorkExhausted`, `FuelExhausted`,
and `GuestTrap`. The unchanged earlier selected replays are bound by their own
receipt and manifests; they are not presented as execution of the refined test.

The final fresh prefix binary SHA-256 is
`0f866bdd5a631264b57973711d2f501f0cb9b087de5d939f7889926f25a3ea47`.
Tools were Rust/Cargo 1.99.0 on aarch64-apple-darwin and Python 3.14.8.
Diagnostic bootstrap was absent from all fresh and qualifying product builds.

The exact independent final command was:

```sh
python3 -B verification/swift-control-macro-independent-review/review_prefix_refinement.py verification/swift-control-macro-implementation/results/20261024T032530904964Z/receipt.json verification/swift-control-macro-independent-review/results/20261024T032417584381Z/receipt.json
```

The saved independent receipt can be checked without rerunning executable code:

```sh
python3 -B verification/swift-control-macro-independent-review/verify_saved.py verification/swift-control-macro-independent-review/results/20261024T032720299561Z/receipt.json
```

This supports acceptance of this bounded frozen extraction by root. It retains
the zero-addition and environment limits above, and makes no full Swift, native,
historical baseline-memory completeness, release, or GA claim.
