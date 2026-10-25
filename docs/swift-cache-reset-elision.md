# Isolated private Swift cache reset elimination

This candidate deletes both redundant 512-slot clearing loops and their charges.
The existing exact-length check now calls the ordinary operation meter's explicit
check at each `ScanReset` and `BuildReset` boundary. The initialized exactly
reserved 512-Patch arena, its charged constructor initialization, all three fixed
buffers, both complete decoder passes and conservative phase inventories remain.
There is no production state, shared decoder, public layout, identity, revision,
dependency, cache policy or runtime-limit change. Root acceptance and any later
target attempt are separate decisions.

The source baseline is checkpoint
`7744c1cc28b24a46f4339b25b38ce4d0cf76cbe8`, VM132 closure
`f2682c6a2fd6f6e74bd00a2394ff32b704aa1e2ed3d2373ef95cdee29fa7eb2c`.
Only `src/experimental_swift_reactor/cache.rs`, its private `cache_tests.rs`
and root-approved expectation-only `lifecycle_tests.rs` differ in the isolated copy. The candidate mirrors, exact patch, all source
manifests, tools, commands, complete outputs and final status are in
`verification/swift-cache-reset-elision/`. The live VM source is not modified.

Both passes start at depth zero. On block, loop or if entry, the unchanged
borrowed decoder checks capacity, charges work and writes all Patch fields
before increasing depth. Else obtains a checked active predecessor; nested end
reduces depth before reading that active patch. Function end reads none. This
allows initialized stale inactive records without letting their values influence
decoding. Every actual byte, local, instruction, branch target and active patch
operation retains its original charge and checks. No clearing work is retained
without charging it.

The test-only private seam seeds every actual owner arena record through the
unchanged borrowed decoder: each record becomes a nonempty If patch with
`start=17`, `alternative=Some(19)`. No uninitialized memory or shared production
decoder modification is used. It redirties all 512 slots independently before
both scan and build on flat, sibling, nested block/loop/if/else and br_table
misses, comparing complete independently specified IR and branch targets.
Depth 379 and inclusive depth 512 likewise run with dirty scratch before both
passes, then reuse the same deep arena for a shallow miss. Complete validation
rejects attempted depth 513 against 512. Five malformed cases (empty-stack else,
duplicate else, truncated control, unclosed control and trailing bytes) fail with
the expected static decoder codes in both direct borrowed passes over the actual
owner's hostile initialized scratch. These direct syntax controls are not
fabricated accepted Swift proofs.

The existing Release cache suite passed 22 selected tests before the final two
narrow controls were completed. It enumerated 773 shorter constructor-plus-miss
work budgets and 621 constructor plus 97 miss cancellation checkpoints. Seeded
resident-hit and eviction-miss paths added respectively 3/80 shorter budgets and
6/37 cancellation checkpoints. Consuming cleanup now also asserts unchanged
cache work and the existing zero combined reservations, tickets, pins and entries.
The final targeted precedence control exercises both new boundaries with the
exact observed work budget, independently with/without cancellation and an
expired deadline: 8 combinations retain the expected first cause and sticky
failure, publish nothing and permit no retry allocation/work. ScanReset occurs
at credit 637 and BuildReset at 749 on this finite 29-definition fixture. Original
count/build mismatch, all allocation ordinals, exact capacity, admission, real
WASI observation, selected deadline origin/overshoot and terminal cleanup controls
remain selected.

A baseline source-copy observation fixture and the candidate give these actual
cache-credit measurements, including the same actual runtime control and owner:

| Fixture | Baseline cold | Candidate cold | Removed reset credits | Resident payload |
| --- | ---: | ---: | ---: | ---: |
| Flat helper | 1,229 | 205 | 1,024 | 40 bytes |
| Nested helper | 1,310 | 286 | 1,024 | 480 bytes |

Both reset stage totals change from 512 to zero; all other measured stages agree.
The 64-slot/64-pin constructor still costs 640 credits. Resident hits still cost
3 credits, and measured hits/releases allocate zero times. Both configurations
reserve the same 88,536 fixed bytes in this fixture. The same eight successful
accesses, including an independently held pin, produce identical pin slots,
nonces, resident slots, LRU ranks, victims, hit/miss/eviction counts and resident/
pinned ledgers. Maximum timestamps strictly increase in both runs; their numeric
values decrease with less performed work, as allowed by the amendment.

The first added precedence test used 120,000ms as its nonexpired run deadline;
the unchanged 30,000ms maximum rejected that fixture during adoption. Its failed
command, source binding and outputs remain preserved. The fixture was corrected
to use `SwiftRunBudget::default().deadline_ms`; the subsequent exact test passed.
Existing caught-panic diagnostics and compiler warnings are retained in full.
The original all-feature Release run also exposed two dependent lifecycle tests
with exact old reset-credit expectations. Root explicitly selected the isolated
expectation-only extension in `lifecycle-expectation-amendment.json`: the cold
fixed cost changes from 1,151 to 127; Initialize/first corpus/second corpus totals
change from 1,803/4,196/4,206 to 779/1,124/1,134. The SL14 fixture exhaustion
budget changes from 1,764 to 740 so it still exhausts immediately after Initialize.
No product budget or other lifecycle expectation changes. The two original
failures remain preserved.

Regression contexts, any remaining failures, final cleanup and seal are recorded
in the packet's receipt; a failed or unrun context is not a pass.

The completed regression execution contexts are default Debug/Release (91 passes,
8 existing ignores each), compatibility stream/cache/span/WASI Debug/Release
(171 passes, 9 existing ignores each), and all-feature Debug/Release (620 passes,
9 existing ignores each). The original all-feature Debug command reached its
180-second outer host limit after 321 individually completed tests; the root-
approved continuation skipped those exact names and passed the remaining 299
with four threads. Release preserved 396 earlier passes and completed 224 remaining
tests after the two exact lifecycle expectation repairs. The compatibility runs'
initial missing-Node oracle failures were resolved by rerunning only that target,
the unexecuted suffix and doctests with the installed hashed Node runtime. The
six continuation commands used 87.85 seconds in aggregate, below the separately
approved 450-second per-command and 900-second aggregate host bounds. Product
work, byte and deadline limits did not change.

All 18 original named cache acceptance functions and all 23 current private cache
functions executed successfully in Debug and Release, together with one positive
and 12 expected-negative downstream compilation controls per mode. The complete
123-line frozen legacy layout/work/error/usage trace is identical in compatibility
and all-feature builds in both modes; four additional Swift-feature allocation
observations are also identical in Debug and Release. Clippy passes. Global
formatting remains failed on the exact same 16 inherited files in baseline and
candidate; all three candidate files have no formatting differences. Unrelated
files were not rewritten.

Cleanup found no open holders or remaining members of any owned command process
group, then removed the disposable source, target, temporary and baseline-format
directories (756,056 KiB according to the bounded pre-cleanup disk inventory).
All 132 live baseline hashes still match. Compact candidate mirrors and evidence
remain; no native instance was created or retired by this lane.

This is synthetic host evidence for one isolated candidate. It provides no new
full FieldLog execution, stdout parity, second corpus, measured target speedup,
Swift/native parity, signed/public package, immutable external consumer, phone
matrix or GA qualification. All original runtime ceilings remain unchanged and
the original failed target packet remains immutable.
