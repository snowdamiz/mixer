# Unselected prefix subtraction: source argument and stopping obstruction

This packet changes one G5 source site in the exact predecessor full source
`a43397ec7cbbec398502acae5911394fced7ed8d220fee096589940eafb49fb1`.
It replaces the `checked_sub`/`Some`/`reject(13)`/`next` assignment with
`remaining -= bytes;`. The complete proposed full source is frozen at
`6ae313ca80cc32e73a081c3925a6c99862c6628dd8e9f1042ecdeedd7d703708`.
`source-assembly.json` records the exact removed/inserted bytes and unchanged
prefix/suffix hashes. No other bytes, caller, G2, merge, G6, budget, role or
public capability change. This is a source proposal, never a selected product
implementation. The argument below is conditional on the existing component
preconditions, and does not prove public File/envelope reachability.

## Completed G2 establishes the sum and eligible set

The semantic entry refuses an arena length other than 8,388,608 and fixture
slot/pin counts outside 1..64 before the G2 block. Candidate2048 remains a
separate exclusive mutable borrow. The fixed Region ranges and nested array
views therefore exist at their complete stated lengths. These are existing
source-domain preconditions, not optimized-away checks.

For physical slots `0..f.slots`, the actual source decodes occupied, function,
bytes and pins first. It refuses occupied>1, pins>f.pins and nonzero reserved6
or reserved7 in the existing lazy order. Occupied rows must have function<80000
and 0<bytes<=f.entry. Only then does their `total.checked_add(bytes)` succeed
and bind a new total. A failed sum returns reason10 before count, requested
identity or timestamp work for that row. Empty rows require function=ABSENT,
bytes=0 and pins=0. No other occupied discriminator is admitted.

Induction over the successful scan consequently gives

`total = sum(bytes[j] for every occupied j below f.slots) <= u64::MAX`.

All terms are nonnegative and occupied terms are strictly positive. A requested
function duplicate refuses reason7; duplicate *other* function identities are
admitted but do not duplicate physical slots. The timestamp word4 is copied
only after the full row succeeds. Word5 is deliberately unexamined. Timestamp
bits, including u64::MAX, are unrestricted. Slots at or beyond f.slots receive
zero timestamp words and no eligibility bit. For each scanned slot, eligibility
gets that physical bit exactly when occupied=1 and pins=0. The initialized mask
has no other set bits. G2 writes its complete LE representation at Candidate
640..648 after the pin scan and before the existing ordered aggregate checks.
Successful completion equates total to prior_total; the prior value is never
used to authorize skipping the checked sum.

Pin and post checks can reject additional states but cannot weaken these
properties. Even a strange admitted pin arrangement with duplicate tokens or
only globally consistent pin counts leaves every eligible row occupied and
unpinned. The argument needs no unstated per-row pin bijection. Neither an
ignored generation nor arbitrary timestamps nor duplicate unrequested function
identities creates an additional physical eligibility index.

## Exact merge is a stable eligible permutation with a sentinel suffix

`check.py` independently reconstructs the complete frozen `fn merge` geometry
and requires exact equality: all 64 literal mask operands, all timestamp source
indices, 32 width1 pairs, five later passes, all 320 emit sites, both selected
arms, all 31 initial/reset two-head blocks, every cursor literal, cfg(test)
counter body and the six complete array-copy destinations. The reconstruction
is an audit of source geometry; it is never compiled or used as product code.
The source equality and the following structural induction are both required.

Use an abstract key for each physical eligible index j: `(0,timestamp[j],j)`.
The source sentinel255 has key `(1,0,0)` and is after every real timestamp,
including a real u64::MAX. The temporary exhausted head256 is not an output
value. Width1 begins with two distinct literal physical slots in ascending
order. Each is replaced by255 iff its eligibility bit is clear. The actual
predicate chooses an absent right last, an absent left last when the right is
real, and otherwise uses `lt<=rt`. Thus each pair emits exactly its two input
values, eligible ones in timestamp order, with stable left preference for a
tie and sentinel values last. No state has been read from a preexisting index
buffer.

Assume a later pass has stable sorted runs of the stated width, each containing
exactly its input physical slots or their sentinel replacements. Its reset
literals partition the 64-element input into disjoint adjacent left/right
runs. lp/le and rp/re are initially the exact run endpoints. A head denotes the
next unconsumed byte of its side, or256 iff that side is exhausted. Timestamp
cache fields are read only for a real byte. A cached value left over on255 or
256 is ignored by every predicate that could select the real other side.

When ri>=255, the predicate chooses left iff li!=256. It therefore chooses a
real left before a right sentinel, drains left sentinels stably before right
sentinels, and chooses right when left is exhausted. When ri<255, it chooses
left iff li<255 and lt<=rt. Thus a real right wins over an absent/exhausted
left; two real heads compare only u64 timestamps with stable left preference.
Both sides cannot be exhausted while an output remains: after k outputs,
exactly k of the run's 2*width positions have been consumed. Hence the chosen
head is never256, including the last output. The chosen pointer advances once;
if still below its endpoint, exactly its next byte is loaded, otherwise its
head becomes256. The other pointer is unchanged. These are the actual source
arms, not an inference about optimization.

This proves by induction within a run that each output consumes a distinct
input position, emits it once, and preserves the sorted stable order. Induction
over widths 2,4,8,16,32 proves that the final Candidate512..576 is exactly the
eligible physical-slot permutation sorted by `(timestamp,slot)`, followed by
255 repeated 64-|eligible| times. The seed writes Candidate1024..1088; passes
then alternate 512..576 and1024..1088 and finish at512..576. Each full output64
is initialized before copying. The immutable source view belongs to the inner
output-constructor block, which ends before the mutable destination copy.

This induction covers every one of the 2^64 masks and all u64 timestamp vectors,
including all-absent, all-equal, u64::MAX, mixed MAX/0 and stable ties. The finite
oracle checks every mask and rank vector over {0,1,MAX} through five active
slots, plus fixed and seeded 64-slot families. These executable samples are
independent corroboration, not the universal proof.

## Arena stability and G5 subtraction

Between completed G2 and the edited expression, `semantic` invokes no external
arena callback and makes no arena payload writes. Miss validation reads the
function/plan/config and writes only Candidate staging at1648..1688 and its
snapshot words. `merge` accepts only the exclusive Candidate borrow and cannot
access `b`. It writes the known Candidate index regions and leaves the mask's
640..648 bytes distinct from both64-byte index ranges and the512-byte timestamp
range. The G2 arena loans end at their explicit block before the G5 shared
`as_chunks` loan is formed. The exclusive `b:&mut[u8]` remains alive for the
whole semantic call; its length and row bytes cannot change through another
safe loan or through the immutable Loan. Fabricating overlapping unsafe
references is outside the existing component's admitted preconditions. No such
aliasing or public admission is invented by this proposal.

For a processed prefix P of distinct eligible physical slots, induct on its
length and retain

`remaining = sum(bytes[j] for occupied j not in P)`.

Initially P is empty and this is the checked G2 total. Every next non255 merge
byte is a distinct eligible occupied slot outside P. Its current bytes equal
the G2 bytes, remain strictly positive, and are one term of this nonnegative
sum. Therefore `remaining>=bytes[next]`. Ordinary u64 subtraction cannot
underflow and establishes the invariant for the next prefix. Early headroom or
sentinel breaks only shorten P. A false final while test cannot extend it.

The preexisting `f.base.checked_add(w[13])` guard, together with request>0,
proves both left-associated headroom subtractions are valid. This proof grants
no elision of their source work. The edit removes the actual Option16 source,
designated-return, caller-received and pattern path; it does not pretend that
an unchanged checked operation is free.

Every malformed input refused before this site retains the exact same source
prefix and therefore its same first refusal and required read ordering:
semantic admission, G2 header/empty/occupied/overflow/duplicate/pin/backlink/
nonce/aggregate errors, function identity and all miss-plan/request guards are
unchanged. All malformed states that G2 actually admits still satisfy the sum,
eligibility and stability proof above. The sole removed reason13 edge was
therefore unreachable under these component preconditions. All other reason13
sites remain. If those preconditions are changed or a counterexample to distinct
eligible output or stable row sizes is found, retain the checked operation.

The G5 candidate byte read and sentinel decision still occur before the row2
byte read; the exact index expression, complete array8 LE read, mask update,
destination update, index advance and final feasible expression are unchanged.
Checked and ordinary finite prefix models compare the complete read trace and
all final values. They execute no product implementation or compiler.

## Decisive G3 necessary trace; no complete-upper or lifetime acceptance

The unchanged merge has a concrete all64-eligible six-bit-reversal timestamp
path. `necessary-G3-witness.json` contains that complete component state: 64
occupied distinct resident functions with bytes1/pins0, one empty configured
pin, prior count/total64/pins0, a defined new requested function64, matching
plan and accepted request64 with base0/capacity64. G2 and miss guards admit this
source state. Public File/envelope reachability is not established.

The new checker independently rederives, without importing any old builder,
the earlier necessary trace: 32 seeded choices,64 seeded timestamp loads,320
later eligible head loads,289 paired choices,31 one-side-exhausted choices and
62 exhaustion stores. Its32929 scalars plus384 separate complete array8 copies
are still a subtrace, never a whole-source upper.

The old68-scalar later-head expansion includes actual Index20 plus expression
and field-receiver work, the index cast/store, timestamp predicate/branch,
complete timestamp array8 argument, LE entry/conversion/designated scalar/
return, and timestamp destination projection/store. It ends at the two scalar
store targets and the predicate branch. It includes none of these six
additional actual source-control edges for an eligible head:

1. `s.li = index as u16;` assignment expression's unit construction.
2. That semicolon's unit discard and statement continuation.
3. `s.lt = u64::from_le_bytes(...);` assignment expression's unit construction.
4. That semicolon's unit discard and statement continuation.
5. The completed timestamp `if` expression's implicit unit construction.
6. That `if` statement's unit discard and continuation to the containing block.

The same applies to the right-side fields. An assignment's scalar result-to-
field store is not its following unit/control result. An LE call's scalar
return is not the enclosing assignment expression's unit. An if predicate
decision is not the completed if expression's unit or its following statement
continuation. These are distinct edges under the selected source grammar;
the selected G2 timestamp assignment already charges statement unit and
continuation separately, and its independent correction separately charges if
unit and continuation. No new owner convention is being used here. Head cache
maintenance and these corresponding control edges remain G3.

Each of the320 actually executed eligible later heads contributes those six
edges, for1920. Each of31 actual initial/reset two-head blocks completes one
unit construction and statement continuation, for62. The separately omitted
`ld(c,640)` contributes only39 definitely executed source edges in this packet:
eight complete actual array-to-slice receiver/argument/call-entry edges plus31
for its actual `b[at..at+8]` range expression, received receiver/index operands,
bounds, address, length, view loan and return. Its first_chunk, expect, complete
array8 transfer, LE result/return and all subsequent sort-view setup remain
positive omitted work. No extra mask-load payload copy is even needed.

Thus the necessary trace is

`32929 + 320*6 + 31*2 + 39 = 34950 scalars`, with384 separate copies.

`ceil(34950/16) + 384 = 2185 + 384 = 2569 > G3 2568`.

`necessary-G3-ledger.json.gz` names each counted source edge once and groups
at most16 scalar edges or one complete bounded copy. `necessary-G3-sites.json`
maps all320 head executions to distinct actual source sites, including the
separate initial and selected-arm reloads at run boundaries. Nothing is moved
to G4; no G2/G4/G5/G6 spare work, omitted positive work, grouping credit,
timestamp compression, optimizer behavior or last-use retirement reduces it.
The ordinary subtraction edit changes no merge byte and cannot remove this
G3 obstruction. Root independent review remains required.

The task stops at this decisive obstruction. There is no complete G3/G4/G5
upper, full G5 fit, changed sorting/helper/caller lifetime reconciliation,
whole role-union acceptance or implementation selection. In particular the
old C3 G6 maxima512/514 and lifetime29344 are not automatically inherited by
this full proposed source. The six final snapshot stores remain G6; its four
merge caller edges remain G6, and merge's callee implicit unit/return remain
G4. Previously selected exact G2 scoped evidence remains scoped to its
unchanged bytes and caps. All role and work caps remain unchanged.

A bounded next design can change the actual eligible-head source to reduce
repeated cursor field projections or cache-assignment statements, then recount
the complete source with any new tuple/full payload copies. Such a design is
unselected and unimplemented; merely renaming ledger edges or moving them to
another owner cannot address this obstruction. No compiler, full-target,
native runtime, UI, capture, process inventory or publication was started.
