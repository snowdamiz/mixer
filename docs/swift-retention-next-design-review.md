# Finite retention result review; selection remains withheld

The sealed count-plan-aware cold-insertion experiment passes this bounded
independent model/result review. No material discrepancy was found in its
declared finite semantics or reported arithmetic. **Implementation selection
remains withheld.** This review selects no VM change, integration or full-target
retry and makes no claim of real runtime improvement.

The reviewed producer seal is
`9fb43c9111e0b4bf5f340358983f404087a5980e7da27c9c3e40483b1649ae57`.
Its 30 members, including the model, frozen contract, explicit traces, design,
raw outputs, failed initial seal preflight and cleanup receipts, match their
retained byte lengths and SHA-256 hashes. The evidence is under
[the independent review packet](../verification/swift-retention-next-design-review/).
Neither this review nor the producer packet is an implementation authorization.

## Independent verification

[The review checks](../verification/swift-retention-next-design-review/checks.py)
pass **18 host methods**, including **292 oracle cases and 46,550 per-request
transitions**. The new oracle uses a fixed slot array and a single sorted
eviction order. It does not reuse the producer's dictionary/shadow/iterated
victim algorithm or its reference helper. It compares resident values, slots,
timestamps, pins, count-plan cells and finite counters after each transition.
The producer's 24 host methods also pass in a separate fresh invocation.
These are overlapping finite checks, not 42 product tests.

The retained Rust `common-tests.rs` loops were independently reconstructed as
explicit warm-up and interval sequences. They match all seven serialized
sequences and all four frozen policies' interval counters and final residents.
The six historical body-work rows also match their raw engine stdout. Their
cumulative hit/decode counters include warm-up; the new interval comparison
correctly removes it. The seventh resident-hit shape is checked separately.
The mixed expensive/cheap/uniform variants share access identities, so their
equal new model rows are not independent body-work improvements.

The new checks cover capacities 0–64; deterministic lower-slot ties;
byte-pressure victims; held abstract pins, then release; valid count-plan reuse;
each changed immutable identity component; replacement collisions; failed scan,
planning, build and admission publication; future timestamps; and the finite
ordinal limit. Random controls use stable sizes per function, collisions,
changing abstract pin counts and all four frozen policies. No candidate policy
or parameter was changed to obtain the result.

The ordinary live VM source closure still contains exactly the same 132 named
files and digest
`16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`.
It is checked before and after each review invocation and at finalization.
The review reads and hashes those specified paths; it does not discover or
execute unrelated hosted harnesses or frozen lanes.

## Semantics and failure boundaries

The model preserves the original count-plan observation before a scan replaces
the cell. The independent collision control first obtains true reuse, then
replaces the same cell with function `f + 512`, then requests `f` again. Both new
admissions are cold even though the cell holds that requested function after
its successful scan. Reconstructing the observation from the replaced cell
would fail this control. A matching function with any changed offset, length
or type identity rejects before replacement; a different function is a
collision and requires a complete scan. Count-plan reuse is only evidence of a
prior successful complete scan. A later planning/build failure can leave that
plan available without a completed resident decode.

The declared replacement order matches the unchanged generic source: occupied,
unpinned, unselected slots, least timestamp, then first/lower slot. The destination
is the last planned victim or lowest original vacancy when no eviction is
needed. Pins exclude their residents even at zero priority. The three-victim
byte-pressure case preserves the pinned resident, and a later abstract release
makes it eligible. Zero is a replacement priority; the next hit promotes that
resident using an increasing ordinal. It is not a time measurement or a decoder
authorization.

Successful scan publication can survive capacity, all-pinned or planning
rejection. Planning failure preserves residents. Build/admission-publication
failure preserves the modeled completed evictions and publishes neither the
attempted resident nor a new pin. On a retry, the retained successful scan can
produce reused priority. These observations do not promise whole-miss rollback.
The finite model commits its selected evictions together and injects failure
afterward; the real generic path removes/drops selected slots in slot order and
can fail during those operations. Individual eviction/drop/cancellation prefixes
remain untested. Model counters and ordinals do not reproduce the product's
sticky attempted-miss/work/statistics ledger.

The producer uses abstract resident pin counts rather than actual opaque pin
records, nonces, owner proofs, acquisitions/releases or cleanup tickets. Copying
Python entry values does not establish preservation of a held product borrow or
pin object. Resident-hit lookup and the immutable adopted source remain outside
the plan-identity miss model. Actual decoder correctness, instruction/security
validation, proof ownership, pin exhaustion and allocation failure are still
unverified by this packet.

## Work and memory accounting boundaries

The reported eight credits per successful miss and zero per hit are an authored
policy schedule. The independently checked arithmetic is `8 * successful model
misses`; it is not measured CacheWork, machine work, timing or net work saved.
Failure-prefix work is absent. Ordinary scan/lookup/index/build/reservation/drop
costs, body sizes and constructor/warm-up work are excluded. The Python global
invariant and timestamp scans are unmetered instrumentation and must not become
unaccounted live operations. The same eight-credit charge applied to both cold
controls is conservative comparison arithmetic; their extra escape-counter
state and implementation are not qualified.

The actual generic path currently publishes its timestamp after the hit/miss
branches join. A separate, reviewed miss publication seam is necessary to carry
the observation without adding a predicate/helper/value to every hit. Zero
estimated hit credits therefore establishes no actual unchanged hit work,
allocation or byte trace. Exact debit placement, full precharge before live
writes and every new work/cancellation prefix remain unresolved.

The specified 64-bit `repr(C)` outcome is a prospective 32-byte layout: three
`usize` counts plus one class byte and seven reserved bytes. The proposal's
dedicated inventory is
`3 * align8(3*32 + 3*R + 2*8 + 3*8 + 4*1 + 4*8) + DeltaExisting`.
That formula explicitly retains complete outcome and typed Result copies.
`R` must be measured for the exact `Result<ScanOutcome, SwiftRunFailure>` type,
including discriminant, error representation and padding; a successful payload's
32 bytes do not determine it. `DeltaExisting` must include every affected
construction, operation and generic inventory, transfer and padding enlargement.
No old inventory slack may pay for new named values. Both quantities and the
final reservation delta remain unmeasured, and the formula cannot certify that
the eventual named-value list is complete before actual source exists.

The zero persistent-policy-byte/allocation/ticket entries describe intended
implementation constraints. They are not measured Rust layout or product-ledger
proofs. The formula does not account for the Python dictionary/Entry headers,
hash-map capacity/slack, deep-copied planning state, 512-cell Python list and
identity tuples, temporary lists, returned results or interpreter/allocator
metadata. Model object sizes, a typed Result reservation, physical stack, allocator
capacity, RSS and product ledger reservations are different quantities. None can
be inferred from these result counts. No new physical-footprint or zero-ledger
measurement was made. Existing cache/entry/combined-byte, resident/pin/ticket,
CacheWork and deadline ceilings remain unchanged.

## Results and disposition

The hot16/stream128 interval reproduces 576 LRU versus 512 candidate decodes,
with 4,096 estimated added policy credits. Cyclic65 reproduces 195 versus 132,
with 1,056 estimated credits. Their policy-only ratios are respectively 64 and
`352/21` credits per avoided model decode. They omit all original work changes.
The old16-to-new64 phase still regresses from 64 to 81 decodes. Old64-to-new64
turnover, including the deliberate plan-collision phase, still regresses from
64 to 128. Eventual turnover in these finite cases is not a general phase bound.
The colliding 65-key cycle's favorable 69 decodes does not establish collision
robustness for arbitrary sequences.

The selected original diagnostic still fails Corpus 1 after 23,358,291 guest
instructions at the fixed 64M CacheWork ceiling. Its five aggregate telemetry
snapshots do not provide the ordered target call stream. The repeated-build
mean is not the cost of each model-avoided function. Multiplying the unchanged
baseline miss count by eight gives 493,024 credits, or 0.77035% of the budget;
those are hypothetical counts, not a candidate forecast. The rejected segmented
and cost/age results remain unchanged.

The initial producer model ran at revision `0a6f110d8857b3732ce40b56aad33b006a187138`;
its final seal and this review began at
`97d436b4ac7357198e36a820ba333b44ae9b9da5`. The retained first seal rejection
and metadata-context receipt distinguish the historical `PLAN.md` hash from
the later root-owned execution index. This review binds its current metadata
separately and requires the live VM and sealed model bytes to remain unchanged.
A root delivery update is not a model rerun, retuning or a failed model test.

Preserve the frozen experiment and this bounded review. Phase regressions,
unavailable call order, absent exact Rust accounting and unresolved publication
work prohibit an inference of target improvement. Any later finite
implementation needs separate authorization and measured generic differential,
hit parity, work/failure-prefix, cleanup ownership and complete inventory
evidence. This review does not choose that work or another policy.

All review children were synchronous Python host processes. Their exact commands,
tool/executable versions and hashes, revisions, inputs, closure digests, raw
streams and output digests are retained. Every freshly owned temporary directory
was removed after device/inode verification on success/failure. No compiler or
native products were produced. No UI, capture, computer-use, native runtime,
simulator/emulator, physical device, full target or process discovery was used.
Those checks remain pending, along with signing/store, provider/operational,
customer, immutable published-package FieldLog and GA acceptance.
