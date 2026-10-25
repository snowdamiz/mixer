# Cost-aware recency candidate rejected by finite controls

Root rejects this isolated miss-only cost/age candidate for live integration and
does not select a full-target run. All six fixed finite traces use more CacheWork
than the ordinary live LRU baseline. The phase-shift control is especially poor:
after sixteen expensive functions stop being used, twelve cycles of sixty-four
cheap new functions cost 553,152 credits versus 17,440 for baseline, or 31.717
times the work. The policy was not retuned after these observations.

| Finite trace | Baseline decodes / trace credits | Candidate decodes / trace credits | Work change |
| --- | ---: | ---: | ---: |
| Original hot16 / stream128, four rounds | 592 / 1,558,624 | 592 / 1,836,400 | +17.822% |
| Original cyclic65, three rounds | 195 / 406,583 | 195 / 476,126 | +17.104% |
| Expensive hot16 / cheap cold streams | 592 / 248,012 | 528 / 363,312 | +46.490% |
| Cheap hot16 / expensive cold streams | 592 / 1,444,044 | 592 / 1,721,476 | +19.212% |
| Uniform hot16 / cold streams | 592 / 222,412 | 592 / 500,188 | +124.893% |
| Expensive old set to cheap cycle64 phase shift | 80 / 17,440 | 784 / 553,152 | +3,071.743% |

These are finite logical-work observations, not real-target elapsed-time or
throughput measurements. The phase shift ends with stale expensive residents
still occupying sixteen slots. In the favorable expensive-hot trace, saving
sixty-four decodes still does not repay the ranking overhead. This evidence
supports rejection without executing the real target or raising any limits.

The candidate was independently authored from the ordinary live 132-file closure
`16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`,
copied directly from `vm/` after verifying that digest. The rejected segmented-LRU
source was not restored or used. The root froze the policy before implementation.
The live engine remains unchanged, and the original actual-target CacheWork
failure after 23,358,291 instructions remains authoritative.

The policy adds a private victim-selection hook only to existing miss planning.
Its default specialization retains the original LRU eligibility loop, one credit
per slot and first-slot ties. The Swift specialization minimizes estimated saved
build work divided by work-based age. Its numerator is
`max(1, body_len + 2*locals + 2*instructions + 2*targets)`, calculated with checked
`u64` conversions, doubles and sums from the existing complete validated `Counts`
and immutable body length. This conservatively estimates repeat-build bytes,
expansion and vector pushes. Parameter/signature checks, local-group overhead and
control patching are omitted. No popularity counter, function-specific constant,
source scan or target observation supplies this estimate.

Each victim scan takes one fixed current-work snapshot. Age is
`max(1, now - last_used)` with checked subtraction. Checked `u128` cross products
compare ratios without division; exact ratio ties prefer the older timestamp,
then the lower slot index. Empty, pinned and already selected slots cannot rank.
Memory pressure repeats this read-only selection for each needed victim. Zero
stored cost, a future timestamp or arithmetic failure fails closed before any
resident mutation. The estimate and its eventual field-write charge are prepared
before existing entry admission/build, after the original byte-size check. No
new fallible operation follows successful decoded ownership before the existing
resident publication.

Resident lookup, the generic pin body, its hit branch and final pin publication,
the Swift pin wrapper, and both release bodies are byte-identical to baseline.
Hashes and byte lengths are recorded in `source-seals.json`. There is no extra
hit-time scan, cost read/write, promotion, allocation or ticket. Both copies use
exactly 2,048 credits for 256 ordinary resident hits, eight per hit, and the
existing adversarial sixty-four-node collision-chain hit remains 260 credits.

Every victim scan adds one precharged logical credit for its clock snapshot and
eight per eligible resident, besides the original per-slot eligibility credit.
The eight grouped units cover cost/nonzero validation, recency/checked age/clamp,
candidate preparation, best-rank probe, two products, ratio/tie comparison, and
conditional local-rank publication. Cost creation precharges twelve units for
body plus three count reads/conversions, three doubles, three sums, clamping and
the eventual resident-field write. These are authored logical operation groups,
not counts of every CPU instruction. Full conservative blocks remain charged on
the first candidate and failing paths.

One `u64` field grows `SwiftResident` from 120 to 128 bytes and its slot from 136
to 144. Exact slot payload increases by 512 bytes at sixty-four slots. Six
existing permanent resident/optional-resident transfer objects add another
48 bytes, so fixed reservation rises from 118,240 to 118,800 and available cache
payload falls by exactly 560. Constructor work stays 4,928 credits and allocation
requests stay five. The forty-seven-field added named-value inventory is 7,264
bytes, including seven bytes of padding; three disjoint complete copies plus
three enlarged existing resident values add 21,816 operation bytes, taking the
operation reservation from 92,350 to 114,166. Construction reservation remains
61,880. The inventory records each field's type, measured offset and size; no
existing owner or inventory slack is reused. This is the existing authored
named-Rust-value/requested-payload model, not physical-stack, allocator-overhead,
opaque standard-library-internal or RSS evidence.

The pristine baseline passes thirty-nine existing cache methods. Adding the same
three finite trace methods gives forty-two baseline passes. The candidate passes
forty-nine: those baseline methods with one explicit policy-specific snapshot
adjustment, the identical three common methods and seven additional controls.
These cover eight capacities including zero and sixty-four, checked extreme
ratios/count arithmetic, exact ties and a selection-only order shift, pinned and
selected exclusion, a sorted rational reference across 385 rank transitions,
metadata corruption, every thirty-seven failed rank-work prefixes and ten rank
cancellation boundaries, three memory victims with a held pin/proof/IR identity,
every 227 replacement-work prefixes and 113 cancellation boundaries, and exact
memory/work/payload accounting. The inherited tests retain complete decode/build
parity, malformed plans, identity, allocation ordinals, earlier failures, sticky
failure and consuming zero-ledger checks. Every final method passes.

Both copies also pass five generic unit and ten generic integration/allocation
methods. Their complete stdout matches after normalizing elapsed seconds only;
work, memory, allocation, error, identity and pin observations are retained.
These controls do not establish an independent review of the producer's work.

Two failed test runs remain in the packet. The old LRU snapshot expected 288
decodes/224 evictions for both shapes; the new thin shape observes 284/220, while
the wide shape remains 288/224. Only that copied assertion was made policy
specific. A new all-pinned test initially overlooked that sixty-four held pins
exhaust the pin-record table before victim planning; its corrected expectation
retains that original earlier `pin_slots_exhausted` failure. An initial edit-script
anchor matched two inventory locations and stopped before compilation; the owned
copies were reset from their fresh baseline and the operation-only anchor fixed.
Moving the new cost calculation after the original byte-size check preserves its
failure precedence. None of these corrections retunes the policy.

The packet records commands, exact per-command source manifests, full stdout and
stderr, Rust/Cargo 1.99.0, Python 3.14.8 and the actual aarch64 macOS host. Complete
ordinary-live, baseline-with-common-tests and candidate source archives are
preserved. Process absence, two empty holder checks and stable device/inode/file
metadata checks preceded removal of only this packet's scratch: 218,566,668
logical bytes across 438 regular files. No signals were sent. The live closure is
rechecked unchanged after cleanup.

No full target/reactor, native/UI/device, provider/network, signing, publication,
customer, published-package FieldLog or GA attempt occurred. Physical phones and
all specified final acceptance gates remain pending. See the
[finite rejection packet](../verification/swift-cost-retention-candidate/),
[frozen contract](../verification/swift-cost-retention-candidate/contract.json),
[derived results](../verification/swift-cost-retention-candidate/result-summary.json)
and [cleanup receipt](../verification/swift-cost-retention-candidate/cleanup.json).
