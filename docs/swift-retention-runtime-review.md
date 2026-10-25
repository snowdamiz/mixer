# Independent review of the rejected retention candidate

The retained single-attempt result supports root's rejection of this segmented
LRU candidate for live integration. There are no blocking evidence discrepancies.
The candidate exhausts the unchanged CacheWork budget after 8,746,437 instructions;
the same original harness, target and budget reach 23,358,291 instructions with
the current engine. This is 37.44% of baseline instruction progress. Both runs
fail, so these are partial-progress observations, not completed-workload latency
or throughput measurements.

The reviewed root result seal is
`e2fe9807c8ff83d1bea08f62b1504e7b50b9e9801af24ca57beb766398f97e64`,
covering 26 retained files including the result report. Its raw-derived summary
is bound at
`3c9b8ae386e4fca7e9514d9047dba89f50d6cdfe9dead5bd2ba54fc93b1901e5`.
Every copied command/marker/selection/event/result byte matches its original
preparation namespace. The selected source closure, executable, tool identities,
argv and environment match the accepted preparation. Selection follows both
independent reviews, and exactly one target command directory and exclusive
marker exist. No historical selection or attribution harness was substituted.

Strict independent parsing of the original stdout reconstructs the recorded
events exactly. Validation and construction complete. Initialize returns
`Initialized`, reaches Ready at 37,328 instructions, and matches baseline
Initialize instruction progress. Corpus 1 fails; Corpus 2 has no begin or result
event. The original typed failure is stage `Cache`, kind `WorkExhausted`, resource
`CacheWork`, code `swift_run_work`, attempted 64,000,001 and limit 64,000,000,
at function 22920 and source offset 4029857. It occurs after 8,746,437 instructions
with 64,000,000 credits charged. Four emitted validation/run/WASI/grant objects
are identical to baseline. No budget is widened.

The child exits 101 after 2.992 seconds. There is no timeout or cleanup signal;
the owned process group is absent before and after the original supervisor's
cleanup boundary, and output EOF/hash receipts are complete. The preserved
driver result reports failure and returns outer exit 1. Its stdout JSON equals
the original result object, and outer stderr is empty. The child panic preserves
the failing diagnostic rather than replacing it with a successful wrapper exit.

Original failure fields, including the complete at-failure observation, match the
final failure apart from the expected added `after_cleanup` snapshot. That copied
component snapshot still has 271,360 foundation bytes and three tickets; it is
not the final consuming ledger. The separate `final_cleanup_usage` has all eight
primary reservation currents, six live currents and live tickets zero, with no
cleanup invariant. CacheWork and instruction counters do not advance during that
consuming cleanup. The nested WASI submeter remains a historical observation.
The original `cleanup_empty: false`, `ownedCleanupEmpty: false` and failed Result
remain unchanged because the prior runtime failure remains present. Zero final
ledger counters establish cleanup completion; they do not establish workload
success.

At its failed phase the candidate records 73,511 completed decodes and 134,721
hits; baseline records 61,627 completed decodes and 537,576 hits. These are
different progress points. This review does not infer a fixed-trace hit rate or
a causal breakdown from them. The actual same-budget regression is sufficient
to reject the candidate's proposed benefit without retuning limits or selecting
a retry.

Root's new `finish.py` preserves the attempt before retiring only restored owned
products. Recorded holder checks are empty, device/inode identities are stable,
and a fresh independent read-only process check also finds PGID27467 absent.
The 78,039,492 removed logical bytes equal the exact prepared-source bytes plus
the 53,777,114-byte target copy and 4,986,496-byte executable: 134 regular files.
The existing gzip and all 122 sealed preparation members/external inputs remain
unchanged. The original target hash remains
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`.
All 132 live VM files still match original closure
`16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`.
Both earlier independent review seals are preserved.

This review performs no target, restoration, compiler, native, device or network
run, creates no build/source scratch, changes no product file and rewrites no
historical output. Root's rejection, no-integration decision and no-retry decision
are verified. Native parity, full regression, signing, published-package FieldLog
and GA remain unaccepted. See the [audit](../verification/swift-retention-runtime-review/audit.json)
and [independent decision](../verification/swift-retention-runtime-review/result-summary.json).
