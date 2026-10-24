# Private Swift memory growth implementation

This is an independently authored private verification overlay against the
accepted normalized 125-file VM closure
`96c945a817c81be17fb526067d87cc667a21cdaf5a47be18179e10fe5ed8de0d`.
The baseline capture observed Git `615a05dc14655dace87c2ff561a610bef4526621`;
root subsequently committed the same VM bytes at
`a1f78d1e88d6e1e934a08cdb85ce90f87f6ff343`. Exact source manifests and archives,
not Git context, bind the evidence. Root integration and independent review of
this growth slice remain pending. No live VM file is edited by this lane.

## Shared algorithm and original authority

`shared_memory_growth!` contains the literal original Frozen grow body. Its
static leaves expose only original owner fields or the actual Swift adapters.
The two statement leaves use brace-delimited macro invocations so the original
expanded Frozen body retains its exact statement sequence and punctuation.
Maximum denial, unsigned overflow, zero delta, checked work arithmetic, chunked
zero/copy, final check, rollback, replacement, and result push remain one shared
algorithm. Swift's work leaf evaluates the checked amount before taking its
short mutable phase borrow; that extra named scalar is positively accounted.

`SwiftGrowthContext` is exactly one 8-byte mutable reference to the real
`state.buffers[3]` Option. The actual compiler-checked `prepare_growth` destructures
State once after original-owner validation and frame-envelope admission and
returns the original `FrameOperationPhase` beside this disjoint ticket borrow.
No accepted owner, operation, phase, cache, WASI, frame, or fixed caller-storage
field changes. `with_cache_operation` remains unchanged.

The caller owns the actual existing `GrowthTransfer` in a 128-byte
`SwiftGrowthStorage`, alongside only uncommitted new-page debit and sticky debt
state. A 24-byte `SwiftGrowthExecution` holds three short references. Neither
wrapper copies ticket authority. `FrameOperationStorage.entry` remains the sole
operation outcome slot. Preparation wrappers and the 7,592-byte retained
`GrowthCompletion` are separately measured and positively charged.

The private entry functions are `growth_operation`, `growth_pinned_caller`,
`release_growth_pending`, and `complete_growth`. The direct helper adds no
instruction fuel or PC effect. The bounded pinned caller fetches the actual
instruction through the retained original pin and cache view, ends the view,
sets the original invocation cursor, admits only MemoryGrow, charges the actual
one instruction/fuel credit and one execution-work credit, checked-advances the
original PC, and calls the same helper. Vacancy of the existing entry slot is
checked before any active/cache/fetch/counter/PC/operand/memory effects. Outer Ok
records publication only; the stored outcome must be inspected.

## Failure and completion ordering

The reviewed state/authority table is in `swift-memory-growth-contract.md`.
Swift validates frame operand floors, one I32 operand, memory length/capacity/
page agreement, and the actual State ticket before pop. Declared maximum,
effective host maximum, and narrowed run page maximum all constrain growth.
Maximum denial returns I32 -1 and zero returns old pages without allocation.
Resource, allocation, cancellation, deadline, or invariant errors are terminal.

For positive admitted growth, full new storage is reserved while old memory and
its actual ticket remain live. Only the positive new page delta is predebited.
The adapter checks around the fallible exact-capacity allocation; the shared
algorithm checks every <=4,096-byte zero/copy chunk and once after the final copy.
Precommit failure destroys only new storage, rolls back only that new live debit,
and validates/refunds only its own new ticket. The original memory/ticket and
prior guest effects remain intact. Rejected work and fuel are not refunded.

Commit moves the old Vec/ticket into the actual transfer slots and the new
Vec/ticket into the original State memory and ticket slot. It converts the new
page debit to committed State ownership, drops old storage, and then refunds the
old ticket. Failure after commit, including result publication, retains committed
memory and pages. The result push uses the accepted actual arena/capacity/live
adapter. Post-pop live mismatch follows the accepted sticky frame debt path.

Refund layout checks and `check_reservation_owner` run while the original N/O
Option is still populated. Under the same exclusive control borrow, the adapter
then takes that exact token and calls `drop_reserved_with_wasi((), ticket, same
WASI observation)`. The borrowed owner check proves every refund predicate:
nonzero matching owner, nonzero live-ticket count, category bytes sufficient,
and combined bytes sufficient. These are exactly the conditions for the three
checked subtractions in the unchanged refund body. Unit has no destructor or
callback; no fallible or mutable boundary intervenes. Corruption-before-take
negatives prove that rejection retains the exact ticket and entire charge.
Controller/cache/WASI source remains byte-identical.

`complete_growth` refuses ordinary frame completion whenever N/O, an actual
transfer Vec, uncommitted page debit, sticky debt, or a populated preparation
wrapper remains. Its Retained variant owns the exact phase/context/growth/fixed
caller storage/preparation objects, keeping the original admitted envelope live.
`release_growth_pending` retries explicitly and independently of cancellation,
deadline, fuel, and work. Sticky unreconciled debt cannot be repaired or cleared
by retry. After successful growth-storage cleanup, completion destroys all growth
and preparation wrappers before calling the original fixed frame completion.
Pin cleanup still uses the original deepest-first drain and retained-pin retry.
G08's absent-cursor Cleanup diagnostic remains explicitly open.

## Accounting and evidence scope

There are 10,356 fresh positive fields: 4,724 production canonical positions,
4,824 additional unit canonical positions, and 808 authored positions. Canonical
arguments, returns, locals, source aliases, directly typed literals, closure
captures, and selected standalone promotions each receive separate source,
argument, returned, and caller roles. Preparation and completion positions belong
to the permanent bound because their returns survive outside the active helper.
The collector includes standalone `growth_pinned_step::promoted[0]` and the
actual preflight promotion and excludes actual test hooks/promotions. It also
includes standalone `release_growth_pending`, even where MIR omits its module
qualification. No old field, equal-layout alias, peak subtraction, reused slot,
or old padding supplies credit.

All 4,800 accepted memory fields and 4,324 accepted bulk fields remain exact.
The memory collector applies only the already-accepted 1,672-name MIR function
qualification spelling delta from the bulk input. Four final Swift/all-feature
production/unit MIR receipts reproduce both accepted inventories and the new
inventory. The complete accepted memory and bulk accounting source tails are
byte-identical.

| aarch64 host logical named-object bound | Production | Unit |
| --- | ---: | ---: |
| Fresh growth permanent addition | 316,376 | 559,472 |
| Fresh growth active addition | 973,920 | 1,815,568 |
| Complete execution header | 2,074,592 | 3,212,368 |
| Complete frame operation envelope | 4,452,888 | 8,115,000 |
| Original construction envelope | 1,069,144 | 1,071,904 |

Sixteen actual baseline/candidate compiler metadata runs cover Swift/all-feature,
Debug/Release, production/unit configurations. Each field has a measured aligned
interval inside its measured containing struct. Fresh production classes have
zero padding; the unit active class contains exactly four padding bytes and the
unit permanent class zero. All fourteen accepted owner shapes/offsets, Frozen's
2,912-byte reservation, State 128 MiB, Combined 256 MiB, and ticket maximum 86
remain unchanged. These are conservative simultaneous logical named-object
bounds. They make no stack, allocator-overhead, optimizer-temporary, or RSS claim.

Final runtime qualification uses all 19 Swift-only / 20 all-feature growth tests
in Debug and Release, plus the complete 98-case all-feature Release execution
selection. The original 312 upstream selections are historical unchanged-component
evidence and are never added to current-source four-configuration counts. The
new tests exercise actual owners, the actual pinned caller and fixed result
slot, allocation/capacity denial, work/fuel/PC prefixes, 767->768 overlap,
zero/copy/final cancellation, actual deadline expiry at selected growth loop
checks with cancellation precedence, foreign N/O retention and explicit retry,
postcommit push failure, sticky debt refusal, and retained-pin cleanup. The Swift fixture helpers
record bounded owner/helper-call counters; the separate Frozen recipe records
five fixed cases in its own MG_FROZEN lines. Each test has finite explicit cases
and records bounded fixtures/steps and never executes a full Swift guest target.

Fresh Frozen differential receipts execute ten finite zero/positive/maximum/
unsigned/allocation/State/work/cancellation cases on baseline and candidate in
Debug and Release. Their complete results, memory digests, usage, cache, and
allocation observations are paired exactly, alongside compiler-expanded identity
of all 39 Frozen methods and fourteen containing owners.

## Collector correction and remaining gates

The initial collector mistakenly shared a Cargo target directory across source
and metadata overlays. An unexpected metadata-only test exposed reuse of the
wrong executable. Those runtime/layout/Frozen receipts are retained as excluded
historical evidence. One owned compiler was deliberately stopped with SIGTERM
while strengthening isolation; its failed receipt is also excluded. Final
commands use exact source-closure, feature, profile, unit/production, and
layout/runtime contexts, and retain executed binary path/hash plus exact selected
test identities. The source implementation did not change during correction.
All affected qualifying runs are recollected under that isolation.

`receipt.json`, command receipts, source archives, MIR, source and function
inventories, layouts/padding, Frozen identity/differentials, cleanup, and the
read-only offline verifier bind the exact candidate. Failed draft commands and
collector failures remain listed separately. Reproduction writes only a unique
owned scratch tree; final cleanup removes it after checking for open files.

Growth integration/independent acceptance, host imports, full dispatch/calls,
Ready/public invocation, a full Swift-target run, native joins,
simulator/emulator joins, separate-repository immutable published FieldLog
consumption, physical phones, signing, store, customer, operational, and GA gates
remain pending. This lane uses no native/device/UI tool and performs no commit,
push, publication, credential change, or tracker mutation.
