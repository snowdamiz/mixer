# Producer source accounting for the standalone candidate

This is a source-bound producer proof, subject to independent review. It is not
measured machine instructions, stack, RSS, full replay acceptance, real-source
binding, or a target-performance receipt. `source-index.json` binds every range
to the final Rust bytes. No optimizer elision is assumed. Test-only counters,
private fault/state construction and fixture allocations are outside the product
inventory. The complete inherited analyzer/envelope definitions are unchanged
prefixes; the new production path invokes their actual parser, field/coordinate
checks, old envelope leaf, finalizer, drain, stability and report functions.

## Debit ownership and primitive units

One scalar group contains at most sixteen named bounded scalar operations. One
copy group contains one fixed copy of at most128 bytes. Source and destination
are both accounted: one movement from a source place into its destination is
one copy, not an omission of either endpoint. Arrays returned or passed by value
have their own copy unit; references and u64 transfers consume scalar operations.
A checked fixed-range access includes address arithmetic, bounds/tag tests and
borrow creation. `ld` includes the slice range, first_chunk/expect checks, eight
byte argument copy, LE decode and scalar return. `st` includes destination range,
eight byte LE-array result source, the argument borrow and fixed store. Each is
bounded by two copy groups and one scalar group; the group tables below fuse
only adjacent scalar operations, never independent array copies. Range objects,
borrow arguments and scalar return/received places are included in the helper
role below. No callback, I/O, formatter, allocator or resizable collection occurs
in the semantic leaf, sort, staging, commit or cleanup.

Record preflight remains8192. A passed preflight pays8151 before read/validation,
including later read failure, malformed record or skipped semantic dispatch.
The old envelope debit separately pays425 for every such charge; the semantic
public debit separately pays7680. Neither depends on a leaf-call count. Setup512
and finish256 are successful actual reservations; `Paid` has one product
construction after both propagating admissions. All subsequent record receipts
increment only after actual `Budget::replay(8151)` succeeds.

The disjoint semantic ownership schedule is:

| Group | Source operations included | Maximum |
|---|---|---:|
| admission/prior/loan | `semantic` guards and its caller's exact-length/borrow admission;16 staged snapshot words; two extra scalar reads/stages; packed first-pin header; fixed local/flag initialization; all non-loop closed field/identity predicates and branch admission |256|
| resident/token/seed | at most64 resident probes, at most64 token probes, timestamp/index seeding including every inactive tail slot, checked total/count and body-defined probe |2560|
| merge comparisons | only actual pair comparison body; index and timestamp checked loads, eligibility predicate, <= comparison, short-circuit branches and scalar received key places;321 at most, eight groups each |2568|
| merge transfers | every one of384 output positions; tail guards, chosen-source address/index update, destination address, complete copy_within source/destination/range and loop controls; one fixed8-byte copy plus <=16 scalar operations |768|
| eligible prefix |64 at most; sorted-index decode, ABSENT/end test, checked capacity arithmetic/Options and received values, resident-byte load/subtraction, mask/destination updates and loop exit |640|
| delta/commit/reset | row/delta scalar staging and all destinations, bounded fixed-row construction, complete commit copies, all scalar commits; sole cleanup including256 explicit zero-word stores and12 complete LE loads/restores |640|
| reply/received/audit | complete24-byte reply construction/return/receive, exact StepBudget/reply audit, call/latch/header update,16 snapshot extractions, caller loop transfers and terminal scheduling |248|
| total | no spare group is transferred to another group |7680|

The resident/token maximum is a shared bound, not64 resident probes plus64
additional inactive probes: R resident iterations and64-R inactive iterations
cover exactly64 scratch rows. Each active resident iteration owns seven8-byte
loads (occupied/function/bytes/pins/generation/reserved/timestamp), the checked
sum Option/result and received scalar, branch tests, and two8-byte seed stores.
Each token iteration owns entry/nonce loads, conditional resident occupancy/pin
loads, free-slot selection, complete received scalars and loop tests. The table
reserves24 groups per resident position (inactive positions need fewer),12 per
pin, and256 for tail/loop/prior-sum/body-check transfers:1536+768+256=2560.

The sort performs six fixed bottom-up passes. Runs have sizes2,4,8,16,32,64;
within each pair, a true key comparison consumes one of the two nonempty runs.
The last element needs no pair comparison. Thus comparisons are bounded by
32+48+56+60+62+63=321. Every pass writes64 indices, hence384 transfers. Eligibility
is an index equal to MAX; a legitimate timestamp MAX remains sortable. Initial
indices are ascending slots, and the comparator chooses left on equal keys.
The actual test counter reaches321/384, with ties, reverse order and MAX cases.
This measurement is a control for the source proof rather than its substitute.

The commit/reset640 schedule owns the following complete copy endpoints and
scalar blocks:event-specific snapshot and row stages (initial prior staging belongs to group1);
up to64-byte resident,48-byte pin and40-byte plan stage; their individual word
updates/zero stores; at most one committed row of each kind; ten snapshot-to-
scalar copies, two retained control scalars and optional pending-byte scalar;
256 in-place8-byte zero stores from one8-byte zero source; twelve complete8-byte already-LE arena scalar-cell loads/restores. No2048-byte zero
argument/return owner exists. Scratch initialization and row construction are
reused sequentially inside the same2048-byte Candidate. The operation map is
claimed within640 but still requires independent source reconciliation; a
numerical declaration alone is not acceptance.

## Setup, finish and inherited work

The new production function expands `cache_body!` directly. The generic
budget-injectable `cache_core` exists only under cfg(test): production does not
create an extra full Result in a forwarding helper. The macro arguments move
four mutable references into named local borrows and bind one scalar limit;
they create no closure, heap owner or hidden Result. Those scalar transfers,
Paid source/destination, Progress144 construction, Option<Fixture>80 and immutable
Fixture72 local/config moves, initial state/scalar stores and projection setup
belong to setup512. No Candidate is initialized before old S534/F47/G112 and
new G128 reservations all succeed. Existing Arena/profile/context/header setup
charges remain unchanged. All new initialization loops have finite fixed counts.

Finish256 owns the full32 projection source/destination, suppressed/visible
branch guards, every enum/getter mapping, observation-to-aggregate movement,
aggregate construction and its source/destination, complete Result source and
external received caller place, and final original fixed-error return. G128
owns the single absorbing absent/readability/invalid-budget/underfunded reply
and caller terminal installation; it is not ordinary record credit. All failed
admissions propagate the original Budget error. Original F42 owns the old early
error path; no unpaid new aggregate is constructed there. New finalization and
one-shot guard are reserved from the unchanged report allowance. No nominal
unused group or spare arena region funds a different role.

## Lexical owners, complete values and drops

The inherited union remains24656. Additional selected roles are control1280,
wire256, report2896 and setup256, giving29344. Each role is a conservative union
of named places, not stack/RSS. All actual new types are measured in host tests:
Progress144, Paid24, SemanticReply24, Loan16, Snapshot array128, observation256,
aggregate488 and complete Result488. Each reserved complete Result place512
therefore covers its actual488 bytes.

| Role | Complete places and coexistence | End/drop boundary |
|---|---|---|
| control1280 | Progress144, SemanticReply return24 and received24, StepBudget16, Loan16, decoded-record borrow8, arena/config/candidate/progress/budget borrow union48, leaf locals/flags/checked scalar values256, merge cursor/key/Range union144, nested rr/pr/pl/ld/st/cq/sq argument/return/range/LE-array helper union192, packed-header helpers24, shape helper arguments64, new caller borrows64, checked arithmetic Option source/received/error union112; total1236 plus44 rounding reserve | each helper returns before its caller continues; sort before prefix; leaf reply before cleanup; record scope ends before next read |
| wire256 | Paid source/received48, zero-array source/received16, enum reply source/received16, cleanup boolean source/received2, all wire borrowing/loop/pair transfer conservatively reserved within174 further bytes; explicit pin stores create no literal array/iterator/Option pair owners | Paid lives through final projection; no independent fixture/state/record copy escapes |
| setup256 | checked parsed config Some<Fixture>80 and local Fixture72 with source/destination transfer union80, primitive reservation/receipt flags24 | config views borrowed only; parser setup function returns before record loan |
| report2896 | observation source/destination512; aggregate source/destination976; two complete Result places1024; complete projection including zero-array source256; four fixed Error places128 | projection returns before report I/O; all output failures drop local observations/aggregate fields and return Err; the sole Ok moves into the external caller |

Source and received leaf replies are separate24-byte places even though no
copy/clone trait is implemented. Snapshot128 is a field of Progress144; it is
not a second standalone array. Scalar staging is physically in Candidate bytes
1688..1943; no `[u64;32]` local is introduced. Resident/pin/plan deltas are only
Candidate ranges1536..1687. The sort's two512-byte index areas and512-byte
key area are Candidate subranges, never standalone arrays. Config is an
immutable72-byte fixture value outside the mutable arena: the profile identities
remain parsed, immutable arena bytes. No `Candidate` is passed/returned by value.

The ordinary envelope leaf owns Candidate first, ends its exclusive borrow,
and installs/audits its actual reply. Only then does the semantic Loan exist.
The semantic leaf borrows the same Candidate and exact-length exclusive arena;
its reply contains no reference. The caller receives/audits the reply, copies
only a committed snapshot, and ends that loan before sole cleanup. Candidate
cleanup completes before any next read, footer, drift check, report I/O or next
leaf. No `?` exists inside the loan/cleanup scope. Pre-candidate setup errors
have no Candidate owner. Post-read/framing errors happen before this iteration's
loan, with the prior iteration already clean. A semantic latch skips future
semantic calls; poison additionally disables the envelope leaf.

## Scalar and range ownership

Per-transition writes are one resident row, one pin row, one plan row at most,
and at most thirteen scalar words. `ROW_CELLS` is21/22/23/17/128/130/131/137/84/141;
retained controls are71/78; pending byte138 is written only by EvictBegin.
Setup also writes selected config cells24..28. No immutable Function96 field,
recency/window/histogram/top data or unassigned arena byte is a scratch store.
All these semantic scalar addresses are disjoint from envelope cells
7/9/10/11/12/13/14/64/65/66/160/161. The first-free pin is encoded as slot+1
in private header bits8..14, not placed in an unrelated arena scalar. The low
byte alone is the absorbing terminal reason; unsupported high bits poison.
The remembered nonce is the unchanged Q.next_nonce: the envelope excludes any
other publication/release during the operation, and only successful publication
increments it. No event updates a profile identity.

Before a loan, exact arena length proves all fixed regions, selected row upper
bounds and all twelve restore source ranges. Record fields and immutable profile
join prove event row destinations. Internal selected indices originate only
from the bounded resident scan, are MAX-tailed or0..63, and never come from
opaque timestamps. Destination and pending masks are checked before commit.
The sized Candidate proves every scratch destination, including all256 clear
stores. The exclusive slice cannot resize during commit/cleanup. Fixed infallible
copies and a private commit-status guard are the only operations after first
arena mutation. The normal guard returns true; test-only fault injection returns
poison after a partial copy. No fallible conversion, callback or I/O remains. Under safe Rust these checked range faults
are unconstructible after admission; a guard failure before loan leaves scratch
untouched and poison forbids both leaves thereafter.

## Terminal order, failures and paid-domain exclusions

Projection evaluates actual input errors first, then envelope/private poison,
private header contradictions, unavailable/unsupported child, child refusal,
zero-call absence, complete Q shape, semantic refusal/Failure/limit, ordinary
limit, CAP and closed success. Only the visible rows read/emit Q. Suppressed rows
initialize all words0 and set only boundary/reason/debit/SS/SF. A real output
failure propagates the original Err after dropping local observations; no typed
observation accompanies it. All four authority getters are literal false and
all six authority/reserved words remain0.

The only production `Paid` construction has literal setup1/finish1 and follows
both actual propagating reservations. `records` changes only after a successful
8151 charge. The only production aggregate Ok occurs in that same lexical body
after its input catch, projection, successful report and final budget check.
Therefore00/01/10 cannot reach any actual aggregate Ok. Failed admissions use
the unchanged32-byte original AnalyzerError variant. The three excluded flag
cases have zero runtime-pass credit; this is a source-construction proof.

No failure applicability, allocator refund or rollback is reconstructed. Failure14
returns before scratch/arena mutation and latches reason14; Taken's previous
removal and BuildReady's absence of resident/token survive in the saved Q.
Overlapping semantic predicates have deterministic source order: prior/control
invariants, resident probes/checked byte total, token probes, total/defined-body
join, then the event-specific guards. Lookup checks nonce, free pin, resident;
publication checks nonce, free pin, resident/destination, bytes/pins; release
checks token, live resident/body bytes and postcount. Single-defect names remain
fixed; an overlap's emitted reason is the first actual violated predicate in
this order, never an alteration to terminal precedence.

## Explicit limitations

This source proof is a producer claim for review. Private fault controls inject a failed status immediately after the first resident
commit copy, and a corrupted Candidate immediately after cleanup. Both run the
actual new walker, suppress all extent as poison and prove by actual call counters
that neither leaf runs again. The hooks and counters compile only in test builds;
normal production commit range safety follows the fixed borrow/range proof.
These are labeled private injected controls, never public-fixture or device passes.
Complete source-work reconciliation and lexical owner proof still require
independent review, rather than accepting these producer proofs as measurements. Physical,
native, target, real adapters/custody, release and GA qualification remain pending.

## Final disjoint delta/commit/reset640 reconciliation

This table supersedes the earlier descriptive paragraph for group6. Initial
prior snapshot staging is group1, not counted again here. Sort and prefix
arithmetic stay solely in groups3/4/5. A `st`/`sq` is two complete8-byte array
movement groups (LE result received and fixed destination store), plus one
<=16-operation scalar group including its checked range, wrapper arithmetic,
parameters and scalar return. A direct fixed-range byte copy is one copy group
plus one <=16-operation scalar group. Already-LE scalar-cell commit/restore
copies need no LE conversion or array result place. These count the actual
source work removed by the final rewrite; no optimizer is assumed.

| Disjoint segment | Actual source bound | Groups |
|---|---|---:|
| Largest event delta: built publication | zero64 copy_within2; six resident field st18; six explicit pin field st18; four scalar sq12 |50|
| Final coordinate/stage delta | six sq at0..5; stage matching belongs to the administrative block below |18|
| Row commit | resident64 and pin48, two complete fixed copies and their separate scalar/address groups; plan commits occur in different event branches |4|
| Scalar commit | ten ROW_CELLS and two EXTRA_CELLS; twelve complete8-byte candidate-to-arena copies with separate checked-address scalar groups |24|
| Zero-word clear | one8-byte zero initializer source/received copy;256 exact8-byte stores, each with its own <=16-operation scalar/address/loop block and copy group |513|
| Envelope restore | twelve complete8-byte arena scalar-cell loads/restores; each with one fixed copy and one <=16-operation scalar/address/loop group |24|
| Non-iteration administration | cleanup exact-length/prologue/epilogue/returned/received guard1; row predicates plus two scalar-commit loop prologues/epilogues2; closed event-stage match1 |4|
| **Maximum** | all endpoints, checked ranges, loop guards, complete fixed copies and returned/received scalar status included |**637**|
| Unspent group6 allowance | remains unused; transferred nowhere |3|

The clear iteration's scalar block is: counter/test/advance, multiplication
`at=i*8`, addition `at+8`, range creation/check, source and destination borrows,
copy-length guard and unit return. The restore iteration's scalar block is:
counter/test/advance, checked constant-cell index, source multiply/add, destination
multiply/add, two checked8-byte ranges, both borrows, length guard and unit return.
Each is at most sixteen scalar operations, including the extra final loop test
in the administrative row. No hidden 2048-byte array initializer or helper
argument occurs in cleanup.

All other event branches are bounded below the built-publication case, including
all cleanup and shared final/commit work: Acquire610, Lookup589, PlanBegin583,
PlanEnd600, MissReady611, EvictBegin589, Taken599, Commit589, BuildBegin583,
BuildReady583, hit-publication619, Release613 and Phase583. These are independent
branch bounds; they are not summed or used as spare credit. PlanEnd publishes
at most one40-byte plan delta; MissReady stages that40-byte plan and seven
scalar changes. Refusal skips all arena commit and has at most the already
staged branch work followed by the same537 clear/restore groups; a partial
commit fault returns poison and still reaches sole cleanup. Private hook/counter
instructions compile only in the separately labeled test build.

The reserved-tail zero source is proved by induction. The first Candidate is
`[0;2048]`; the old envelope only writes888..983, disjoint from1944..2047. The
semantic timestamp0..511, index512..1535, row1536..1687 and scalar1688..1943
ranges are all disjoint from that104-byte tail. Built/empty resident staging
copies1944..2007 into1536..1599 with one exclusive Candidate borrow; source and
destination are fixed, nonoverlapping64-byte ranges. No semantic instruction
writes1944..2047. Normal cleanup clears all2048 bytes and restores only888..983,
so it re-establishes the tail invariant before another envelope/semantic leaf.
A commit/cleanup poison disables both leaves and the tail is never trusted again.

The eligible-prefix source also removes repeated Option/closure owners. A
preceding checked `base+request<=capacity` proves `headroom=capacity-base-request`;
the loop compares `remaining<=headroom`. Each of at most64 iterations owns the
sorted-index load2, resident-byte load2, checked-subtraction Option source and
received places2, and <=four scalar groups for capacity/ABSENT guards, complete
Result branch, remaining/mask/destination and loop transfers: at most10. No
arithmetic overflow is silently wrapped and no new exception case is accepted.
