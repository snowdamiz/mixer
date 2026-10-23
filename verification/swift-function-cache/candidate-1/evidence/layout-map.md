# Private Swift cache named-object map

Implementation evidence only; independent/root cache acceptance remains pending.
`layout-map.json` is generated from the exact named Debug/Release test outputs
and the literal checked sums in cache.rs. It includes every chosen type's actual
size/alignment and every simultaneous conservative count. All figures are
logical requested payloads and named Rust object footprints, excluding allocator
overhead, compiler stack placement and RSS. No slack from another category or
live phase is used.

The current aarch64-apple-darwin cache header is992 bytes; the already retained
proof header is664, leaving328 exclusive bytes. Those328 explicitly retain both
original adopted ticket handles48, three Vec handles72, four optional cache
tickets96, copied usage96, owner/nonce16. The permanent cleanup sum is36760,
so one exclusive header ticket admits37088. The512-Patch buffer is16384 bytes;
64 Swift slots are8704 and64 pin records1024. Default fixed cache requested
capacity is63200; zero entry/pin limits omit their payload requests but retain
three fixed tickets. At most64 aggregate resident-or-incoming payload tickets
exist, and there is no per-pin or cleanup ticket.

Construction additionally reserves31880 on the same existing construction ticket.
The operation additionally reserves21120. Their complete literal type/count maps
are in JSON. These include caller-owned ConstructionReturnSlot (Option<Result>
1808) and OperationReturnSlot (Option<Result>1096), each with two conservative
transfer shapes. The tests take the final owner/diagnostic, leave the return slot
empty, and pass that actual slot into consuming complete before restoration.
Original large construction failure wrappers end an inner scope first. A final
Result<SwiftFunctionCache,SwiftRunFailure> or Result<SwiftFunctionPin,SwiftRunFailure>
is1096 bytes, exactly a whole named foundation failure-transfer slot; a ready
cache owner also remains under its already admitted permanent header. No partially
owned cache/error wrapper is silently assumed to disappear at a callee return.

Frozen legacy scratch remains9312 with the exact old formula: two4128-byte
PassStates, two32-byte Readers,64-byte bool plan,72-byte Meter, three200-byte
failures and256 scalar bytes. One scan wrapper frame has returned before the
build wrapper begins, so exactly one literal128-Patch PassState can coexist with
the new borrowed adapters. The conservative measured simultaneous named set is
6088, including three CacheParts, three CacheFields, two operations/policies,
three PassParts/function spans, two decoded owner transfers, four Counts, both
reader transfers, three failures, plan and the unchanged256 scalar allowance.
No512-element stack array or second Swift arena exists. Exact legacy field
sizes/alignments/offsets and122/126 observation lines replay identically against
the original Git engine under frozen-only/Swift+span, Debug and Release.

# Final cleanup transfer boundary

Caller cleanup preflight borrows its wholly intact Some(cache), validates actual
WASI provenance and intact cache header, then takes the slot. Rejected preflight
leaves that exact owner intact. After destructive entry, every remaining entry,
fixed buffer and whole adopted proof drains despite later invariant errors.
The actual three payload vectors are dropped before their aggregate refund;
the actual proof is dropped by root before its two original refunds. Cleanup
always returns the same header ticket in a tail, carrying first failure.

The successful Result/tail/owner moves and entry/vector/ticket/borrowed/fault
objects remain under the37088 header ticket, including the complete caller
Option and return scopes. `drop_cleanup_return_storage` consumes the tail and
actual supplied storage. Its frame, original1136-byte tail and failure field
have ended before any observed header refund. It returns only40-byte
CleanupCompletionParts: two borrowed handles16 plus the same optional ticket24.
Omitted completion retains the full header charge. No cleanup phase enlargement,
work, allocation, time/cancellation check or service occurs.

# Whole foundation slots after header refund

The root v3 upfront model is16504 and binds four SwiftRunFailure1096, four
SwiftRunUsage504, six ReservationTicket24 and six Option<WasiUsage>112, plus
three proof664/control1720/adopted712 objects each. The old two plain104-byte
WasiUsage allowance was rejected; the accepted root six-Optional amendment is
bound by verification/swift-observation-accounting/acceptance.json. Historical
failed/proposed evidence remains preserved, not silently rewritten.

Control slot1 is the sole actual RuntimeControl owner. Whole control transfer
slot2 is assigned to CleanupCompletionParts40 while completing this phase;
there is no simultaneous adoption/control move or enclosing live cache operation
phase using that slot. All ordinary phases have explicitly completed before
cleanup. Control transfer slot3 is reserved for final owned control consumption,
which can occur only after the tail's exclusive borrow ends. The helper's small
borrowed handles therefore use an entire named phase-alternative transfer slot,
not padding or presumed room inside the still-live control. The three proof and
adopted slots are not repurposed: the actual cache proof has already been dropped.

Four failure slots cover caller outcome, refund Result, fail's local/return
transfer and final output/record_cleanup transfer. All Option and unit Result
failure shapes are exactly1096. The failure stored inside the actual control
belongs to control slot1. Returned usages already nested in failures/control are
counted by those owners. Four standalone usage slots cover usage local/return,
fail's at_failure transfer and record_cleanup's local/after_cleanup transfer.
A refund Result scope ends before record_cleanup begins.

Six ticket slots cover optional header extraction and forwarding through the
completion tuple, drop_reserved and refund, including source/destination moves.
Option/ticket shapes are both24. No replacement ticket is admitted. Six optional
WASI observation shapes cover the retained caller observation (when present) and
nested drop_reserved/refund/cleanup_fault/fail/usage arguments, exactly as in the
accepted root global call-chain map. Cache completion retains no local copied
observation; it samples actual context usage at each boundary. Actual usage
returned inside SwiftRunUsage/SwiftRunFailure is already counted by that owner.
No seventh external observation copy is assumed free; composed executor callers
must separately reserve their own named outer copies until their own final tail.

The tests measure both destructive cleanup and tail completion allocation
intervals, assert construction is already at its foundation floor, preserve
actual WASI/control charges, and distinguish at_failure from after_cleanup.
Deliberately injected foreign-ticket corruption conservatively retains the
unusable foreign ledger charge; it is not reported as a clean zero-ledger run.
All honest whole-owner closures finish at zero combined bytes and tickets.
