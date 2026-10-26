# Independent source-only G2 row-probe review

The typed-row G2 source is feasible under its unchanged 2,560-group cap **with
this bounded accounting addendum**. Do not select the producer's original
2,332/2,230-group totals or its 1,140-byte scoped Control inventory unchanged.
Root must explicitly select this source plus the corrected accounting before
integration. This review does not select a source or change product files.

The frozen producer seal is
`8d3317005e5db2b6114a9bd2be3c40682920f20041a5b46bd22d50ae929aab7f`:
29 members / 2,106,607 bytes. The actual complete source is
`source/cache_state.rs.txt`, SHA256
`a43397ec7cbbec398502acae5911394fced7ed8d220fee096589940eafb49fb1`.
Every member was verified independently. G2 is the exact unique source excerpt
at lines14596–14689; its preceding/following bytes match the packet's separately
frozen prefix/suffix digests. That verifies those declared boundaries, without
reading an old packet or independently asserting the old source's custody.

## Decision and corrections

The corrected complete G2 conservative upper is **26,491 scalar operations plus
838 distinct complete payload copies**:
`ceil(26491/16)+838 = 1656+838 = 2494 <=2560`.
The valid64 occupied/pinned resident and64 live-token AcquireBegin witness is
**24,881 scalar operations plus835 copies**:
`ceil(24881/16)+835 = 1556+835 = 2391`.
The complete-upper maximizer is the conservative `complete.n64.m64` recipe.
It is deliberately an incompatible branch relaxation, not a valid state or
reachable maximum. The valid witness remains separate.

The submitted ledger bypasses tuple constructor-to-designated-return field
transfers for four `as_chunks` calls and `split_at_mut`, and bypasses separately
retained `Option<&array>` designated returns. The submitted capacity inventory
itself retains constructor, designated-return and caller-received places, so
those transfers cannot be removed by an optimizer assumption. It also describes
an indexed `arena_words` range and nested row chunks as if their element width
were one byte: the extra width8 scale operations must be named. A full
`Option<u64>`16 constructor-to-return transfer and full returned array8 payloads
must remain complete copies. A returned `SemanticReply` is24 bytes; the
`return reject(...)` caller-received-to-semantic-return transfer cannot be only
one scalar. We retain the submitted scalar transfer as conservative excess and
add that complete24-byte move, plus the reject constructor-to-return move.

`correction-addendum.json` names every added edge per component. It also retains
all source statement/control endpoints: the resident success dominator has14
extra scalar edges (body entry, six conditional unit/continuation pairs, and
the let-else statement continuation); the pin dominator has9 (body entry plus
four conditional pairs); a tail body adds its scope entry. Three loop final
unit/continuation pairs are charged once in the prelude, even on early returns
where some loops never complete. Every post path receives all three conditional
pairs; refusal templates additionally retain three scope-exit operations.
These are named source-control bounds, not unnamed spare credit. Successful
occupied/matching/eligible iterations maximize these endpoint counts. Empty
and early-return paths execute fewer joins; the enumerated larger source-edge
set conservatively dominates them. Source fixed Index scaling/bounds, complete
array8 arguments, Option16 copies, casts, pattern projections, borrowed fields,
helper entry/return, source/received values and final loop tests stay in the
44 audited primitive templates. No producer Python is imported or executed.

The grouped corrected ledger contains each expanded scalar once in groups of
at most16 and every distinct complete copy separately, each at most128 bytes.
It retains full8/16/24-byte payloads. No copy is pooled with another copy, and no
operation group borrows funding from another semantic group. Full reject reply
work is conservative G2 bounding slack; its actual G7 ownership remains as
selected previously. This does not create a revised G7 ownership contract.

## Source audit

The review covers the actual changed G2 block, its eight initial accumulators,
the actual `reject` definition, the exact semantic guards and the immediate
callers in the same proposed text. It does not rely on the names of helper
functions or syntax matching alone as a semantic proof. The hand audit is
recorded in `source-audit.json`; checker anchors bind that audit to exact bytes.

Resident row and pin row references are8-byte pointers, not64/48-byte copies.
The array patterns bind seven resident word references or two pin word
references; backlink patterns bind two resident word references. Wildcards
perform no payload reads. Resident fields0,1,2,3 are read in order; reserved6/7
remain behind the earlier short-circuit predicates. Field4 is read only after
the entire current resident validation; field5 remains unread. Pin fields0/1
are read before validation. Its backlink reads remain field0 then field3, only
after entry and nonce guards. Splitting the pin header/backlink `if` does not
change its first refusal or lazy arena read sequence. Immutable fixture/record
reference formation occurs earlier, but does not read arena payload.

`from_le_bytes(word).to_le_bytes()` is the identity for every eight-byte word,
so the timestamp assignment preserves all bits and the actual required read.
A legitimate `u64::MAX` timestamp remains data; eligibility still uses occupied
and unpinned state. All unused timestamp words are initialized. A rejected row
has not yet overwritten its timestamp. Earlier validated rows' timestamp writes
and mask timing match the pre-row layout shown in the supplied diff. The mask
amendment at Candidate bytes640..648 is inherited from the unselected seeded
source. This review compares the two G2 read layouts and does not independently
qualify that seeded merge amendment against exact C3's complete implementation.

Arena admission requires8,388,608 bytes. Resident words960000..960512 produce
exactly64 rows of eight words; pin words960512..960896 produce64 rows of six.
All ranges fit the1,048,576-word arena. The Candidate split512 yields512-byte
and1,536-byte disjoint views; its timestamp view is exactly64 words, and the
right-view mask128..136 maps to actual bytes640..648. Configured slots/pins are
1..64. Every live pin checks `entry < configured_slots` before its fixed-row
index. Thus fixed-view/expect/bounds failure branches are unreachable under
admitted preconditions, while their actual successful checks remain charged.
No claim is made about library implementation instructions or machine bounds.
All G2 arena/Candidate loans end at block exit, including refusal paths.

First-empty/first-free behavior, requested-function duplicate detection, checked
byte total overflow, aggregate pin counts, duplicate release nonce reason11,
nonce0/MAX boundaries, and the common post-check order remain the same in the
audited source. No G2 ownership is reassigned to G1, G3, G7, setup, finish or
terminal guard.

## Scoped logical lifetimes

The complete named **added** logical G2 Control maximum is **1,220 <=1,280**;
Wire remains24 <=256 and Setup80 <=256. These are roles additional to inherited
old-envelope roles, not the entire machine stack. `G2-lifetimes.json` retains the
actual caller base480, all232 bytes of block locals, all resident/pin named
body references/scalars to lexical scope ends, and full source/received/return
payload capacities. It adds explicit array-to-slice source/received views32,
both full Region24 constant sources48, ephemeral array-pattern projection
owners, a complete tail-index/array-return phase, and the semantic designated
reply24 on refusals. The view phase reaches1,220; each other enumerated phase
is smaller. The constant/materialized Region objects are not reduced to one
field. Full tuple32, slice16, Range16, Option16, Option pointer8, array8 and
reply24 places are retained. Existing arena/Candidate aliases add no payload.
No last-use retirement of named locals supplies this fit.

The scoped inventory does not accept the entire new source, the29344 role
union, changed sorting lifetime, machine stack, compiler ABI/layout or library
internals. The historical selected exact-C3 union and G6 bounds are not inherited
by new changed callers or helpers. Root must select the new scoped accounting;
remaining complete lifetime review stays pending.

## Reproduction and limits

Run from repository root:

```
python3 -B verification/swift-cache-state-row-probe-independent/run.py
python3 -B verification/swift-cache-state-row-probe-independent/freeze.py
python3 -B verification/swift-cache-state-row-probe-independent/freeze.py --verify
```

The standalone checker consumes source and primitive JSON only as data. It
independently reconstructs all29,440 recipes:4,096 slot/pin completions,
64*12 resident terminal prefixes and64*64*6 pin terminal prefixes. Six resident
and five pin continuations and all eight post paths are checked for weighted
`scalars+16*copies` domination. Every configuration1..64 and early prefix0..63
is covered; the configured maximum cannot outrun this weighted bound under
ceil(scalars/16)+copies grouping. All recipe arithmetic and every actual group
are checked. This is a complete authored-source G2 API-abstraction upper, not
a proof of arbitrary stdlib internals or the source outside the named scope.

The reviewer separately authored old byte-offset and new typed-row logical
models. 4,402 finite cases check first refusal, required payload reads and
partial timestamp/mask scratch. They include every4,096 capacity pair, all13
kinds, MAX timestamps, header/body/reserved/empty failures, overflow, requested
duplicates, pin/backlink failures, release duplicates, nonceMAX-1/MAX, reachable
reachable aggregate post paths,256 deterministic mutations and six constructed states
(empty/publish/pin/release/touch/evict). The six states are not execution of the
full transition engine. 386 LE samples include all bit bases/complements; the
byte identity additionally follows algebraically for every8-byte value.

Normal and optimized Python checks pass with explicit checks retained. Eight
in-memory negative controls reject a changed producer seal,17-scalar group,
129-byte copy, duplicate event ID, missing Option16 return copy, missing recipe,
missing lexical row owner and changed source. Each expected failure is recorded
in `check-result.json`; none mutates the sealed input. `authoring-attempts.json`
retains the failed early JSON inspection (wrong `components` key and output
truncation), then six successful checker revisions with source-bound reasons.
Command logs retain every checker revision's normal/optimized outputs and exit
codes; only the latest revision is selected.

No Rust/compiler/VM/native/simulator/emulator/physical-device, UI/capture,
process inventory, Git, frozen hosted catalog/authority/harness, publication,
credential or customer operation was run. No instance or runtime/capture
process was started; no cleanup was necessary. Other projects' processes and
data were preserved. Newly unrun native checks remain paused and pending.
G3/G4's earlier finite2443/543 observations are not complete upper bounds.
G3–G5, remaining lifetime/implementation/combined-work qualification, real
binding, immutable published-package FieldLog, signing/store/customer/operations
and accountable GA gates remain unaccepted.

`ownership-boundaries.json` fixes the handoff to future G3–G5 proofs. G2 owns
only the eight accumulators and actual G2 scan/post block. G2's timestamp and
mask stores do not pay any later merge read, view, compare, output array, cursor,
argument/return or victim-prefix operation. Future proofs must preserve all
those source edges and their own fixed caps; G2's unspent66 groups cannot fund
them. Corrected reply slack cannot free or relocate actual G7 funding.

The finite packet additionally executes the exact sealed producer witness. The
`prior_pins > configured_pins` post alternative is unreachable after equal live
counts bounded by configured pins; it remains charged in the conservative
branch union. No finite logical case is claimed to reach that alternative.
