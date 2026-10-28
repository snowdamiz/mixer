# VM cancellation CI correction proposal

This packet freezes a test-only correction at source revision
`d87ce0a1b05a9ad42cd2118bbf2ccc5491499663`. Independent review and all Rust
format/compiler/test/lint execution remain pending. Only root integrates and
delivers this slice. No engine source, public contract, dependency, budget,
status/gate metadata or other lane's source was edited.

## Observed failure and limits of the diagnosis

Ordinary VM CI run `40631875922`, job `122629888437`, reported actual
`ExecutionFailureKind::Cache` where the cancellation test expected `Cancelled`
at the old `vm/tests/span_execution.rs:685`. The authoritative saved tail is
`verification/github-delivery-dependency-model/job-122629888437-tail.log`.
It does not print `ExecutionFailure.code`, `cache_failure`, counters or the
nested cache kind. The exact underlying remote error is therefore unproven.

The removed fixture spawned an infinite-loop invocation, slept for one
millisecond and cancelled its token. That delay established neither guest
progress nor the phase in which cancellation was observed. The instance used
the normal finite fuel (1,000,000), execution work (64,000,000) and cache work
(64,000,000) budgets. Sleeping longer or increasing those budgets would retain
the scheduling race.

`SpanInstance::cache_error` in `vm/src/experimental/execution/mod.rs:538` wraps
every cache error in `ExecutionFailureKind::Cache` and preserves its nested
details. `FunctionCache` checks cancellation while pinning/decoding. Existing
`vm/tests/span_execution_allocations.rs` already requires the nested cache kind
when cancellation lands in that phase. These facts establish an allowed source
path for a `Cache` wrapper; they do not prove that was the remote cause. This
proposal neither remaps cache failures nor accepts a wider set of outcomes.

The executor contract, `docs/span-execution-design.md`, deliberately excludes
arbitrary host callbacks. The existing capability guest test can synchronize
on its separately observable mailbox state; `SpanInstance` exposes no such
in-flight state. Adding a production callback or changing the token solely to
synchronize this regression would expand the correction unnecessarily.

## Frozen correction

The existing admission/preconstruction/predispatch test retains its strict
assertions. Its scheduler-dependent suffix becomes a separate deterministic
mid-invocation test at `vm/tests/span_execution.rs:682`.

The new test reuses the existing independently authored allocation observer
from `vm/tests/common/allocation_observer.rs`. It wraps the system allocator for
this test binary. Ownership and cancellation arming are thread-local; ordinary
allocations in other harness threads cannot consume the cancellation ordinal.
The observer has no test functions of its own, so this binary has one armed
observer lane. Its fault-denial ordinal is zero: allocation refusal is disabled.

The fixture warms and releases the decoded function before constructing the
instance. During invocation, the guest stores the value 7, then requests growth
from one page to two. Warm-cache scalar execution does not allocate; the first
armed allocation is the actual growth allocation. The observer cancels that
instance's existing token synchronously at that allocation. The real growth
zero-fill checkpoint then observes cancellation while a guest frame owns a
cache pin.

The test requires all of the following:

- Exact top-level `Cancelled`, static code `cancelled`, no nested cache error,
  and the full error printed if those assertions fail.
- Exactly five dispatched guest instructions and exactly one armed allocation.
- The earlier store survives, while memory remains one page and the growth
  state reservation rolls back to its pre-invocation value.
- A subsequent invocation returns the identical terminal failure.
- All frames, values, controls and cache pins are released through the existing
  `clean` assertions.

This proves mid-invocation cooperative cancellation at memory growth without
depending on thread scheduling. It does not claim a new external-thread latency
measurement, an arbitrary instruction-boundary cancellation probe or a new
infinite-loop throughput result. Existing allocation-ordinal cache cancellation
tests remain intact.

## Evidence and proposed execution

`receipt.json` records the source revision/tree, observed tool versions, source
hashes, saved command outputs and the successful targeted whitespace diff check.
`source-manifest.sha256` covers only the enumerated inspected source, contract
and CI evidence; its digest is not a digest of other active lanes or the full
repository. `proposed-change.stdout` is the frozen test diff.

`validation-plan.json` provides exact argv commands with a cumulative maximum
of 55 seconds: tool versions, targeted formatting, all 17 span tests in Debug
and Release with normal harness concurrency, and focused test-target lint. Root
should run that plan only after independent review. Timeouts or missing offline
artifacts remain incomplete evidence, never a pass. The ordinary remote VM job
must also pass after integration and authorized delivery.

This lane ran no Cargo/compiler/VM tests, started no native runtime or capture
processes, attempted no global process inventory and performed no Git mutation.
Phones, computer use, capture and simulator/emulator runtime remain paused.
This packet supplies no OTA, device, FieldLog or GA qualification.
