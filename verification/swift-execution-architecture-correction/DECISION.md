# Architecture runner correction

This sibling packet corrects independent-review findings R1 and R2 in the
source-ready two-arm experiment. The original comparison and independent review
remain byte-exact. No new compilation, finite/harness execution, full attempt,
commit, push or dispatch occurred. Root retains delivery and dispatch selection
after independent review of this correction.

The immutable comparison decision and source contract are
`../swift-execution-architecture-comparison/DECISION.md`, sealed by
`b20440be09778e3209de5c1e6dae941e0580b8737fe28ed35be53777e3292f70`.
The independent review is
`../swift-execution-architecture-independent/REVIEW.md`, sealed by
`c1ecb422803c2e43dc69206b28e6f51e2b023b9b8fab13054e20ecc7976a7486`.
Both seals are checked by this runner before source preparation.

## Narrow correction

R1: after verifying the original failure and consuming cleanup, the runner
rejects `swift_run_unexpected_capacity`, resource `ExactCapacity`, or any non-null
`observed_capacity`, before admitting an ordinary resource result. Each identity
is sufficient to stop. It also rejects structural `TicketInventory` and
`OwnerIdentity` resources and their producer codes. The frozen control emits
`swift_run_ticket_inventory` as `ResourceExhausted`; it is structural accounting,
not an experimental budget ceiling. Ordinary allocation failure remains an
ordinary diagnostic. A synthetic historical-log fixture traverses the real
classifier and real `execute_profile` inside mocked orchestration; it retains the
original failure and zero-resource evidence, spends exactly one mocked full
attempt, closes ten mocked commands, and never admits the second arm. This is
pure runner evidence, not VM execution.

R2: both prefix parsing and final-usage joining enforce unsigned 64-bit
instruction/fuel counters, cumulative fuel at least cumulative original
instructions, and fuel delta at least instruction delta. Validation starts at
zero, covers every prefix interval and the final join, and also covers an empty
prefix list. Thus non-increasing extra fuel is rejected even when each individual
record has fuel greater than its instruction count. Valid extra bulk fuel and
fuel charged before a failed instruction increment remain admissible. Prefix
validity remains separate from the unchanged eleven-field oracle.

## Preserved experiment

All six generator/source inputs are copied byte-for-byte. The generated source
closures remain:

- Control: `af58b29a605384f3ac3ac2d3a3b513533e0da4f140f0e5d2c22807eb78bcb2f7`.
- Dense candidate: `3db26064abc07200219b62c9637850f50868f470bb2d0ca7598223131c2033d4`.

The original harness, 53,777,114-byte artifact, 11-field oracle, metering,
validation/capability/byte/frame/host ceilings and cleanup stay unchanged. The
identical finite calibration remains 1B lifetime fuel, 8B execution work, 768M
cache work, and 600,000ms whole Runtime/WASI duration. Numeric headroom is an
experimental hypothesis, not a production default or feasibility result.

Both optimized Rust 1.99.0 builds, finite suites, harness controls, actual
geometry no greater than 256MiB, and zero-cleanup receipts must close before any
full attempt. The driver retains nine preparation commands, at most two full
attempts and eleven total commands, a 2,700s aggregate allowance, a 46-minute
command step and a 55-minute job. No retries/refunds, custody exceptions or
resource-limit success claims are added. The workflow invokes this sibling's
driver/tests and writes corrected output paths; it shares the original workflow
concurrency group to prevent overlapping versions.

## Evidence and remaining work

`python3 -B verification/swift-execution-architecture-correction/verify.py`
rechecks the complete frozen packets, immutable runtime readset, both regenerated
source identities, all 38 pure controls, and differential reproductions of both
reviewed defects. Process creation, sockets, signals and wait/custody operations
are denied for this pure run. `receipt.json`, `correction-evidence.json`,
`pure-check.stdout`, `pure-check.stderr`, `source-check/` and `readset.json`
retain its actual scope and identities. `seal.json` binds this complete packet.

Compiled geometry, finite-suite timing, runtime semantics, two-corpus equality,
actual cleanup, performance, physical/native checks, published FieldLog, signed
OTA and GA remain pending. The unchanged 90s finite watchdog decides actual suite
fit only when a remote run is selected. No extra release-work metering policy is
introduced; the review's coverage/timing notes remain pending observations.
UnitA, broad hosted/PostgreSQL work, held actor groups 20745, 20770, 20780, 20817,
20842, 20851 and 20866, local FieldLog compiler work, native/UI/capture work and
all other active holds remain unchanged.
