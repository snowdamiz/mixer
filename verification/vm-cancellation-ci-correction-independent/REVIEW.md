# Source review: deterministic test correction is suitable for validation

No blocking source finding in `vm/tests/span_execution.rs`, SHA
`8412a9914c6d4698fd9e0d9f71506101aafe80d218e56c389d1a95047d377321`.
Recommend root's selected bounded local formatting check and existing ordinary
remote VM CI. Both full-feature Debug and Release commands at
`.github/workflows/verify.yml:372` onward include this integration binary; the
separate ignored-case commands remain intact. The producer's six-command local
proposal is source-reviewed but unexecuted and is not newly selected. This
review ran no Cargo, rustfmt, compiler, lint or tests.

The patch preserves all admission/preconstruction/predispatch assertions. It
replaces only the one-millisecond/infinite-loop suffix with a separate test,
increasing the binary from 16 to 17 declared tests. The exact proposed diff
matches the live diff and the recorded historical before hash. A narrow Git
comparison of `vm/src` and the shared observer is empty: no engine behavior,
cache-error classification, budget, cancellation token or observer implementation
changed.

The new coverage is meaningfully mid-invocation. Before arming, it decodes/pins
and releases the function and constructs the instance. The executor already
preallocates value/control/frame stacks. The guest then executes `i32.const 0`,
`i32.const 7`, `i32.store`, `i32.const 1`, and `memory.grow`. The first armed
allocation cancels that instance's existing token synchronously. FAIL=0 permits
allocation, rather than injecting refusal. The real growth zero-fill checkpoint
observes the token before committing replacement memory.

Strict `Cancelled`, code `cancelled`, no nested cache failure, exactly five
instructions and one observed allocation reject cancellation before guest
progress or during decode. The preserved store proves earlier guest mutation;
one page and unchanged state reservation reject committed growth or rollback
failure. Identical sticky error and zero frames/values/controls/cache pins check
terminal cleanup. A future executor allocation before growth would make these
phase assertions fail; it would not silently move this test's checkpoint.

Observer isolation is appropriate for normal harness concurrency. ACTIVE,
OWNED, cancellation ordinal and token are thread-local. `request()` returns
before incrementing CALLS on other threads. Only this new test arms the observer
in this binary; helper facilities have no test registrations. Its guards are
thread-bound, and finishing/dropping disarms cancellation and denial. The
unchanged ledger serializes registration/removal, removes before freeing, and
retains old ownership across realloc failure. The new binary-wide allocator
wrapper still requires real Debug/Release/default-concurrency validation; source
reasoning does not establish that those commands pass.

The saved remote failure reports Cache versus Cancelled at old line 685. Its
failing-test section does not print the nested cache error, code or counters.
Earlier unrelated test traces in the same log do print other error records;
they do not diagnose this failure. Cache pin/decode cancellation is a real
source path with existing nested-kind tests, but neither cancellation nor
exhaustion is established as the remote cause. The correction accepts no wider
error set and changes no product behavior; call it a deterministic test
correction, not a diagnosed product-bug fix.

This five-instruction fixture covers a cooperative growth checkpoint. It does
not newly qualify external-thread latency, arbitrary instruction-boundary or
compute-bound long-loop cancellation. The design document's broader long-
execution matrix is not made complete by this test. Preserve that limit even
if ordinary CI passes.

Root should record the actual formatter/tool/source/output receipt and then
observe the new test in both ordinary remote configurations, preserving any
failure with full ExecutionFailure diagnostics. No local Cargo target, cleanup
controller or local Debug/Release/lint result is claimed. The proposed local
timeouts sum to 55 seconds; they confer no unobserved pass.

Thirty-three source/packet/evidence inputs were checked before and after with
equal hashes. Two reviewer-only check attempts are preserved: a newline mistake
in the source-function comparison, and an overbroad search across unrelated CI
traces. The corrected source review passed. No runtime or test was replayed.
No product/dependency/budget/metadata edit, commit, push, native/UI/capture/device
action or process inventory occurred. No build artifact was created; no cleanup
is owed. Remote CI, native/device, FieldLog, OTA and GA are not passed here.
