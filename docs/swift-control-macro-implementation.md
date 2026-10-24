# Frozen literal control source extraction

The bounded W08 source extraction is implemented and its host packet passes.
Root implementation acceptance remains separate. The single private macro emits
`SpanInstance::pop32`, `close_control` and `branch` directly on their original
inherent owner. It does not implement Swift control execution, active frames,
entry/return/unwind, a dispatcher, native execution or a GA gate. The binding
product scope remains `mixer-product-plan.md`.

## Product change and unchanged contract

`vm/src/experimental/execution/borrowed.rs` now contains the frozen no-argument
`frozen_control_methods` macro and feature-gated `pub(super)` re-export. The
original span-enabled `impl SpanInstance` invokes it once at the old `pop32`
position; the old three definitions are removed. Signatures, private visibility,
literal method bodies, direct owner work/pop/push/observe calls, and their error,
trap, effect and work order are unchanged. No callsite, runtime wrapper, trait,
adapter, owner, field, allocation, reservation, layout, budget, dependency, public
API or Swift invocation is added.

The proposal's introductory comment incorrectly described its file as an unused
overlay. Root authorized a product-only wording correction to “Private literal
control methods, emitted on the original frozen owner.” The immutable proposal
and rejection records remain unchanged. Rustfmt removes only the blank lines
left by the method removal. The offline verifier checks the exact appended
macro bytes including that one comment correction and the original owner body
with only the literal method replacement/removals and whitespace normalization.

The accepted baseline is revision `6341a5633b98f8c698c1234e533d0387cc01e81a`
with 116-file VM closure
`96b16d4886b9218e132a2a1255c0ce4e66c60879ed7bb5f1ea1185b0ca08b8c7`.
The final test-inclusive candidate has 117 files and closure
`5d1da3fedb28804ed8ddc271ce78461b58b06b8475b5cc8eb411226626bc199f`.
Only the two implementation files differ between baseline and candidate;
the new integration test is byte-identical in both test-inclusive builds.

The frozen 26-group, nine-Try-site zero-addition transient map still applies.
The prior compiler-expanded method equality, 66-row production/unit layout
comparison across 16 binaries, and three compiler privacy rejections remain
sealed history. They measured the unchanged fixed formula as **2,912 bytes**.
This implementation changes no formula, field or boundary and introduces zero
runtime objects or failure transfer positions. It does not claim a fresh proof
that the entire historical baseline memory inventory is complete. The rejected
fallible adapter's additional Result boundaries are absent.

## Executable host evidence

The primary receipt is
`verification/swift-control-macro-implementation/results/20261024T032530904964Z/receipt.json`.
It contains eight independently built final public test binaries: baseline and
candidate in span-only/all-features × Debug/Release. Every binary's complete
`--list` contains exactly the same six expected test identities, and all six
execute successfully. There are **795 identical control observation rows per
configuration**, covering values, complete failure/trap identity and cursor,
usage, cache usage, state reservations and requested allocation observations.

| New runtime test | Meaningful behavior and failure coverage |
| --- | --- |
| `shared_control_public_parity_trace` | Fifteen hand-authored success fixtures: block/loop/function with and without results, End results, both br_if conditions, both if arms, chosen/default/negative br_table selectors, and a real nested call; explicit unreachable trap. Known values are asserted independently of parity. |
| `shared_control_close_partial_effects` | Public End/result-close/conditional-pop paths at every attainable bounded work refusal. The separate actual-owner probes below expose the private partial states hidden by public terminal cleanup. |
| `shared_control_branch_targets_and_frame_boundary` | Loop retention, function/block exits, table target choices and nested callee/caller continuation through real public calls. Private target pc/control and out-of-frame checks are in the probe packet. |
| `shared_control_work_and_fuel_prefixes` | Each of the fifteen success fixtures plus the unreachable trap runs with every integer work budget from zero through observed terminal work plus one, and fuel from zero through terminal instruction count plus one: 581 prefix runs per binary. Sticky errors repeat with identical result, unchanged usage/cache, and zero allocation requests under first-allocation refusal. |
| `shared_control_warm_dispatch_allocation_free` | Every involved function is warmed by the actual successful call. Repeating each fixture while refusing the first allocation observes zero requests, reallocations and requested-byte growth, with unchanged state/cache reservations. Cold decode allocation requests are separately measured; every observed ordinal is refused and cancelled, retaining the original cache error/cursor and releasing all pins and temporary ownership. |
| `shared_control_cancellation_and_limits` | Pre-invocation cancellation for all fixtures; real recursive calls at exact aggregate value/control peaks and one below; call-depth and cache-pin limits with terminal cleanup. Per-function operand and function-inclusive control ceilings are explicit validator rejections, because invalid functions never reach public execution. |

`bounded-prefix-coverage.json` enumerates every observed fixture and its work/fuel
budget lists. Warm refusal is limited to those control fixtures and their warmed
functions. Cold decode is explicitly outside the zero-allocation claim. No
blanket feature or allocation claim follows from these selected tests.

The inherited final source packet is
`results/20261024T032202022153Z/receipt.json`. It supplies:

- The unchanged Frozen `span_execution` (16 tests),
  `span_execution_allocations` (one test) and `span_numeric_extraction` (one test)
  in all four configurations. Exact runtime identities are preserved. Numeric
  observations also match baseline byte-for-byte (455 rows per configuration).
- Two private-order tests on baseline/candidate × all four configurations,
  using only an appended inline test module in archived `mod.rs`. Original
  cache construction and `enter` create every frame and pin. The live product
  has no test hook. These tests check result-pop-before-height/work, all close
  refusal stages and truncate-before-push, consumed non-i32 pop32, real End's
  fixed credit/control removal before close failure, loop result-flag copying,
  target pc/control truncation, all branch refusal stages, actual callee control
  boundaries, and cancellation at each helper's first existing charged boundary.
- Twelve accepted Swift-value regression identities in Swift-only/all-features
  × Debug/Release. These remain the previously accepted zero-frame value route.
- Eight ordinary default/span/Swift/all-feature × Debug/Release library checks,
  format verification, and all-features library Clippy with warnings denied.
  The refined final archived candidate also passes a fresh format check.

Private probes deliberately mutate invalid height/type/depth states or inspect
an owner before public terminal cleanup. They are labelled derived invariant
probes. They do not present invalid bytecode as public execution, fabricate
frames/pins, or establish new authority. The Block probes use original dispatch
to enter the Block, then inspect the original owner after a bounded work
refusal; they do not claim public recovery after a terminal error. Every probe
explicitly runs the original cleanup and checks all pins are released.

Only `tests/span_control_extraction.rs` changed for the final trap-prefix
refinement. The inherited regression/unit/library targets do not compile or
import that standalone integration test. Exact source manifests prove the sole
delta; 24 retained compiler dependency files independently bind inherited
binaries and exclude the changed integration source. Consequently unaffected
regressions, private probes and checks are inherited explicitly rather than
rerunning a full suite. The older packet itself inherits unchanged original
baseline regression outputs from `results/20261024T031953637944Z/`.

All qualifying commands retain argv, cwd, start/end time, source checks before
and after, stdout/stderr and hashes. Test binaries retain identities, hashes,
sizes and exact complete/selected runtime lists. Source manifests and archives,
runner inputs and compiler dependency records are preserved. Cargo/rustc
**1.99.0** on **aarch64-apple-darwin** and Python **3.14.8** were observed.
Ordinary builds/tests do not enable `RUSTC_BOOTSTRAP`. Existing minimal-feature
warnings are retained; the scoped all-feature Clippy command passes.

## First failures, boundaries and verification

Exploratory host setup initially lacked Cargo on PATH; invoking Cargo by absolute
path also lacked rustc on its inherited PATH. The runner now prepends the actual
installed rustup bin directory. Initial integration compilation assumed `Limits`
was Copy; it is Clone. The retained first compile log records this error. The
first runtime run correctly rejected an operand ceiling during validation;
those cases were corrected to explicit validator rejection checks. The five
other tests passed in that failed run. These exploratory commands were not
source-guarded qualification runs.

The first isolated collector completed its public matrix but stopped when its
Swift-value count assertion expected nine identities and the real binary listed
twelve. No tests were removed; the successful packet executes all twelve. That
collector also used a separate archived probe file and archived library alias,
which exceeded the intended single-file overlay. Its derived probe runs remain
preserved and are explicitly excluded from qualifying evidence. A correction
attempt retained a stale fixture include and failed compilation; the final
single-file overlay has its own small hand-authored module encoding and passes.
A later offline coverage parser initially matched `validation_work_used` when
looking for `work_used`; the final explicit field matcher verifies the complete
581-prefix list against the raw runtime observations. No failed attempt is
relabeled as a pass.

Run `python3 -B verification/swift-control-macro-implementation/verify.py` for
an offline hash/source/identity/parity inspection. It performs no guest or native
runtime execution and leaves the proposal/rejection histories unchanged.
`collect.py` preserves the earlier complete final packet procedure;
`refine_trap.py` preserves the bounded final test refinement procedure.
Independent review has its own separately owned packet and does not become
root acceptance automatically.

Computer use, screen capture, native apps, simulator/emulator tests and physical
phone discovery/runs remained paused. No device action, publication, customer
message, credential change, commit or push occurred in this lane. Native/final
physical acceptance, shared Swift control/active frames, immutable external
FieldLog consumption, signing/store/customer/operational evidence and all
unsatisfied GA gates remain pending.
