# Independent cold-start coordinator review

No actionable defect was found in the frozen candidate's five new production
files or their reviewed composition with the private store, signals and concrete
attempt. This is a bounded experimental source/lifecycle review, not release or
GA qualification.

The candidate is `2026-10-23-candidate-1`, source manifest SHA256
`68177f0a8488386138c8e9f2a92c7ea7d4c788caf74b7053c8f648179f95c078`.
The immutable owner final receipt SHA256 is
`32d31ae27e2665dd92ba6d4e0fcfed59a9402ff18bc2a64004518c7d5db69661`.
`receipt.json` binds the exact candidate, production file hashes, original review
source/commands/logs/state files, owner evidence manifest and review findings.

## Source review

The reviewed design is `docs/capability-durable-updater-api-design.md`.

- The public facade accepts installed material and signed download bytes. Its core,
  initializer, store, verifier, selection, consumed input and concrete attempt are
  private/internal. There is no public executable/validator/adapter ingress and no
  public post-enable invocation API in this slice. The trusted configuration has
  no accepting callback. The existing owner public compile negatives and
  cross-compiles were inspected as existing evidence, not rerun by this reviewer.
- Control admission uses the synchronous lock before owned data snapshots, worker
  calls or task captures. Ordinary work, cancellation and notification work are
  bounded. The closed latch rejects new work independently of private actor or
  native cleanup progress. Startup is one-shot. Ordinary tails repoke the same
  notification stream when a notification encountered busy work.
- Local stop is published to signals before stopping concrete resources or closing
  store admission. First cause remains immutable; checked bridge failure has a
  separate first-failure field. Worker checks current operation and authoritative
  signal state after each awaited startup step. A terminal latch prevents health
  publication and reconciliation cannot request a live fallback after effects.
- A successful disabled startup is followed by durable effects intent, native
  enable, then monotonic observation. Earned health retains the active attempt for
  later failure accounting. Store commit entry is synchronous and cannot promise
  rollback after close: actual/uncertain durable outcomes must survive separately
  from the closed execution phase.
- The notification consumer's closure retains a weak worker box, signals stream
  and generation. Its temporary strong worker reference ends before the next
  stream wait. Store reservation retention does not provide a strong back edge to
  the cold-start worker or concrete resources. One close job joins observation
  consumer and timer cancellation, then ordinary tails, then closes store I/O and
  begins reservation retirement. Native/adapter retirement remains independently
  counted. Fallback joins the prior attempt before constructing a replacement.

## Original executable probes

`ColdStartCommitCloseProbe.swift` reuses the root review's independently signed
TESTONLY fixture scaffold (itself credited to transition candidate3). The race
assertions and gates here are original. It links only the frozen owner's
`libMixerCapabilityActivationColdStart.dylib`, with no additional native archive
or old Activation product. `nm -gU` and `otool -L` evidence records this topology.

Each case starts a real signed Wasm guest, completes the real disabled-startup /
effects-intent / enable flow, and supplies synthetic trusted embedding milestones.
The process-local monotonic clock, store, verifier, native runtime and concrete
lifecycle are real. A bounded synchronous fault hook holds one filesystem boundary;
it never accepts replacement bytes or substitutes execution/validation.

1. Hold the actual health transaction before state-file fsync. Start 24 concurrent
   public close calls. Closed admission and possible effects remain observable
   while filesystem I/O is held; none of the close waiters or the process slot can
   retire early. After release, all 24 close callers complete, actual entered
   health remains stored, the durable attempt is closed as `effects_closed`, and
   no healthy guest is republished. Cancellation/close does not count as a trap.
2. Hold the actual health transaction after state rename, then inject an error
   after 24 concurrent close calls have stopped admission. Releasing the hold
   produces a poisoned owner with actual health and active effects linkage still
   on disk. Cold reopen records `unknown_interruption_after_effects`, clears the
   incomplete attempt/stage, and preserves actual health and sequence high-water.

Both original cases passed against the candidate's Debug, Release and Swift TSan
products (six executions, 144 concurrent close calls). Every mode verifies the
frozen export and workspace candidate input hashes before and after the run,
including production and test inputs at the time of that run. The parent later
identified a separate hosted Swift 6.2.4 test-expression complexity issue; any
subsequent test-only repair is outside this frozen review candidate.

Exact outer commands, run from the repository root:

```text
python3 verification/capability-cold-start-runtime-review/run.py --mode debug
python3 verification/capability-cold-start-runtime-review/run.py --mode release
python3 verification/capability-cold-start-runtime-review/run.py --mode tsan
python3 verification/capability-cold-start-runtime-review/seal.py
```

The driver intentionally refuses to overwrite an existing mode output directory.
All compiler commands, tool versions, durations, outputs, exit codes, source
hashes, artifact hashes and durable states are retained in the per-mode receipts.
No failed probe experiment occurred in this lane.

## Limits

The review did not rerun the owner's full 95-function matrix or 13-function derived
matrix, nor the root's separate timer/restart/admission/cancel-open flow probes.
The owner's existing test and opacity/cross-compile receipts are bound as original
evidence without claiming those are newly independent executions. Source tracing
and these two held boundaries do not exhaust scheduler interleavings or prove
allocator/RSS or Swift task destruction. Swift TSan excludes uninstrumented Rust
and system frameworks. The probes do not reproduce indefinitely hung native I/O.

No physical iOS/Android tools or runs were attempted. Phones remain disconnected
and device checks pending. There was no publication, store action, credential
change, customer message or production source mutation. Real UI milestones,
FieldLog consumption of separately published immutable packages, operational
reconciliation and accountable GA review remain separate pending gates.
