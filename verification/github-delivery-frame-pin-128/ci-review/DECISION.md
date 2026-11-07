# Actual 128-frame / 128-pin CI review

Accept the retained artifact as a closed diagnostic comparison. Both arms
passed their compiled finite controls and original harness control, advanced
beyond the previous 64-frame boundary, and then exhausted the unchanged cache
work budget during `corpus_1`. Neither produced a complete original eleven-field
corpus observation or started `corpus_2`. Host feasibility is not accepted.

Run [40779075333](https://github.com/snowdamiz/mixer/actions/runs/40779075333),
attempt 1, job 123135853660, is bound to commit
`295f3f18a53459449f22253687bd2d0b2c09a0ed`, tree
`294faafd3be568208a366ea66f85c5538a376ffa`. Artifact 12857735315 is 164,027 bytes,
SHA256 `ca55e3492b608049a0d28695573269a44e629ef5942357ba180365b3a8b2285a`.
All 67 ZIP members were read, CRC checked, strictly parsed where JSON, hashed,
and joined to the original command output hashes. Both source packets and all
sealed members match their selected seals and committed Git blobs. Pure
regeneration reproduces both complete copied source closures and patches;
the original 53,777,114-byte Wasm, native oracle, full two-call harness,
validation, capabilities, complete budgets and grants are unchanged.

CI used Rust/Cargo 1.99.0, LLVM 23.1.1, x86_64-unknown-linux-gnu and Python
3.12.3. Both Rust builds used release optimization, overflow checks,
locked/offline dependencies, two build jobs and no incremental compilation.
Executable hashes are CI-reported manifests checked there before execution;
the executables were removed with scratch and are not independently rehashed
from retained bytes here.

| Observed result | Control | Dense |
| --- | ---: | ---: |
| Finite tests passed | 9 | 10 |
| Original harness controls passed | 1 | 1 |
| Conservative combined bound, bytes | 266,788,262 | 266,805,982 |
| Headroom under unchanged 256 MiB, bytes | 1,647,194 | 1,629,474 |
| Peak frames / pins in full attempt | 67 / 67 | 67 / 67 |
| Original instructions at failure | 789,501,731 | 791,082,590 |
| Attempted cache work / limit | 768,000,001 / 768,000,000 | 768,000,003 / 768,000,000 |
| Failure function / offset | 15838 / 3713734 | 52085 / 11115894 |
| Peak combined logical reservation, bytes | 184,414,334 | 183,810,617 |

The first failure is `WorkExhausted`, `swift_run_work`, `CacheWork`, stage
`Cache` in both arms. The original cause remains sticky through consuming
cleanup. This is ordinary budget exhaustion, with no exact-capacity,
ticket-inventory, owner-identity, invariant, unsupported-operation, external
timeout or command-custody failure. All authoritative final logical reservation
and live-resource currents, and live tickets, are zero. The earlier nested
failure cleanup snapshot is historical; `final_cleanup_usage` is authoritative.
`cleanup_empty=false` preserves the execution failure while
`cleanup_reservations_and_live_empty=true` records successful resource release.

Compiled finite output proves the +4,096-byte frame arena and +1,024-byte pin
arena, no additional tickets, 128 retained/restored actual frames, rejection
above 128, all fifteen integrated allocation failures and six capacity failures.
Dense uses a sixteen-byte two-word bitmap and the unchanged 160,000-byte map.
The independent conservative formula includes the arena growth inside the
unchanged category ceilings; the deltas are not added again. Both preparations
and geometry checks finish before the first full attempt. All eleven owned
commands are sequential and closed, with no cleanup signal, and owned scratch
is removed. The two full attempts exhaust the selected campaign allowance.

At 25M/50M/100M original instructions, observed fuel, execution work, host calls,
function and offset match across arms. Dense cumulative Runtime elapsed is
7.63%/8.06%/8.35% lower in this one sequential sample. These are matched observed
prefixes, not proof of identical entropy or complete guest state. Cache credits
are policy debits, not CPU time. Final instruction/fuel/work counters and
failure cursors differ; no endpoint or full-workload speedup claim is valid.
Raw wait4 RSS retains the known launcher floor and supports no per-arm VM
memory comparison.

The ordinary exact-head push workflow
[40779048792](https://github.com/snowdamiz/mixer/actions/runs/40779048792)
also completed successfully: all six jobs are green. Those workflow results
do not qualify physical devices, native/mobile behavior, external immutable
FieldLog distribution, signed OTA, customer use or GA.

`review.py` passed 188 offline checks under Python 3.14.8 with a sixty-second
internal bound. Audit and explicit guards deny network, child processes,
process inventory/signaling/waits and out-of-lane writes. No local compiler,
guest, native/UI/capture process, held-group probe, Git mutation, dispatch,
rerun or runtime retry occurred. Raw archive, log and complete review stay
local; `sanitized-summary.json` is the small derived summary. Root owns the
next source decision. This review selects no resource widening or further
full attempt, changes no production defaults, and promotes no GA gate.
