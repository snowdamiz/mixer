# Guarded snapshot admission F1/F2 correction

Status: bounded design and accepted-source signature proof, awaiting fresh
independent review. This packet amends the frozen 70-member proposal; it does
not replace its other requirements or select operational admission. The exact
root selection is `../swift-semantic-adapter-root-review/guarded-snapshot-export-admission-correction-selection.json`.

## F1: failure before an owning scope can be returned

The selected ingress must return a sum that retains its actual primary failure
and its independent retirement result. A successful scope finalizer cannot own
an exit that happens before the scope exists. In the future shared admission
core, preserve the original admission order, owner, Cancellation backing and
source/metadata/control/Construction tickets. An authentic selected body's
private entry is still the only possible selector of Snapshot. No bool,
callback, byte count, digest, or test event selects that product profile.

The explicit selected pre-scope failure result is structurally:

```rust
struct SnapshotPreScopeFailureV1 {
    primary: SwiftRunFailure,
    retirement: Result<(), SwiftRunFailure>,
}
```

`primary` is the exact actual original final-check failure. Preserve its stage,
kind, code, function/offset, resource, attempted/limit, capacity, deadline origin,
WASI/guest payload and `at_failure`; only its existing `after_cleanup` observation
is populated by consuming cleanup. The retirement result does not replace it.
Original first_failure remains the original first failure. In particular, an
original refund can return that first failure again while recording a separate
cleanup invariant. Do not relabel that return as a new primary.

Before beginning admission, charge the actual early ingress/selector/scope-
return/caller-return/error/Option/cleanup/move places in the selected foundation.
The concrete types in `prototype/control_append.rs` add measured candidate
places; they do not establish the complete final implementation inventory.
The authentic selected body and original shared-core arguments, transfer moves,
and original common inventory continue to be charged independently. These new
numbers cannot fund objects retroactively or authorize a grant.

The consuming failure sequence is:

1. Keep the actual original primary while its error/return storage remains live.
2. Destroy the actual `AdoptionBodyV1` before refunding its source/metadata tickets,
   as the original path does. Consume the concrete early storage aggregate. Its
   actual Option return slots, body slot, selector, and cleanup return slot are
   dropped. Refund any aggregate-owned ticket only after that storage drops.
3. Attempt all originally owned source/metadata refunds even if the early
   retirement returns an error. Retain retirement separately. Preserve the real
   first_failure and cleanup invariant established by the original helpers.
4. **Conservative selected limit:** do not narrow the enlarged Construction ticket
   while the primary/error/return/move lifetime remains unproven. Consume the
   original control through the unchanged `finish_owned_cleanup`. Its one
   foundation test rejects that enlarged charge; retain its Construction charge,
   live-ticket count, combined usage and ConstructionBound (or earlier real)
   cleanup invariant. A retired aggregate does not prove all retained places
   have died. This branch is unqualified for healthy cleanup.

Before successful Construction admission there is no selected Construction
ticket to narrow or release. Destroy the actual body and early storage and
refund only actually admitted original tickets. The original finish can show
healthy zero only if those actual owners retired without an invariant. A
retirement error still remains independent from the primary. No byte-equality
alternate foundation, new RuntimeControl field, repaired ledger, or fallback
healthy observation is permitted.

This packet deliberately does not claim complete selected pre-scope lifetime
closure. Healthy cleanup of the post-Construction branch remains pending until
the actual implementation proves consuming destruction of all additional live
places before returning to the one actual Original foundation. Any later
common-core foundation change must remain the single authoritative formula,
admitted before its objects exist; this packet selects no such change.

`run_correction.py` reconstructs the actual accepted `adopt_body` method as a
test-only source probe with recorded exact substitutions. It uses the actual
body, real validation proof, RuntimeControl, reservation ledger, terminal check,
failure type, refund, and unchanged finish. It adds a compiler-measured concrete
early-place extent before the original Construction admission. Test events
originate actual cancellation or expire the actual deadline immediately before
the exact original post-admission `control.check(cursor)`. They are test-only
boundary events, never selection or stop authenticity in a product entry.

The proof builder is copied byte for byte from the accepted original control
fixture; it passes full original validation and creates ordinary provenance.
These are admission/cleanup lemmas. They do not execute an authentic selected
ingress, the proposed shared core, or any initial-profile wrapper. The original
300,000 profile remains refused; the controls use unchanged SwiftRunBudget
defaults, never a new product limit or proposed operational floor.

The six F1 boundary cases per build mode are retained: source refusal, metadata
refusal, Construction-capacity refusal, cancellation at the final check, deadline
at the final check, and a real foreign-ticket retirement fault. The last case
gets the ticket from a separate actual control's real admission. Its foreign
owner remains charged for the lost ticket; the test does not repair it. Host
storage destruction releases process resources; the retained accounting is
intentional uncertainty, never reported as healthy zero.

## F2: one owner through both phase outcomes, then a shared reborrow

Replace the proposed `Result<SnapshotPhaseV1<'c>, AdmissionError>` handoff with
an opaque private access sum that owns the same exclusive borrow in **both**
branches:

```rust
enum SnapshotAccessV1<'c> {
    Admitted { control: &'c mut RuntimeControl, previous: usize },
    Refused { control: &'c mut RuntimeControl, error: SnapshotAdmissionErrorV1 },
}
impl SnapshotAccessV1<'_> {
    fn shared_control<'s>(&'s self) -> &'s RuntimeControl;
    fn complete(self, storage: SnapshotPhaseStorageV1)
        -> Result<(), SwiftRunFailure>;
}
```

The private real begin method must finish all nonterminal preflight/work/storage
operations and return this sum, including the actual error on refusal. For an
admitted phase, capture `previous` from that same original Construction ticket
before its enlargement. There is no caller-supplied base, mutable control escape,
additional ticket, or independently spendable authority. On refusal retain
original control unchanged and carry the actual nonterminal admission error.
The refusal branch grants no encoder storage and creates no plan/output buffer.

Both states call the same `shared_control` immediately before the **one original
guard literal**. That immutable return lifetime is tied to the shared borrow of
the live access owner. The exporter, original header encoder and original row
writer accept only the actual original guard. Every guard-derived proof/control/
row/header view is contained in a lexical block. All these borrows end before
`access.complete(...)` moves the access owner. There is no direct borrow of the
earlier `control` binding after the access owner has acquired it.

Completion receives the concrete actual phase-storage type, never generic unit
as evidence of retirement. Admitted completion consumes that storage through
the original `end_construction_phase` and the privately captured bound. Refused
completion drops its actual small phase slots without ledger mutation. The
original primary outcome, export attempt, and phase-completion failure remain
separate retained outer results, charged in the selected scope. Header refusal
exits the guard block and then completes the phase; it must not bypass completion.
The actual owning selected scope subsequently performs its own consuming cleanup.

The source proof relocates the original sole literal into a private composition
helper. Its original real guard, original header/row signatures, actual proof
views and control observations compile together. The helper returns primary plus
phase completion. A compiler-only adapter retains the original wrapper ABI so
existing fixture callsites typecheck; it reads `.primary` and is **never executed**.
It is not a working integrated wrapper and does not qualify ignoring phase
completion in product code. The actual future wrapper must retain both results.
All original eight enum variants and payloads remain byte-for-byte unchanged.

The helper's `signature_witness` reads actual original stop/ticket state and
captures an actual bound but does not implement complete cache/WASI pairing,
conditional storage enlargement, planning debit, or export admission. Its
admitted state grants no additional bytes. Its fixed Option phase fields remain
already-covered source-proof slots. Runtime tests separately execute both sum
states, their immutable views, and consuming completion against real control and
proof owners. The compiler typechecks the sole real guard/header/rows composition
in both states; the runtime tests do not execute that writer or the wrapper.

The negative changes only the helper guard's control field from the shared
reborrow to the earlier direct mutable-control binding. The live access owner
is consumed afterward, so Debug and optimized compilation must each reject
with exactly E0502. A successful build is a failure of this control.

## Measurement and acceptance limits

`results.json` and the retained LLVM constants report every new measured type in
unit Debug, unit optimized, ordinary-production Debug and production optimized.
The source manifests reconstruct all 144 files from the immutable accepted tree,
the frozen original append-only prototypes, the recorded wrapper relocation,
the new corrections, and the derived test-only admission probe. Scratch compiler
artifacts are removed; exact sources, transformations and manifests remain.

`CorrectionPreScopePlacesV1` deliberately sums early argument/drop, primary/error,
Result/Option return, caller, retirement and move roles. `CorrectionReborrowPlacesV1`
sums the access/return/Option, Result preflight, refusal, shared-receiver/return,
guard/borrow/views, phase storage/move/drop, original-primary, completion/move and
paired-return roles. The inventories are conservative additions, not physical
stack/RSS, a simultaneity claim, a minimal floor, or a complete live envelope.
Unimplemented authentic entry/scope-return/finalizer and full conditional writer
source places remain pending. Do not add these partial figures to the previous
partial sum and call the result a grant.

The original eight outcomes, single guard, owner/tickets, default/narrowing-only
budgets, P/R work formula and no-refund policy remain requirements. Nothing in
this packet increases a product limit, selects a floor, implements a writer,
changes canonical code, qualifies FieldLog, or verifies a GA gate. Native/device/
simulator/emulator/UI/capture/process inventories remain paused. Frozen wrappers,
hosted catalog/authority/rejected-worker harnesses and stopped Android startup
paths are not imported or executed. Fresh independent review is required.
