# Dispatch, returned-child and destruction lifetime contract

Implement one isolated finite event/region model next. Its first job is to reject
an incomplete storage/capacity explanation of the existing dispatch boundary,
while keeping source ownership separate from physical storage evidence. It must
not select a grant, change the current selectors, execute the fixture or convert
synthetic numbers into a ReviewedWholeQuote. The model and its test module are
the proposed next code slice; neither is implemented or executed by this packet.

The accepted accounting join is
`verification/swift-semantic-adapter-root-review/layout-accounting-join-acceptance.json`.
The exact isolated source remains source146
`91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f`.
The finite observation roster is accepted for its pinned Rust1.99.0,
aarch64-apple-darwin, source/cfg only. The general type normalizer is unqualified;
this contract uses explicit current types and methods. No new query is needed
to start the model.

## First boundary and current reachability

The exact boundary is:

1. `AdmittedImmutableOwnerV1::correlation_scope_v1` issues the expected/attempt
   pair, making original acquisition retirement permanently sticky.
2. `run_one_admitted_fixture_v1` obtains the complete child quote and reserves it
   before constructing/calling its actual closure.
3. The closure consumes fixture and attempt by value, borrows expected, and calls
   `run_prepaid_admitted_fixture_v1` exactly once.
4. Dispatch returns `PrepaidOwnedV1<AdmittedFixtureOutcomeV1>`. The admitted
   payload encloses either every original partial setup owner/error or the
   complete bound loader/leaf result, rows/snapshot/cancellation/claims.
5. The outer owner observes through short shared views, consumes the complete
   child in `destroy_returned_admitted_fixture_v1`, and only after destruction
   returns may P0 release a child-only `DestroyedStorageV1` token.
6. The outer then attempts original acquisition retirement. A previously issued
   scope returns Retained before any cleanup effect, so child release cannot
   release original acquisition storage.

Production currently refuses before this conditional dispatch path:
`selected_parent_account_v1` returns RootPolicyPending and
`selected_whole_quote_v1` returns WholeQuotePending. Original acquisition startup,
allocator/custody selection are also pending. The event model describes current
source transitions under future reviewed authority or isolated synthetic inputs;
it does not claim these branches ran or are production-admissible today.

## Finite events and branch coverage

The machine begins after an already-reserved original acquisition, using its
existing ledger/owner identities. ScopeIssue sets the sticky barrier before
checking/taking the attempt. Repeated issue refuses without clearing it. The
normal dispatch route is:

`ScopeIssue → ParentReady → QuoteReady → ChildReserve → ClosureConstruct →
ClosureConsume → RootCapture → SetupReady → LoaderReturn → Correlate →
LeafOrRefusal → BoundReturn → ChildWrap → ObserveBegin → ObserveEnd →
DestroyBegin → PayloadDropComplete → WrapperDropComplete → TokenReturnSome →
P0ChildRelease → RootRetireRetained`.

`events.json` fixes the typed event preconditions, effects and evidence class.
The terminal alternatives are finite:

* Parent/quote/reservation refusal: no closure/fixture effect and no new child
  charge committed on a reserve refusal. An issued original-root scope stays
  sticky. Child work, current storage and peak update atomically only on reserve
  success; no later refund of work or peak is introduced.
* Setup stage k=0..4 refuses: retain the exact prefix of k successfully opened
  File owners plus the original io::Error in SetupOutcome::Refused. Stages0..2
  open source/build/session; stages3..4 use create_new for rows/snapshot. No retry,
  truncation, loader, cancellation or leaf follows. InvariantRefused retains the
  actual five-slot Option<File> array without fabricating Ready ownership.
* Ready setup has five File owners. Loader return retains source/build/session
  and optional executable with the complete selected proof or original failure.
  Correlation refusal keeps the whole selected/failure carrier and uses the
  consumed attempt's root, including a foreign expected-root mismatch.
* The fixed loader frame has three primary branches: LoaderRefused,
  CorrelationRefused, and Leaf. Leaf itself yields either the original
  SnapshotPreScopeFailure or the complete SnapshotScopeFinish. The correlated
  route invokes the existing scope/construct/outer/finish sequence once. Finish
  may retain cleanup/retirement failures; it is not a healthy-close receipt.
* Normal explicit destruction drops the complete payload, takes the reservation,
  drops the emptied child wrapper, then returns Some(token) or None. Only Some
  may be released, once, in pre-funded P0. None permits no release/retry.
* Ordinary `PrepaidOwnedV1::drop` destroys its current payload but never releases
  storage. Its reservation field has no refunding Drop. Work/peak remain retained.
* Unwind at existing quote/reserve/call/setup/loader/correlation/leaf/drop call
  edges is distinct. Pure capture field moves introduce no separate unwind edge.
  A payload-drop unwind cannot pass TokenReturnSome. Existing
  cleanup drops may run, but no token or storage release is inferred from them;
  double-panic abort and incomplete drop-glue effects remain outside acceptance.
* ForgetChild skips payload/wrapper destruction and token creation. Its charge
  and backing obligation cannot be discharged. Keeping a numerical charge in a
  live ledger is not durable funding after the ledger itself ends; root shutdown
  remains blocked/pending, not certified by the leaked reference.

The first model must cover exactly these source branches. It must not introduce
retry, callback, new public ownership extraction or a root-refund event.

## Identity and containment rules

`regions.json` gives a compact ownership map. Use three different identity
domains: semantic owning values, physical storage regions, and separately owned
backing/resources. A value move transfers semantic custody and preserves backing
IDs. It proves neither a new allocation nor physical overlap of source/destination
buffers. Unknown physical overlap cannot be deduced from MIR StorageLive/Dead.

The observed closure is48 bytes/alignment8. Its captured attempt is part of that
closure; do not add the32-byte attempt again. Its expected reference does not own
the24-byte correspondence or original acquisition. The complete returned child
is13640 bytes/alignment8 and includes the13624-byte admitted outcome and13616-byte
payload. These nested extents are not separate allocations. The56-byte scope pair
includes its24/32-byte members. The8-byte Option<&admitted> and16-byte primary view
are short representations, not their pointees' proof/File/error backing.

For the child, retain stable identities for each successful setup File owner,
optional executable, proof/source allocation family, original io/error backing,
claims owner, rows/snapshot owners and the Cancellation Arc backing. Moving these
through RawCorrelationOutcome, RawFixtureResult, RootBound and the child never
creates a fresh resource identity. Cancellation::clone shares its one Arc backing
with another live owner; its capacity and allocator correspondence still need
evidence. A child File opened on a path also held by IR01 is a distinct File owner;
equal paths/inodes do not prove shared accounting allocation or authority.

The original acquisition independently retains its thirteen input slot owners,
five native and five retained path backing slots, claims/original-failure state,
reservation and ledger obligations. Root references in result wrappers do not
replace those. P0 independently owns the reviewed immutable binding/identity
preimages, account/root-policy/bookkeeping, late caller frame, token return/args
and final result/observation bookkeeping. A post-destruction token cannot fund
the parent frame from the child it just released.

## Existing quote partition, preserved completely

`quote-partitions.json` enumerates every retained partition and its boundary.
The original IR01 quote has acquisition_work, cleanup_work and peak_storage,
including its bridge metadata/offset/allocation/read/hash/path/correlation/
retirement inputs. Admission's correlation and correlation_storage debit already
belongs to that original acquisition. The sticky scope barrier retains the full
original storage charge on unused, refused, destroyed or forgotten results.

P0 is separate and preexisting. The child ReviewedWholeQuote has six positive
work/storage components, summed with checked arithmetic by the existing source:
P1 setup; P1 loader including separately priced original validation; P2 arguments;
P3 pre-store shell; P4 selected route; P5 returned owners/diagnostics/destruction.
Root-bound envelopes/transfers belong in those exact components or an explicitly
reviewed amendment, not in a second copy of the fixed leaf. Parent account/quote,
destroy/token/release and final outer bookkeeping stay in P0. Product VM work
budgets do not fund host setup/loader or original acquisition work.

The proposed region model must explain coverage of these components. It does
not silently replace the existing six-component storage sum with a global peak
or select a new price. Existing overlapping conservative charges must be rebound
explicitly before any deduction; unknown terms stay unknown. All selectors remain
fail closed while authority, work prices or capacities are unresolved.

## What source/MIR establishes, and what it cannot establish

Source and accepted retained MIR establish sequencing, whole-value containment,
affine moves, exact capture fields, typed branch payloads, borrowed inspection,
drop-before-token order, cleanup edges and the absence of a child/root refund
on ordinary Drop/unwind. The source's Custom Drop in this boundary is
`PrepaidOwnedV1<T>::drop`; the result envelope types use implicit field/variant
drop. Explicit SnapshotRun::finish has its own cleanup protocol and is not an
implicit result Drop. Native File healthy close is not proven by Rust Drop.

They do not establish concrete stack-region addresses, caller/callee return-slot
aliasing, register spills/inlining, actual allocator capacities/overhead, full
monomorphized stdlib/drop-glue costs, backing completion on unwind or durable
forgotten-root custody. The accepted catalogue supplies type widths, not these
physical facts. `source-frontier.json` distinguishes source+selected-MIR facts
from source-only setup/root-retirement/dependency facts. No new physical region,
runtime or compiler evidence is claimed.

## Small next implementation and evidence gate

`IMPLEMENTATION.md` specifies two new isolated Rust files: a finite event/region
model and its synthetic tests. The model accepts explicit current-shape IDs,
symbolic capacities/evidence states and typed transitions. It computes checked
max-of-unions only over fully evidenced physical regions/backings; unresolved
inputs return IncompleteEvidence. It can assess a synthetic capacity limit,
but exposes no ReviewedWholeQuote, production grant, source-authority constructor
or conversion into child/root reservation. No generic type parser is needed.

That slice can proceed after contract review without a compiler layout query or
actual fixture run. Its tests can qualify the finite state/arithmetic model only.
Later root-selected physical/capacity evidence must address the dispatch return
buffers, destroy/take/drop overlap and P0 token frame specifically; it need not
re-enumerate all645 MIR roles. Native/File/allocator/drop behavior requires a
separate bounded runtime release, and paused native/device checks remain pending.

This packet performs only pinned source/MIR review and offline evidence writing.
No checker, compiler, amended parser, product code, runtime, child workload,
global process inventory, native/UI/capture/device or network command is run.
No previous packet, canonical source, central metadata, commit or push changes.
