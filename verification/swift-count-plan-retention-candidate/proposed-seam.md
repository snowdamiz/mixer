# Proposed private seam, frozen before policy implementation

The root-selected work is an isolated finite feasibility candidate. This proposal
does not select live integration or a full target. The accepted finite model and
its eight-credit estimate are unchanged; this candidate independently charges
57 conservative source-policy credits per completed miss. No policy retuning is
permitted after its results.

`CacheMode` receives an associated `ScanOutcome` type, an infallible
`scan_counts(&ScanOutcome) -> Counts`, a fallible miss-only
`prepare_miss_publication(&mut Meter) -> Result<(), Failure>`, and an infallible
`miss_timestamp(&ScanOutcome, &Meter) -> u64`. FrozenMode uses exactly Counts,
returns its copy, performs no preparation and returns `meter.work_used()`.
Its owner, scratch, fields and generic concrete layout remain unchanged.

SwiftMode uses a 32-byte repr(C) outcome containing Counts, a repr(u8)
Cold/Reused tag and seven explicit zero reserved bytes. A successful original
full-identity count-plan probe yields Reused before any scan replacement. Empty
and different-function cells yield Cold. Matching function with mismatched
offset, length or type rejects through the existing identity error. The original
scan/build/decode validation remains complete and fail closed.

The existing generic hit branch receives a literal copy of its original common
publication tail and returns there. Miss publication duplicates that same tail,
using the outcome only in its timestamp expression. Thus no new helper,
predicate, policy value, debit or allocation executes on the resident-hit path.
After a successful build and the existing publication check, the new preparation
debit completes before resident_insert can modify its index. It is failure-cleaned
like existing resident_insert failure: drop the attempted decoded owner, clear
construction usage, return the original error, publish no attempted slot or pin.
The infallible timestamp helper executes after the existing insert, decode,
pin-statistics and pin-count writes, at the same timestamp position as baseline.
Reused therefore receives the ordinary current work counter including insertion
work; Cold receives zero. It introduces no fallible operation after insertion.

## Measured inventory and consumers

The actual arm64 Rust layout probe measures:

| Exact type/value | Bytes |
| --- | ---: |
| ScanOutcome | 32 |
| Result<ScanOutcome, SwiftRunFailure> | 1,096 |
| Result<Counts, SwiftRunFailure> | 1,096 |
| Result<(), SwiftRunFailure> | 1,096 |
| Original proposed named inventory | 3,464 |
| Complete enlarged candidate inventory | 6,824 |
| Three disjoint complete candidate inventories | 20,472 |

One complete candidate inventory has the original three complete outcomes,
three complete typed outcome Results, two usize indices, three u64 timestamps,
four decision booleans, and four thin borrows. The four borrow roles are the
counts helper's outcome, preparation's mutable meter, timestamp's outcome and
timestamp's shared meter. Its additional fields are three complete Counts
copies for the new extraction boundary, and three complete
Result<(), SwiftRunFailure> values for the new preparation boundary. No aggregate,
error representation, discriminant or padding is inferred from its Ok payload.
All four boolean and both index slots remain reserved even where the Rust source
uses an inline expression. Three whole inventories cover source, argument/return
and caller roles in addition to all existing inventories.

The exact formula is
`3 * align8(3*32 + 3*1096 + 2*8 + 3*8 + 4 + 4*8 + 3*24 + 3*1096) = 20,472`.
The candidate adds this entire amount to the existing Swift operation-phase
reservation. Existing construction/operation/generic inventories and Counts
Results remain fully reserved and unmodified. The existing PlanInventory output
continues to account for the unchanged decode::scan_borrowed Counts result;
the new outer Swift scan result is wholly separately reserved here.

Measured DeltaExisting is zero: PlanInventory stays 1,304, OperationScalar stays
760, OperationBorrowChain stays 976, ConstructionScalar stays 296,
ConstructionBorrowChain stays 184. No changed concrete associated output is
embedded in an existing owner or generic inventory. Slot remains 136 and resident
120. Header remains 92,128; cleanup remains 62,888; construction remains 61,880.
Operation moves from 92,350 to the expected 112,822 bytes, to be remeasured on the
implemented candidate. No persistent payload, allocation or ticket is added.

The existing phase preparation enlarges the already owned construction ticket
before the phase, generic fields, scan values or helper results are constructed.
The same phase complete consumes return storage and restores the previous bound
on success and failure. This raises absolute reservation bytes during Swift hits
as well as misses and can cause earlier memory admission failure under unchanged
limits. It is expressly **not hit-byte parity**. Root authorized measuring this
limitation in the isolated feasibility candidate. No old slack is borrowed and
no new under-accounted miss preflight is proposed.

## Exact debit schedule and failure prefixes

All original work calls remain. The candidate adds these complete blocks, with
no refunds and no partial new resident publication:

1. After original identity validation/copy or a successful complete scan, before
   constructing/returning the outcome and before cold scan-plan replacement:
   `work(41)`. Thirty-three credits conservatively count the three complete
   outcome payload copies (three Counts fields, one tag, seven reserved bytes
   each). Seven cover the new counts-extraction borrow, three field reads and
   three copied fields. One covers its helper invocation. Classification is the
   tag value in these aggregate copies; existing identity probes keep all their
   original debits. The infallible later extraction has already been precharged.
2. After build and existing Publication check, before resident_insert's first
   live mutation: `work(16)`. One preparation-meter borrow, three preparation
   Result transfers, two timestamp borrows, one tag probe, one branch, one
   work-counter helper call, one counter read, three timestamp transfers, one
   timestamp write and two preparation/timestamp helper invocations are charged.
   Baseline already accounts its ordinary publication operations; deliberate
   overlap is conservative. The timestamp helper is infallible after this block.

Failure before the first added block never constructs/publishes an outcome or a
new plan. Failure inside that block retains prior residents and the original
plan. Failure during original cold plan-publication debit also retains the old
plan. A successful scan-plan replacement remains published through later
capacity/planning/build failure, as before. Planning failures preserve residents;
original per-slot remove/drop failures preserve exactly their completed eviction
prefixes. Failure at the second block drops the built attempted owner and
publishes no index/slot/pin. Failure during original resident_insert also drops
that owner. After successful insertion all remaining publication is infallible.
Original attempted misses, sticky failures, release of held pins and destructive
cleanup semantics remain authoritative.

These are auditable source-policy work groups, not a claim to count machine
instructions, memcpy bytes, stack footprint or CPU cycles. Actual complete VM
CacheWork, allocator requests/bytes and reservation traces will be measured.

## Differential and selected host verification plan

Run pristine-copy and candidate generic private tests plus public generic cache
and allocation integration tests. Add the same actual FrozenMode finite success,
failure/work-prefix and layout probe to both copies and compare its complete
normalized reports. Run original Swift cache tests in both copies; retain any
changed expected policy test as a failure rather than silently rewriting it.
Append the exact retained six-trace test bytes to both copies and compare actual
interval work and cumulative/interval decodes. Separately measure 256 hits for
CacheWork, allocation requests/bytes and every checkpoint ledger snapshot.

New Rust controls will use actual validated owners, opaque pins and borrowed
views; original work/cancellation boundary hooks; every shorter debit prefix;
individual allocation/capacity failures; committed partial eviction, failed scan,
build and publication cleanup; all-identity corruption; true original-plan
collisions; adversarial phase and collision sequences; and narrow memory
admission boundaries. Existing consuming cleanup must return combined bytes,
tickets, resident entries and pins to zero. Tests are finite host tests only.
There is no native runtime, UI/capture, full target or excluded hosted execution.
