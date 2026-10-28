# Independent correction review

Decision: **source-qualified accept**. R1 and R2 are corrected in the frozen
runner, and this review found no additional blocker to root selecting the
already bounded remote comparison. This is source and pure-runner acceptance;
the candidate has still not been compiled or run by this review.

The reviewed correction seal is
`4efa21ab9e7bf43cec647c760bdacf6c3e5b2be944976240ec186c738370a6d2`
(25 files, 349,259 bytes). Its immutable 64-file readset digest is
`8fa269fba7e152771339bc80f03ad31371fce245bef74cebb108d88d41a8fa59`.
Both were checked before and after this review, as were the complete original
comparison and original independent-review packets. No predecessor changed.

## R1: actual campaign stop is enforced

The generated `RuntimeControl::exact_capacity_with_wasi` uses failure kind
`Allocation`, code `swift_run_unexpected_capacity`, resource `ExactCapacity`,
and a non-null observed capacity. The corrected validator rejects any of those
three identifying fields before it assigns an ordinary resource outcome.
`TicketInventory` is emitted as `ResourceExhausted`, so its new resource/code
rejection is necessary; the actual owner-exhaustion producer uses `Invariant`,
and its explicit identity rejection also prevents broad-kind misclassification.

The independent harness replaces only child execution, source preparation and
prepared-source identity checks. It runs the real `run`, `execute_profile`,
attempt reservation, command guard, historical-log classifier, result validator
and prefix validator. All nine mocked preparation commands pass through the
real command guard. It does not use the producer's orchestration test helper.

Nine negative campaigns cover the complete exact-capacity failure, each of its
three individual identities, both ticket identities, both owner identities,
and an invariant failure. Each spends one mocked full attempt, closes exactly
ten mocked commands, retains the original final failure and zero-resource
cleanup evidence, and stops without admitting the dense arm. The persisted
attempt count is checked inside the mocked child call, proving admission was
recorded before execution. The classifier's telemetry is valid in these
fixtures, so invalid telemetry is not masking the intended rejection.

An ordinary allocation control still closes both diagnostic arms in two mocked
attempts and eleven commands, with no feasibility milestone claimed. A separate
missing-group-absence control stops with unresolved custody, only nine closed
commands, and retained scratch. The review removes that scratch only after the
pure mock has completed; no real process or unresolved actor exists in it.
Detailed fixtures and persisted campaign/result records are retained in
`campaign-evidence/`.

## R2: fuel consistency is checked across the complete observed lifetime

The unchanged source charges one fuel before incrementing the original
instruction count. Nonnegative bulk charges can increase the difference between
fuel and instructions; no legitimate interval may reduce it. The correction
checks unsigned 64-bit counters, cumulative fuel at least instructions,
monotonic counters and fuel delta at least instruction delta. It starts at zero,
rechecks every prefix, and includes the final usage even when no threshold was
reached.

The independent 21-case prefix matrix rejects both original accepted-invalid
examples, an impossible final interval, an impossible empty-prefix final
record, final regressions, and negative, boolean, oversized, fractional, null
and string final counters. Direct helper negatives additionally check both
monotonicity failures. The four reviewed logical defects remain accepted by the
original runner, confirming the differential. Valid bulk excess, fuel charged
before an unsuccessful instruction increment, and a zero-instruction owner
remain admissible. `prefix-evidence.json` retains the cases and dispositions.
These observations remain separate from the eleven-field guest oracle.

## Preserved source and bounds

The six generator/Rust inputs are byte-identical to the original packet.
Independent regeneration reproduces both original source closure hashes:

- Control: `af58b29a605384f3ac3ac2d3a3b513533e0da4f140f0e5d2c22807eb78bcb2f7`.
- Dense: `3db26064abc07200219b62c9637850f50868f470bb2d0ca7598223131c2033d4`.

The comparison still uses the same 53,777,114-byte Wasm input, original harness,
two corpora, eleven-field oracle, 256 residents, 64 pins, 160,000-byte dense map
and eight-byte bitmap. Its shared experimental profile remains 1B lifetime fuel,
8B execution work, 768M cache work and 600,000ms cumulative Runtime/WASI duration,
with no reset and a hard 256MiB combined envelope. Both optimized builds, finite
suites, harness controls, compiled geometry and zero-cleanup receipts precede
every full attempt. Two full attempts, eleven total commands, the existing
watchdogs, pre-admitted cleanup margin, no retry/refund and fail-closed custody
remain. The corrected workflow retains the original concurrency group and
invokes the corrected sibling's driver and tests.

The unchanged source algorithm is covered by the original independent review;
this correction introduces no engine edits. Its remaining timing/accounting
observations are still limitations, not new source blockers. Cache credit shares
are not CPU shares, and finite calibration is not a production-default change.

## Evidence and limits

`python3 -B verification/swift-execution-architecture-correction-independent/review.py`
passed under Python 3.14.8: 412 checks including complete before/after byte
bindings, all 38 supplied pure tests, 11 independent mocked campaign cases and
21 prefix cases. `review.stdout`, `review.stderr`, `checks.json`, source
excerpts, fixtures and `receipt.json` record the run. An audit hook denied real
process creation, sockets, signals and writes outside this packet; explicit
guards denied process waits and OS process helpers. All owned pure scratch was
removed.

No compiler, guest, finite/harness runtime, native runtime, simulator/emulator,
UI, screenshot, CI dispatch, process inventory or held-group probe ran. No
canonical/global metadata, Git state, predecessor packet or unrelated lane was
edited. UnitA, broad hosted/PostgreSQL work, local FieldLog compiler work and
held groups 20745, 20770, 20780, 20817, 20842, 20851 and 20866 remain untouched.

Actual Rust compilation, the 90-second finite-suite fit, compiled simultaneous
geometry, runtime semantics, both complete corpus results, real cleanup and
custody, performance, native/mobile evidence, published FieldLog, signed OTA and
GA remain pending. Root retains delivery and runtime dispatch selection. This
review adds no runtime attempts or authorization to reuse prior attempts.
