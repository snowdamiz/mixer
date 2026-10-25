# Isolated Swift resident-retention candidate

The isolated deterministic segmented-LRU candidate passes its finite host
correctness and accounting checks. It remains unselected for live integration or
a full Swift reactor attempt. The original 64,000,001 / 64,000,000 CacheWork failure
remains authoritative. These synthetic results show both a scan-resistance benefit
and substantial workload-dependent costs:

| Finite trace | Original LRU | Candidate SLRU | Observed difference |
| --- | ---: | ---: | --- |
| 16 warmed functions, four rounds of 128 one-use functions followed by the hot set | 592 decodes; 1,558,624 trace credits | 528 decodes; 1,460,132 trace credits | 64 fewer decodes; 6.319% fewer trace credits |
| Three cycles of 65 functions | 195 decodes; 406,583 credits | 195 decodes; 415,162 credits | No decode benefit; 2.110% more work |
| Existing fixture: 256 resident hits cycling over 64 functions | 2,048 credits | 46,648 credits | 22.777 times the hit work, without redecoding |

The last regression matters: the prior actual target recorded 537,576 hits and
61,628 misses. Aggregate counts cannot show how often it would promote or demote
residents. The bounded promotion scan may therefore consume more work than the
candidate saves. No actual-target benefit is established, and the policy was not
retuned after these measurements.

Every completed decode enters probationary state. A second successful resident
pin promotes it. Protected capacity is exactly `floor(3 * allocated_slots / 4)`;
zero or one slot admits no protected resident. At capacity, promotion demotes the
oldest protected resident. Victims are ordered by probationary before protected,
then existing work-based age, then slot order. Pinned residents cannot be evicted;
demotion changes no pin or liveness state. Memory pressure can require multiple
victims and can still evict protected residents when probationary payload is
insufficient. The policy contains no target function IDs, prewarming, unbounded
history, or new public API.

The shared private cache mode uses an associated `HitPlan`: unit for the original
non-Swift mode and a bounded enum for Swift. Its default victim scan retains the
literal original LRU work trace. Swift prepares promotions read-only and precharges
all tier writes; the by-value plan commits beside the existing infallible final pin
publication, after the last fallible operation. Rejected hit preparation changes
no retention metadata. Misses retain complete proof-backed parse/build validation,
identity checks, admission, first-failure ordering, pin handling, and cleanup.

The additional Boolean increases the measured resident slot from 136 to 144 bytes.
The existing reservation admits that complete slot payload before allocating it.
At 64 slots, fixed reservation grows from 118,240 to 118,752 bytes and available
payload falls by the same 512 bytes. Three disjoint 2,672-byte named operation
inventories cover plans, helper arguments, closure borrows, map arguments, and
return objects: operation reservation grows from 92,350 to 100,366 bytes.
Constructor allocation requests remain five. These are logical named-object
bounds, not RSS or compiler-stack measurements.

Every tier probe and write receives additional CacheWork. In the four-slot
promotion fixture, the ordinary eight-credit indexed hit gains one tier read,
eight occupied/tier reads, three protected-age reads, and two writes: 22 credits.
A protected hit costs nine. Constructor work grows by 64 tier writes. The first
hit through a 64-node collision chain costs 390 credits rather than 260; its extra
130 credits remain fully charged. All resource and time limits remain unchanged.

The final host release run passes 47 cache methods, including eight capacity
boundaries, deterministic ties and an order-preserving selection-only age shift,
real-clock phase adaptation, every 22 failed promotion-work prefixes and 20
cancellation boundaries, every 122 replacement-work prefixes and 62 cancellation
boundaries, three-victim memory eviction, all-pinned rejection, malformed decode
plans, build parity, proof ownership, allocation ordinals, and first-failure
precedence. The original baseline passes 42 methods. Both copies pass five
non-Swift cache unit methods and ten non-Swift integration/allocation methods.
Their output is byte-identical after normalizing elapsed seconds only; work,
memory, allocation, error, and pin observations are preserved.

The initial age-shift test wrongly combined shifted old ages with a later real
clock update; its failed output and test-only correction remain in the packet.
Two historical Swift snapshots initially failed because they asserted old work
charges. Their copied candidate expectations now state the added charges and
SLRU outcomes explicitly; original baseline snapshots remain intact. The inherited
PATH initially lacked Cargo, so two prelaunch attempts dispatched no command;
the existing explicit stable toolchain resolved that invocation issue. Other
recorded compiler warnings are inherited. Policy logic stayed unchanged after its
initial implementation; the named operation inventory was expanded to include
explicit closure reborrow and map argument objects before the final run.

The packet binds the original `7b6048642b42e4900cccff4e14aa0fe8949ab35e`
132-file source closure
`16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`,
the compact complete source archives, precise commands, Rust/Cargo 1.99.0,
Python 3.14.8, host environment, outputs, corrections, and cleanup. Root's later
`b375e55ded9e3e10c327891ab681beff2a471e26` checkpoint is contextual only;
the live VM closure remains unchanged. Owned build and source scratch is retired
after source archives and holder checks. No simulator, emulator, phone, UI, signing,
publication, customer, FieldLog release, or GA gate was exercised.

Independent correctness/accounting review must precede any separately selected
same-budget actual-target comparison. A measured target regression must be
retained and used to reject the candidate rather than changing limits.

See [the finite packet](../verification/swift-cache-retention-candidate/),
[contract](../verification/swift-cache-retention-candidate/contract.json), and
[derived results](../verification/swift-cache-retention-candidate/result-summary.json).
