# Isolated dispatch region model v2: R01 corrected, execution pending

The reviewed contract is implemented in exactly two Rust files:
`source/model.rs` and `source/tests.rs`. No compiler, test binary or formatter has
run. The frozen host plan requires a separate exact root release before one
compile and one host-test invocation, serially in the single runtime lane.

This version preserves the original ten-member source-only packet and its
independent review unchanged. That review held the original host plan for R01:
the complete pre-wrap return value could be covered only by an unknown Body
frame. The frozen review and its four case specifications are pinned in this
version's input manifest. No original host attempt occurred.

Every transition into BodyReturned now creates a distinct AdmittedReturn owner,
bound to the accepted 13,624-byte AdmittedFixtureOutcome shape. This includes all
five setup refusals, the explicitly counterfactual invariant fallback, and every
BoundReturn branch. Whole backing obligations transfer Body -> AdmittedReturn ->
Child. The unknown Body activation/frame remains independently live through the
return segment and is removed only at ChildWrap. It cannot substitute for the
complete carrier, nor can the carrier substitute for the separate frame.

The model derives no physical slot from these ownership moves. A complete return
extent needs its own identity/capacity/lifetime evidence. Reuse or overlap with
the later child is possible only as an explicit physical declaration with a
qualified arena identity, compatible funding and checked union. Coexisting frame
storage still needs its own coverage and physical relation. All such input in
the prepared tests remains a synthetic hypothesis.

The model imports only standard collections. It imports no product module and
performs no File, environment, allocator probe, process, engine or VM operation.
Its vectors/maps are ordinary model data, not allocator observations. Canonical
source, product selectors and all previous packets remain unchanged.

## Implemented boundary

TraceState exposes a closed Phase/Event machine. Scope-pair return and split are
explicit, followed by parent/quote/reservation outcomes, closure consumption,
five setup stages, typed loader/correlation/leaf branches, complete child return
and short inspection. Explicit destruction separates payload take, payload-drop
start/completion, reservation take, wrapper-drop start/completion and token return.
Ordinary Drop has its own phases and grants no token or refund. Unwind entry,
cleanup start/return and resume are distinct phases; pure capture moves introduce
no unwind edge. Invalid transitions operate on a candidate copy and leave the
original state/history unchanged.

Child token identity is distinct from AcquisitionId. Successful child release
retains acquisition charge, consumed work and historical peak. The conservative
underflow branch consumes the token but retains child storage. Forgetting and
interrupted destruction preserve unreleased backing obligations and never certify
durable root funding. Current production pending selectors are represented only
as source-contract outcomes; this model neither calls nor changes them.

The setup invariant fallback preserves an observed prefix mask without inventing
Ready ownership. It is a conservative typed fallback observation; it does not
prove that normal File calls can reach inconsistent setup state. Likewise token
None is a conservative missing-token outcome, not a claim that a fresh private
dispatch normally loses its reservation.

## Physical and capacity evidence

Semantic owner/backing history is separate from Declarations. Every live owner
needs an explicitly evidenced inline extent; actual source type widths alone do
not provide physical regions. Arena identity, disjointness, capacity, alignment,
current shape, containment, source/compiler/target/cfg binding and backing final
destruction are checked. Unknown facts refuse. Distinct numeric arena IDs alone
do not establish disjointness.

Checked interval unions handle partial overlap and containment once per proven
arena. Incompatible overlapping funding is refused. Separately retained backing
capacity is counted once per BackingKey/BackingId while any semantic owner remains;
Cancellation's scope clone shares its original backing. Proof/error keys stand
for complete opaque backing obligations: a supplied bound must cover the entire
underlying graph, not one convenient allocation. They are not measured allocations
or a physical ownership reconstruction of product failures.

Missing final destruction refuses a completed capacity explanation. Forgotten or
unwound terminals remain incomplete even if supplied bounds look reviewed.
Original acquisition, P0 and C0–C5 coverage are all mandatory, with distinct Work
and Bytes types. The existing checked child-component storage/work sums are
retained in the assessment and are not replaced by a smaller union envelope.
No numeric grant is selected.

**Every Assessment is model_only**, including fitting ReviewedBound-looking data,
incomplete input, invalid traces, overflow and capacity refusals. Its private marker
has no false variant. Evidence labels/IDs are model hypotheses and cannot mint a
ReviewedWholeQuote, reservation, policy, source authority or production grant.
The public shape roster is explicit; no generic type normalizer is implemented.

## Tests prepared and future execution

The original twenty unexecuted methods are retained byte-for-byte and implement
the twenty contract families. Their
finite subcases cover partial setup, actual-root preservation, both leaf results,
single leaf count, pair/capture/child containment, unresolved moves, partial union,
missing capacity/final destruction, identity conflict, checked overflow, shared
Cancellation, live views, normal/ordinary destruction, existing unwind sites,
forgotten child, child-only token/underflow, all ten quote partitions and model-only
results for reviewed-looking evidence. Every numeric test capacity/work value is
arbitrary synthetic data; none is a product price or grant.

Four additional unexecuted methods implement review cases C01-C04. They narrow
every owner extent to semantic live segments and begin child coverage only at
ChildWrap. Across five setup refusals, one counterfactual fallback and five
loaded return branches, missing, undersized, wrong-shape, expired or unevidenced
return coverage must refuse. Complete separate coverage and explicitly declared
return/child overlap may fit only as model_only. Missing identity, missing frame
disjointness, an expired Body frame and incompatible funding remain adverse
cases. The 8-byte unknown frame bound in synthetic fixtures is arbitrary input,
not an observed frame width or a substitute for the 13,624-byte carrier.

host-test-plan.json binds the exact files/toolchain/linker and two argv arrays:
one Debug rustc --test compilation, then that one binary with one test thread.
Root owns the serial execution and one55-second total budget; there is no new
producer runner or broad build system. No optimized second build, version query,
formatter, retry, model layout query or product fixture is proposed. The command
directory must not preexist and becomes execution-owned only after root release.
The proposed binary must execute exactly 24 tests, with none ignored. Compiler
failure stops before the test command. All command outputs, owned child/
group closure, source/binary hashes, generated-file inventory and cleanup must be
retained by root in this lane. Ambiguous artifacts are preserved.

Preparation receipts record Python's exact command/tool/version and source/input
hashes. Rust compilation, test results and all runtime/physical/capacity/price/
funding acceptance remain pending. A future passing host model test qualifies only
this model, not actual File/drop/allocator behavior, root durability, complete
ownership, FieldLog, OTA or GA.
