# Failed thin-array and inline-source merge proposal

The concrete refinement still fails the unchanged G3 cap. Its necessary source
subtrace is **35,529 scalar operations plus384 complete array8 copies**:
`ceil(35529 / 16) +384 =2605 >2568`, an obstruction of37 groups. This packet
stops at that gate. It is a rejected source proposal, not implementation,
compiler, behavior, layout, lifetime, release, or GA acceptance.

`source/merge.rs.txt` uses `&[u8;64]` and `&[[u8;8];64]`. Safe `as_chunks` and
`first_chunk` form the timestamp view once and each index source once per pass.
Six explicit64-element output constructors remain. All load/emit bodies are
written directly in source, including both arms, local `index`/`out` values,
cursor advances, bounds decisions, exhaustion stores, test-only counters and
direct block-result transfers to array elements. There is no load/emit helper,
macro, optimizer-inlining assumption, unsafe block or reinterpretation.

The selected scalar fixed-array Index20 model remains intact, including the
fixed-length predicate operand, address scaling even for width1, receiver,
entry, returned-reference, dereference and result edges. Each indexed timestamp
still moves its complete8-byte array into `from_le_bytes`; the LE designated
return source, return control and received field store remain explicit. The
two projected-field address edges remain for each cursor reference. The thin
receiver removes exactly one actual slice-length transfer per Index, two per
eligible head, reducing70 to68 scalar operations per head. It saves no other
operand or primitive work.

The all-eligible six-bit-reversal timestamp witness has321 pair selections,
63 one-side-exhausted selections,384 head loads and384 outputs. Its minimal
selection cost is26 per pair and17 per nonpair. The actual witness's nonpair
arm costs19; adding its126 exhaustion stores gives a larger counted G3
subtrace of36,033 scalars plus384 copies, or2,637 groups. These are both lower
bounds for the whole proposed merge. Neither count relies on uncounted positive
setup or statements becoming free. The prior necessary bound already excluded
load-head helper entry/return work, so removing those boundaries cannot lower
the2,605 floor.

The counted G4 subtrace is10,332 scalars plus12 copies, or658 groups. It retains
384 saved output locals/casts, cursor arithmetic and bounds guards, all57 run
resets, six source ranges, six destination ranges/receiver/coercion/check/copy
tails, six complete64-byte constructor-to-received moves and six actual64-byte
copies into the existing Candidate. It removes actual helper argument and
callee-return edges but retains each direct inline block-result transfer.
This is a subtrace, not a G4 upper bound or pass. `subtrace-summary.json` lists
the positive omitted source work, including all seven `first_chunk`/`expect`
boundaries, split/chunk tuples, complete cursor constructors and inline block
statement continuations. The callee merge unit/return remains pending G4 work.

`finite-subtrace-ledger.json.gz` names and groups every counted operation once.
It includes all384 output exhaustion guards, including126 false outcomes and
their exhausted-head stores. The source-written merge has no loop or
`Option<usize>`/`Option<u64>`16 return; its outer `first_chunk` niche pointer
Options8 are explicitly omitted positive work. The selected full Option16
source/received copy rule is unchanged for the affected G2/G5 source. No
G2/G5 full ledger was built after this necessary-bound failure.

The full unselected `source/cache_state.rs.txt` and `proposed.diff` bind the
proposal to frozen C3 SHA-256
`0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8`.
They retain the frozen cached-head packet's G2/G5 byte-layout source ideas
without inheriting its numeric claims. The old packet seal
`772ee1eab231fad68be582c7c17c794c437dadf1d46ae4ea77d04f9b331f3bdd`
and all22 members/787075 bytes were independently hash-checked. The actual
whole Candidate owner, cleanup/staging, G6 source suffix, exact `merge(c)` call
and its headroom guard remain byte-identical. `source-assembly.json` records
those bindings. The private u8 index layout remains unselected.

The selected four caller-only G6 operations remain G6: c reborrow, pointer
transfer into merge's received c, call entry and caller unit continuation.
G3 owns head selection/loading/cache maintenance. G4 owns emission/cursor/run
administration/source ranges/complete output copies and callee unit/return.
No work or spare groups moves between owners. G2=2560, G3=2568, G4=768,
G5=640, Candidate2048, role union29344 and wire256 remain unchanged. Source
presence does not select a layout amendment or authorize a new implementation.

The source-only build and independent verifier check custody, source expansion,
finite arithmetic and the single obstruction witness. They do not run the
Rust proposal, another packet's model, any product workload or old harness.
Complete G2/G5 accounting, all-group acceptance, fresh compiler layouts,
whole Result/caller lifetimes, the full role union, native/device qualification
and GA remain pending. No compiler, product runtime, native instance, UI,
capture, process inventory, Git operation, hosted read, commit, push or
publication was started. No cleanup of other projects was attempted; no test
instance or build directory was created. Only this new owned packet was written.
