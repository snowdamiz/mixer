# Miss-only insertion experiment remains unselected

The next bounded experiment is a **count-plan-aware cold-insertion policy**.
Its frozen finite model improves the scan-heavy sequences with substantially
less estimated policy work than the earlier adaptive model, but still adds
decodes during a working-set change. **Implementation selection remains
withheld.** No live implementation, integration, full-target retry or changed
limit is selected. The existing failed results remain unchanged.

The [frozen experiment](../verification/swift-retention-next-design/contract.json)
was written before the first model execution. The first result is retained in
[model-attempt-1/stdout](../verification/swift-retention-next-design/model-attempt-1/stdout).
There was no policy retuning after observing it. Plain cold insertion and a
fixed every-32nd-miss MRU escape were frozen controls, not proposed fallback
implementations. Their phase behavior is worse than the primary candidate.

## What the selected evidence establishes

The accepted live decode-plan closure remains
`16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`.
The ordinary 132-file closure was recomputed by hashing exactly the retained
baseline manifest's member names before and after each new host invocation.
All consulted input bytes remained unchanged during each model/test invocation.
Root subsequently updated `PLAN.md` during its separate delivery. The initial
seal preflight rejected that historical/current metadata mismatch; its failure
is retained under `seal-preflight-attempt-1/`. The final receipt records the two
execution-index hashes separately. The frozen model, contract, selected engine
evidence and live VM source remain unchanged. No model rerun or retuning was
needed for that root-owned context update. No excluded hosted or rejected
WorkerV2 lane was read, restored, imported or executed.

The original actual target fails Corpus 1 after 23,358,291 guest instructions.
Its selected supplementary telemetry attributes 34,500,496 credits to 61,142
repeated completed builds: 53.907% of the fixed 64M budget. It contains aggregate
counters, bounded histograms and a small first-repeat identity sample. It does
**not** contain the ordered call stream needed to replay replacement decisions.
The mean repeated-build work is a sensitivity input, not the cost of each saved
function. See [the selected diagnostic](swift-current-attribution-runtime.md).

The segmented-LRU candidate reaches the same limit after 8,746,437 instructions.
Its resident-hit and decode counts are taken at a different progress point and
cannot be compared as a fixed trace. Its rejection remains authoritative. The
cost/age candidate preserves its hit path but uses more real engine CacheWork
on all six finite traces; its favorable expensive-hot trace saves 64 decodes
while adding 115,300 credits. Permanent protection of the stale expensive set
is particularly poor on the phase control. The adaptive proposal saves model
decodes but adds four credits on every hit, large miss overhead and 40 phase
decodes. These three findings motivate the new experiment's low hit overhead,
unchanged victim scan and cheap admission signal. They do not establish that
the new signal fits the real target.

Selected member hashes were checked against the retained seals: the exact
six-trace source, both cost-candidate raw engine stdout files and summary; the
complete adaptive packet; the current attribution events, telemetry and summary;
and the segmented result/events/result summary. The integration receipt and
source manifest were read and bound. This is a scoped evidence use, not a new
independent audit of every historical archive, source inventory or cleanup.

## Exact proposed policy

Keep ordinary baseline resident lookup, pin admission, release, actual decoded
owners, proofs, hash index, limits and complete body build/validation. Keep the
baseline victim loop: among occupied unpinned, not-yet-selected slots choose the
lowest replacement timestamp, with the lower slot winning ties. Byte pressure
can require multiple victims. The destination remains the last selected victim,
or the lowest initially empty slot when no victim is required.

On a miss, preserve one local observation of the **original** count-plan probe:

- A matching function plus matching body offset, length and type is `reused`.
- An empty cell or different function is `cold`; a collision provides no reuse
  evidence and no authorization to skip the complete scan.
- A matching function with mismatched immutable identity fails through the
  existing plan-identity error. Do not weaken or overwrite that check.

The existing 512-cell direct map remains count-scan evidence, not resident IR,
a proof, an eviction ghost directory or an unbounded popularity history. A
successful scan may publish its existing plan before later capacity, planning
or build failure. Thus `reused` means **prior successful complete scan**, which
does not necessarily imply a prior completed decode. One finite control covers
this distinction explicitly. No new permanent history, resident field, mask,
queue, counter, allocation or ticket is proposed.

After a successful miss build/admission, publish the ordinary current-work
replacement timestamp for `reused`, and zero for `cold`. Zero is a deliberate
cold replacement priority; it is not the actual time of last access. A resident
hit still publishes the ordinary current-work timestamp and thereby promotes
that resident using the already-existing hit operation. Pins exclude residents
from eviction regardless of priority. The zero sentinel never authorizes a
decoded instruction, UI operation or security capability.

This is a Mixer-authored finite proposal, not an implementation of an external
cache package or a claim of a canonical published algorithm's guarantees. No
competitor source, generated implementation or new dependency was used.

## Failure and publication boundary

The local observation must be retained before a successful scan replaces its
cell. It cannot be reconstructed afterward, cached across requests, or confused
with a function-only match. All fallible work and classification preparation
must precede the corresponding live publication. A failed scan cannot publish
its new plan. Existing completed scan publication is not rolled back on later
planning failure. Pre-mutation planning failure preserves residents. A failed
build preserves actual completed evictions and their existing cleanup behavior;
it does not publish the attempted resident or pin. There is no whole-miss
rollback promise.

Any future implementation would need an explicitly reviewed private miss
publication seam to carry the insertion observation and choose the timestamp.
It must preserve the ordinary hit path and default generic work/error/allocation
trace, rather than silently adding a new helper, predicate or carry operation
to every hit. The current common timestamp publication happens after both
branches, so this is an unresolved implementation boundary, not a claim that
the new behavior can be inserted by changing one assignment. No such seam was
implemented here.

## Work and memory accounting

The frozen estimate adds **eight logical policy credits per successful miss**
and zero per resident hit: two for the original observation/classification, two
for its prepared transfer, two for timestamp choice/validation, and two for
precharged insertion publication. It adds no policy victim scan, ghost lookup,
ratio division, sort, frequency update or allocation. These are authored groups,
not machine instructions or measured VM CacheWork. A future implementation must
freeze and test the exact debit placement on every failing prefix; this model
does not execute work/cancellation accounting. Full blocks must be precharged
before their first live write and unused credits must not be refunded.

The comparison charges all eight credits to the two cold control policies too,
so those controls are deliberately conservative policy-cost estimates. Their
extra escape-counter implementation/memory cost is not qualified. Constructor,
warm-up, ordinary baseline lookup/index/decode/build/reservation/cleanup costs,
body-size effects, CPU time and new failure costs are excluded from the shown
policy-only estimates. Python global invariants and future-timestamp checks are
unmetered test instrumentation; they are not an authorized extra live scan.

The proposal adds zero persistent policy payload, zero policy allocations and
zero tickets. A new `repr(C)` `ScanOutcome` would contain the existing three
`usize` count fields, a one-byte insertion class and seven explicit reserved
bytes: **32 bytes** on the specified 64-bit layout. This is a proposed layout,
not a measured Rust type. Three disjoint complete outcome copies must be
reserved, even though existing count objects also remain accounted.

The prospective dedicated named-value inventory must include three complete
`ScanOutcome` copies, three complete typed `Result<ScanOutcome,
SwiftRunFailure>` values, two index values, three timestamp values, four decision
booleans and four thin borrow/reborrow values. Its explicit 64-bit byte formula is
`align8(3*32 + 3*R + 2*8 + 3*8 + 4*1 + 4*8)`, where `R` is the **measured** typed
Result size. Reserve three disjoint complete inventories, plus `DeltaExisting`:
every measured enlargement of existing construction/operation/generic inventories
containing the changed scan output, including padding and transfers. Never use
old inventory slack to cover these values. Newly introduced helpers or values
must enlarge this inventory rather than disappear into the formula.

`R`, `DeltaExisting`, the exact final reservation delta and hit-byte parity are
**unmeasured**, because no Rust candidate exists. They cannot be assumed zero.
This is an explicit accounting boundary and another reason implementation
selection is withheld. The permanent decoded-owner layout is intended unchanged;
the prospective outcome is transient. Any changed reservation must still be
admitted against the existing cache and 256-MiB combined ceilings, using existing
tickets before constructing named values, and consumed at existing boundaries.
No physical stack, allocator overhead, RSS or zero-ledger proof follows from the
Python objects. The 16-MiB cache, 8-MiB entry, 64 residents/pins, 86 tickets,
64M CacheWork and deadlines remain unchanged.

## Frozen finite observations

The seven access sequences are reconstructed exactly from the retained
`common-tests.rs` loops and serialized as
[explicit synthetic trace bytes](../verification/swift-retention-next-design/synthetic-traces.json).
Warm-up is excluded from all columns below. The historical cost engine printed
cumulative decode/hit counters while excluding warm-up from work: its 592/528
hot-stream totals correspond to 576/512 interval decodes. The new baseline model
matches both historical packets after this explicit adjustment.

| Synthetic interval | LRU decodes | New policy decodes | Adaptive model decodes | New added policy estimate | Adaptive added policy estimate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original hot16 / stream128, four rounds | 576 | 512 | 512 | 4,096 | 124,104 |
| Cyclic65, three rounds | 195 | 132 | 163 | 1,056 | 32,844 |
| Expensive hot / cheap cold | 576 | 512 | 512 | 4,096 | 124,096 |
| Cheap hot / expensive cold | 576 | 512 | 512 | 4,096 | 124,096 |
| Uniform hot / cold | 576 | 512 | 512 | 4,096 | 124,096 |
| Expensive old16 to twelve cheap new64 cycles | 64 | **81** | 104 | 648 | 22,856 |
| 256 resident hits | 0 | 0 | 0 | 0 | 1,024 |

The three expensive/cheap/uniform variants have the same access identities. This
model does not execute their different bodies, so their identical new rows are
not three independent net-work wins. On the hot/stream shape, 4,096 / 64 = 64
estimated added policy credits per avoided decode; on cyclic65 it is
1,056 / 63, approximately 16.762. Neither ratio includes the original work saved
or spent elsewhere, or proves that the real target has these shapes.

The phase regressions remain visible. The retained phase adds 17 decodes. A new
adversarial phase from **64 hot old residents to 64 new functions** takes 128
decodes versus LRU's 64; all old residents eventually leave. In the same finite
12-cycle interval, plain cold insertion takes 768 decodes and the frozen
every-32nd-miss escape takes 653. Those controls can pin stale old priorities
for long periods. A 64-cycle version of the old16 phase still takes 81 new-policy
decodes, so the 17 extra decodes do not grow indefinitely on that tested shape.
That is a scoped model observation, not a general phase bound.

All-512-spaced keys collide in one plan cell. A 65-key colliding cycle takes 69
new-policy decodes versus 195 for LRU, but this favorable result does not make
collisions safe for every access sequence. The separate old64-to-new64 phase
with deliberate plan collisions still doubles decodes to 128. A scan640 control
exceeds the plan table; the model retains its 16 warmed residents there. No
function identity, protected size or escape parameter was tuned to these results.

At the observed baseline hit count, the adaptive four-credit hit tax alone is
2,150,304 credits. Eight credits at the **unchanged hypothetical baseline miss
count** would be 493,024, or 0.77035% of the fixed budget. Actual candidate hits,
misses and saved function costs are unknown. This is sensitivity arithmetic,
not a target forecast or permission to spend more work.

## Verification and decision

[The executable checks](../verification/swift-retention-next-design/test_model.py)
pass **24 host methods**. They cover all 65 capacities from zero through 64 for
four frozen policies; 48 independent sorted-list reference cases; exact old
baseline counts; deterministic slot ties; valid and corrupt plan identity;
collision behavior; held pins and three byte-pressure victims; successful-scan
publication versus later planning failure; committed eviction/build failure;
failed scans; future timestamps and a finite ordinal boundary; exact frozen
output reproduction; and selected historical member hashes. The model does not
test actual decoder correctness, proof ownership, pin-record exhaustion,
allocation failure, cancellation prefixes or the product cleanup ledger.

Commands, Python 3.14.8 executable hash, arm64 macOS environment, Git source
revision, consulted-file hashes, ordinary source closure, exact raw streams and
cleanup receipts are retained under
[the evidence directory](../verification/swift-retention-next-design/).
The model and test invocations used separate freshly named temporary directories;
both synchronous children exited zero and both directories were removed after
device/inode identity checks. No background, native, simulator/emulator, capture
or UI process was started, and no broad process discovery was used.

The candidate has a materially cheaper synthetic policy schedule than the
previous adaptive proposal and merits preserving as an experiment. Its phase
regressions, missing actual call order, unmeasured Rust accounting and unresolved
publication seam prevent implementation selection here. Preserve the frozen
result, decline a full-target run, and obtain independent design review before
any separate implementation authorization. A later finite implementation would
still need exact generic differential and unchanged-hit receipts, every new
work/cancellation prefix, failure/cleanup ownership tests, measured complete
inventories, identity/collision boundaries and the same six body-work traces.

No VM candidate, actual target, native runtime, device, signing, store,
operational, customer, published-package FieldLog or GA gate was attempted or
passed by this packet. Live source and the original failures remain unchanged.
