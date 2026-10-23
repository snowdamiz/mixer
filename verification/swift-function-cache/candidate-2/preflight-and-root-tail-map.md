# Candidate 2: exact named-value phase map

This is a producer implementation map awaiting independent and root acceptance.
`preflight-root-tail-map.json` binds the exact source SHA, commands' output,
compiler version, both executed profiles, all model field sizes/alignments/offsets,
and all literal component counts. Its source is
`vm/src/experimental_swift_reactor/cache.rs`, SHA-256
`3a247fdfe0a09e39b6185a303168f48f0e30274d836207bcf5c616d287c3b36d`.
The two `preflight-root-tail-layout-*-final.log` commands each selected exactly
one named test and passed. Debug/Release layouts are identical on this
`aarch64-apple-darwin` host. These are authored named Rust value footprints;
compiler stack placement, opaque library/platform implementation internals,
allocator overhead and RSS are outside this model.

Candidate 1 is preserved byte for byte under `candidate-1/evidence` and
`candidate-1/source`, with old-to-preserved mapping in
`candidate-1/preservation-map.json`. Its receipt and source are historical,
not an accepted implementation and not overwritten by this correction.

## Before ordinary enlargement succeeds

The upfront foundation remains **16504**, with the frozen counts: 3 proof,
3 control, 3 adopted, 4 failure, 4 usage, 6 ticket and 6 optional WASI shapes.
The actual owner stays in slot 1 of each owner class. The selected prepare graph
borrows the proof/adopted/cache; no whole proof/adopted/control ownership move
occurs before prepare returns. The following complete groups get entire slots;
no remainder or bytes inside an existing live owner fund another group.

| Whole local foundation slot | Whole size | Exact phase group | Size / alignment |
|---|---:|---|---:|
| Control transfer 2 | 1720 | PreflightGroupA | 1352 / 8 |
| Control transfer 3 | 1720 | PreflightGroupB | 1664 / 8 |
| Proof transfer 2 | 664 | PreflightSetupInventory | 440 / 8 |
| Proof transfer 3 | 664 | PreflightOwnerInventory | 352 / 8 |
| Adopted transfer 2 | 712 | PreflightPrimitiveInventory | 368 / 16 |
| Adopted transfer 3 | 712 | PreflightEnlargeInventory | 632 / 8 |

Compiler-evaluated assertions require every complete group to fit its assigned
whole slot. The JSON `model_fields` table is the exhaustive field-to-type/size
inventory. Prefixes name the actual source helper or closure. A field does not
stand for a semantic name multiplied to cover arbitrarily many nested frames.

The phase sequence and overlapping roles are:

1. **Pure layout constants.** `compute_cache_*_bytes` uses explicit Rust const
   initializers and checked multiplication/addition. The `sum_named!` macro
   expands const statements, with no runtime array/fold iterator. Getter calls
   still return actual `Option<usize>` values; the previous-bound checked add,
   `and_then` and `ok_or_else` values are accounted in Group B. This depends on
   const semantics, not optimizer or inferred last use.
2. **Prepare plus helper plus pairing.** Setup includes distinct prepare, helper,
   and pairing control/WASI/proof/cache handles and cursors. Actual closure
   captures, header Option borrow, previous-bound capture/argument, layout-failure
   args and checkpoint args remain separately named. Group A holds its retained
   observation, cursor/bounds, handles, layout Fault and active result. Group B
   holds a separate outgoing result and the standalone successful usage return.
3. **WASI provenance and owner checks.** Owner includes `checked_usage`'s
   self/control/cursor/header, `then` context borrow and context usage receiver;
   `reservation_owner_matches` self/ticket and bool receiver/result;
   adopted-source and metadata ticket borrows; nested `check_adopted_owner` and
   `check_reservation_owner` receivers/cursors/tickets; reservations.category
   receiver/category/returned reference. Missing/foreign WASI does not fund any
   local temporary. All groups are charged by this local control before checking
   provenance; untrusted foreign owners stay intact in their own callers.
4. **Owner violation branch.** The Option violation source, copied match Option,
   tuple pattern and separate invariant/code bindings have distinct Owner fields.
   `get_or_insert` receiver, invariant argument and returned mutable borrow also
   have separate fields. Fault source/transfer/kind/code, fail receiver/cursor,
   usage receiver, native Instant, Duration, micros/conversion and returned scalar
   fields live in Primitive. No failure/usage value is borrowed as padding.
5. **Successful helper usage and bounds.** Group B's whole 504-byte
   `usage_return` covers the standalone `control.usage(observation)` return before
   its `.reservations.construction.current` extraction. It is an additional
   explicitly named group member, not an assumed spare root Usage slot. Failure
   branches use the root four whole Usage slots for fail/usage transfers. Success
   and fail paths are exclusive, and the helper frame ends before enlargement.
6. **Post-helper admission before commit.** Prepare's handles/cursor/observation,
   `PreparedBounds` result/pattern and `previous_bound`/bound remain covered by
   Setup and A/B while Enlarge is live. Enlarge covers distinct enlarge/check/
   preflight_bytes/category_limit/category/commit/category_mut receiver frames;
   cancellation/Instant comparison; old construction `.as_ref().map()` Option
   and closure; category/combined checked Options and predicate inputs/outputs;
   category limit/kind; limit Fault/resource/attempted/ceiling; returned pair and
   its pattern; mutable construction-ticket borrow. Primitive covers nested
   fail/usage/time values. No new ordinary-phase bytes are used until
   `commit_bytes` succeeds. Group B/A remain the active/outgoing large-result
   whole roles while `Result<(usize,usize),Failure>` propagates to enlarge and
   then prepare. On denial, all six groups remain supported by the original
   upfront foundation.
7. **Return boundary.** Helper frames and prepare have ended before construct,
   Partial, pin/decode or proof-drop ownership transfers begin. The resulting
   ordinary phase uses its explicitly admitted additive envelope. This proof
   cannot be reused for arbitrary enclosing executor copies; those need their
   own separately mapped caller header.

### Large results, observations and root class roles

All the selected large return variants measure 1096: `SwiftRunFailure`,
`Result<(),Failure>`, `Result<WasiUsage,Failure>`,
`Option<Result<WasiUsage,Failure>>`, `Result<Option<WasiUsage>,Failure>`,
`Result<PreparedBounds,Failure>` and `Result<(usize,usize),Failure>`.
A/B each reserve one **whole** 1096 result-shaped member, in addition to the root
four failure-transfer slots F1..F4. The active phase role transitions are:

| Branch / expression phase | A result role | B return role | Root F1..F4 roles |
|---|---|---|---|
| checked_usage / owner fault | checked_usage Result or owner-check Result | map Option<Result> / immediate caller propagation | fail local/return, cleanup-fault or owner-check return, Result construction and outward failure transfer |
| map then transpose | checked_usage-to-map result | map Option<Result> | transpose Result, pairing outward Result, helper `?` residual and outward failure transfer |
| pairing/helper return | pairing Result | helper Result<PreparedBounds> | completed leaf slots become pairing/helper/prepare propagation alternatives |
| enlarge check / bytes denial | root check or bytes Result | enlarge Result / prepare propagation | fail local/return, preflight_bytes Result pair, check/enlarge propagation and outward failure transfer |
| successful prepare | helper Result<PreparedBounds> | prepare phase Result | no live root fault chain |

These are statement/helper-frame phase alternatives, never simultaneous claims
on the same slot. A completed callee frame ends before its enclosing return is
constructed; expression temporaries end at their Rust statement scope. No named
variable is assumed dead merely because it has been read. The failure already
stored inside the actual control is covered by the full control owner, not
charged a second time as a standalone failure. Embedded usages in that failure
are covered by its whole owner. The four standalone Usage slots cover usage
local/return, fail's at_failure transfer, and record_cleanup local/after_cleanup
transfer. Preflight never calls record_cleanup.

Six whole 112-byte optional-WASI slots O1..O6 remain available independently.
The raw `WasiUsage` getter value is 104 and can take a whole optional slot as an
explicit phase alternative, not a partial-slot allocation. During direct sampling:
O1 is the input/receiver observation, O2 the context return/raw value, O3 the map
argument or raw return, and O4 the enclosing Option return; O5/O6 remain for
outward argument/return transfers. During the checked-owner/fault branch,
O1 is a retained caller observation, and O2..O6 are distinct observed helper,
cleanup-fault, fail and usage argument/return copies along the deepest root
chain. Group A separately holds prepare/helper's named retained observation.
The map/then closure borrows are in Owner/Setup; they are not extra owned WASI
observations. Failure-nested observations are already covered by whole failure
values. Missing/foreign provenance passes None to root and uses the same local
slot model. The map/transpose Result wrappers use the separate whole failure
roles above; their inline successful observation is not double-counted outside
that whole Result owner.

## Ordinary component phases and primitive root boundaries

The measured additive component envelopes are cleanup **62096**, header
**62424** (328 exclusive owner + cleanup), construction **57128**, and operation
**80566**. Their literal type/count rows are in JSON, including copied budget
136, CacheParts 80, result/Option adapters, payload owner transfers, Reader32,
Counts/Operation/Instruction/Patch/Value, closure captures, loop/scanner/planning
counters and iterator types. The counts remain conservative source, argument/
return and caller transfer bounds for each explicitly enumerated binding group;
they do not stand in for unenumerated nested references.

`OperationBorrowChainInventory` explicitly lists each nested meter/reference
receiver from pin_acquired through Mode::build, build_payload, build_borrowed,
scan_borrowed, Reader::uint/byte, SwiftMeter::work and CacheControl::work.
Reader::take's filter has its own captured Reader handle and `&usize` argument.
The locals filter and nested is_some_and have two distinct captured policy
handles, an outer `&usize` and an inner `usize` argument. Permanent's explicit
`(&SwiftFunctionPin,&PinRecord)` closure row maps to checked_record filter's
captured pin and its `&PinRecord` argument. Its Option<PinRecord> source/adapter/
return shapes are distinct from the 16-byte PinRecord values. Fixed float
conversion arrays/Results are by-value `[u8;4/8]`, as authored by `.try_into()`.

Control slot 1 remains the owner. Whole Control2 holds
`CompletionBorrowInventory` (192/8): the 40-byte completion tuple, outcome
borrow, phase control/WASI/previous, and construction/operation phase shapes.
Whole Control3 holds `RootLeafInventory` (1632/16). Its typed union has complete
nonrecursive alternatives. A member cannot switch while its caller frame lives:

| RootLeaf member | Exact group size / alignment | Call-chain roles |
|---|---:|---|
| admission | 1136 / 16 | admit/admit_entry + check/bytes/category/commit + fail/usage primitives |
| owner | 720 / 16 | WASI sampling, pairing and owner checks + fail/usage primitives |
| work_live | 1632 / 16 | work/add_live/exact_capacity + check/bytes superset + fail/usage primitives |
| remove_live | 560 / 16 | remove_live/live_parts/checked_sub/live_mut **and simultaneously** cleanup_fault/get_or_insert + fail/usage primitives |
| refund | 1104 / 16 | drop_reserved/refund/cleanup_fault/record_cleanup; phase-end bounds; fail/usage primitives |

The remove-underflow member is independent of refund. It covers the still-live
remove receiver/resource/amount, live_parts tuple/current usage, Option next and
pattern while cleanup_fault retains receiver/invariant/code/Cursor, insertion
receiver/argument/returned borrow and the complete Primitive group. The larger
work_live member is not used to fund this fault branch by switching mid-call.
RootPhaseEnd includes the authored root foundation's seven `(count,size)` array
items, actual IntoIter and checked fold scalars/Options; this leaves the root
source unchanged. This scope covers authored logical values only.

## Same-header completion and after header refund

All ordinary phases must complete before cache cleanup. Preflight rejection
leaves the exact caller Some(cache) intact. Once draining starts, the same header
is returned in CacheCleanupTail despite terminal/invariant faults. Its original
return/owner/failure storage stays covered by the permanent header envelope.

`drop_cleanup_return_storage` consumes the tail and supplied actual storage;
its original tail/failure and caller return/owner wrappers end with this helper
frame. Only the 40-byte `(control,WASI,Option<header ticket>)` tuple returns.
The tuple and caller outcome borrow use whole Control2's 192-byte group.
No proof/adopted transfer slot is reused in final cleanup.

Control3 takes the **owner** RootLeaf member during
`wasi.map(AccountedWasi::usage)` evaluation: it explicitly covers AccountedWasi
and WasiContext usage receiver handles plus map/then borrowing. O1..O6 cover
raw/optional source, call and return transfers as described above. The sampling
call/closure frame ends before `drop_reserved_with_wasi` starts. Control3 then
uses the **refund** member for drop_reserved -> refund -> cleanup_fault -> fail
-> usage. This member names category/combined/count Option locals, tuple match
and usize patterns; category/category_mut handles; cleanup_fault and Fault
source/transfer/scalars; fail and native time/Duration/micros/conversion values.
Ticket source/extraction/tuple/drop/refund transfers stay in the six whole
24-byte ticket roles. Six Optional112 shapes cover the retained external
observation and up to five nested observed-control argument/return values.

The discarded refund Result's statement ends before record_cleanup. For the
second sampling statement, Control3 again takes owner only while sampling;
then refund member covers record_cleanup's receiver, failure Option borrow,
outcome pointer and nested usage/time values. Root F1..F4 cover caller outcome,
refund Result/fail local/return and final record/output transfers; U1..U4 cover
standalone usage transfers. All Option and unit Result failure shapes are1096.
An already latched prior cause retains its exact at_failure and receives actual
after_cleanup usage. Successful refund may remove the cache header; all named
post-refund values above are funded by upfront whole foundation slots, with no
cache header or foreign WASI-header dependency.

Every root primitive frame and both whole Control2/Control3 phase alternatives
end before final `RuntimeControl::finish_owned_cleanup` consumes the actual
control by value. The exclusive borrowed tail prevents that consume from
coexisting with its completion. No enclosing executor/caller copies are claimed
free, and these local phase assignments cannot authorize them.

## Scope of executable claims

The original 18 named bodies are preserved; helper assertions promoted into
them now check exact 376-operation owned-IR parity and three target offsets,
129-parameter rejection, 64 simultaneous distinct pins followed by the 65th
failure, exact-minus-one/exact phase/header admission, actual deadline/exact-work
cleanup, and cache-owned final-header refund failure with actual WASI/prior
cause. Full immutable Debug/Release qualification and legacy replay follow this
map freeze. The named ownership body executes nonce exhaustion, not cache-owner
identity exhaustion; the named sticky body repeats PinLimit, not every terminal
kind. Candidate 2 coverage will qualify those limits. Missing-WASI and same-owner
WASI-underflow injections remain separately bound independent-review evidence,
not producer named-body assertions. Legacy full replay is a separate executable
receipt, not an assertion within the frozen-layout named body. No target
instantiation, phone/device, compiler fixture, GA or release claim follows.
