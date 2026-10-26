# Independent Swift attribution runtime audit

Accepted as retained **host diagnostic measurements**, with no blocking findings
within this scope. The workload still fails. The binding product scope and all
unmet acceptance gates remain unchanged.

The read-only [audit](../verification/swift-current-attribution-runtime-review/audit.py)
passed on macOS 27.0.1 arm64 with Python 3.14.8, at source revision context
`7b6048642b42e4900cccff4e14aa0fe8949ab35e`. Its exact command, source digest,
tool version and output hashes are in the
[receipt](../verification/swift-current-attribution-runtime-review/receipt.json).
No target, restoration, cleanup, compiler, native, device, hosted or discovery
operation was dispatched by the audit.

| Binding | Independently checked SHA-256 |
| --- | --- |
| Runtime result seal, 26 members plus external result document | `46449fdf0a02fd6c10140803eea197505540f70616f8f0e27174da68ea9619ba` |
| Accepted schema correction, 32 members | `c00ce1412238f08f176d7983b882c25891cbafd6570c0e489dc4733875935c20` |
| Prepared binary, 4,960,000 uncompressed bytes | `fc27c22f8f771e7f148bcb73781b09a974a2bcebce7be7466b951ff85d9fafaf` |
| Exact instrumented source manifest, 132 files | `8eccfedefb8a64fd828743ecb4899ea2624be2359ef879229be00d90a4d5185d` |
| Runtime driver | `6b5583fbfd2e0ffcc277dac9396d9963719e97df9309e197252f129908574b4d` |
| Supplementary classifier | `4ce989553db9502fb9afde2103ef94951beede1fdb543864bb54a69fbc08bb5c` |
| Original prepared harness | `8c7730239b38250671f7dc23cc46859ffd5b4b9253f1eabaf34f161c061ec078` |

All runtime seal members and external document matched. The original preparation,
its original review, and schema-correction packets also matched their seals. The
audit reconstructed the 132 prepared source files in memory, hashed the retained
compressed binary's decompressed bytes, and checked every root-selection binding.
The runtime driver/classifier are byte-identical to the accepted correction.
The retained command, attempt marker and source/tool snapshots bind the exact
binary and reactor. Root selection predates the sole retained target attempt;
the exclusive attempt marker and dispatch guards remain present. The outer
driver exited 1; its inner libtest command exited 101, without timeout or signals.

Raw events independently reproduce validation and Initialize success, then Corpus
1 `CacheWork` failure at 64,000,001 requested against 64,000,000 allowed after
23,358,291 instructions. Corpus 2 never begins. Work, memory, resident, pin,
ticket and time limits remain unchanged: all emitted budgets/grants equal the
previous failing run, and the prepared source, harness and binary are unchanged.
The original failure fields and original result are retained; result persistence
precedes supplementary classification.

All five telemetry snapshots pass the accepted closed typed schema, original
event bindings, partition sums, cumulative monotonicity and sticky rejection
checks. They emit 4,430 bytes, within the 4,608-byte per-envelope and 27,648-byte
lifetime bounds. The six previously accepted malformed inputs are rejected; two
additional in-memory probes reject counter regression and failure-field drift.
The audit verified the retained root 38-method pass and preserved initial five
fixture errors without rerunning those methods or changing their source.

| Final successful-credit measurement | Observed |
| --- | ---: |
| Completed / distinct / repeated decodes | 61,627 / 485 / 61,142 |
| First / repeated build credits | 434,091 / 34,500,496 |
| Repeated build / fixed work budget | 53.907025% |
| First / repeated scan credits | 330,379 / 3,590,363 |
| Repeated scan plus build credits / fixed work budget | 38,090,859 / 59.5169671875% |

The first rejected debit requests one credit at build site 13, function 23610,
offset 4154038. Requested rejected work is excluded from successful counters.
These are aggregate work-credit ratios, not elapsed-time percentages, individual
function popularity, eliminated-work guarantees or proof of a replacement policy.

Original legacy `ownedCleanupEmpty` remains **false**. Separately, final consuming
usage has zero current runtime reservations, live counts and tickets, with no
cleanup invariant. The retained holder checks and device/inode ownership records
precede removal; their 78,030,702 logical bytes match reconstructed source,
executable and target-copy sizes. The audit observes both owned process groups
and all three owned paths absent, and the original compressed binary unchanged.

This accepts the recorded diagnostic packet and its measurements only. Complete
workload, performance, native, signed, separately published FieldLog package,
physical-phone and GA qualification remain unpassed. A cache-retention change
still needs independent correctness/accounting evidence and a separately selected
full run.
