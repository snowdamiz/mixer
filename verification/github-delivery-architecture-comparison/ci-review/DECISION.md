# Actual bounded architecture comparison review

Accept the retained artifact as a **closed diagnostic comparison**. Neither arm
established host feasibility. Both full attempts stopped in `corpus_1` at the
same frame-admission boundary: `FrameLimit`, `swift_frame_depth`, `Frames`,
attempted 65 against limit 64, function 24126, offset 4394310. No complete
eleven-field guest observation was produced, and neither reached `corpus_2`.
The workflow's successful completion means the bounded diagnostic campaign
closed correctly; it does not mean the workload passed.

This packet is local review evidence. Root owns subsequent selection and any
derived delivery. It does not authorize another full attempt, integrate the
candidate, alter defaults, or promote a GA gate.

## Bound identity and executable evidence

- Run 40768719255, attempt 1; job ID 123099796496 supplied by root's handoff.
- Exact head `dfd0e3196543cc1749c9cc924cc7accf28c9dc25`, tree
  `3cc58d6744649fdd138b9d3963b436db62480ecf`.
- Artifact 12851363846, 151,935 compressed bytes, SHA256
  `362d80ece5ed8b6b3678ba0d7fddfc61ce44368066fc61fd1094de19b6f4f6aa`.
- All 67 archive files were read, CRC checked, strictly parsed where JSON,
  hashed, and inventoried. All eleven command stdout/stderr hashes match their
  receipts. Started receipts, argv, environment, exit codes, deadlines and
  sequence agree with final receipts.
- The exact commit's Git object and tree entries independently bind the
  reviewed workflow, corrected runner, generator/Rust inputs and four selected
  seals. This used byte reads and SHA1 verification, with no Git command.
- All four source/review seals and the correction's complete readset match
  before and after verification. Pure regeneration from the frozen archive
  reproduces all 133 files and the complete patch in each arm. Control closure:
  `af58b29a605384f3ac3ac2d3a3b513533e0da4f140f0e5d2c22807eb78bcb2f7`;
  dense closure:
  `3db26064abc07200219b62c9637850f50868f470bb2d0ca7598223131c2033d4`.
- The same 53,777,114-byte Wasm is independently decompressed and rehashed as
  `24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`.
  The original native oracle and full two-call harness are unchanged.
- The remote receipts identify Rust 1.99.0, LLVM 23.1.1,
  `x86_64-unknown-linux-gnu`, Cargo 1.99.0, and Python 3.12.3. Both builds use
  release optimization level 3, overflow checks, no debug assertions,
  locked/offline dependencies, two build jobs and no incremental compilation.
- Control passed four finite tests and one harness control; dense passed six
  finite tests and one harness control. Both preparations and their compiled
  geometry/zero-cleanup observations completed before either full attempt.
  The job log also reports the corrected runner's 38 pure tests passing.

The control executable manifest reports 6,164,296 bytes, SHA256
`f0c3bf4e55f60c911efaec76e82cd46adf2d497e8edb8439402c0cac6313c640`;
dense reports 6,173,592 bytes, SHA256
`a2bbca7b786ff32c1eb1fe58a09e13bf9c2b0bf3d327fc8ff8fcd55b17a02ed1`.
Build output and all finite/harness/full argv join to those separate arm paths.
These are hashes reported by CI and checked there before execution. The
executables were removed with owned scratch before upload; this review cannot
independently rehash retained executable bytes because none were retained.

## Actual cause, geometry and cleanup

Both arms retain 256 residents, 64 active pins, a 64-frame limit, 1B cumulative
instruction fuel, 8B execution work, 768M cache work, 600,000ms cumulative
Runtime/WASI duration and the 256MiB combined logical envelope. Dense's compiled
map is 160,000 bytes and its free-pin bitmap eight bytes. Independently
recomputed conservative combined bounds are 266,788,262 bytes for control and
266,805,846 for dense, leaving 1,647,194 and 1,629,610 bytes respectively.
These are conservative logical admission bounds, not measured process RSS.

| Actual full attempt | Control | Dense |
| --- | ---: | ---: |
| Original instructions at failure | 736,058,045 | 734,611,941 |
| Instruction fuel | 741,107,070 | 739,659,254 |
| Execution work | 5,094,730,699 | 5,090,365,432 |
| Cache work | 553,238,194 | 212,289,804 |
| Runtime elapsed at failure, seconds | 379.452709 | 324.084982 |
| Full process wall time, seconds | 380.536678 | 325.178257 |
| Peak combined logical reservation, bytes | 183,613,204 | 183,804,889 |

The first cause is frame admission. Neither arm reached the shared fuel, work,
deadline or combined-memory ceiling. The failure has no exact-capacity,
ticket-inventory, owner-identity, invariant or unsupported-operation identity.
The original first failure survives consuming cleanup unchanged. Raw stdout
independently reproduces every field of the retained classified results and
raw stderr reproduces every prefix record.

Fuel is at least original instructions throughout, with nondecreasing excess:
157,033, 400,573 and 951,486 at the three shared prefixes; 5,049,025 at control's
final observation and 5,047,313 at dense's final observation. Every prefix and
the final interval passes the corrected R2 cumulative and interval checks.

Final cleanup usage has zero current values for all authoritative logical
reservation categories, live resources and live tickets, with no cleanup
invariant. `cleanup_reservations_and_live_empty=true` is the resource result;
`cleanup_empty=false` deliberately retains the fact that execution failed.
The failure object's earlier `after_cleanup` snapshot precedes consumption of
the final three shared/construction tickets. It must not be confused with the
later authoritative `final_cleanup_usage`, which is zero. Nested WASI usage is
a historical observation and is not the authoritative live owner ledger.

All eleven command groups are recorded absent, with no timeout, cancellation
or cleanup signal. Custody has no pending command, all eleven closures are
proven by the remote receipts, and owned scratch is reported removed. These
are retrospective remote receipts; this review did not probe any process.

## Defensible paired measurements

At 25M, 50M and 100M original instructions the two arms have identical observed
instruction fuel, execution work, host-call count, function and offset. Those
are the available paired observations:

| Instructions | Control Runtime seconds | Dense Runtime seconds | Elapsed reduction | Control cache credits | Dense cache credits |
| --- | ---: | ---: | ---: | ---: | ---: |
| 25,000,000 | 12.834879 | 11.280298 | 12.112% | 18,392,516 | 11,782,768 |
| 50,000,000 | 25.547238 | 22.518432 | 11.856% | 35,807,139 | 19,409,505 |
| 100,000,000 | 51.012657 | 45.007598 | 11.772% | 71,571,614 | 35,049,415 |

Dense is a promising candidate on this one sequential comparison. The elapsed
measurements begin with the Runtime owner, exclude validation/process launch,
and include work outside the cache and diagnostic overhead. There is no timer
for individual cache categories. Credit reductions of 35.937%, 45.794% and
51.029% are reductions in policy debits, not CPU shares or CPU savings.

Equal observed prefixes do not prove identical host entropy or all guest
state. There is one sample per arm, with control first. The different final
instruction counts make endpoint timing an unpaired measurement; it cannot
establish an overall workload speedup or a numeric production winner. Raw
wait4 RSS has the known launcher high-water floor and provides no attributable
per-arm VM memory comparison.

## Next decision and limits

The executed frame-entry source uses
`budget().frames.min(64)` before frame publication. Increasing the selected
`frames` number alone cannot resolve the current stop. A useful next bounded
source investigation is frame representation/admission and the recursion that
reaches it, while preserving pin authority, failure atomicity, accounting,
capability validation and consuming cleanup. A deeper-frame experiment would
need executable finite frame/pin/owner geometry within the existing envelope
before another full attempt. This review selects no experiment and spends no
additional full attempts; root retains that decision.

Neither full corpus, the two-corpus eleven-field milestone, native/mobile
runtime, immutable external FieldLog distribution, signed OTA, customer use,
nor GA is accepted here. Production defaults and all native/process/custody
holds remain unchanged.

`review.py` passed 252 checks under local Python 3.14.8 in a bounded offline
process. The audit hook and explicit guards deny network, child processes,
process inventory/signaling/waits and mutations outside this lane. The reviewer
ran no compiler or guest, created no scratch, and made no Git writes. Two
initial verifier assertion mistakes were corrected and retained in
`review-attempts.json`; neither was an artifact failure or runtime retry.
The final readset, artifact inventory, checks, receipt and all original inputs
are sealed in this packet.
