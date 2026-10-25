# Count-plan Rust candidate rejected after finite measurements

The isolated count-plan-aware cold-insertion candidate is rejected for live
integration and a full-target retry. It improves complete engine CacheWork on
three of the six frozen finite traces and regresses on three. It also requires
20,472 additional operation reservation bytes and fails memory admission where
the unchanged baseline succeeds. No live VM source, production limit, frozen
model, hosted lane or existing result was changed.

Root separately selected this finite implementation after accepting the earlier
model result. The selected [private seam and complete debit schedule](../verification/swift-count-plan-retention-candidate/proposed-seam.md)
is hash-bound by [the root selection receipt](../verification/swift-count-plan-retention-candidate/root-selection.json).
This selection authorized an isolated Rust feasibility measurement. It did not
select integration or an actual-target run. Root subsequently agreed to preserve
and reject the measured candidate without retuning.

## Implemented policy and ownership

Two fresh copies were made from exactly the 132 live VM names in the retained
baseline manifest, using `vm/` as their base. Their pristine closure is
`16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`.
The candidate changes only those owned copies. Exact pristine, instrumented
baseline and candidate source archives, member manifests and patches are in
[the candidate packet](../verification/swift-count-plan-retention-candidate/).

The original 512-cell count-plan probe supplies a transient Cold/Reused outcome
before a successful scan can replace its cell. Matching function, body offset,
length and type are required for Reused. Empty cells and different-function
collisions remain Cold; an equal function with different immutable identity
fails through the existing error. No new persistent history, decoded owner,
slot field, allocation, ticket or dependency was introduced.

Ordinary lookup, complete decode/build validation, resident index, pin authority,
victim scan, slot tie order and byte-pressure planning remain intact. A cold
successful miss receives replacement priority zero. A reused miss receives the
ordinary current-work timestamp, including completed insertion work. A resident
hit uses a literal copy of its original publication tail. Generic FrozenMode
retains its Counts output and measured concrete layout.

All fallible preparation precedes resident-index mutation. Scan publication can
survive a later capacity/planning/build rejection. Planning failure preserves
residents. Failed eviction/build/publication preserves the actual completed
eviction prefix, drops the attempted decoded owner, publishes no attempted pin
or slot and preserves the original sticky failure. There is no whole-miss
rollback promise. A sticky terminal runtime cannot retry merely because a
successfully completed scan remains in its plan table.

## Actual work results

The exact retained six-trace Rust test bytes ran against both copies. Fresh
baseline rows exactly reproduce the historical baseline engine stdout.
The table excludes warm-up decodes and work. Historical raw decode counters
include sixteen warm-up decodes on every row except cyclic65; this subtraction
is explicit in [the comparison](../verification/swift-count-plan-retention-candidate/comparison.json).

| Finite interval | Baseline decodes | Candidate decodes | Baseline work | Candidate work | Work change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hot16 / stream128, four rounds | 576 | 512 | 1,558,624 | 1,461,008 | -97,616 |
| Cyclic65, three rounds | 195 | 132 | 406,583 | 303,416 | -103,167 |
| Expensive hot / cheap cold | 576 | 512 | 248,012 | 150,228 | -97,784 |
| Cheap hot / expensive cold | 576 | 512 | 1,444,044 | 1,460,948 | **+16,904** |
| Uniform hot / cold | 576 | 512 | 222,412 | 232,148 | **+9,736** |
| Expensive old16 to twelve cheap64 cycles | 64 | 81 | 17,440 | 25,918 | **+8,478** |

The original model's eight-credit estimate remains unchanged and unqualified as
actual work. This implementation precharges 41 source-policy credits before
outcome construction/return and cold plan replacement, plus sixteen before
miss publication: **57 per completed miss**, zero per resident hit. Its complete
outcome, extraction, preparation and timestamp operations are named in the
frozen implementation schedule. These are conservative source-policy groups,
not machine instruction, memcpy, stack, CPU or RSS measurements. The table is
actual complete VM CacheWork, including all original costs.

The actual cold, reused and three-victim probe operations respectively change
from 129 to 186, 119 to 176 and 204 to 261 work credits: exactly 57 each. Every
shorter work allowance and every cancellation checkpoint is exercised for cold
and reused paths. The phase control remains 81 decodes after 64 cycles too;
old64-to-new64 turnover, including a deliberate count-plan collision phase,
remains 128 versus 64. These favorable or adverse finite observations do not
provide an actual-target call-order forecast.

## Measured memory and hit behavior

The implemented `repr(C)` ScanOutcome measures 32 bytes. The exact
`Result<ScanOutcome, SwiftRunFailure>` measures 1,096 bytes, as does the new
preparation `Result<(), SwiftRunFailure>`. Each dedicated inventory contains
three whole outcomes, three whole outcome Results, three additional Counts,
three preparation Results, two indices, three timestamps, four decision booleans
and four thin borrows. Its 25 fields occupy 6,820 bytes plus four bytes padding.
Three complete 6,824-byte inventories reserve **20,472 bytes**. All named field
sizes and offsets are retained in
[the inventory report](../verification/swift-count-plan-retention-candidate/inventory-fields.json).

Measured DeltaExisting is zero. PlanInventory stays 1,304 bytes, operation scalar
and borrow inventories stay 760 and 976, construction scalar and borrow inventories
stay 296 and 184. Slot stays 136, resident 120, header 92,128, cleanup 62,888 and
construction 61,880. The entire added inventory is reserved independently; no old
slack pays for a new value. The existing operation ticket is enlarged before
the phase exists and consumed/restored through its existing completion boundary.

Swift operation reservation increases from **92,350 to 112,822 bytes**. The
constructor still makes five allocator requests totaling 54,976 bytes in the
selected fixture, and its work remains 4,928. No extra persistent payload or
ticket is added; the selected trace peaks remain 73 tickets under the fixed 86
ceiling. All production byte/work/count/deadline limits remain unchanged.

Both copies execute 256 resident hits for **2,048 work credits**, zero allocator
requests and zero allocated bytes. Their eleven actual hit checkpoints have
identical relative work, order, cache bytes, tickets, pins and entries. After
operation admission, candidate construction and combined reservations are
20,472 bytes higher. The unchanged hit fixture's admitted construction total
is 361,966 versus 382,438; combined total is 487,257 versus 507,729.
This is work/allocation parity, **not hit-byte parity**. The complete
[ledger differential](../verification/swift-count-plan-retention-candidate/hit-ledger-differential.json)
preserves absolute values, including the identical pre-admission checkpoint.

With only 92,350 or 112,821 bytes of operation headroom under the existing
combined-byte ceiling, baseline preparation succeeds while candidate preparation
fails before allocation. Candidate succeeds at its measured 112,822 boundary.
These earlier memory-admission failures are retained as regressions, not
discounted against the eight-credit model or hidden in a cache payload total.

## Verification, retained failures and disposition

Pristine and candidate generic private suites each pass five methods. Their
public generic cache suites each pass nine methods plus one allocation method.
The added actual FrozenMode differential compares **109 identical records**:
owner/field/meter/scratch/associated-output layout, decoded IR, resident state,
pin records/nonces/statistics, all selected miss work prefixes and cancellation.
Its [report](../verification/swift-count-plan-retention-candidate/generic-differential.json)
does not substitute syntax inspection for execution.

The pristine original Swift cache suite passes **39 methods**. The candidate
passes **37 and fails two original baseline-policy observations**. One expects
288 baseline decodes and sees 225; the other expects a cold insertion's timestamp
to equal current work and sees zero. Those original assertions remain intact,
and their failures are retained. They are separate from the new finite suite:
**eight baseline methods and nine candidate methods pass**, followed by the
three unchanged common-trace methods in each mode.

New actual Rust checks include 65 capacities and 24,576 independently modeled
slot transitions per mode; original-plan collisions and all identity/count
corruptions; an opaque held pin and unchanged borrowed instruction allocation
across turnover; a malformed real scan with no published plan; all shorter work
and cancellation prefixes; three allocation-failure ordinals; scan retention
through later failure; real all-pinned rejection; and three-victim byte pressure
with observed completed eviction prefixes zero, one, two and three. The held
pin remains valid through those partial failures. Every successful consuming
cleanup control returns combined bytes, tickets, resident entries and pins to
zero. The two original policy-test panics unwind before their later consuming
cleanup, so they are not claimed as zero-ledger cleanup receipts.

The first candidate compile failure is also retained: an existing test-only
mismatched-count helper needed to extract Counts from the new output before
deliberately corrupting them. That adapter preserves its actual build-rejection
assertion. A separate first new-probe compile failure used an unavailable failure
kind name; it was corrected to assert the existing `all_entries_pinned` code.
Neither correction changes production policy or removes a failing observation.

The packet records commands, compiler/tool hashes and versions, exact source and
input hashes, raw streams and output hashes. The ordinary live closure and both
sealed model/review packets remain unchanged; root-owned execution-index drift,
if any, is recorded separately. All synchronous host children have exited. Owned
scratch copies, compiler products and temporary directories are removed after
device/inode ownership verification; source archives and evidence remain sealed.
No process discovery, native runtime, simulator/emulator, physical phone, UI,
capture, excluded hosted harness, full target, publication or credential action
was performed. These and independent integration review, immutable published
FieldLog consumption and all final acceptance gates remain unqualified.

Preserve this measured rejection. An independent result audit is the next
acceptance step for this packet. The missing ordered calls in the original
actual-target telemetry still prevent predicting whether a favorable synthetic
shape occurs there; the favorable rows do not authorize another full run.
