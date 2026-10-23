# Bounded Swift reactor WASI services

Root accepted this isolated adapter for implementation on 2026-10-23. It supplies
the next W08 import boundary, not validation/admission/execution of the reactor.
The full Swift reactor and size/product/mobile acceptance remain open. Do not
change frozen imports, published profiles, release identities or C/native routes.

Use the official Preview1 ABI, including the installed SDK's `wasi/api.h`, and
the [versioned WASI specification](https://github.com/WebAssembly/WASI/blob/a2b96e81c0586125cc4dc79a5be0b78d9a059925/legacy/preview1/docs.md).
The retained reactor descriptor inventory is
`compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/descriptors.json`.
Its exact 34 names/signatures are the complete selected adapter vocabulary;
uninvoked declarations are not omitted. Independently implement from those
specifications. No external runtime, libc implementation, tests or fixtures.

## Boundary

Root exposes a nondefault `experimental-swift-wasi` Rust module. It has no
dependency on the existing eager interpreter, no feature-selected admission,
guest export, FFI or native capability wrapper. Implement an exact `WasiFunction`
enum with a resolver checking module bytes, name bytes and complete scalar
signature. Unknown modules, names, parameter/result types or extra results reject.
Enum variants do not authorize a VM to call them; a future sealed span policy and
owned execution integration must make that decision separately.

`WasiContext::new(WasiGrants, WasiBudget, Cancellation)` requires explicit native
service grants. Grant fields are secure random, realtime, monotonic, stdout and
stderr; defaults deny all. Caller-supplied clocks, randomness, callbacks, raw file
descriptors, filesystem paths and host environment are not public construction
inputs. The dispatcher receives a selected enum, exact typed args and bounded
mutable guest memory; it validates that memory. Private typed host services get
only bounded scratch and typed clock requests, never guest memory or pointers.
Deterministic/failure services may exist only in unit tests.

The invocation result distinguishes WASI errno from terminal guest exit and
terminal adapter failures. `proc_exit` records the u32 exit code and becomes a
sticky terminal outcome; it never exits the host or returns success to the guest.
Allocation, budget, cancellation, deadline and internal invariant failures are
also sticky and allocation-free. Subsequent dispatch cannot perform services.
No invocation silently refills any resource budget.

## Limits and accounting

`WasiBudget` is narrowing-only: maximum/default calls32,768, cumulative transfer
4 MiB, work32,000,000 credits, one transfer65,536 bytes, iovecs64, total retained
log bytes65,536, and lifetime deadline30,000 milliseconds. Zero grants/budgets
deny or exhaust explicitly; overflow/widening rejects before allocation.

Preallocate fallible exact bounded scratch and stdout/stderr capture buffers.
Their capacities, fixed context state and any scratch overlap are reported as
current/peak reservations. Two log buffers may each reserve the chosen log cap,
but combined committed length must not exceed it. No per-call growing allocation,
unbounded retry, process environment copy or filesystem enumeration is allowed.
Work covers argument/range/iovec scans, checked copies, zero fill and service
bytes. Charge checked counts before work/effects. Usage retains calls, work,
transfers, random bytes, log bytes, failures and reservations; counters do not
claim RSS or cryptographic quality tests. Do not record actual secure random
bytes in verification receipts.

Cancellation/deadline checks occur before calls, bounded copy chunks and actual
services, and after services before committing output. Deadline is cooperative;
document any non-preemptible platform-call limitation, never claim hard realtime.
No synchronous host reentry is exposed. Output buffer aliasing is rejected before
services where writes could overlap input metadata/payload or another output.
All pointers/lengths are unsigned wasm32 with checked addition/multiplication;
zero-length ranges must still lie within the memory's inclusive end.

## Exact behavior

- Fixed argv is one UTF8 string `mixer` plus NUL. Environment is empty. Sizes and
  pointer arrays use little-endian wasm32. Validate all output spans and reject
  overlap with INVAL before any write; no host argv/environment is exposed.
- `random_get` requires the random grant, validates its complete range and budget,
  fills owned bounded scratch with the OS cryptographically secure source, then
  copies only after service success and cancellation/deadline recheck. No PRNG,
  constant fallback, partial guest write or fabricated success. Prefer bounded
  nonblocking OS APIs where available; unsupported platforms fail explicitly.
- Clock functions accept realtime0/monotonic1 only and require the matching grant.
  Query actual platform clock time/resolution; encode u64 nanoseconds with checked
  conversion. CPU clocks are denied, unknown IDs invalid. Unsupported/failed clock
  services return explicit errors without writing output; do not invent resolution.
- Fds1/2 are bounded capture sinks when stdout/stderr is granted. `fd_write`
  validates all iovecs, aggregate transfer and `nwritten`, rejects output aliasing,
  copies into owned scratch, and appends exactly once if total log capacity fits.
  Public borrowed stdout/stderr views permit later native diagnostics. There is
  no automatic print/file/network effect. Full capture returns NOSPC with zero
  progress and no append; valid zero-byte writes may succeed. This is a specified
  capture sink, not proof of platform logging delivery.
- `fd_fdstat_get` on an open granted sink returns a zero-padded 24-byte structure:
  generic/unknown filetype0, flags0, rightsBase FD_WRITE only, inheriting rights0.
  It must not copy Node's host pipe flags/rights. `fd_close` closes only that
  context's logical sink; repeated/unknown/denied fd access returns BADF. No host
  process fd is closed. Unavailable fd metadata/read/seek/flags/sync operations
  return NOTCAPABLE on known open sinks and BADF on other fds, with no mutation.
- No filesystem preopens exist. Both prestat operations always return BADF.
  Every path operation returns BADF for its nonexistent directory authority.
  These denied operations need not dereference guest pointers and produce no
  output, filesystem/network action or successful no-op.
- `poll_oneoff` returns NOTSUP and never waits. There are no sockets or process
  creation. `proc_exit` follows the terminal rule above. Every declared operation
  has one tested outcome; no wildcard success or call-count-based behavior.

Return errno values from the official Preview1 definitions, not host errno
numbers. OOB ranges return FAULT; overlapping output/input ranges return INVAL.
Freeze and test precedence: terminal state, exact args/budgets/cancellation,
service grant or fd authority, then relevant ranges, then effect. Denied operations
can reject without touching invalid pointers. All error paths leave guest output
and captures unchanged unless an explicitly recorded earlier call committed them.

## Ownership and acceptance

Adapter lane owns new `vm/src/experimental_wasi/**`,
`vm/tests/swift_wasi*.rs`, `verification/swift-wasi/**` only. Root owns feature/lib
wiring and this contract; other lanes own span execution and Android transport.
Do not alter validator/cache/executor or add production admission. Coordinate
any required public seam before dependent edits.

Execute original tests for all34 descriptors (including malformed signatures),
every denial, FD close state, argv/env layout, real OS random/clocks, exact capture,
large/overflow/OOB/zero/alias iovecs, unsigned boundaries, denial before pointer
access, partial service failures, cancellation, deadline, every resource bound,
allocation failure and no output/effect on failure. Compare ABI layout with the
official header. Test deterministic services only for fault paths; distinguish
them from real secure-service smoke. Run Debug/Release and focused lint. Record
tools, exact sources/digests/commands/output and source isolation. No downloads or
physical devices. Passing this adapter cannot qualify full Swift or any GA gate.
