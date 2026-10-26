# Remaining Swift cache work after decode-plan reuse

The next bounded slice should complete a fixed-memory successful-credit observer
and present it for a separately selected diagnostic run. The current evidence
fixes planning at **11,828,480 credits (18.48%)** and locates the final failure
inside IR rebuild decoding. It cannot rank total rebuild work, repeated plan
conflicts, free-pin probes and resident-index work. Changing the plan policy or
decoder first would therefore select an optimization without its current
attribution. No new full run or production algorithm is selected by this packet.

This diagnosis binds source revision context
`6403eea98031207f6e40a72b55dfd3bd4e7e6ec2`, the accepted 132-file VM closure
`16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`, and the
completed full-result seal
`8f04098c444d63e9d638c32e22297eccdad346222241529ef710c524473e7526`.
It preserves the original failure. Validation and Initialize pass; Corpus 1
fails at CacheWork 64,000,001 / 64,000,000, function 23610, offset 4,154,038,
after 23,358,291 guest instructions and 4.840104 seconds at the causal checkpoint.
Corpus 2 is unrun. The previous checkpoint was 15,753,076 instructions; the larger
prefix under the same budget is not a CPU speedup or full-completion result.

The terminal post-drain cache reports 537,576 hits, 61,628 misses, 61,627 completed
decodes, 61,564 evictions and 63 residents. The causal failure's live cache-entry
count is 64 because a newly admitted rebuild is still live; these observations
must not be substituted for each other. Final consuming cleanup returns all
current primary reservations, live counters and tickets to zero, without a
cleanup invariant. The original success-oriented cleanup flags remain false
because the runtime failure is retained. See the
[sealed original result](swift-exact-reactor-after-plan-reuse-result.md).

The cache's separate resident, construction and fixed maxima sum to 2,457,776
bytes: 1,847,979 + 491,557 + 118,240. Even that conservative simultaneous sum is
below the unchanged 16,777,216-byte limit, so memory pressure did not require
multiple victims. Every miss after the first 64 evicts one entry:
`61,628 − 64 = 61,564`. Completed decodes minus evictions leave 63 residents,
showing that the final unsuccessful decode committed its victim removal.
Its scan and both fixed planning walks therefore completed. Source charges are
exactly `128 × misses + 64 × evictions = 11,828,480`: 7,888,384 for empty-slot
search plus plan recount, and 3,940,096 for exact oldest-unpinned searches.
No final uncommitted-plan allowance is needed for this observation.

Offline section/body inspection treats the exact 53,777,114-byte module as data.
Function 23610 begins at 4,153,760, has 811 bytes, and ends at 4,154,570. The
failure offset lies 278 bytes into it, with 532 bytes following. A successful
count scan would leave the cursor at the final end byte; a plan hit leaves it at
the initial body offset. Neither planning nor index maintenance advances that
cursor. After the observed victim removal, only the rebuilding decoder advances
it inside the body. This identifies the blocked operation as build decoding;
it does not prove that build decoding consumed most prior credits. No module
instantiation, Initialize or invoke was performed for this inspection.

The present source gives the following bounds on successful credits, using the
terminal cumulative counters. They are arithmetic constraints, not measured
target semantic stages or CPU time. The intervals overlap and are not additive
upper-bound predictions.

| Component | Credits |
| --- | ---: |
| Constructor | 4,928 exact |
| Lookup header, free-pin search, resident hash/chain | at least 4,547,120 |
| Empty-slot, victim and plan-count walks | 11,828,480 exact |
| Resident removal and insertion | 1,047,092..32,337,732 |
| Count-plan work, scan/build and both policy lookups | 986,042..46,572,380 |

A successful hit costs `3 + p + 4k`, where `p` is the first-free pin probe length
and `k` is the complete resident bucket-chain length. The index validates the
entire chain even after finding the requested identity. A hit has `k ≥ 1`; a
miss may have `k = 0`. The lower bound is therefore `8 × hits + 4 × misses`.
Free-pin work alone lies between 599,204 and 38,349,056 at the 64-pin capacity;
the observed active-pin peak of 38 tightens this run's upper bound to 22,769,752.
Before counting a hit/miss the in-progress acquisition itself is live, so a
first-free probe length cannot exceed that observed peak. These bounds still
cannot rank free-pin work. Every victim removal costs `5 + 4k` with `k ≥ 1`,
and each successful insertion costs `8 + 4k` with `k ≥ 0`.

The 512 count plans are directly indexed by `absolute_function & 511`. They
retain counts, never resident decoded IR. A matching identity probes function,
body offset, body length and type index before copying all three count fields.
A conflicting function performs a complete new scan and replaces the cell only
after successful scan and the existing publication debit. Every IR rebuild still
parses the complete body, makes exact fallible allocations, constructs output,
patches branches and checks actual counts against the plan. A resident hit never
consults the count plan.

For a complete valid body, define P parameters, B body bytes, G local groups,
L expanded locals, I instructions including final end, C nested block/loop/if
entries, A else instructions and T explicit br_table targets excluding defaults.
The unchanged decoder charges `S = 1+P+B+G+L+I+2C+A+T` for count scanning and
`K = 1+P+B+G+2L+2I+3C+2A+2T` for building. Including scan policy and the new plan
operations, an empty plan costs `14+S`, a conflicting plan `15+S`, and a matching
plan 10. Building including its policy costs `1+K`. These formulas exclude
resident lookup, planning and index maintenance. Reset checks retain zero work
credits. A conflict's avoidable scan benefit depends on its body's S; it is not
a constant percentage that can be applied to the target.

The new finite Release fixture copies all 132 accepted VM files and appends a
test-only observer to three copied files. It preserves original proof validation,
owner operations, work debit/check order, failure values, output/count validation
and consuming cleanup. Sixteen explicit sites observe successful credits after
the original debit returns; rejected requested credits never enter the sum.
This avoids historical CacheStep buckets that charged scan policy under Lookup
and build policy under Planning. Exact isolated bytes, patch, tool versions,
argv, raw streams and all thirteen fixed observations are retained in
[the packet](../verification/swift-plan-cache-remaining-work-diagnosis/receipt.json).

| Finite actual-cache sequence | Work | What it establishes |
| --- | ---: | --- |
| Flat cold body | 164 | scan 4, build 5, one new plan |
| Nested block/loop/if/else cold body | 245 | scan 37, build 53; independent IR/branch assertions pass |
| Single resident hit, first free pin 0 / 63 | 8 / 71 | retained free-pin probe cost |
| 64 functions cycled twice | 11,015 | 64 decodes, 64 hits, no evictions or plan reuse |
| 65 functions cycled twice | 25,629 | 130 decodes, 66 evictions, 65 plan hits; no plan conflicts |
| Evicted flat IR with retained matching plan | 229 | no count scan, but full build and all 192 planning credits |
| Evicted flat IR after 34/546 plan conflict | 238 | complete scan and replacement, nine more credits than the matching-plan case |

The two 34/546 controls use ordinary 64-resident pressure under default limits;
they do not lower the resident ceiling to force the result. One test passes,
with 386 tests filtered out, zero ignores and two inherited compiler warnings.
It covers all 164 shorter cold-work budgets and three cancellation checkpoints,
reconciles successful credits with original cache_work, preserves sticky typed
failures and drains every original owner to zero without cleanup work. Only the
negative work-prefix controls lower a synthetic fixture's work budget. This is
finite observer verification, not a fresh complete VM regression or production
accounting acceptance. Compilation plus test takes 23.134 seconds; the named test
itself reports 0.03 seconds. No guest instructions, Initialize or invokes run.

The full target does not expose plan hits, conflicts, scan/build credit totals or
current distinct decoded identities. Its completed-decode count is below 79,832
defined bodies, so aggregates alone do not establish how many are repeated.
The historical 485-distinct/98.77%-repeat attribution belongs to an older source
and shorter prefix; it cannot supply these missing current measurements. Even
fewer than 512 distinct identities would not prove direct-map conflict freedom.

The highest-value next slice is the
[minimal observer proposal](../verification/swift-plan-cache-remaining-work-diagnosis/observer-proposal.json).
Keep the demonstrated sixteen successful-credit/call counters, four plan-event
counters and one first-rejection record. Add one 10,000-byte completed-decode
bitmap covering absolute indices below 80,000 and fixed counters partitioning
scan/build credits into first and repeated IR decodes. Mark only original
completed-decode publication. This distinguishes expensive repeated conflicting
scans from first visits, and remaining repeated builds from free-pin/index work.
It needs no dynamic map, histogram, top-function sample, guest-loop log or clock.
Actual observer layout/output bounds and bitmap/failure-prefix controls remain
required before a fresh source/harness/executable/argv can be selected for one
diagnostic full run. The observer remains external test-only memory and overhead.

If that measurement is deferred, the best evidenced production candidate is
eliminating the empty-slot walk and boolean-plan recount using a fixed accounted
occupancy/free-slot structure and maintained victim count. Their current gross
charge is 7,888,384 credits (12.3256%); replacement operations, storage, checks and
publication must be accounted before claiming any net saving. Preserve the
lowest empty index, exact oldest-unpinned order and tie behavior, pin/nonce
safety, atomic index/entry publication, cancellation/failure precedence and Frozen
behavior. The victim walk's additional 3,940,096 credits are separate. This is a
bounded candidate with a known gross opportunity, not a selected implementation,
CPU-gain prediction or assurance that either corpus will complete. Greater
free-pin, repeated-conflict or build opportunities require the proposed current
attribution before they can outrank it.

All live VM hashes match before and after the fixture. The exact owned process
group is absent and holder checks are empty. Device/inode checks bind removal of
the owned copied-source, build and temporary directories, reclaiming 24,007,177
logical bytes without signals or touching other projects. The exact isolated
source is retained compressed. No native instance, UI, phone, network, provider,
signing operation, Git operation or frozen hosted lane is used. Early read-only
exploration guessed nonexistent decoder/source paths; those reads changed no
evidence and selected no execution. Root updated PLAN.md and STATUS.md during
the diagnosis. Their initial observed hashes and separately archived seal-time
hashes are both retained; this concurrent document upkeep is not VM source drift.

The 16-MiB cache, 8-MiB entry, 64 residents/pins, 86 tickets, 64-million work,
256-MiB combined limit and 120-second validation/30-second run deadlines remain
unchanged. Full reactor completion, Corpus 2, native/public/signed behavior,
immutable published-package FieldLog consumption, final physical phones and all
specified GA acceptance remain pending. This diagnosis advances W08 within the
complete product plan; it does not narrow that scope.

Read-only verification performs no compilation or guest execution:

```sh
python3 -B verification/swift-plan-cache-remaining-work-diagnosis/verify.py
```
