# Swift cache work attribution preparation

This packet prepares a new isolated Release executable and exact target command.
It does not execute the full Swift target. The root preparation selection is
`verification/swift-cache-work-attribution-root-selection/preparation.json`
(SHA-256 `0f6538d299958465f47fb87e2041f33cdb9d433305e92abeb20ee63c68a8596c`).
It authorizes copied test instrumentation and finite controls only. The fresh
executable, harness, driver, source transforms, target input and complete argv
are bound in `verification/swift-cache-work-attribution/prepared-selection.json`;
a new exact root selection must precede its one permitted target attempt.

The immutable after-cache packet is method and observation data. Its driver,
target command, compiler and native oracle were not imported or executed. The
existing diagnosis verifier checks its 20 sealed artifacts, input bindings and
132 live source files without compiling or running a guest. The copied baseline
is exactly
`b28da766c84b6353a4511e2fc3fbcb0d4302d5b8a5a74da1ee3d7fb776ca2c11`.
No live VM files, root trackers, Git state, devices, publication, credentials or
frozen hosted catalog/authority and outbound V2 lanes are part of this packet.

The only copied source changes are `experimental/cache/borrowed.rs`,
`experimental_swift_reactor/cache.rs`, its `cache_tests.rs`, and an include at the
end of its `lifecycle_tests.rs`. `transform.py` verifies each original seam and
reconstructs the four exact transforms. The frozen legacy meter receives only
default no-op `cfg(test)` observer methods. Production layouts, cache algorithm,
credit amounts, cursors, work results, sticky failures, hooks, cancellation,
deadlines, reservation authority and consuming cleanup are unchanged.

The twelve credit sites have this fixed order:

| Index | Site | Original work attributed |
| --- | --- | --- |
| 0 | constructor | Existing slot, pin and patch initialization credits |
| 1 | lookup_header | Initial lookup credit |
| 2 | free_pin_probe | Existing free-pin iterator credits |
| 3 | resident_probe | Existing resident-slot iterator credits |
| 4 | scan_policy | Existing scan descriptor/signature policy credit |
| 5 | scan | Existing borrowed scan credits |
| 6 | empty_slot_search | Existing `slots.len()` planning charge |
| 7 | victim_probe | Existing oldest-victim iterator credits |
| 8 | plan_count | Existing `MAX_ENTRIES` planning charge |
| 9 | build_policy | Existing build descriptor/signature policy credit |
| 10 | build | Existing borrowed build credits, including allocation checks |
| 11 | publication | Publication boundary; zero successful credits is valid |

Each work callback observes the original `work_with_wasi` result and returns that
same result. Only successful requested work enters the site sum. The first
rejected work retains its site, cursor, attempted request and original typed
failure copy. A failed check without a work call does not create a rejected-work
record; the harness preserves the original runtime failure separately.

The observer uses twelve credit counters, twelve work-call counters, two fixed
65-bin histograms, one first rejection, a `[u64; 1250]` bitmap (compile-asserted
10,000 bytes for absolute function indexes below 80,000), and at most sixteen
first distinct repeated-completion identities. It has no dynamic function map
or per-credit output. Every completed-decode event follows the original decoded
counter publication. Distinct plus repeated completions must equal authoritative
decodes; bitmap population must equal distinct completions. The selected target
has 34 imports and 79,832 definitions, within the bitmap range. Samples identify
the first sixteen distinct repeated functions, not the most frequent functions.
Occurrences of repeated identities absent from those samples are counted.

Free-pin histograms contain successful probe lengths once resident lookup begins;
resident histograms contain completed hits only. An interrupted lookup therefore
need not publish a histogram entry. Authoritative eviction totals and resident
bytes accompany snapshots. Eviction controls check known totals and capacity
identities; there is no independent eviction event attribution.

Counter overflow, invalid site/index, histogram overflow or observer borrow
failure invalidates diagnostic reconciliation without panicking or supplying VM
authority. Snapshot serialization omits bitmap words and caps the observer JSON
at 16,384 bytes. The fixed observer state and serialization are external
`cfg(test)` overhead. This is successful-credit attribution, not a CPU profile;
its overhead may change elapsed time and the unchanged deadline outcome.

The finite Release controls use the actual copied cache: hot resident/free-pin
positions, 64- and 65-function cycles, nested scan/build work, ten finite
cache-work caps, six reached cancellation prefixes, disabled/enabled/invalid
observer comparisons, saturation and reentrant observer borrowing. A separate
small lifecycle harness proves construction, Initialize, two corpus calls,
aggregate snapshots and consuming cleanup. It is synthetic wiring evidence.
The host controls cover exact PGID observation and refusal of missing or
mismatched root selection. Failed compile/fixture receipts and repairs are
retained literally; passing controls do not rewrite them.

The target remains the original 53,777,114-byte Wasm with SHA-256
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`.
The harness preserves the original 120-second validation, cumulative 30-second
runtime and 30-second WASI deadlines, grants, corpus input, parity checks and
owner operations. The proposed process limit is 170 seconds with five seconds
for TERM and five seconds for KILL. A missing or mismatched fresh root selection
refuses target execution; an exclusive attempt marker prevents a second target
launch. No expected CacheWork failure is coerced into diagnostic success.

`receipt.json`, command receipts and `cleanup.json` record exact tools, sources,
argv, environment, process identities/PGIDs, raw output hashes, EOF scope and
unchanged live source. Owned compilation and temporary scratch are removed after
holder/group checks. The exact source snapshot and executable are intentionally
retained for root inspection/selection. Physical devices remain pending, and no
full-corpus, public/legacy, native, signed-release, published-package FieldLog or
GA acceptance follows from this preparation.
