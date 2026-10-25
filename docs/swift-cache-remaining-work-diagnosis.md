# Remaining Swift cache work after reset elimination

Select a bounded, test-only attribution observer next. The current evidence does
not justify choosing a residency-policy, lookup-index or decoder-pass rewrite.
The observer should separate the free-pin/resident scans, LRU planning and the
two decoder passes, and count unique completed decodes with a fixed-size bitmap.
No fresh full-target attempt is selected or executed by this packet. The exact
source/harness/driver proposal is in
[`instrumentation-proposal.json`](../verification/swift-cache-remaining-work-diagnosis/instrumentation-proposal.json).

This diagnosis binds the accepted 132-file VM closure
`b28da766c84b6353a4511e2fc3fbcb0d4302d5b8a5a74da1ee3d7fb776ca2c11`.
All live source hashes matched before and after the synthetic fixture. The
[after-cache result](swift-exact-reactor-after-cache-result.md), sealed result
and root result binding are read-only input references with retained hashes.
No sealed driver was executed, and no sealed evidence was edited.

The existing full-target observation remains `Cache / WorkExhausted /
swift_run_work / CacheWork`, function 1356, source offset 492821, attempted
64,000,001 against 64,000,000, after 12,971,689 guest instructions. Initialize
completed; Corpus 1 failed; Corpus 2 did not execute. The terminal post-drain
snapshot records 280,175 hits, 39,433 misses, 39,432 completed decodes and 39,368
evictions, with 64 resident entries. These are previously measured observations,
not new target measurements. The post-drain snapshot is distinct from the
internal resource-failure checkpoint. An offset alone does not name the failing
inner cache operation: planning/build paths can retain the scan's last offset.

`borrowed::pin` pays one credit for entry to lookup, linearly probes free pin
records, then linearly probes resident slots
(`vm/src/experimental/cache/borrowed.rs:695`, `:707`, `:739`). A successful hit
therefore costs `1 + free-pin probe length + resident probe length`, or 3..129
credits at the selected 64/64 limits. Every counted miss completes all 64
resident probes and costs 66..129 lookup credits. Releasing/viewing a valid pin
uses its checked record index directly; it does not repeat these searches
(`borrowed.rs:595`, `:644`). The 87.6621% aggregate hit ratio does not describe
lookup cost or prove cheap hits.

Each successful cold decode also pays a 64-credit empty-slot search and a
64-credit plan count. Every selected victim requires another complete 64-slot
oldest-unpinned search (`borrowed.rs:783` through `:814`). Timestamps are updated
in place on a successful pin; there is no separate hit-time LRU list walk.
The plan's actual eviction/drop loop and the fixed boolean plan initialization
have no distinct work calls; their CPU cost must not be equated with the
planning credit count. The existing metering precharges the empty search's full
slot length even if `position` returns early. This diagnosis preserves that
contract.

Source arithmetic over the existing counters yields these bounds. They concern
successful work credits, not sampled target stages or CPU time:

| Component | Credits implied by source and sealed aggregates |
| --- | ---: |
| Construction | 640 |
| Hit/miss lookup | 3,443,103..41,229,432 |
| Planning for completed decodes and recorded evictions | at least 7,566,848 |
| Planning including a possible uncommitted final-miss prefix | at most 7,571,072 |
| Both decoder passes and their policy checks, by subtraction | 15,198,856..52,989,409 |

The planning lower bound is `128 × 39,432 + 64 × 39,368`, or 11.8232% of
64,000,000. The conservative extra final-plan allowance is `128 + 64 × 64`;
it does not assert that the failed miss reached planning. The lookup bounds
include every counted hit/miss. The large remaining intervals prevent ranking
lookup against decoding as the target's dominant credit consumer. Deadline
checks, observation/cursor handling, allocation and actual instruction costs
also prevent interpreting credits as a CPU profile.

The aggregate completed-decode count is smaller than 79,832 defined bodies.
Thus neither the miss count nor `evictions = decodes − 64` proves that any target
body was decoded twice. They are consistent with both repeated access after
eviction and a stream of distinct bodies. The resident peak is 1,847,979 bytes,
construction peak 491,557 bytes and fixed reservation 88,536 bytes; even the
sum of those separate maxima is 2,428,072 bytes against the 16,777,216-byte cache
limit. Together with the full 64-entry terminal cache and eviction arithmetic,
the evidence is consistent with entry-count pressure; it does not establish
reuse distances or a better eviction policy. Raising either bound is not the
next selected action.

The private Swift adapter still runs `scan_borrowed` once for exact counts and
`build_borrowed` once for fallible exact allocation, output construction and
count agreement (`cache.rs:1921`, `:1990`; `decode.rs:497`). Each pass checks
the descriptor/parameters and reads every body byte; both charge local
expansion, instruction handling, control scratch and branch-target work. Build
additionally charges each output push and end/else patch. Reset boundary checks
remain, with zero scratch-clearing credits. For a complete successful valid body
the two passes plus their policy lookups cost:

`4 + 2P + 2B + 2G + 3L + 3I + 5C + 3A + 3T`

Here P is the parameter count, B the encoded body length, G local declaration
groups, L expanded locals, I decoded instructions including the function end,
C nested block/loop/if entries, A else instructions and T explicit br_table
targets excluding defaults. This formula follows every existing work call in
`decode.rs`; it excludes lookup/planning and assumes both passes finish. It is
not applied to the target without the missing function-frequency data. Removing
a pass would change preflight sizing/admission and exact allocation/failure
contracts. No such rewrite is selected.

A new Release fixture used a copy of all 132 current VM files, original proof
validation, original owner/control and actual cache/scan/build/cleanup under
unchanged default budgets. The sole copied implementation change observes
successful work after the original `work_with_wasi` call; an appended test drives
the finite source-authored modules. Independent flat/nested IR targets are
asserted. Exact source diff, copied manifest, command, tools and raw streams are
retained in
[`verification/swift-cache-remaining-work-diagnosis/`](../verification/swift-cache-remaining-work-diagnosis/).

| Synthetic actual-cache operation | Observed credits | Observed behavior |
| --- | ---: | --- |
| Flat helper cold miss | 205 | one decode |
| Nested block/loop/if/else cold miss | 286 | one decode |
| Resident slot 0, free pin 0 | 3 | hit |
| Resident slot 63, free pin 0 | 66 | hit |
| Resident slot 63, free pin 63 | 129 | hit |
| 64 functions cycled twice | 15,335 | 64 decodes, 64 hits, zero evictions |
| 65 functions cycled twice | 30,888 | 130 decodes, zero hits, 66 evictions |

These observations establish the mechanisms on the named synthetic sequences.
They do not establish that the target has either reuse pattern. The helper
formula gives 11 flat and 92 nested decoder/policy credits, matching the cold
totals after the 66 lookup and 128 planning credits. The existing eight raw
`CacheStep` buckets are not exact semantic stages: scan policy's one credit is
still charged under Lookup, and build policy's one credit under Planning. For
example flat cold raw buckets are Lookup 67, Scan 4, Planning 129, Build 5.
The proposed observer labels policy before those calls and separates the two
lookup loops. Merely adding the previous eight-bucket hook to another target
run would leave those distinctions unresolved.

One fixture test passed in 22.840 seconds including compilation, with 368 tests
filtered out. Existing compiler warnings are preserved. No fixture execution
failed or timed out. All four original owners finish with zero combined
reservation, live tickets, cache entries and active pins, without cleanup work.
The exact owned process group was empty, and an owned-directory holder check
was empty before removing scratch, build and temporary paths. Cleanup reclaimed
23,828,046 logical bytes and sent no signals. No device, UI or native instance
was used. Initial exploration encountered nonexistent guessed `Sources`,
`tools`, `crates`, and prior-packet filenames; those read errors selected no
execution and changed no evidence.

The smallest next attribution slice uses fixed successful-credit/call counters
for constructor, lookup header, free-pin probes, resident probes, scan policy,
scan, empty search, victim probes, plan count, build policy, build and
publication. Add 65-bin probe histograms, one first-rejected-credit record, a
10,000-byte bitmap covering absolute function indices below 80,000, and at most
16 first-repeated function identity samples. `distinct completed + repeated
completed = authoritative decodes` must reconcile exactly. The samples are not
a top-function ranking. No unbounded map, per-instruction log or clock call is
needed. This observer is external test-only memory and overhead; it supplies no
production reservation/accounting acceptance.

The proposal names exact copied-source seams, lifecycle snapshot changes and a
new one-shot driver. Its finite controls must validate successful-credit sums,
hit/miss/eviction reconciliation and work/cancellation failure prefixes before
root sees any target selection. A fresh root selection must bind the new copied
source, observer, harness, driver, executable, complete input closure and argv.
The prior sealed selection does not authorize a changed executable. Preserve
the same runtime budgets and deadline; observer overhead can change elapsed
time or the first resource reached and must be reported literally. Stop before
executing a full target until that separate selection exists.

Only after attribution should root choose between eliminating actual lookup
probes with a private accounted index/free-slot structure, eliminating redundant
planning walks with maintained invariants, improving residency under the same
64-entry ceiling, or changing decode construction. Each has different
allocation, overflow, cancellation, failure-prefix, pin/nonce/LRU and frozen
legacy requirements. The present evidence selects instrumentation, not a
specific optimization or budget increase. Full target/corpus parity, public and
signed/native behavior, published FieldLog consumption and all specified final
acceptance gates remain pending. Physical phones remain disconnected.

Read-only packet verification, without compilation or guest execution:

```sh
python3 -B verification/swift-cache-remaining-work-diagnosis/verify.py
```
