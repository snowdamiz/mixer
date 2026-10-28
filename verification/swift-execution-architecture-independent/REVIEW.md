# Independent architecture candidate review

Decision: **changes required before dispatch**. The reviewed source candidate
remains uncompiled, with zero new finite/harness/full runtime attempts. The
architecture comparison is a reasonable bounded hypothesis, but the current
driver does not enforce two of its stated failure and telemetry conditions.

Reviewed producer seal:
`b20440be09778e3209de5c1e6dae941e0580b8737fe28ed35be53777e3292f70`.
The complete 26-file, 309,831-byte sealed inventory was verified. Regenerated
control and dense source identities match
`af58b29a605384f3ac3ac2d3a3b513533e0da4f140f0e5d2c22807eb78bcb2f7` and
`3db26064abc07200219b62c9637850f50868f470bb2d0ca7598223131c2033d4`.

## Blocking findings

**R1 — Stop on unexpected allocation capacity before admitting the next arm
(P1).** `campaign.py:205-209` accepts every failure with an allowed broad kind,
including `Allocation`. The bound control source's
`RuntimeControl::exact_capacity_with_wasi` emits exactly that kind with code
`swift_run_unexpected_capacity`, resource `ExactCapacity`, and a non-null
`observed_capacity` when the allocator returns a capacity different from the
admitted request. This is the explicitly forbidden unexpected-capacity condition
in `DECISION.md`, rather than an ordinary resource-budget exhaustion. With clean
cleanup, `validate_result` accepts it as `resource-limit-diagnostic` and
`run` proceeds to the next prepared arm.

The independent reproduction mutates the original historical log as a **pure
synthetic fixture**, re-parses it through `base.classify`, and calls
`validate_result`. The unexpected-capacity failure shape is accepted, telemetry
is `valid`, and the original final failure remains preserved. No VM execution is
represented by this fixture. See `unexpected-capacity-reproduction.json`.

Reject this resource/code/observed-capacity defect explicitly before admitting an
ordinary resource result. Add a negative that traverses the real classifier and
validator and proves the second full attempt is not admitted. Preserve the
failure and consuming cleanup evidence; no retry or refund is implied. The same
review should distinguish structural ticket/identity accounting failures from
ordinary selected resource ceilings rather than relying only on `kind`.

**R2 — Enforce original-instruction fuel consistency in prefix observations
(P2).** `campaign.py:229-251` checks unsigned values, selected upper bounds,
threshold order, monotonic individual counters, and final domination, but does
not enforce their required relationship. `instruction_with_wasi` charges one
fuel before every original instruction increment; bulk operations only add
fuel. Therefore `instruction_fuel - instructions` must start nonnegative and
never decrease through the prefix records and final owner usage.

Two independent synthetic cases are accepted by both `prefix_records` and
`validate_prefix`: 25,000,000 instructions with zero fuel; and 25,000,000 followed
by 50,000,000 instructions while fuel remains at 100,000,000. The latter passes
even a simple per-record `fuel >= instructions` check. See
`impossible-prefix-reproduction.json`. Reject both absolute and delta
inconsistency, including the final join, and retain the distinction between
observer validity and the unchanged eleven-field oracle.

## Source review observations

- Both arms use byte-identical original harness/lifecycle, complete profile and
  prefix observer. Only the expected copied cache hooks, Swift cache and Swift
  cache tests differ between algorithms. The two frozen generic IR/token test
  bodies are unchanged apart from visibility.
- Dense hits validate the actual slot and function identity. Missing mappings
  and structural mutations audit every occupied resident's reverse mapping.
  Publication follows all fallible index work; new entries cannot become
  executable through a map-only authorization. The bitmap preserves lowest-free
  selection, live-count checks, actual free-record checks and original
  owner/slot/nonce validation. Release keeps cleanup available after a terminal
  owner failure. No concrete incorrect-code authorization or token-publication
  defect was found by source inspection.
- The new index payload is reserved before allocation and destroyed before its
  header reservation ends. Added owner/scratch fields and separate conservative
  inventories are present in the permanent, construction and operation shapes.
  This is a source observation; exact compiled sizes and the simultaneous
  256MiB envelope are still pending.
- The inherited release path intentionally performs no new work debit so it can
  clean up a terminal owner. The added release-mask validation and set also have
  no separate debit; the source's five acquisition credits name acquisition
  checks and the acquisition mask write. Treat reported cache credits as the
  declared metering model, not a complete instruction or CPU-operation count.
  If the contract intends the new release operations to be separately counted,
  account for them in an explicit acquisition precharge without making cleanup
  fallible on exhausted work. This is an accounting clarification, not an
  independently established execution blocker.
- The new finite cases invoke actual cache-owner controls and independently walk
  map-to-slot and bitmap-to-record agreement. Constructor work-prefix coverage
  grows from 5,085 to 84,702 cases; it remains finite. The prior complete finite
  command took about 1.45 seconds, but that is not a timing receipt for this new
  suite. The unchanged 90-second watchdog must decide its actual fit.
- Both complete optimized builds, selected finite suites, harness controls,
  compiled geometry and zero-cleanup receipts precede any full attempt. Nine
  preparation commands must close before either full attempt. Each full attempt
  is persisted before spawn, and the total remains two full attempts and eleven
  commands without refund or retry. The inherited helper pre-admits per-command
  time and retains unresolved custody. Independent mocked negatives confirmed
  nonpositive PIDs, placeholder exit codes and missing group-absence proof keep
  custody unresolved.
- The 2,485-second pessimistic command/cleanup/receipt sum fits the 2,700-second
  driver allowance, 46-minute command step and 55-minute job. The source
  comparison does not prove either full arm completes within those bounds.

## Verification and limits

`python3 -B verification/swift-execution-architecture-independent/review.py`
ran under Python 3.14.8 against revision
`56ff14c925168284761c5aca4f0bd4129cf3c995`. It completed 51 independent checks
and reran all 32 supplied pure tests. The two findings are accepted-invalid
negative fixtures; passing these review checks means the defects were reproduced,
not that the candidate passed acceptance. Outputs and hashes are retained in
this packet. Process-spawn, wait4 and killpg operations were guarded in the pure
review. All owned source-inspection copies and temporary fixtures were removed.

The producer and frozen historical packets were not changed. No compiler, guest,
container, PostgreSQL, native runtime, UI, capture, CI, publication or held actor
probe ran. UnitA, broad hosted/database work and custody actors 20745, 20770,
20780, 20817, 20842, 20851 and 20866 remain held; local FieldLog compiler work
remains held. No commit, push or dispatch occurred. Compiled geometry,
runtime semantics, two-corpus equality, complete cleanup, performance, mobile,
published FieldLog, signed OTA and GA remain unverified by this review. Root
retains delivery and dispatch selection after the findings are corrected and
the revised packet is independently checked.
