# Private Swift control integration checkpoint

Root accepted and applied the exact nine-file private control overlay, source
closure `241f7a6037100d29a4d277e1ec176fec55c0380b4283c17120bb8ace045318d5`.
The original frame, control and value owners now execute private block, loop,
if/else, end, branch, branch-table and return helpers. Shared literal macros
preserve the Frozen interpreter's expanded bodies and 2,912-byte reservation.

The producer and independent reviewer each pass four 46-test frame/value/control
runs and four six-test Frozen runs. Review adds seven adversarial groups in all
four configurations and source-isolated full libraries: 168 Swift-only and 197
all-feature tests in Debug and Release. Eight fresh layouts reproduce the exact
production and test accounting; 38 canonical functions per configuration and
the 400-field test-hook supplement are checked. Root reviewed the original-owner
mutations, floors, branch bounds, first failure, cleanup debt and caller boundary,
verified both frozen packets, and passed 46 integrated Release tests plus six
Frozen parity tests from a new owned build directory. That directory was removed.

Control execution assumes the future caller obtains the decoded instruction and
branch target from the retained cache pin, charges fuel/work once, advances the
cursor once, and calls the accepted completion path. There is no production
fetch loop, full dispatcher, Ready transition or public reactor invocation yet.
The tests exercise that caller contract through bounded fixture steps.

Production header reservation is 1,514,504 bytes and the frame-operation envelope
is 2,211,968 bytes; the unchanged nested value envelope is counted once. State
and combined ceilings remain 128MiB and 256MiB. These logical ownership bounds
are not physical-stack or RSS measurements. Library Clippy passes; broad Clippy
still reports the same 26 baseline findings. The original post-pop underflow
keeps its Cleanup diagnostic with absent function/offset/resource and the actual
WASI observation; G08 source-diagnostic qualification remains open.

The review's failed oracle and shared-target build attempts are preserved and
excluded; corrected, source-isolated runs supply the acceptance evidence. See
[root acceptance](../verification/swift-control-behavior-root-review/acceptance.json),
[producer](swift-control-behavior-implementation.md) and
[independent review](swift-control-behavior-review.md).

No native or physical test was run for this host slice. Full Swift execution,
memory and host imports, native joins, immutable published FieldLog consumption,
signing/store/customer/operational qualification and all GA gates remain pending.
