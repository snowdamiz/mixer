# Private Swift resident index candidate

The isolated candidate replaces private Swift resident scans with a fixed, exactly admitted 192-byte index. It is ready for independent review under the [selected contract](swift-cache-resident-index-contract.md). The live 132-file VM remains at `b28da766c84b6353a4511e2fc3fbcb0d4302d5b8a5a74da1ee3d7fb776ca2c11`; no full reactor retry, native/device run, integration into live source, publication or GA acceptance is included.

The index stores 128 bucket heads and 64 next links as slot-plus-one bytes; zero is empty. A fixed multiplicative hash chooses a bucket. Keys remain in actual resident decoded functions. Every lookup validates the entire encountered chain, including slot range, occupancy, key bucket, duplicate requested identities and cycles, with an inclusive 64-node bound. A matching key does not bypass the rest of the chain validation. There are no tombstones, rebuilds or function-count-sized allocations.

The shared sealed mode gains lookup/removal/insertion hooks. FrozenMode retains its literal linear loop and no-op mutation hooks. Private Swift uses its index through the existing scratch adapter. Every actual initialization cell, hash, link validation, resident probe and link read/write is metered. Removal validates the complete chain and admits both link writes before unlinking. Insertion validates the empty slot and chain, then admits both writes before the infallible index/slot publication. A failed insertion drops the built entry and its ticket; a failed removal retains the affected resident. Existing eviction planning, strict LRU ranking, 64-entry limit, pin ownership/nonces, decoder validation, sticky failure and consuming cleanup remain enforced.

A fourth exact-capacity vector owns the 192 bytes, initialized with 192 actual charged writes. All owner/ticket/borrow transfers and temporary inventories are admitted using measured Rust layouts. These are named-object reservation envelopes, not stack/RSS measurements:

| Reservation or work | Baseline | Candidate |
| --- | ---: | ---: |
| Default cache fixed bytes | 88,536 | 89,376 |
| Cache header bytes | 62,424 | 63,072 |
| Cleanup temporary envelope | 62,096 | 62,696 |
| Cache construction envelope | 57,224 | 57,896 |
| Cache operation envelope | 80,566 | 88,294 |
| Foundation construction envelope | 269,232 | 269,616 |
| Default constructor credits | 640 | 832 |

The cache increase is 192 payload bytes plus 648 header/cleanup bytes. Dependent bootstrap owner shapes also enlarge the admitted foundation envelope by 384 bytes. Every production memory/work/deadline ceiling remains unchanged. The conservative FrozenMode helper inventory grows from 6,088 to 8,032 bytes within its existing 9,312-byte reservation.

The identical finite fixture constructs 64 residents and performs four complete hit sweeps. Fresh baseline and candidate builds use separate target directories:

| Actual cache work | Baseline | Candidate |
| --- | ---: | ---: |
| 64 cold decodes | 13,127 | 9,671 |
| 256 resident hits | 8,832 | 2,048 |
| Retained decoded payload bytes | 2,600 | 2,600 |
| Hit allocation requests | 0 | 0 |

The hit fixture uses 76.81% fewer credits; this is neither a CPU speedup measurement nor a completion prediction. A first-slot single-resident hit grows from three to eight credits. An intentional 64-collision chain costs 260 credits per hit, validates its full bound and rejects a cycle. All actual work remains charged, including unfavorable collision behavior. The measured reactor's repeated-decoding cost is not solved by this index.

The final candidate closure is `02fd25a32b05cf8c4b10e0f68df029d8851e14610ccecbec772be09af5073f8d`. Six files differ: shared hooks, their conservative legacy test inventory, the private cache and its tests, and exact lifecycle/construction test expectations. Final all-feature Release verification passes 626 tests across unit/integration/doc groups, with nine inherited ignored tests. The final private-cache Debug suite passes all 29 tests; default and compatibility Debug suites, production Clippy with warnings denied, and formatting for the six changed files pass. FrozenMode's complete literal trace is identical to a fresh baseline, and eight LRU access states retain the same victims, pins and ranks.

Actual-owner controls cover collision head/middle/tail deletion, same-slot reuse and reinsertion, all-pinned retention, inclusive 64-node chains, invalid/empty/wrong-bucket/cyclic links, four constructor allocation/capacity refusals, decode/allocation/deadline controls and zero consuming cleanup. Each of three collision-victim positions exhausts all 130 shorter replacement work budgets and all 82 cancellation checkpoints. Existing independently expected IR, dirty-scratch, depth, owner/nonce, sticky-failure and zero-allocation controls also pass.

Initial preparation assertions, stale count expectations, missing Node PATH, and a 240-second broad Debug timeout remain recorded. One exit-zero frozen control reused a stale baseline Cargo binary from the original shared build directory; its source qualification is explicitly invalidated. Final qualification uses fresh separate targets and records executed binary hashes. The full broad Debug timeout is not a pass. The installed, hashed Node development oracle was already listed in `THIRD_PARTY.yml`; no dependency was added.

[Receipt](../verification/swift-cache-resident-index/receipt.json), [comparison](../verification/swift-cache-resident-index/comparison.json), [patch](../verification/swift-cache-resident-index/candidate.patch) and [seal](../verification/swift-cache-resident-index/seal.json) bind exact source, tools, root selection, commands and raw output. All recorded child streams close and owned process groups disappear. Owned build scratch is removed after a holder check; sources, failed evidence and other projects remain preserved. Physical phones, native parity, published FieldLog consumption and all specified final acceptance gates remain pending.
