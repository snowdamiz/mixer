# Private Swift index ticket-storage diagnosis and proposed contract

Recommend grouping the existing exact 192-byte resident-index `Vec<u8>` payload
under the existing cache-header reservation, with three buffer-ticket slots. This
recovers one persistent ticket without increasing the unchanged 86-ticket limit
or any memory, work, entry, deadline or capability limit. It retains the current
vector allocation, 128 heads, 64 links, 192 individually charged initialization
writes and every index operation. This is a source-backed diagnosis and finite
copied-prototype result. Root has not selected or integrated this correction.

The input is the integrated 132-file closure
`02fd25a32b05cf8c4b10e0f68df029d8851e14610ccecbec772be09af5073f8d`,
reported by the selected execution packet at commit
`be472ce6424a691de5673e3438d2768264827d23`. The frozen full-target result seal is
`05d31bc936466d9dd6c2b21c411e30e75087396e6f6903a0e6fc597f401948fd`
and receipt is
`2f5d03babfa28f8fad02dced2fc480f68fdd0ff5a8b2f9e2286da42447022d77`.
All live closure members were checked before copying. No Git operation, live
engine edit, full reactor, native run, phone, signing or publication was performed.

## What the existing failure establishes

The unchanged full-target harness passed construction and Initialize, then
refused attempted ticket 87 against 86 during Invocation at function 79,548,
source offset 15,881,589. It had executed 6,555,490 guest instructions and used
31,475,443 cache work credits. Existing before/after snapshots show construction
21 to 22 tickets and completed Initialize 85 to 86 with 64 cache residents.
The source adds exactly one persistent ticket for `buffers[3]`, the index vector.
The source and snapshots support that persistent delta. They do not identify
the requesting owner or requested bytes of the refused 87th ticket.

The existing final consuming cleanup snapshot has zero current reservations,
live tickets and live categories, without a cleanup invariant. The raw
success-oriented `cleanup_empty` remains false because the first failure is
retained. This diagnosis preserves that distinction and makes no completion or
equal-prefix performance claim.

## Proposed ownership contract

1. Keep `index: Vec<u8>` in both `Partial` and `SwiftFunctionCache`. Keep its
   exact reserve request/capacity check for 192 and the existing loop of
   `work(1)` before each zero push. There is no array literal, implicit buffer
   initialization, additional data copy or new allocation strategy.
2. Define the cache-header reservation as the measured exclusive cache-owner
   bytes plus the complete existing cleanup/helper/owner/return envelope **plus
   exactly 192 bytes of fixed index payload**. The header is admitted before
   any index allocation or initialization, including every partial-construction
   path. All terms use checked arithmetic and the existing category/combined
   admission. Do not add 192 a second time in `fixed_reserved`.
3. Reduce both buffer-ticket arrays from four to three. Slots, pin records and
   patches retain their current separate tickets. Remove only the separate
   index admission. Never coalesce resident decoded-entry tickets, release the
   header early, borrow spare inventory slots, or increase ticket capacity.
4. During partial failure, explicitly destroy `take(&mut partial.index)` while
   its header is charged, then preserve the existing proof and partial-owner
   destruction/refund ordering. Before header admission, that vector is empty
   and has no allocation. Any allocation/capacity/work/cancellation refusal
   continues to preserve its first terminal cause and consume partial ownership
   to zero.
5. During consuming cleanup, validate the same header provenance before moving
   the owner. Drain residents and existing buffers as before, then explicitly
   destroy `take(&mut cache.index)` **before** moving the header into
   `CacheCleanupTail`. The header stays charged while proof, owner, failure,
   return and caller storage retire. Only `CacheCleanupTail::complete` refunds
   it after the existing drop helper ends. A dropped/uncompleted tail continues
   to leave its header charged. Foreign-header preflight must retain the owner.
6. Retain all measured inventories: concrete `Partial`, cache owners, Option and
   Result shapes, scratch slices, index helper records, Vec headers, helper
   borrows, construction and cleanup transfers. Existing `size_of` formulas in
   cache, execution and foundation automatically incorporate the smaller ticket
   arrays. Do not remove conservative transfer or helper terms merely because
   the index payload now shares a ticket. These are named-object envelopes,
   not allocator-overhead, stack-high-water or RSS claims.
7. Shared FrozenMode, all-chain validation, 64-entry capacity, strict LRU,
   pins/owner/nonce behavior, mutation precharging and atomic publication remain
   byte-identical. No limit, dependency, capability or public/native contract
   changes. Preserve original refusals; a finite transient headroom result does
   not authorize another full-target attempt.

The current header already has the required lifetime. In `Partial::cleanup`,
the payload can be destroyed before `drop_reserved(self, header)`. In ordinary
cleanup, the header moves through the existing tail whose completion first
drops caller storage. Grouping therefore uses an existing longer-lived
reservation; it does not refund an allocation while it is reachable or merely
hide an extra ticket. The fixed 192 bytes remain charged even on construction
paths that fail before allocating the vector, which is conservative.

## Measured comparison on this host

The finite prototypes use Rust/Cargo 1.99.0 on aarch64-apple-darwin. Values below
are bytes measured from concrete Rust layouts and current formulas. Grouped
values come from the actual modified copied implementation. The inline column
is a layout-only minimum, not an executed or qualified implementation.

| Quantity | Integrated vector/ticket | Grouped vector/header | Inline array minimum |
| --- | ---: | ---: | ---: |
| Cache owner | 1,040 | 1,016 | 1,184 |
| Partial owner | 928 | 904 | 1,080 |
| Cache cleanup envelope | 62,696 | 62,576 | 64,088 |
| Cache header reservation | 63,072 | 63,120 | 64,608 |
| Cache construction envelope | 57,896 | 57,752 | 59,288 |
| Cache operation envelope | 88,294 | 88,294 | Not qualified |
| Foundation envelope | 269,616 | 269,424 | Not qualified |
| Fixed reservation, default 64 entries | 89,376 | 89,232 | At least 90,720 |
| Composed execution header | 11,696,664 | 11,695,392 | Not qualified |
| Composed construction envelope | 1,073,920 | 1,072,912 | Not qualified |
| Composed positive cleanup envelope | 159,400 | 159,112 | Not qualified |
| Composed positive active envelope | 966,928 | 966,112 | Not qualified |
| Composed positive final envelope | 40,152 | 40,104 | Not qualified |

The grouped header increases by 48 bytes because its 192-byte payload addition
is offset by reduced owner/transfer layout. Total fixed reservation falls by
144; the index payload has not disappeared. The separate three buffer payloads
total 26,112 bytes, so grouped fixed accounting is exactly 63,120 + 26,112.
All four real allocations still request 26,304 bytes, including the index.

The inline shape places `[u8; 192]` in the cache owner and
`Option<[u8; 192]>` in the partial owner, allowing a hypothetical implementation
to postpone initialization. Its measured owner/partial growth is 168/176 bytes
over grouped storage. Layout-only cloned cache formulas include measured owner,
Option, Result, partial and standalone array transfer shapes; no array value is
created or initialized by this probe. The reported inline envelopes are lower
bounds because a safe initializer, its late Option-array transfers and any new
helper/return temporaries still need a concrete complete inventory. No missing
array, Option tag or helper storage is treated as free or as already qualified.

An immediate `[0; 192]` in the current `Partial::new` would write before the
header admission and bypass the current initialization charging. A safe late
array design needs full precharging before materializing the array, correct
partial-failure handling, and reservations for every actual array transfer.
It must also account all larger containing execution/foundation objects. There
is no need to take on that separate proof for this ticket correction: grouping
keeps the exact existing allocator and per-byte initialization path and has
direct finite lifecycle evidence.

## Finite evidence and boundaries

An independently authored diagnosis control uses the actual
`SwiftReactorInstance::construct`, its actual control/cache/WASI/state owners and
the existing fully validated synthetic 100-function module. It pins/releases
64 distinct decoded residents. This is a finite owner probe, not execution of
the full target or its Initialize path.

| Finite actual composed owner | Integrated | Grouped |
| --- | ---: | ---: |
| Constructed live tickets | 22 | 21 |
| After 64 residents | 86 | 85 |
| Real additional transient admissions accepted | 0 | 1 |
| Next refused attempt / unchanged limit | 87 / 86 | 87 / 86 |
| Final current combined bytes / tickets | 0 / 0 | 0 / 0 |

The transient request is deliberately a zero-byte diagnostic admission through
the real ledger. It proves the exact ticket boundary and does not claim to be
the full-target requester. Both runs preserve TicketInventory as the first
cause after consuming original-owner cleanup and report no cleanup invariant.

Both prototypes perform four constructor allocations requesting 26,304 bytes,
exactly 832 cache credits and 192 zero index cells. Every one of the 832 shorter
work budgets fails closed and consumes cleanup to zero. Cancellation at every
observed constructor checkpoint does likewise: 852 integrated and 851 grouped.
The one removed checkpoint is the removed separate index admission; actual
initialization charging and its 192 writes remain unchanged. A measured
consuming cleanup destroys the buffer/proof payload before tail completion,
while the cache category retains exactly the header reservation. Completion
then retires it to zero with no allocation or added cache work.

The grouped copied cache suite passes all 31 tests (29 existing plus two
diagnosis controls). This includes deliberate collisions, head/middle/tail
removal, reuse/reinsertion, bounded malformed chains, LRU/all-pinned behavior,
every mutation boundary, four allocation/capacity refusals and owner/nonce
safeguards. Initial suite runs are retained: 29 passed/two failed and then
30 passed/one failed. Their failures were old literal ticket-count and header
capacity assertions. The copied expectation patches change the old 74 count
to 73 at all three assertions and place the zero-entry minimum at
header + patch payload, since header already includes index payload. The
allocation count remains four and the zero-entry fixture still makes two
allocations. These are explicit test changes, not passing reinterpretations.

The grouped copied execution/construction suite passes 21 tests and the existing
lifecycle suite passes 49. One fresh literal FrozenMode trace test passes on
each prototype; their complete extracted observation bytes are identical.
The final two diagnosis controls are rerun on each prototype with explicit
zero assertions for all six live categories after the original owner retires.

The clean handoff separates the one-file production patch from the necessary
one-file accounting-expectation patch, without diagnosis wiring or controls.
The production-only closure is
`3cafd3345b9073aeec5e4f576dbe8f6c942d88f790b495970b17e5050f5762ab`;
with accounting expectations it is
`2d2c8c7af0bff7bf99b1ba4abe292b3ba283b2ddfafaab92293e7a18f963eb60`.
Both have 132 members. The clean closure is preserved and **has not been
executed or selected**; executable evidence belongs to the explicitly separate
copied overlays whose production bytes match it. Root must select an isolated
implementation and independent review must repeat allocation/partial/header
lifetime, metering, ticket-boundary and consuming-cleanup checks on that exact
selection before integration.

The remaining command receipts, literal Frozen trace comparison, cleanup,
source manifests and packet seal are linked below. Debug host tests do not
qualify physical iOS/Android, native parity, a new full-target run, performance,
published FieldLog packages, signing, stores, customer/operational or final GA
gates. The actual refused full-target ticket owner remains unobserved.

[Diagnosis receipt](../verification/swift-index-ticket-storage-diagnosis/receipt.json),
[seal](../verification/swift-index-ticket-storage-diagnosis/seal.json),
[prototype production patch](../verification/swift-index-ticket-storage-diagnosis/grouped-prototype.patch),
[clean production patch](../verification/swift-index-ticket-storage-diagnosis/implementation-production.patch),
[clean accounting patch](../verification/swift-index-ticket-storage-diagnosis/implementation-accounting-expectations.patch),
[clean handoff](../verification/swift-index-ticket-storage-diagnosis/clean-handoff.json),
[controls](../verification/swift-index-ticket-storage-diagnosis/controls.rs),
[initial failure](../verification/swift-index-ticket-storage-diagnosis/commands/grouped-cache/receipt.json),
[second failure](../verification/swift-index-ticket-storage-diagnosis/commands/grouped-cache-final/receipt.json),
[qualified cache run](../verification/swift-index-ticket-storage-diagnosis/commands/grouped-cache-qualified/receipt.json).
