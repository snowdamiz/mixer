# Minimal next code slice

After this contract is reviewed, implement only:

* `verification/swift-root-bound-dispatch-region-model/source/model.rs`
* `verification/swift-root-bound-dispatch-region-model/source/tests.rs`

These are proposed future paths. This packet creates neither file. Keep the model
independent of product modules and canonical selectors. No File, allocator probe,
engine/VM, process, environment reader or generic type normalizer is needed.

The public-to-the-test-module surface should contain:

* A closed Event enum for the events.json roster, including SetupRefused stage0..4,
  the three raw correlation branches, the two typed leaf branches, explicit versus
  ordinary destruction, unwind, forgotten child and sticky-root retirement.
* Distinct AcquisitionId, ChildId, ValueId, BackingId, PhysicalArenaId and RegionId
  types. They are finite fixture IDs in this model, never authority tokens or
  guessed resource addresses. One child and one dispatch attempt per trace.
* CurrentShape IDs for the accepted closure, pair, returned child, admitted/payload
  containment and short views. Bind explicit IDs to exact accepted input rows.
  A borrow does not reuse a value shape, and generic types require no substitution.
* CapacityEvidence = Missing or ReviewedBound with units, upper-bound capacity,
  exact evidence identity and source/target/config binding. Synthetic evidence
  must be tagged Synthetic and must never produce production-authorized output.
* A TraceState transition function returning either the new state or a typed
  refusal. It updates semantic owner sets, child charge/token disposition and
  sticky root status atomically; refusal does not partially commit state.
* A representation/physical-region table kept separate from owner transfer state.
  A physical inline extent requires arena identity, offset, capacity, alignment,
  live event interval and evidence. Contained fields reference the parent extent;
  separate backing retains its own capacity and owner set through final destruction.
* assess_capacity(trace, declarations, limit) yielding IncompleteEvidence,
  InvalidTrace, ArithmeticOverflow, InsufficientCapacity, or ModelFitsCapacity.
  Every result remains model_only; it cannot mint a grant or a ReviewedWholeQuote.

Do not implement policy selection, actual reserve/release methods, new runtime
wrappers or a new product return path in this slice. Existing source continues
returning RootPolicyPending/WholeQuotePending. The model's ChildReleased state
means a legal model trace used a returned child-only token, not an actual release.

## Checked union/capacity algorithm

1. Validate the closed event sequence and every declaration. Half-open intervals
   have begin<end or an explicit unreleased terminal state. Inline capacities
   cover the accepted type width and required padding/alignment. Reject absent
   evidence, unbound IDs, out-of-range setup masks and incompatible funding.
2. Compute each region end with checked offset+capacity. Alignment is positive,
   a power of two, and satisfied by its proven offset. A PhysicalArenaId is accepted
   only with evidence that establishes identity; two arbitrary distinct fixture
   integers are not physical disjointness evidence for a product claim.
3. At each finite event segment, group live inline extents by proven arena identity.
   Sort by offset, merge overlap/containment, and use checked subtraction/addition
   to count the union once. Partial overlap is handled as union, not blindly sum
   or blindly max. Unknown aliasing refuses a physical capacity result.
4. Add upper-bound capacity once for each live separately funded BackingId, even
   when several owners/borrows share it. Drop an owner only after its modeled
   destruction event; backing ends only with a complete last-owner destruction
   witness. Forget and interrupted destruction keep an unresolved/unreleased
   obligation. No File/OS resource becomes zero byte backing because capacity is
   unknown; use an explicitly reviewed bound/conversion or return incomplete.
5. Include original acquisition, P0 parent/token and child components under their
   retained funding identities. Avoid double charging a physical region to two
   partitions. Do not deduct from original IR01 charge or silently change the
   existing checked six-component child quote. Produce a coverage assessment for
   those retained terms, not a replacement price.
6. The maximum checked total over every normal/refusal/cleanup segment is the
   model envelope. Compare it with a synthetic capacity using checked arithmetic.
   Unknown work prices, authority or physical evidence keep production admission
   unavailable even if ModelFitsCapacity is returned for synthetic data.

The decisive first tests are an overlapping interval union, missing capacity,
same-payload transfer with unresolved physical buffers, partial setup ownership,
payload-drop unwind before token creation, child-only versus acquisition release,
and forgetting without refund. prospective-tests.json gives the finite matrix.

## Evidence after that implementation

The first implementation receipt should bind exact model/test bytes and all
synthetic traces under a separately root-selected bounded host-test command. It
must state that no actual product/allocator/File path ran. A passing model is
permission to prepare the next narrow physical/capacity evidence plan, not a
funding receipt.

For an eventual concrete charge, obtain either exact toolchain physical-region
evidence or a reviewed implementation that makes the relevant storage explicit,
covering call/return and destruction frames too. Then join actual backing upper
bounds and all retained quote terms. Source move order, MIR StorageDead, allocator
requested size and semantic destructor counters alone cannot stand in for the
complete physical/capacity proof. Runtime File/error/drop evidence and original
root durable custody remain separately gated.
