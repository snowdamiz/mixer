# Independent preaccess criteria

This packet precedes access to the producer work audit and active source
composition. It reviews only the root-accepted pure encoder, its exact frozen
embedding, and the original frozen `ExecutionWork` control semantics. It selects
no operational grant, work floor, writer, or release. `WorkAuditPending` remains
the correct composition state until root review.

## Input custody and scope

The candidate seal must be SHA-256
`eadbe533d23459573ead21c7a9bac54ae929b98cdbc76dd47aebe34b5ceb2b1f`,
with 1,256 members. Its final source manifest declares 144 source members and tree
`447719d8fef2928674d9d196266408ca72c70ce152cf0251807d2c3bcd7e7c43`.
The root acceptance receipt must be SHA-256
`4d0eb23c7306e4d63d039f989391e59e45a928be98ece531f69f543952eb15cb`.
This packet verifies those metadata identities and the three actually read source
members. It does not freshly verify every byte of all 1,256 candidate members.

The source ledger below uses `host/encoder.rs` line numbers. That entire file is
embedded byte for byte exactly once in frozen `source/vm/src/experimental/swift.rs`,
beginning at line 732; add 731 for corresponding embedded lines. Frozen
`source/vm/src/experimental_swift_reactor/control.rs` is the only other engine
body read before this seal. General plan hierarchy and paused-environment
instructions were read separately. No active work-audit or composition content,
hosted catalog inspector, authority driver, rejected WorkerV2, broad hosted
harness, stopped Android v5, interpreter startup, closure, runtime, UI, capture,
or process inventory was read or executed.

## Logical action interpretation

A work unit must name a source operation. It is not an elapsed CPU-time, allocator,
RSS, native stack, hardware, or instruction-count measurement. A conservative
bound may group fixed operations, but must expose its grouping and dominate all
operations assigned to it. Distinct actions cannot disappear merely because they
occur in the same row or helper. Count copied or initialized byte lengths as
byte-touch actions, each evaluated directory candidate as a directory probe,
each invocation of `record_word` as a reconstruction, and the operations inside
that reconstruction separately. Additional scalar/helper/branch actions need
explicit bounds; the geometric counts alone are not a complete work formula.

The independently authored `arithmetic_controls.py` reads no encoder, audit, or
composition source and runs neither encoder nor VM. It compares two integer
geometry methods and preserves exact event vectors. Those controls establish
geometry and overflow expectations, not complete primitive coefficients.

## Required source mapping

| Source | Required coverage |
| --- | --- |
| 46-109 | `field`, `require`, integer conversion, fixed header reads/writes, all `words` iterations, option/type/result mapping, checked span addition, success and refusal branches. `SpanCheckV2` addition refusal is `InternalField(15)`, not `Arithmetic`. |
| 111-159 | Every WASI branch, selected-provenance lookup, missing-selected refusal, proof borrow, construction of the view and result. Repeated refused preparation calls are not free. |
| 162-331 | Layout and policy short circuiting; zeroing 2,560 header bytes; magic copy; all fixed word arrays; provenance/runtime helper calls; five duplicated-field copies; optional fields; absent memory/table errors; five validation-cap checks; compound requirements and their late failures. |
| 332-422 | Nine inventories; per-inventory conversions and resource checks; count/capacity/charge arithmetic and joins; nine eight-word directory writes; accumulated metadata charge; bounded imports; runtime checks; final extent and cursor construction. Capacity is not the emitted record count. |
| 423-528 | One full record construction for **each requested word**, not each row: lookup, span checks, signature/type/kind bounds, scalar and type mapping, all five array slots including zero padding, final word lookup/copy, errors from any point. |
| 529-572 | All runtime cap loops (17 and 7); five presence-word checks; optional twelve-word absence loop; final compound predicate with repeated header reads. A helper call is not sufficient evidence for its unexpanded primitive cost. |
| 573-644 | Per-call terminal check; local setup; while checks and header copy; directory scan anew in every nonheader iteration; source conversions/copy; metadata index/word/skip arithmetic, full reconstruction, conversion to bytes and copy; local increments; final emitted assignment and block/result construction. |
| Frozen control.rs 889-921, 1435-1485 | Original control checks first failure, cancellation and deadline before work admission. Admission uses checked addition and `next <= limit`; failure observation uses saturating attempted sum and does not update used credits. Exact equality is admitted. |

The encoder calls frozen guard/provenance helpers whose bodies lie outside the
preaccess read scope: `snapshot_selected_v2`, `snapshot_proof_v2`,
`snapshot_encode_v2`, `snapshot_runtime_v2`, and the eight inventory helpers.
The work audit must identify and cover the exact frozen definitions, including
their loops, copies, conversions and failure branches, before fixed preparation
is accepted. This packet does not invent a helper cost from its output size.

## Block and traversal criteria

1. The directory search evaluates candidates `0..=sid`, hence costs `sid + 1`
   probes on each successful nonheader iteration; it is not nine probes for an
   entire block. A failed search evaluates all nine. Every probe calls `get`
   twice even when that section is empty. Its branch uses short circuiting.
2. Source bytes copy in a bulk step per intersecting block. Metadata advances by
   the remainder of one eight-byte word. An unaligned full metadata block visits
   513 words; an aligned one visits 512. A complete block has at most 513 loop
   bodies/nonheader iterations and at most 4,617 directory probes. A safe bound
   can be larger; a claim of 512 visits for every block is false.
3. `record_word` reconstructs five `u64` slots on every visit, including repeated
   validity checks. A width-five row normally reconstructs five times, and a
   block split adds another reconstruction. Other row widths are 1, 3 or 4;
   they still construct the same five-slot temporary on every requested word.
4. For section start `a`, end `z`, width `w`, and block `[b,b+4096)`, let
   `lo=max(a,b)` and `hi=min(z,b+4096)`. If `lo < hi`, exact metadata visits are
   `ceil((hi-a)/8) - floor((lo-a)/8)`. Summing visits times `sid+1` gives exact
   successful directory probes. The packet independently compares this closed
   interval method with a stepwise integer schedule.
5. Whole-stream visits for a metadata section are `count*width` plus each
   interior block boundary that splits a word. Because all metadata sections
   have eight-byte-multiple lengths, all have the same alignment residue as the
   source. Count every split again. Empty sections have zero visits.
6. Global bounds must use actual inventory counts, exact source length, actual
   section ordering, header bytes, and a stated number of block/terminal calls.
   Applying a 513-visit maximum to every possible source-only block is safe but
   must not be mislabeled an exact count. Maximum section capacities do not
   establish actual emitted counts. The maximum wire extent is 69,765,152 bytes;
   it takes 17,033 nonempty calls. The maximum-capacity aligned case has 331,716
   metadata word visits; the `maximum source - 1` case has 648 split repeats and
   332,364 visits. These are geometry counts, not a work floor.

## Errors, call boundaries and arithmetic

1. Include early missing-provenance/layout/policy errors and late preparation,
   directory and record errors. The failed operation itself costs work, not only
   successful output bytes. An error after a copied prefix still incurs that
   prefix work. Error representation and result propagation need coverage.
2. `next_block` updates `self.emitted` only after the entire while loop succeeds.
   A late error can leave transfer bytes modified while the cursor position is
   unchanged. Retrying must not reuse a consumed work charge; a bound for one
   clean traversal does not authorize unbounded failed or terminal calls.
3. On success each nonterminal iteration makes at least one output byte of
   progress. Prove source range, nonzero width, `skip < 8`, nonzero copy length,
   bounded transfer slices, `at <= extent`, directory extent and bounded indexes.
   Explicitly justify unchecked arithmetic from these accepted invariants rather
   than asserting that every source arithmetic operation is checked.
4. Candidate arithmetic must check every addition/multiplication/conversion in
   work-bound construction, including fixed preparation plus block charges,
   byte lengths plus overhead, record visits times primitive coefficients,
   repeated helper costs, section totals, ceil division, source plus header,
   existing usage plus new credits, and retry/call totals. No wrap, underflow or
   saturation may turn overflow into an affordable grant. Saturation is allowed
   only for original failure observation, not successful admission.
5. Preserve the original control's first-failure/cancellation/deadline ordering,
   shared `ExecutionWork` counter and limit, exact-boundary success and no counter
   increment on failed admission. A new private counter or operational grant
   chosen from arithmetic alone is outside this review.
6. Compare adversarial mutations against these controls: once-per-block directory
   accounting, once-per-row reconstruction, missing five-slot array work,
   ignoring split repeats, dropping last failed operations, reusing a failed
   call's charge, prep omitted because it emits no bytes, ceiling-by-`n+4095`
   overflow, and wrapping multiplication/addition. Retain original failure
   evidence even after separate corrections.

## Verification boundary and cleanup

Only Python integer arithmetic, source reads and SHA-256 checks run here. No
Rust/compiler/VM/writer or native runtime test runs. The tool version and exact
command are recorded with arithmetic output. There are no scratch native
instances, spawned children or capture processes from this lane to clean up.
Unrun native/device/simulator/emulator checks and complete operational work,
storage, cancellation and cleanup admission remain pending. No process inventory
was attempted to make a broader cleanup claim.
