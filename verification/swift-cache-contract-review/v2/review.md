# Independent refined Swift cache contract review

Decision: bounded contract acceptance, with no remaining concrete contract
blocker found. This acceptance covers the refinement's ownership/accounting
design. Root must separately accept the code prerequisites before whole-cache
implementation begins. Actual cache/cleanup layouts and simultaneous-object
mapping remain mandatory implementation evidence; no measured byte amount or
whole-cache behavior is accepted here.

## Earlier findings resolved

### R1: rejected cleanup preserves the actual owner

The revised borrowed `&mut Option<SwiftFunctionCache>` API validates the actual
WASI/control pair and intact cache header before `take()`
(`docs/swift-cache-stage-contract.md:358-378`). Rejection leaves the exact
`Some(cache)` in the caller's slot. It creates no unboxed rejected-owner return
wrapper and cannot implicitly drop a consumed cache on a preflight error.
The original control can still consume/drain the original owner afterward.

After successful preflight, `take()` leaves `None`, all entries/fixed buffers/
the actual adopted proof are drained despite later invariant errors, and the
function always returns `Ok(CacheCleanupTail)` carrying the first failure
(lines 378-397). This cleanly distinguishes a reversible rejected preflight
from cleanup that has begun destroying owned storage. Release similarly returns
its original owned pin on rejection.

The acceptance inventory now requires intact rejection, unchanged owner effects
and both ledgers, successful original-owner reuse, terminal cleanup, and
continued draining after a later invariant. No new public authority is exposed.

### R2: actual WASI observation has proven provenance

The revised helper first reads the actual sealed header ticket, uses a pure
exact nonzero identity predicate, and only obtains a context observation for a
matching owner before full owner/accounting validation
(`docs/swift-cache-stage-contract.md:310-335`). Missing/foreign headers therefore
cannot contribute foreign counters. A same-owner ledger/accounting invariant
retains the actual current context usage. No copied observation admits resources.

The fixed preparation order is optional WASI pairing, actual proof tickets or
intact cache header, then ordinary cancellation/deadline/work/admission phase
preparation. The actual owned proof supplied after construction preparation is
rechecked. The immutable context borrow excludes simultaneous dispatch and
header changes through the synchronous operation; later boundaries resample its
actual usage. The helper is safe for terminal cleanup because it has no time,
work, allocation or admission check. Existing dispatch behavior remains outside
the contract change.

The acceptance manifest records the same distinction and requires real
different dispatch counters for foreign-context tests, actual same-owner
invariant counters, and preservation of an existing first cause.

### R3: cleanup accounting survives its own return

The revised permanent header reservation adds a checked named-object cleanup
envelope to the original exclusive header subtraction, using the same one
header ticket (`docs/swift-cache-stage-contract.md:230-268`). It explicitly
includes caller Option/cache slots and moves, Result/tail owners, entry/vector/
ticket transfers and borrowed/failure/usage objects. It stays reserved after
ordinary construction/operation phases finish and cannot be replaced with a
last-minute admission. Partial-constructor cleanup before header ownership is
covered by its still-live outer construction phase.

The successful destructive cleanup returns the same header ticket in a private
non-Clone must-use tail tied to the exclusive control and validated immutable
WASI borrow. It does not refund the header before returning a large Result or
possibly cache-sized Option. Caller first ends those Result/branch/move scopes,
then passes the now-empty owner slot and remaining named storage into consuming
tail completion. Completion drops them before observed refund and returns unit;
copied failure output avoids a further large returned owner. Omitting completion
retains the header charge conservatively (lines 388-407).

The remaining small completion/refund/output objects are expressly required to
map to the existing foundation's 4 failure, 4 usage, 6 ticket and 2 WASI usage
simultaneous allowances, without unproven spare capacity or double use with
another active phase. Exact Result/Option sizes and overlaps are pending. If an
implementation cannot substantiate this mapping, root must revise the upfront
model before acceptance. This is an appropriate implementation gate, not a
current claim that the mapping has already been measured.

## Prior invariants and scope retained

The refinement retains original proof adoption without copying/re-adoption,
both source/metadata owner checks, one-shot construction, exact prior-bound
restoration, one construction ticket, and non-refunding omission. It retains
the 86-ticket maximum, three fixed cache buffers, one header ticket, at most 64
resident-or-incoming aggregate entry tickets and no per-pin/cleanup ticket.

The one permanent 512-Patch Swift arena, explicit reset work in both passes,
511 nested-control/512 function-inclusive boundary, declared-locals-only decoded
payload and 128 parameter/256 parameter-plus-locals limits remain unchanged.
Legacy layouts, 128-Patch stack state, scratch formula, allocation requests,
work/error order, static mode specialization, identity and release semantics
remain frozen.

The descriptor ambiguity is resolved: `host_maximum` is the stored effective
maximum, table 46,713 rather than independent policy ceiling 65,536. The fixture
manifest now asserts it. An O(1) checked absolute global initializer offset
accessor is specified separately, preserving `GlobalView` layout. Exact function
and segment payload boundaries, empty ranges, absolute indices, original source
borrows and encoded segment order remain explicit.

All 18 named future cache tests remain pending. Root prerequisite acceptance,
whole-cache implementation/layout/allocator/source/privacy tests, regression
commands, executor integration, separately authorized bounded target runner,
physical devices, immutable published consumer, performance and GA gates remain
open. Neither this review nor the artifact checker grants target execution.

## Independent checks

`check_review.py` independently compared all five historical-v1 artifacts to
their hashes in the original independent review receipt, in addition to their
archive manifest. All five match. The current v2 producer receipt's five
artifact bindings also match the observed files.

The normal and optimized Python artifact checkers pass. The three artifact-test
functions pass in both Python modes, including 29 negative plan mutations and
one historical-byte mutation per mode. This verifies artifact consistency and
fail-closed guard checks only. No new cache engine test or producer seal
collector was run. The reviewed artifacts remained unchanged during the checks.

`receipt.json` records source hashes, exact commands, versions and full outputs.
This lane wrote only `verification/swift-cache-contract-review/v2/`; the original
review/evidence and historical-v1 remain preserved. No product/proposal changes,
target instantiation, device discovery/run, commit, push or publication occurred.
