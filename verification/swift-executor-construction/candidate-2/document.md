# Private uninitialized Swift owner construction

This bounded slice implements retained-descriptor State construction, composition
of the original runtime control/proof with the accepted cache and actual WASI,
and consuming cleanup of an uninitialized owner with empty execution stacks.
It implements no interpreter, `_initialize`, corpus invocation, activation,
public constructor/export, target runner, or physical-device work. The binding
product plan and all pending algorithm, target, published FieldLog, platform,
signing, store, customer, operational and GA gates remain unchanged.

The fourteen `swift_construction_*` tests are narrower producer qualification.
They do not stand in for any of the frozen twenty full executor acceptance
functions. Accounting maps below are a concrete candidate for independent root
review, not a claim of final executor/accounting acceptance. Candidate 1 is
preserved under `verification/swift-executor-construction/` and is blocked by
independent accounting findings. Its original document is retained as
`historical-candidate1-construction.md`. Candidate 2 supersedes its constructor
error-return protocol below. Its positive exact-type supplements are frozen in
the independent `candidate2-api/proposal-freeze.json`; root acceptance of the
incorporated source remains pending.

## Private contracts

`SwiftExecutionState::prepare(&mut control, &cache, &wasi, cursor)` validates the
actual WASI pairing, then the cache/control header, before ordinary checks and
enlargement of the one existing Construction ticket. The returned
`ExecutionConstructionPhase` borrows all three owners, permits one `construct`
attempt, and `complete<T>` drops returned temporary storage before restoring its
exact previous bound. Dropping a phase without completion retains its charge.
The chosen State/instance/frame/operation/parts/phase fields remain literal.

`SwiftReactorInstance::construct(&mut Option<(RuntimeControl, AdoptedProof)>,
grants, wasi_budget, started, cursor)` checks provenance and admits the outer
construction envelope while the caller's exact pair is intact. Preparation
rejection leaves that slot `Some` without allocation or destruction. After the
single take, nested cache, WASI and State phases complete inside out; successful
composition restores the exact outer bound and returns `Lifecycle::Uninitialized`.
No Ready owner is created. No proof is revalidated, copied, re-adopted or replaced.

The constructor returns `Result<Self, ConstructionFailure>`. A preparation
rejection returns `Rejected(SwiftRunFailure)` while the original pair and its
foundation stay charged. An error after take drains acquired component payloads
and returns `Cleanup(ConstructionCleanupTail)`. This must-use, non-Clone tail
wraps the existing ExecutionCleanupTail and exact previous outer bound, retaining
the original control, optional same execution header and enlarged Construction
charge through the whole constructor Result/Option return. It does not report a
final zero inside the constructor.

The caller extracts the tail and supplies every large possible-owner Result/
Option/pair/partial return object to its unit completion method. A helper ends
those objects and returns only HeaderCompletionParts plus the previous bound;
a full-statement destructure precedes exact outer restoration, same-header refund
and foundation consumption. Only copied diagnostic outputs survive. An outer
restore error also drains the owner and returns this deferred tail. Its rejected
Construction charge remains visible. Omitted completion retains its charge.

`SwiftReactorInstance::cleanup_owned(&mut Option<Self>)` requires an owned slot
with its original control. While the slot remains intact it pairs WASI, checks
the cache and all seven State tickets, and rejects nonempty frame/value/control
stacks or cache pins. A rejection leaves the owner in its slot. This is deliberate
bounded construction cleanup; populated interpreter unwind remains pending.
After take it drops each arena before refund, removes the actual initial page
debit, drains the cache while actual WASI lives, captures actual final WASI usage,
destroys WASI, and returns the same execution header in `ExecutionCleanupTail`.
Its accepted completion helper consumes caller owner/Result/Option storage
before the final header refund, then consumes the original control. Only copied
failure/usage outputs survive that boundary. Cleanup allocates nothing, spends
no work, and performs no ordinary cancellation or deadline check.

## Initialization of storage

State requests values, controls, frames, memory, table and globals in legacy
order. Each byte product is checked before admission and `try_reserve_exact`;
actual capacity must equal the request. Zero capacities issue zero allocations.
The sole State header includes State, the composed-owner residual and permanent
cleanup envelopes. There is no second execution header or ledger.

The retained memory minimum is compared with the narrowed page budget before
any State admission/allocation. Memory is zeroed in chunks of at most 4,096 bytes;
table entries become None. Numeric globals use their exact retained slices and
absolute first-opcode offsets. A dedicated bounded reader checks each byte,
signed/unsigned LEB width, numeric type, float bits, `end`, and full consumption.
The old frozen initializer remains byte-for-byte unchanged.

All data ranges, then all element ranges, are checked before any active payload
copy. Retained payload cursors include empty segments. Application preserves
source order and overlap; element readers consume exactly the retained count and
slice and check each function's structural signature exists. The base work
schedule remains memory bytes + table entries + globals, 16 per global constant,
one per range descriptor, then exact data/element payload length before effects.
Checks remain inside loops and after final chunks. Adding initial live pages is
the last fallible publication step; failed partial builders have acquired no
page debit and never subtract an earlier owner's pages.

## Candidate named-object accounting

All formula evaluation is compile-time. `construction_bytes()` and
`execution_header_bytes()` copy precomputed checked Options; they create no
runtime formula arrays, iterator or fold. Counts below reserve source, argument
and returned positions separately. Payload tickets remain disjoint. These are
requested logical object bytes, not allocator overhead, RSS or stack bounds.

| Additional whole inventory | Count | Roles and live call window |
| --- | ---: | --- |
| ConstructionBootstrapInventory | 1, foundation | Pair-slot/owner borrows and constructor grants/budget/Instant arguments before take; State preparation borrows; actual AccountedWasi checked_usage, CacheControl/check_header and control owner/admission borrow, Option, scalar and snapshot-return objects. Its 2,216 bytes are admitted by root's foundation change before entry; the later phase is never used retroactively. |
| ConstructionDescriptors | 3, outer/State phase | Memory/table/global/segment views and Option returns in construct_partial/initialize_segments; byte requests, budget, type, numeric bytes/bits/shift/width in constant/signed/byte. Three positions account caller, helper argument and return independently. |
| ConstructionTransfers | 3, outer/State phase | Actual adopted pair slot/take, phase Results, ticket/allocation Results, unit/value/scalar Results, checked endpoint and composed input transfers. Nested phase owners continue to carry their independently accepted additional envelopes. |
| ConstructionBorrowChain | 1, outer/State phase | Constructor and State helper reborrows through construct_partial -> initialize_segments/constant -> signed/byte -> checked/work; vector/slice arguments, loop/copy scalar positions, Cursor and temporary observation/fault transfers. |
| ConstructionIterationInventory | 3, outer/State phase | Complete global/table/descriptor/element Range and unsigned StepBy objects, float IterMut and Option item, retained borrowed descriptors, typed Value/i64/u32/u8 Result shapes, TryReserveError and error callback capture roles. They do not use integer or diagnostic padding as iterator slots. |
| CleanupPreflightInventory | 1, same permanent execution header | Whole intact-slot owner/component/header Option borrows, six-ticket slice Iter and Option item, cache usage return, cursor/error-callback transfers and nonempty predicates. It remains charged through component cleanup and is not present after the final tail helper ends. |

The original eight-map terms remain separately reserved: State/instance and
partial owner source/return/caller objects; their possible-owner Result/Option
slots; nested construction phases; scalar-reader transfers; and caller copied
diagnostics. Cleanup uses the original whole-owner slot/source/argument, State,
tail source/return/caller and Result slots, cache slot/tail/outcome, WASI source/
argument and Results, actual observation copies, arena Vec/ticket transfers and
caller diagnostics. Construction-only cleanup never creates a frame/pin guard.
Operation, pin-return and growth algorithms/maps are still pending.

The retained final foundation group is unchanged: two diagnostic output borrows,
sequential refund/record/finish call groups, four failure/four usage/six ticket
and six optional WASI classes, plus the accepted 864-byte final group maximum.
The new bootstrap is additive; no historical class or old conservative cache row
is reclaimed. `layout-map.json` records actual production/test Debug/Release
sizes, alignments and every selected field offset. Root independently reviews
the proposed counts against authored success/error/cleanup call chains.

Candidate 2 additionally preserves all rows above and charges the independently
frozen `ConstructionPositivePreflight`, `ConstructionPositiveActive`,
`ConstructionPositiveCleanup`, `ConstructionPositiveFinal` and unit hook argument
inventories. Its 615 concrete classes map 5,004 array indices one-to-one to named
source/helper/receiver/return/callback/callsite argument positions; fifteen
additional unit-hook positions have an explicit test-only inventory. Empty
Option/Result receivers, complete closure captures, generic Vec reference kinds,
PartialState borrows, new ConstructionFailure/cleanup-tail/possible-owner return
shapes and end-phase completion objects have their own positive classes.
No old class is replaced or used as a same-sized alias for a different type.

The private retained-descriptor supplement lives in the owning Swift validator
module so its actual private Buffer/metadata types remain private. Its 2,480-byte
constant covers only reached State descriptor getter paths after enlargement;
it is added to construction, not the bootstrap. There is no executable getter
change or production metadata probe. The positive final group is separately
added to the foundation; the accepted 864-byte final group is retained.

| Candidate 2 checked bound | Production | Unit instrumentation |
| --- | ---: | ---: |
| Foundation including old classes and positive bootstrap/final | 267,800 | 268,336 |
| Additional construction | 1,062,312 | 1,065,072 |
| Same execution header including positive cleanup | 207,352 | 208,312 |

These conservative logical reservations include mutually exclusive source
branches without reclaiming their slots. They are not stack measurements or a
claim that the totals alone prove coverage. The source-bound independent map and
each concrete field/callsite position are the acceptance input. Runtime limits,
ticket count, fixed owner layouts and work schedules are unchanged.

## Executable evidence and limitations

The owned same-ABI fixture has 29 definitions, 34 unchanged Preview1 imports,
the real 584-page minimum and 46,713-entry fixed table. Its globals cover all
numeric types, preserved NaN/signed-zero bits, both signed minima and padded
negative LEBs. Ordered data/elements overlap; empty data reaches the memory bound.
Malformed reader probes are separate bounded reader tests and do not fabricate
a validated execution authority.

Tests observe all thirteen integrated cache/WASI/State allocation ordinals and
all six State unexpected-capacity reports, first-cause retention, actual WASI
ArgsSizesGet observations, exact base work, zero stack capacities, page-minimum,
State/Combined rejection before allocation, selected work/cancellation prefixes,
one-shot State construction and exact outer restoration. A deliberately invalid
restore bound drains all actual allocations while retaining the one rejected
Construction ticket. Valid cleanup observes zero final current bytes/tickets and
no allocation/reallocation. Nine selected cancellation samples are not complete
all-prefix or every-loop deadline qualification.

`verification/swift-executor-construction/collect.py` freezes VM inputs and
records revision/dirty state, source digest, tools, commands, outputs and exact
test counts. Production metadata exports exist only in the derived measurement
overlay; product source gains no public route. The full future executor remains
unaccepted, and no full 53,777,114-byte target was instantiated or executed.
