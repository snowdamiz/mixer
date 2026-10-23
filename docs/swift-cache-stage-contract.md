# Swift cache/decoder stage contract

Proposed bounded freeze for root review, 2026-10-23. This refines the accepted
`swift-reactor-execution-stage-design.md`; it does not change that design or
authorize target execution. Foundation `020f909` supplies the single
`RuntimeControl` and non-Clone tickets. Accounted WASI has a separate review and
is a dependency, not cache-lane ownership. All implementation acceptance below
is **pending**. The 53,777,114-byte reactor must not be instantiated, initialized
or invoked until root separately accepts its bounded runner.
Revision 2 incorporates accepted review findings R1-R3 from
`verification/swift-cache-contract-review/review.md`. Exact v1 artifacts and its
receipt remain under `verification/swift-cache-stage-contract/historical-v1/`.
Whole-cache implementation must wait for root prerequisite acceptance.

## Ownership and dependency freeze

| Owner | Allowed work / prerequisite |
| --- | --- |
| Root | `experimental/{descriptors,swift,policy}.rs` borrowed descriptors, root-owned control observation variants, Cargo/module wiring, API freeze, combined review and publication |
| Cache lane | `experimental/cache/{mod,decode,borrowed,tests}.rs`, new `experimental_swift_reactor/{cache,cache_tests}.rs`, separately assigned cache receipts; no validator/control/WASI/executor edits |
| WASI lane | Existing separately assigned accounted constructor/context ownership; no cache edits |
| Later executor lane | `ExecutionParts`, fixed state arenas and per-frame Swift pins after this contract's implementation acceptance |

Root must freeze descriptor signatures and observed control methods before cache
implementation. Root wires the new module; the cache lane cannot broaden its
file ownership to fix compiler dependencies. The cache exposes only private
pin/view/release/cleanup operations, no execution or public Swift constructor.

## Root-owned borrowed descriptors

All additions are `pub(crate)` or narrower, immutable, allocation-free borrows of
the original sealed proof. Keep `ValidatedSwiftReactor`, `ValidatedSpans`,
`Metadata<FrozenDeclaration>` and the existing public `SegmentView` literal
fields/layouts unchanged. Widen the existing private signature/global view
visibility only as needed; never expose `Metadata`, `Buffer`, writable slices,
an authority constructor or a legacy conversion.

```rust,ignore
SignatureView<'a> { params: &'a [Type], result: Option<Type> }
FunctionSpanView<'a> {
    absolute_index: u32, type_index: u32, body_offset: usize, body: &'a [u8]
}
GlobalView<'a> { ty: Type, mutable: bool, initializer: &'a [u8] }
SegmentExecutionView<'a> {
    destination: u32, count: u32, payload_offset: usize, encoded_payload: &'a [u8]
}
MemoryExecutionView { minimum: u32, declared_maximum: Option<u32>, host_maximum: u32 }
TableExecutionView { minimum: u32, declared_maximum: Option<u32>, host_maximum: u32 }
```

Freeze these `ValidatedSwiftReactor` method meanings (names may be harmonized
once by root before dispatch): `execution_signature(absolute: u32)` and
`execution_type(type_index: u32)` return `Option<SignatureView>`;
`execution_function(absolute: u32)` returns `Option<FunctionSpanView>` and rejects
imports, rather than interpreting the index as a defined-body ordinal.
`execution_global(index: usize)`, `execution_data(index: usize)` and
`execution_element(index: usize)` return the corresponding views; each collection
has a scalar `execution_*_count()`. Segment lookup preserves encoded source
order, including overlapping segments. `execution_memory()` and
`execution_table()` return their sealed descriptors: `host_maximum` means the
effective metadata maximum, memory 768 and table **46,713**, rather than the
independent policy table ceiling 65,536. The separate
`execution_global_initializer_offset(index: usize) -> Option<usize>` returns the
checked absolute start of the initializer expression in retained source (its
first opcode, including the expression's ending `end` in the borrowed slice).
It is O(1), returns None for an absent index and adds no `GlobalView` field.
Function bodies start at local-group declarations after their body-size LEB;
element payloads start after the element count, data payloads after byte length.
Preserve exact offsets for empty ranges. `execution_imports()`
returns `&[WasiFunction; 34]`, indexed absolutely without reparsing names.
`decode_policy()` returns only the existing closed private borrowed `Policy`.
The scalar source extent is always `source().len()`, independently of the
policy's 64 MiB ceiling. Every returned body/payload/initializer lies within that
exact retained allocation; offsets refer to the entire module. Bounds are already
sealed by complete validation, and failed descriptor access is a typed invariant.
No export name search or independently executable descriptor is introduced.

The common sealed `SnapshotView` minimally supplies `source() -> &[u8]`,
`defined_function_count() -> usize`, `imported_function_count() -> usize`,
`function(absolute: u32) -> Option<FunctionSpanView<'_>>`,
`signature(absolute: u32) -> Option<SignatureView<'_>>`, and the closed decoder
policy borrow. Its private implementations delegate the methods above or the
unchanged frozen metadata; they copy no metadata. Separate sealed decoder
policy adapters statically select Frozen/Swift getters and scratch rules.

## One algorithm, statically selected borrowed adapters

Add sealed private `SnapshotView` and `CacheMode` traits; only sealed
`ValidatedSpans`/`ValidatedSwiftReactor` snapshots and frozen/Swift modes implement
them. No trait object, callback, downstream implementation or stored policy enum
is permitted. The mode fixes its snapshot, slot, pin, usage, failure and operation
types at compile time; a frozen mode cannot receive Swift authority.

```rust,ignore
CacheParts<'a, M: CacheMode> {
    snapshot: &'a M::Snapshot,
    slots: &'a mut [M::Slot], pins: &'a mut [PinRecord],
    owner: u64, next_nonce: &'a mut u64, usage: &'a mut M::Usage
}
pin<M: CacheMode>(parts: CacheParts<'_, M>, absolute: u32,
                 operation: &mut M::Operation<'_>) -> Result<M::Pin, M::Failure>;
view<M: CacheMode>(parts: /* immutable checked parts */, pin: &M::Pin)
    -> Result<FunctionView<'_>, M::Failure>;
release<M: CacheMode>(parts: CacheParts<'_, M>, pin: M::Pin,
                     operation: &mut M::Operation<'_>) -> Result<(), M::ReleaseFailure>;
```

These are ephemeral field borrows, not stored replacement owners. The common
pin/lookup/LRU/planning/publication/release algorithm dispatches mode-specific
checks and accounting statically. Mode operations cover bounded work/checks,
counter preflight, entry admission/drop and pin issuance; they cannot mint proof.
`FrozenMode` uses the exact old `Slot`, `FunctionPin`, `Meter`, `CacheBudget` and
`CacheUsage`. `SwiftMode` uses `SwiftSlot` with one entry ticket,
`SwiftFunctionPin` with owner/slot/nonce, and Swift-only copied diagnostics.
Do not add a ticket, field or discriminator to any legacy stored type.

`FunctionCache::{new,pin,view,release}` remain thin frozen specializations with
the same signatures. Preserve literal `FunctionCache`, `FunctionPin`, `Slot`,
`PinRecord`, `DecodedFunction`, legacy `PassState` and `Meter` layouts, all public
enums/revisions/identities, allocation counts/requested bytes and usage formulas.
The frozen decoder wrapper retains its stack `[Patch; 128]`; `scratch_bytes()`
retains its two pass states/readers, 64-element plan-array size, meter, failures and
256-byte scalar allowance exactly. Here the plan array is `[bool; 64]`, not a
replacement heap/bitset. If extracted borrowed temporaries cannot fit the
existing model, stop for root review instead of changing reported legacy bytes.

## Decoder contract

Use one scan/build opcode algorithm with sealed borrowed policy/meter/state
adapters. Policy getters distinguish `floats`, `tables`, exact source extent,
parameters per signature, local groups, parameters-plus-locals, instructions and
function-inclusive control depth. Do not synthesize widened `Limits` or a
`TableMemoryV3` identity. Use existing owned `Operation`/numeric semantics.

The frozen wrapper preserves its old locals-only checks and exact work trace.
Swift checks `params <= 128`, groups `<= 256`, and checked
`params + declared_locals <= 256` in **both** passes. `Counts.locals` and the
decoded `locals` vector still mean declared locals only; entry payload accounting
uses that vector capacity. Later executor frames reserve parameters plus locals.
Count/build agreement compares declared locals, instructions and branch targets,
plus the same sealed parameter count/total invariant. Never allocate parameters
again as decoded locals or lose their contribution to the 256 ceiling.

The Swift cache constructor admits and allocates one `Vec<Patch>` with exact
capacity/length 512 and initializes it under `Work::Cache`; this is its third
fixed buffer beside slots/pin records. Sequential scan/build borrow that same
arena. No second arena, 512-element stack array or per-miss heap scratch exists.
Swift charges/checks every reset slot in each pass before use; patch writes and
publication are checked. A function frame counts toward depth 512, allowing 511
nested controls; depth 513 fails complete validation before a cache exists.
Retain valid 379-depth coverage and exercise the actual 512 boundary. Reset uses
one fixed documented credit per slot; other shared decode credits preserve the
old reader/local-expansion/instruction/target/patch schedule. Record additional
Swift descriptor/parameter scan credits explicitly, never hiding work in getters.

`Reader::byte/take`, LEB loops, local expansion, reset, instruction scans,
br_table loops, patching, allocation and final checks run through the operation
meter. `take` charges its byte count before access; no long unchecked loop or
bulk initialization is introduced. Both passes must finish inside the exact
body extent and agree before entry publication. Failures carry the absolute
function/body cursor and static code without allocating.

## Adopted ownership, tickets and cache accounting

Cache construction uses this private outer phase, following accounted WASI:

```rust,ignore
SwiftFunctionCache::prepare(control: &mut RuntimeControl, wasi: Option<&AccountedWasi>,
                            adopted: &AdoptedProof, cursor: Cursor)
    -> Result<CacheConstructionPhase<'_>, SwiftRunFailure>;
phase.construct(adopted: AdoptedProof) -> Result<SwiftFunctionCache, CacheConstructionFailure>;
phase.complete<T>(returned_phase_storage: T) -> Result<(), SwiftRunFailure>;
CacheConstructionFailure { failure: SwiftRunFailure, rejected_adopted: Option<AdoptedProof> }
```

After validating optional WASI pairing and the actual borrowed adopted owner,
`prepare` reads/stores the previous construction bound, enlarges its one ticket
before CacheControl/phase/builder/cache/Result wrappers exist, and borrows the same control
for the phase. `construct` runs at most once, including after a failed attempt;
caller invokes consuming `complete` only after `construct` returns and all named
transfer temporaries leave scope (or are supplied for drop). It restores the
**previous bound**, never the foundation floor if an enclosing phase is live.
The returned cache remains covered by its own header ticket. Omitting completion
conservatively retains the enlarged charge; no Drop refund or free-room claim.
Nested phases must complete inside-out. A second construct is an invariant and
returns its supplied proof intact without adopting/dropping it or allocating.
The phase's control borrow prevents
completing against a different control.

`construct` consumes the entire wrapper. Store that **same** `AdoptedProof`
whole; `proof()` is its only borrow and root's descriptors borrow through it.
Do not extract/recreate a proof, duplicate its source, re-adopt usage, issue
replacement proof tickets, or change the proof/`AdoptedProof` layouts. Root's
existing `drop_proof(adopted)` consumes it during cache cleanup and drops the
actual proof before refunding its two original tickets.
Root must first add
`check_adopted_owner(&AdoptedProof, Cursor, Option<WasiUsage>) -> Result<(), SwiftRunFailure>`:
validate **both** sealed source and metadata tickets against this control before
any cache work/admission/effects, not just a newly issued cache-header ticket.
`prepare` checks its borrowed proof before enlarging the phase; `construct`
rechecks the actual supplied owned proof before further effects, since it may
differ from the preparation borrow.
A foreign adopted owner is returned intact on this ownership-check failure so
its original control can consume/drop it; it cannot be silently dropped or
refunded against the wrong ledger. Use a private owned construction failure
wrapper to return this proof, without duplicating its authority or allocating.

The cache has exactly three fixed-buffer tickets (slots, pin records, patches),
one exclusive-header ticket and at most 64 resident-or-incoming aggregate entry
tickets. Every `SwiftSlot` holds an optional resident whose one ticket covers
all three locals/instructions/targets vectors. Admission precedes the first
`try_reserve_exact`; each observed capacity must equal requested capacity,
including zero-capacity vectors. Drop all partial vectors before refund on any
failure. Do not grow vectors, admit allocator excess after allocation, or create
a ticket per pin. Evict before incoming construction so an incoming entry never
becomes a 65th ticket. The whole runtime inventory stays at most 86.

Slots use capacity `min(run_budget.cache_entries, defined_function_count)` and
pin records use `run_budget.active_pins`, each at most 64. Zero remains a valid
narrowing: no zero-limit `InvalidBudget`; an unavailable slot/pin is exhausted
at use. Legacy zero-entry/zero-pin invalid-budget behavior remains exact.
`SwiftCacheUsage` records current/peak payload, construction, pinned subset and
hits/misses/decodes/evictions; these observations do not authorize allocations or
mirror the authoritative `RuntimeControl` work/live counters. A copied Swift
cache identity has the Swift policy and decoder/validator revisions, no
fabricated legacy `CacheIdentity` or `Profile`.

Charge Cache for actual buffer capacities, 512 times `size_of::<Patch>()`, entry
payloads and this permanent exclusive-header reservation, using checked arithmetic:

```rust,ignore
cache_header_bytes() = size_of::<SwiftFunctionCache>()
    .checked_sub(size_of::<ValidatedSwiftReactor>())?
    .checked_add(cache_cleanup_temporary_bytes()?)?;
```

The same one header ticket covers the entire sum. Admit it during construction,
before a cache owner requiring cleanup can escape; no extra cleanup ticket is
created. `cache_cleanup_temporary_bytes()` is a checked conservative named-object
sum, frozen with actual target sizes/alignments and simultaneous counts for:
caller-owned Option/cache slot and taken/active cache moves; cleanup Result/tail
and their Option owner shapes; aggregate-entry/three-vector drop-transfer owners;
fixed-buffer Vec and optional-ticket transfers; borrowed cleanup parts/wrappers;
and observed refund/fault/failure/usage transfers. Include every actual chosen
type and simultaneous move count, not unsubstantiated WASI counts or a reused
foundation allowance. Concrete target/count bindings are required implementation
acceptance evidence; this proposal claims no measured byte total.
Keep this permanent cleanup envelope reserved after all ordinary construction
and pin/decode phases complete, through any rejected cleanup and the successful
destructive cleanup tail's caller-completed return/drop transfer.
Never enlarge construction, admit a reservation, or require an operation phase
to begin cleanup. Partial-constructor cleanup before header ownership exists is
covered by its still-live outer construction phase, including all partial and
failure return wrappers. The header remains charged through its last actual
drop/refund transfer; permanent allowance and ordinary operation-phase temporary
allowances cover distinct named live sets and cannot be substituted for each other.

The header subtraction retains both adopted-ticket
handles and every cache ticket/option/Vec handle: only the already counted proof
header is excluded. Source/metadata stay solely RetainedSource/RetainedMetadata;
pinned bytes remain a subset of resident bytes. Do not sum old cache total peaks.
Record target sizes/alignments and observed requested allocation bytes.

Before borrowed readers/parts/meters/builders/failure values and wrapper moves
coexist, enlarge the **existing** construction ticket by a checked conservative
named-object bound. Keep its foundation floor; do not borrow the legacy scratch
estimate or allocate/admit a second scratch ticket. End a phase only by passing
its actual temporary owner through `end_construction_phase`, after drop. Reset
and passes reuse the permanent patch allocation, which remains charged in Cache.
Pin/decode operations similarly use an outer borrowed operation phase: prepare
before their named parts/meters/readers/results exist; retain that extra bound
through their return; caller completes after temporary drop, restoring the
operation's previous bound. A local scope ending inside a function before its
return wrappers move is insufficient. Header/payload tickets never replace this
temporary transfer reservation.
Their preparation likewise takes direct control/WASI borrows, creating the
`CacheControl` wrapper only after enlargement. Private fields prevent callers
from constructing that wrapper early or bypassing the operation phase.
This ordinary operation-phase rule does not apply to admission-free release or
consuming cleanup; their named wrappers/transfers use the permanent header envelope.

## Failure order, observation and cleanup

Freeze the legacy trace: scratch-capacity preflight; one initial work credit;
defined-function lookup; nonce preflight; pin-record scan; slot hit scan; then
hit or miss. A miss increments misses/preflights decodes, scans, checks entry
size and base fit, plans LRU victims without effects, precharges all 64 plan
positions and eviction-counter overflow, checks, drops unpinned victims, records
construction, builds, checks, publishes decoded entry and issues the pin. Ties
retain first slot order. Work failure during planning evicts nothing; build
failure may leave planned victims gone. Release ignores cancellation/work and
rejects wrong owner before stale nonce/entry. No fallible step follows legacy
publication. Counter/error snapshots match the pre-extraction baseline exactly.

For Swift the same algorithm uses control checks before work/admission, checked
limit/counter preflight before effects, aggregate entry admission after victim
drop, and a final publication check. Preflight `Live::CacheEntries` and
`Live::ActivePins` before mutation and roll back any acquired live count on
failure; no pin or entry escapes a failed publication. LRU timestamps use the
authoritative cumulative cache work. The first terminal cause remains immutable.
Do not retrofit Swift checks or failure order into the frozen specialization.

```rust,ignore
CacheControl<'a> {
    control: &'a mut RuntimeControl,
    wasi: Option<&'a AccountedWasi>, // None before actual context construction
}
```

Preparation first validates optional WASI observation provenance through this
root-owned prerequisite, without cancellation/deadline/work/admission:

```rust,ignore
AccountedWasi::checked_usage(&self, control: &mut RuntimeControl, cursor: Cursor)
    -> Result<WasiUsage, SwiftRunFailure>;
RuntimeControl::reservation_owner_matches(&self, ticket: &ReservationTicket) -> bool;
```

`reservation_owner_matches` tests exact nonzero ticket/control identity only;
it is pure and cannot fail, latch, check time, charge or authorize reservation.
`checked_usage` handles a missing header with `fail(..., None)` and obtains no
context observation. With a header, compute `belongs` using that pure helper,
then pass `belongs.then(|| context.usage())` into
`check_reservation_owner(header, cursor, observation)`. Thus a foreign header
failure carries `wasi=None`; a same-owner ledger/accounting invariant carries
the actual context usage. Full owner/accounting validation is still mandatory.
Only after it succeeds return actual usage. Existing WASI dispatch is unchanged.

The fixed order for construction, operations, release and cleanup is: validate
optional WASI pairing; validate both actual adopted-proof tickets or the intact
cache header using the trusted observation; then, for ordinary work/allocating
operations only, check terminal/cancellation/deadline, enlarge the existing
construction bound, and create phase/parts/meter/reader wrappers. Recheck the
actual owned proof supplied later to construct in this same order. A consuming
rejection returns the supplied owner intact; release returns its owned pin.

After successful pairing validation this synchronous borrowed operation samples
actual `wasi.map(AccountedWasi::usage)` anew at each control boundary. Its
immutable WASI borrow excludes dispatch/header changes until the operation ends;
no copied observation or validation authority persists between operations. Root
adds `*_with_wasi(..., Option<WasiUsage>)` variants for `work`, `admit`,
`admit_cache_entry`, `enlarge_construction`, `exact_capacity`, `add_live` and all
their potentially failing private preflights. Existing methods delegate `None`
with exact old behavior/layout. Cache-local faults call existing `fail` with
the same current observation. `check_reservation_owner` already accepts it.
Cleanup also needs observed `drop_reserved`, `drop_proof`, `remove_live` and
`end_construction_phase` paths, because a cleanup invariant can be the first
cause. Never call an unobserved failing method then patch its latched snapshot.
No observation is stored on `RuntimeControl`; WASI remains the only WASI meter.

Every cache operation validates its optional WASI pair and checks the intact
cache header before effects; a different control cannot mutate/drop/refund it.
The private pin is non-Clone, bound to cache owner/slot/nonce and checked on
view/release. Releasing one of several pins removes pinned bytes only at the
last pin. A view borrows the cache and cannot span mutation or release; later
execution copies one scalar instruction/target and ends the borrow before calls.

Freeze this private borrowed owned-slot cleanup API:

```rust,ignore
cleanup<'a>(owned: &mut Option<SwiftFunctionCache>, control: &'a mut RuntimeControl,
            wasi: Option<&'a AccountedWasi>)
    -> Result<CacheCleanupTail<'a>, SwiftRunFailure>;
CacheCleanupTail<'a> {
    control: &'a mut RuntimeControl, wasi: Option<&'a AccountedWasi>,
    header: Option<ReservationTicket>, failure: Option<SwiftRunFailure>
}
tail.complete<T>(self, returned_phase_storage: T,
                 outcome: &mut Option<SwiftRunFailure>) -> ();
```

Use direct borrows and only pre-reserved wrappers. Validate optional WASI pairing
and the cache header while the caller's slot is wholly intact, before `take()`.
On rejected preflight return Err with that exact slot still Some(cache), with no
vector drop, pin/live change, refund, admission, work or allocation. Caller handles
that failure and can reuse the slot with the original control and correct WASI
pair. Preserve an already-latched first cause. Never destructure/drop an owner
merely to return a pairing error. After successful preflight `take()` leaves None;
drain pin records/counts,
drop every entry's three vectors before refunding its ticket, then fixed vectors,
the whole adopted proof through `drop_proof`, and exclusive header storage.
Constructor failure does the same for every actually acquired partial owner.
Drain all remaining ownership despite a later refund/invariant error. After
destructive entry always return Ok(tail), carrying the first failure if any;
the caller's owner slot is None and no rejected cache remains. Report the
independent cleanup invariant without replacing a prior cause. Cleanup allocates
nothing, spends no work, performs no deadline/cancellation check and calls no service.
The tail is private, non-Clone and must-use; it retains the **same** header ticket,
exclusive control borrow and immutable validated WASI borrow. No new ticket or
admission occurs. Caller ends the cleanup Result/branch/move scope, then supplies
the now-empty owner slot and all remaining named phase/return storage to complete.
No large Result or Option containing a possible cache may survive header refund.
Completion drops that actual storage and remaining tail wrapper fields before
the observed header refund, writes the immutable first failure into the caller's
copied outcome slot, and returns unit. Omitted completion conservatively retains
the header charge. The tail's exclusive borrow prevents control substitution;
pairing diagnostics use attributable actual WASI usage without time/work checks.

The small completion/refund/output tail must be mapped explicitly to the existing
foundation's **4 SwiftRunFailure, 4 SwiftRunUsage, 6 ReservationTicket and 2
WasiUsage** named simultaneous allowances (plus its separately named
proof/control/adopted objects). Record exact Result/Option sizes and overlapping
active values; no assumed spare allowance or double-use with another live phase.
The private complete API returns unit to avoid a further owned failure wrapper
after refund. Its caller-owned outcome and observed refund/fault transfers must
fit that frozen named model; otherwise root revisits the upfront accounting model
before implementation acceptance. Cleanup never obtains last-minute extra room.
No ticket has a ledger pointer or self-referential borrow. Ordinary accidental
ticket loss conservatively retains charge; only explicit consuming cleanup
refunds. Cache-only cleanup leaves control/WASI reservations live; after all
component cleanup and control consumption, combined current/tickets are zero.

## Executable acceptance before executor dependence

`verification/swift-cache-stage-contract/acceptance.json` freezes named test
functions, required assertions and commands. Each future function must execute
at least once in Debug and Release; filters selecting zero tests are failures.
`python3 -B verification/swift-cache-stage-contract/check_contract.py` checks
only these proposal artifacts. After implementation, `check_contract.py
--run-synthetic verification/<root-assigned-cache-run-directory>` executes the
18 exact functions per mode and retains full output/source bindings. Run the
manifest's regression commands separately; neither command grants root acceptance.
Allocator observation scopes exclude fixture construction/validation/harness
storage and use the current thread's existing unit observer, never a new global
allocator. Test hooks remain `cfg(test)` and create no product callback/clock.

Original small Wasm fixtures must pass the unchanged public complete validator:
34 exact ordered imports/signatures, at least 29 definitions, memory 584 with no
declared maximum/host 768, fixed table 46,713/46,713, and only the exact three
exports (initialize 35, corpus 62). Fixture byte content is small; an instantiated
state would still require the real memory. Cache tests perform no instantiation.
Vary nonexported helper bodies/types for params, locals, all opcode/immediate
families, if/else patches, 379/512 depth and br_table edges. Malformed ABI/depth
or 257 total locals fails validation; never fabricate a proof to test the cache.
Pure private decoder count/build mismatch fault tests must be labeled internal
invariant tests and cannot count as accepted Swift authority.

Required coverage includes every allocation ordinal and every work/check
cancellation ordinal in constructor, scan/build/reset, victim planning and
publication; capacity-mismatch injection; all 64 pins, recursive pin patterns,
all-pinned, foreign/stale/exhausted nonces, hit/LRU/eviction; simultaneous combined
exhaustion; zero limits; actual first-cause/WASI counters on cache work/admission
failure and cleanup; no-effect repeated failure; source/layout/privacy parity.
Also require foreign-adopted proof rejection before cache effects, intact return
to its original owner, phase one-shot/omission checks, nested previous-bound
restoration and transfer peaks after constructor/operation return.
Exercise rejected owned-slot cleanup and successful same-ticket tail completion
after ordinary phases end, including cancellation, expired deadline, exhausted
work and a latched terminal cause; omission must retain charge. Use an actual
foreign WASI context with different counters: foreign/missing header usage None,
same-owner ledger invariant actual usage, and no owner effects before preflight.
Inject cancellation through the real shared token at deterministic test-only
check boundaries and exhaust work at every prefix, including the final boundary.
Deadline tests expire during scan/build/reset and confirm selected origin and
overshoot. Wall-clock sleeps alone cannot prove which loop checked the deadline.

Keep full default/stream/cache/span/WASI/all-feature Debug/Release and external
compile-fail tests green. Retain pre/post size/alignment/field-offset and exact
allocation/work/error/usage baseline observations in both feature modes; merely
checking source syntax or `size_of` is insufficient. The existing C/native
surface/header inventory and public Swift reactor surface remain unchanged.
Every receipt binds source manifest, revision/dirty state, tool versions, full
commands/output, budgets, exact counts, failure/cleanup snapshots and scope.

Open prerequisites for implementation are the root descriptor/control freeze;
implementation acceptance additionally requires concrete target layout/transient
bounds and the later executable evidence. This document's
checker only checks the contract artifacts; it is not cache acceptance. Root
owns final dependent-lane approval. Phones remain disconnected; no device
discovery/runs, target execution, size/performance, immutable consumer, release
or GA qualification is implied by these synthetic cache tests.
