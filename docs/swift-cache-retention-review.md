# Independent finite Swift retention review

The sealed segmented-LRU candidate has no blocking finite correctness or
accounting findings. This review accepts only the prerequisite for root to select
one separate isolated same-budget full diagnostic. It does not select that run,
accept live integration, or establish actual-target benefit.

The reviewed producer seal is
`6507e85f869d0f1a052b9e8e5356ac07910c67813f87b309fa6a5b348e803c13`;
its candidate 132-file manifest is
`d840933a706131e64c50b74812af771ead622912d57575336770434387f5b99d`.
Read-only reconstruction verifies all 99 producer members plus its report, both
132-file archives, command/output bindings, selected final results and normalized
generic output pairs. The live VM still matches original closure
`16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`.
Review inputs record contextual HEAD `b375e55ded9e3e10c327891ab681beff2a471e26`.

Source review confirms that hits validate the resident index against actual
function identities, prepare tier changes read-only, and precharge every tier
mutation. A by-value plan publishes only after the last fallible operation,
beside final pin publication. Miss victim planning changes no tiers; eventual
slot publication resets probationary state after its reset credit is admitted.
Pinned residents are excluded from eviction. Demotion may include a pinned
resident but changes neither its pin nor liveness. Complete proof, decoder,
policy, resident IR and pin authority remain intact. Equal age comparisons retain
the first slot; selected victims cannot re-enter a multi-victim plan.

Seven independent Release host methods pass using the explicit existing stable
Rust/Cargo 1.99.0 toolchain, with offline Cargo and one test thread:

- A sorted reference policy with an ordinal clock matches 6,400 mixed pin/release
  transitions across capacities 1–8, 63 and 64, including tier membership, pin
  counts, relative ages, actual index membership and live ledgers.
- A held oldest protected resident is demoted while pinned, survives later
  pressure, preserves pin/proof/decoded identity, and becomes evictable after
  release. The stale handle is rejected.
- Every 25 failed work prefixes and 22 cancellation boundaries of a five-slot
  promotion preserve all tiers, ages, cache statistics and the pre-existing live
  pin; the original failure remains sticky and consuming cleanup returns zero.
- Three-victim memory pressure evicts probationary and protected residents while
  preserving a held protected resident. All 161 failed work prefixes keep every
  surviving resident unchanged and never publish the new function.
- Eight equal-age cases across four capacities and two selection-only shifts
  verify pinned demotion and victim slot-order ties. Four all-pinned capacities
  reject a new function without changing retention or held pins.
- Measured layouts verify 144-byte slots, the 2,672-byte retention inventory,
  exactly 8,016 added operation bytes, the zero-sized FrozenMode plan, and zero/
  one-slot behavior.
- A separate FrozenMode oracle passes 2,048 occupancy/pin/selection/age cases:
  default victim work is exactly one credit per slot, sorted LRU and tie choices
  match, unit preparation/publication has no effect, and owner/slot/pin/scratch
  layouts retain their baseline values.

The 40-field added inventory maps plans, helper arguments and results, iterators,
closures/reborrows, ranks, demotion/publication arguments, and returned values to
three disjoint complete copies. Existing owner and other-phase bytes are not
reused. The full enlarged slot payload is admitted before its existing allocator
request. At 64 slots the extra fixed 512 bytes reduce payload by exactly 512;
constructor work adds 64 credits. Additional victim work equals eligible tier
probes per scan. A probationary hit adds one tier read plus `2*slots`, protected
age reads and its complete one/two-write commit; an already protected hit adds
one credit. The held-pin five-slot test costs 25 credits because its unchanged
pin-record lookup costs nine, followed by 16 retention credits.

This is the existing authored named-Rust-object/requested-payload model. It
excludes opaque standard-library internals, compiler stack placement, allocator
overhead and RSS. The existing unnamed constructor slot literal remains such an
expression; no new named constructor binding/helper argument is introduced.
Its enlarged resident payload is counted before allocation. No physical-stack
measurement or reservation substitution is inferred from these checks.

The producer's 47 Swift cache, five generic unit and ten generic integration/
allocation methods remain separately verified recorded evidence. Its generic
outputs match baseline after elapsed-seconds-only normalization. The four full
regression contexts were not repeated; they follow the actual-target benefit
decision. Initial reviewer output is retained: one expectation missed the credit
for an occupied pin record; a later generic probe used an assumed constant
instead of the existing `scratch_bytes()` function. Both corrections affect only
review tests. Product source stayed unchanged. The bounded extraction preflight
also rejected an initially small byte limit before extraction or command launch.

Known performance tradeoffs remain material: the producer records 6.319% fewer
synthetic hot16/stream128 credits, 2.110% more cyclic65 credits, and 22.777 times
the cyclic64 resident-hit work. Its prior actual target has 537,576 hits and
61,628 misses; these totals do not identify retention behavior or prove benefit.
The prior actual CacheWork failure remains authoritative. A target regression
must be retained and reject this candidate without changing resource limits.

No full reactor, guest execution, native/UI/device, hosted/network, signing,
publication, customer, published-package FieldLog or GA attempt occurred. Physical
phones and all specified final acceptance gates remain pending. Review-owned
source/build/tmp retirement removed 49,527,606 logical bytes across two bounded
rounds (295 regular files), after absent-process/holder and device/inode/mutation
checks; no signals were sent. The producer's retired 203,735,362 bytes/436 files
and immutable source archives remain verified. See the sealed
[review packet](../verification/swift-cache-retention-review/) and its
[decision](../verification/swift-cache-retention-review/result-summary.json).
