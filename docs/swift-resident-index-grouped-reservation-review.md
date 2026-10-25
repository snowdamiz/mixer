# Independent review: grouped resident-index reservation

Bounded accept for the selected isolated implementation. No actionable product
finding was observed in this review. The selected source manifest is
`3ffa1055e462be74c10ee9830bf891bbd196a896dfc7a66dc6befe2a6d9bb70f`, with
132 members and source revision context
`be472ce6424a691de5673e3438d2768264827d23`. This review authorizes no full-target,
native, public, signed, published-package, operational or GA claim.

All 132 selected members were verified before copying and again after testing.
Reversing the sealed diagnosis production/accounting patches in an owned copy
reconstructed all 132 baseline hashes exactly, manifest
`02fd25a32b05cf8c4b10e0f68df029d8851e14610ccecbec772be09af5073f8d`.
Exactly `cache.rs` and `cache_tests.rs` differ. The selected formatting change
only expands the checked-header `let else`; no diagnosis code is in the selected
product source. The two accounting test changes match the new ownership: 73
instead of 74 cache-only live tickets, and a header that already includes the
index payload. The diagnosis packet's original failed runs are retained as
failures in this packet.

The index remains the same `Vec<u8>`, reserve request, 128 heads, 64 links and
192 individually charged writes. Checked header arithmetic adds its payload
exactly once before any index allocation. `fixed_reserved` adds only the other
three independently reserved buffers. Successful per-category/combined
admissions precede those allocations; no limit or shared-cache source changed.

Both owner ticket arrays shrink from four to three. No other storage strategy
or transfer is introduced: `take` moves the existing Vec handle. The constructor
retains three measured `Vec<u8>` transfer slots and three complete Partial/cache
owner shapes; permanent cleanup retains four Vec slots, three Option-cache
slots, two cache-owner slots, cleanup-tail/Result/completion shapes and existing
conservative ticket transfers. Construction, operation and foundation formulas
continue to measure actual containing types. No array payload, duplicate
index value, fallback allocation or unused interior capacity was substituted.
These are named-object envelopes, not measurements of stack high water or RSS.

Partial cleanup drains the three other buffers, explicitly destroys the index,
then drops proof/partial storage and refunds the header. Successful cleanup
checks provenance before taking the owner, drains residents/buffers, explicitly
destroys the index, and only then transfers the header to the existing tail.
`complete` retires caller storage before refunding that header. Dropping a tail
without completing it has no refund path. Foreign provenance preserves the
owner, confirmed by the existing actual-cache and composed-owner controls.

Independent controls were appended only to owned source copies. Review-only
observers bracket the actual index drop and read the existing allocator/ledger
without allocating or replacing the implementation. The allocator observed the
192-byte deallocation between those points with the same header charge on both
sides. A return-storage Drop sentinel was observed retired in the existing
completion helper while the header remained charged. Both complete consuming
cleanup and each constructor failure in the independent controls finish with
zero reservations/tickets and all six live categories zero, retaining the
original terminal failure. Deliberately corrupted foreign-ticket controls
retain the foreign charge as their specified failure behavior.

| Independently observed selected fixture | Result |
| --- | ---: |
| Owner / Partial bytes | 1,016 / 904 |
| Cache cleanup / header / construction bytes | 62,576 / 63,120 / 57,752 |
| Cache operation / foundation bytes | 88,294 / 269,424 |
| Fixed reservation | 89,232 = 63,120 + 26,112 |
| Real allocations / requested payload bytes | 4 / 26,304 |
| Index payload / constructor work | 192 / 832 |
| Shorter work budgets / cancellation checkpoints checked | 832 / 851 |
| Work failures with allocated index / cancellation failures with allocated index | 192 / 195 |
| Pre-Partial cancellation refusals with zero allocations | 1 |
| Allocator failure ordinals / header-refusal allocation requests | 0 through 3 / 0 |

The actual `SwiftReactorInstance` control/cache/WASI/state owner was constructed
and populated with 64 distinct decoded functions on both copied clean variants.
Construction tickets fell from 22 to 21; populated tickets fell from 86 to 85.
The selected owner admitted a real zero-byte diagnostic ticket at 86 and refused
the next request at 87 under the unchanged 86 limit. Both owners consumed to
zero with no cleanup invariant and preserved TicketInventory as the first
failure. This finite synthetic owner probe does not identify the prior
full-target requester or predict completion of FieldLog/Initialize/Invocation.

The final focused checks pass: three independent controls; six resident-index
controls covering collisions, head/middle/tail removal/reuse, full-chain
corruption, inclusive 64-node chains, all-pinned behavior, and all replacement
work/cancellation boundaries; six selected accounting/ownership/LRU/nonce and
partial-allocation controls; three composed inventory/provenance/completion
controls; and one existing Frozen observation on each variant. The complete
53,784-byte Frozen literal trace is identical between variants and to the sealed
diagnosis literal, SHA-256
`f29eb7ce9850f90c944d3f08d4d56cd8e66708b385f5c33a0bbd8c0cdb104bad`.
The root's full cache/execution/lifecycle regression matrix is separate evidence.

The first new partial-failure control run passed its owner and successful
cleanup checks but failed an observer assumption: the first cancellation can
reject preparation before Partial exists. Its command/source/binary/output are
preserved. The corrected test requires zero allocations and zero Partial events
for that one path, and retains all 851 cancellation ordinals. It changes only
review tests. The corrected run passes all three controls. The intentional
owner-counter unwind diagnostic in an existing passing test also remains in
stderr; it is handled by that test's existing unwind assertion.

Commands used Rust/Cargo 1.99.0 on aarch64 macOS, isolated owned target paths,
offline locked builds and direct execution of hashed test binaries. Each build
and test receipt records its source manifest, exact command/environment,
executable hashes, complete stdout/stderr EOF, exit status, timeout/signal
status and process-group exit. All groups exited; no timeout or signal occurred.
The initial independent-test assertion failure remains an exit-101 failure.
No live engine, Git, full target, native runtime, phone, hosted service,
credential, signing or publication operation was performed. Frozen hosted
catalog-inspector, authority-driver and rejected outbound-worker transport V2
sources were not read or executed.

The review source archive contains 264 verified members from the two owned
copies. After checking that no process held the owned scratch tree, its copied
sources and targets were removed; other project processes and native instances
were untouched. The source archive, manifests, observers, controls and commands
remain available to reproduce the bounded evidence.

[Review receipt](../verification/swift-resident-index-grouped-reservation-review/receipt.json),
[packet seal](../verification/swift-resident-index-grouped-reservation-review/seal.json),
[command summary](../verification/swift-resident-index-grouped-reservation-review/command-summary.json),
[selected delta](../verification/swift-resident-index-grouped-reservation-review/selected-delta.patch),
[independent controls](../verification/swift-resident-index-grouped-reservation-review/lifetime-controls.rs),
[owner control](../verification/swift-resident-index-grouped-reservation-review/owner-control.rs),
[lifetime observers](../verification/swift-resident-index-grouped-reservation-review/lifetime-observers.rs),
[Frozen comparison](../verification/swift-resident-index-grouped-reservation-review/frozen-comparison.json),
[cleanup](../verification/swift-resident-index-grouped-reservation-review/cleanup.json).
