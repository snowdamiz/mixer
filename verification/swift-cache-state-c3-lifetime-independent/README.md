# Independent correction-3 lifetime review

This is a finite, source-only review of producer seal
`703bf7ca338dac74574c60a7ac42addcd4d1bc44645d559dd05ca0c4dad56c22`
(36 members, 483,656 bytes) and frozen `cache_state.rs`
`0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8`.
No producer verifier, collector, harness, compiler, product or native code was
executed or imported. Python standard-library checks read data and source bytes.

The producer's exact phase completeness claim needs the bounded corrections in
`findings.json`. In its semantic reply row, named `stage: u64` is absent despite
its lexical scope continuing from source710 to773. The final projection return
row similarly omits `child`, `f`, `q`, `stage`, `active`, `planned`, and `pending`
(35 bytes) at source1088. Corrected Control row totals are584 and275. These are
mapping defects, not evidence of a role overflow. The producer's aggregate
Control peak1201 and all numerical contracts remain sufficient for these two
corrections.

Several finite regions are named/listed by the producer without an explicit
live-owner phase map. The independently authored `coverage-addendum.json`
provides those maps, including pin/fill loops, plan/reset loops, final None,
semantic early replies with branch owners, common-stage helpers, and the actual
post-reply caller snapshot. Those schedules preserve every named owner to its
lexical scope; a helper's source/designated/received endpoints do not authorize
retiring a caller local. Generic endpoint superphases intentionally overcount
sequential transfers. No predecessor spare slot is a credit.

The independent schedules and reviewed producer rows fit the existing added
allowances: Control1280, Wire256, Setup256, Report2896. Maximum added values remain
Control1201, Wire152, Setup160, Report2688. Inherited roles total24656; fixed role
union29344, reservations41984, ceiling65536, unused margin23552. This review does
not change these contracts and does not authorize use of the unused margin.

The selected predecessor framing/envelope closure is inherited through exact
root acceptance and byte-identical source prefixes. This review verifies those
bindings and the accepted inventory arithmetic; it does not independently replay
the predecessor's entire historical proof. The C3 candidate source-tree digest
is reproduced from its sealed path/size/hash rows, with the three library files
checked directly. Test fixtures and broad harness source were not opened or run.

The five old232 aggregate/Result capacities become five488 capacities, growing
Report by1280. Five separate new observation capacities256 grow it by1280;
four additional Error32 capacities add128. Total2688 fits2896. Whole aggregates
contain framing104/envelope128/cache-state256; those fields are aliases of their
parent storage, not three additional payload allocations. The full public
Result488 is retained on Err paths. Four488 capacities suffice for immediate
caller source/self/designated-extraction/received overlap; the fifth capacity
also covers the earlier public constructor/return sequence. No compiler elision,
inactive-variant discount, arbitrary application forwarding-depth or libstd
internal bound is claimed.

All16 anonymous128 clear statements are individually bound to source781..796;
their temporaries end with their own statements, before the next clear or any
of the12 restores. Paid24 remains live, making Wire152. A named initializer128
plus local128 would instead require280 with Paid24 and is not selected. Range
fields and slice data/length components are complete. Candidate2048 remains a
single retained payload with its separate inherited2048 initializer source.
Outer `cache_walk.arena` reference8, outer Arena/Vec24, and each slice16 are
different value objects; their referenced payload is not duplicated. Loan16,
semantic StepBudget16, SemanticReply24, record8, words128 and prior envelope
received128 remain live through actual cleanup. Semantic callee locals have
ended before cleanup.

Run from the repository root:

```
python3 -B verification/swift-cache-state-c3-lifetime-independent/review.py
python3 -O -B verification/swift-cache-state-c3-lifetime-independent/review.py
python3 -B verification/swift-cache-state-c3-lifetime-independent/seal.py --verify
```

Commands and their Python identity, script/source hashes, output, errors and exit
codes are preserved under `commands/`. Findings and arithmetic are repeatable;
syntax coordinates are custody/navigation checks only, not OTA release proof.
All23 producer-referenced input identities were checked. The first normal and
optimized attempts failed in this review's own capitalization of the inherited
`io` role; the corrected checker passed in both modes. Both attempts are retained.

Outcome: the frozen producer packet is not accepted as an exactly complete
phase map. This independent addendum supplies bounded corrections for root
selection. Root must explicitly select it before calling the combined lifetime
proof accepted. G6's separately selected512/514 source work bound does not itself
accept lifetimes. No implementation, native/device/compiler-target, signing,
store, customer, operational, published FieldLog, release or GA acceptance is
granted. Newly unrun native checks remain pending under the current pause.
