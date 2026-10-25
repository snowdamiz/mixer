# Current Swift cache attribution result

The single selected full host diagnostic reproduces the original failure: validation
and Initialize pass, then Corpus 1 exhausts CacheWork at 64,000,001 / 64,000,000
after 23,358,291 guest instructions. Corpus 2 is unrun. No work, memory, resident,
pin, ticket or time limit changed. The original failure remains authoritative.

The corrected supplementary classifier accepts all five snapshots, with no issues
and 4,430 emitted bytes. The final cumulative measurements identify repeated work:

| Measurement | Observed |
| --- | ---: |
| Completed decodes | 61,627 |
| Distinct functions with completed decodes | 485 |
| Repeated completed decodes | 61,142 |
| First-build work credits | 434,091 |
| Repeated-build work credits | 34,500,496 (53.907% of budget) |
| First-scan work credits | 330,379 |
| Repeated-scan work credits | 3,590,363 |
| Repeated scan and build combined | 38,090,859 (59.517% of budget) |

The first rejected debit is at build site 13, function 23610, offset 4154038,
requesting one additional credit. These are aggregate successful-credit counters,
not elapsed-time percentages or a per-function popularity trace. They motivate a
bounded cache-retention improvement, but do not establish which replacement policy
will help or that all repeated decoding can be eliminated.

The accepted preparation binary remains SHA-256
`fc27c22f8f771e7f148bcb73781b09a974a2bcebce7be7466b951ff85d9fafaf`.
Root copied the corrected driver and classifier byte for byte into the sibling
runtime directory, retaining original immutable source/binary locations and
selecting that exact command. The two original prepared packets remain unchanged
and their read-only verifiers still pass. The runtime selection, attempt marker,
complete command streams, original events/result, supplementary telemetry and
source/tool bindings are retained in
[the runtime packet](../verification/swift-current-attribution-runtime/).

The root host rerun initially omitted the producer's two temporary directories;
its five fixture errors are retained. Creating those empty directories makes all
38 unchanged methods pass. This was a root invocation repair, not a source edit.
The strict schema correction closes all six prior invalid-input acceptances and
keeps original result persistence before supplementary classification.

Both owned process groups are absent. Holder and device/inode checks passed before
removing the restored source, uncompressed executable and runtime scratch:
78,030,702 logical bytes. The original compressed executable and sealed receipts
are unchanged. Original final consuming usage has zero current reservations,
live counts and tickets and no cleanup invariant. The earlier legacy
`ownedCleanupEmpty` field remains false and is preserved separately; it does not
replace the observed final consuming counters.

This is host diagnostic evidence, not successful full-reactor, native, signed,
published-package FieldLog, physical-phone or GA qualification. The next work is
the measured cache-retention improvement and its executable correctness/accounting
checks before another separately selected full run.
