# Standalone Swift reactor WASI adapter evidence

The accepted contract is `docs/swift-wasi-adapter-design.md`. This independently
authored implementation owns only `vm/src/experimental_wasi/`,
`vm/tests/swift_wasi*.rs`, and this directory. Root supplied the nondefault
`experimental-swift-wasi` feature/module wiring. No validator, executor, cache,
production admission, guest routing, FFI, dependency, release identity, or native
capability wrapper was changed by this lane. The installed official WASI header,
versioned Preview1 specification, retained reactor descriptor inventory, Rust
standard library and native platform APIs were the implementation inputs. No
external implementation, fixture, test suite, runtime, or library was imported.

`python3 verification/swift-wasi/collect.py` passed all 15 commands against one
unchanged sampled VM source manifest, with exact command/output/tool information
in `evidence/2026-10-23/receipt.json` and numbered logs. Observed revision was
`35a9a36c8837fd2dd3e491419b7965b6307cd6b9` with the dirty file listing retained.
The manifest SHA-256 is
`bf4f14d446646ea0025892ca2472f45393b76b2f6dbad8e1d3f38a4042d97be4`;
the official SDK header SHA-256 is
`8cf2859277ea2fc984780a00048686955805fd8a00c7be1d8f916105becf0174`.
Tools were rustc/cargo 1.99.0, Clippy 0.1.99, Python 3.14.8, and Apple Clang
21.0.0 on aarch64 macOS. Tool stdout in the receipt is authoritative.

Both Debug and Release passed 8 private service/fault unit tests, 9 integration
tests, and 1 allocator test (18 tests per profile). Focused Clippy with
`-D warnings`, owned-source rustfmt checking, and the two compiled C ABI probes
also passed. The Preview1 probe compiles for wasm32-wasip1 against the installed
official header, checking iovec/fdstat size and offsets, clock IDs, rights and
errno values. The host probe type-checks the Darwin FFI signatures, clock IDs and
timespec layout against the installed platform SDK.

The tests cover all 34 exact names/signatures, every wrong scalar parameter type,
wrong arity/results/modules/names, all declared denial branches, fixed argv and
empty environment, context-local close state, zero-padded sink metadata, two
capture sinks and combined capacity, zero-length/end pointers, unsigned/OOB/alias
ranges, iovec counts/aggregate sizes, the exact 65,536-byte payload boundary,
every budget, sticky exit/failures, cancellation at every bounded copy checkpoint,
deadline expiration, clock conversion overflow, partial service failure before
and after a successful random chunk, and unchanged outputs on failure. Real
Darwin getentropy, clock_gettime and clock_getres calls passed separately from
private deterministic fault services. No actual secure random bytes are logged;
these are OS-source smoke checks, not cryptographic-quality measurements.

The allocator probe observed four construction allocations, exactly 262,144
requested heap bytes at default limits, plus a 1,328-byte production context
(including the fixed 64-iovec array). Its reported current/peak reservation is
263,472 bytes. Each construction allocation ordinal was failed independently
with no retained allocation. Measured random, clock, argv, fdstat, write, close,
cancellation and sticky-failure dispatch paths allocated zero Rust heap bytes
under an allocator that rejects the next allocation. Reserved capacity never
grows. This measures allocator requests and fixed object state, not OS internals,
stack-frame overhead, shared caller cancellation storage, RSS, or full VM memory.

Accounting is cumulative for the context lifetime. Calls and argument work are
charged before authority/range/effect checks. Operation-specific range/iovec work
and complete transfer charges precede copies or services. Each logical payload
or scalar-output transfer is bounded separately; fd_write can accept a 65,536-byte
payload while separately charging its four-byte nwritten output. Transfer work is
conservatively eight credits per byte, covering initialization, service/staging,
backup, commit, capture initialization/copy and worst-case rollback; range and
iovec scans are additional. Failed work is not refunded. Buffers reserve capacity
at construction and initialize only bounded charged chunks on demand. Log
capacity returns NOSPC without a visible append or guest-output write. Failure
counts include non-success errno outcomes and the first terminal failure/exit;
sticky follow-up dispatch does no work or service and leaves counters unchanged.

Precedence is terminal state, exact typed args, call/argument-work budgets,
cancellation/deadline and memory extent, then service grant/fd authority, relevant
ranges/alias checks and operation-specific budgets, then effects. FD/path denials
do not dereference their invalid pointer arguments. Output commits check between
256-byte chunks; cancellation/deadline after any partial guest copy rolls back
from bounded owned backup without requiring remaining work budget. Capture bytes
become visible only after the final check, when logical length and nwritten
commit together. There is no callback or synchronous host reentry seam.

Deadline is cooperative. A platform call, bounded copy/zero-fill chunk or failure
rollback cannot be preempted. Darwin getentropy requests are at most 256 bytes;
Linux/Android getrandom uses GRND_NONBLOCK and treats short/interrupted/failed
calls as explicit failure with no retry/fallback. Platform implementations are
limited to the named 64-bit Darwin/Linux/Android ABIs; other targets return
NOTSUP. Only aarch64 macOS was compiled/run in this receipt. Linux, Android/iOS
compilation/linkage, physical devices, signing, stores and operational reviewers
remain pending. No device was queried or asked to reconnect.

`evidence/early-allocator-probe-failure.log` retains the initial original test
meter failure: it incorrectly assumed unrelated test-harness allocations were
freed on their allocating thread. The corrected probe uses a fixed eight-slot
allocation registry restricted to the observed constructor interval. The final
Debug/Release receipt measures this corrected probe. This was a test-meter defect,
not an adapter allocation or service failure.

This adapter cannot execute or qualify the full Swift reactor. Complete sealed
import/resource admission, span VM integration, actual initialization plus corpus
parity, sustained use, product/mobile behavior, artifact size, immutable published
FieldLog consumer packages, physical platforms and all GA gates remain open.
No production publication, customer messaging, credential operation or commit
was performed by this lane.
