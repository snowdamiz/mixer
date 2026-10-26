# Scalar-cursor source proposal and bounded proof

This is a producer source/model proposal requiring fresh independent review and
root selection. It is not a selected product implementation or an OTA authority
check. It does not execute Rust, a compiler, the VM, a fixture harness, a native
runtime, a simulator/emulator, a phone, UI automation or capture.

The full source SHA-256 is
`f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b`.
Its authorized predecessor is the full prefix-subtraction proposal
`6ae313ca80cc32e73a081c3925a6c99862c6628dd8e9f1042ecdeedd7d703708`.
`source-assembly.json` binds exact prefix/suffix bytes and the one contiguous
changed merge/cursor fragment. Five aggregate constructors become eight scalar
locals each: `lp/le/rp/re:usize`, `li/ri:u16`, and `lt/rt:u64`. Every actual
`s.indices`, `s.timestamps` and scalar field use becomes an ordinary fixed-array
reference or scalar use. The existing shared `source` and `timestamps` bindings
supply the references. No new ownership of Candidate2048 or its payload exists.
The aggregate type is removed. No mask, timestamp read, condition, reset, output,
array-copy destination, call boundary, G5 expression or error path is edited.
The source includes unchanged cfg(test) counters; extra atomic instrumentation
is outside the production authored-source work model used by the selected caps.

## Universal semantics and subtraction safety

Relate the old cursor aggregate state to the new local state component by
component. The initial values are equal; an old field read and its corresponding
new scalar/reference read therefore yield equal values. The literal endpoint
resets are unchanged. Every branch condition and every mutation has exactly the
same operand values and destination component under this relation. Induction
over the actual unrolled source expressions consequently preserves all reads,
branch choices, cached head values, cursor values and output bytes. This is a
source-state simulation, without optimizer, register, last-use or compiler credit.

For completeness, take an eligible slot's key to be `(0,timestamp,slot)` and
sentinel255 to be greater than every real key. Timestamp MAX is ordinary u64
data. Width1's literal slots are distinct and ascending; its mask expression
replaces each ineligible slot with255. Its predicate puts eligible values before
255 and uses left preference on a real timestamp tie. Both outputs are exactly
the two input values, with stable sentinel order. Neither a preexisting index
buffer nor a timestamp discriminator defines eligibility.

For a later run, lp/le and rp/re partition its two disjoint adjacent input runs.
The current head is its side's next byte, or256 if its pointer reached the
endpoint. Real heads cache the exact timestamp; the predicate never consults a
cached value for255 or256. If ri>=255, take left iff li!=256; otherwise take left
iff li<255 and lt<=rt. This drains real values before sentinel255, then drains
sentinels stably, and chooses a real right over an absent/exhausted left. At an
output before the end, both sides cannot already be exhausted: after k outputs
exactly k input positions have been consumed. The selected output is therefore
never256. Exactly that side advances, loading its next input byte if in range,
otherwise installing256. The other side remains unchanged.

Induction within each run proves a stable sorted permutation. Induction across
widths2/4/8/16/32 gives the final64-byte output: each eligible physical slot once,
sorted by `(timestamp,slot)`, then64-|eligible| copies of255. This covers all2^64
masks, all64-tuples of u64 timestamps, all-absent, MAX, all ties and mixed MAX/0.
The complete array is initialized before each copy. The input fixed-array loan
ends with the inner output-constructor block before the destination mutation.

The G2 source and all pre-merge guards are byte-identical to the authorized
predecessor. A successful G2 scan overflow-checks the sum of every occupied row's
strictly positive bytes and checks that sum against prior_total. Each eligibility
bit denotes one physical occupied, unpinned row. Empty rows contribute zero;
other duplicate function identities or arbitrary generation/timestamp values do
not duplicate physical slots. A failed occupied sum refuses before count,
requested-function and timestamp work for that row. Header/body/duplicate/pin/
aggregate refusals keep their exact previous lazy reads and first reasons.

The arena's exclusive loan and immutable configuration contract remain assumed
component preconditions, not a newly established public File admission. Between
G2 and G5 no arena payload write or external callback occurs. Miss staging and
merge mutate only distinct Candidate staging, timestamp/index/mask regions;
merge has no arena argument. The typed G2 loans end before the later G5 arena
loan starts. Thus every G5 size still equals the G2 value.

For a consumed prefix P of distinct eligible physical slots retain
`remaining=sum(bytes[j] for occupied j not in P)`. Initially this is the checked
G2 total. The next real output is a distinct eligible occupied slot outside P,
so its size is a nonnegative term of that remaining sum. Consequently
remaining>=next_bytes, ordinary u64 subtraction cannot underflow, and it
preserves the invariant. Any headroom/sentinel break only shortens P. The prior
successful `base.checked_add(request)` guard proves both headroom subtractions.
This retains the authorized conditional subtraction proof; fresh independent
full safety review is still required. Changing these preconditions, the stable
permutation, or arena stability would require restoring checked subtraction.

Every earlier malformed/refused path has unchanged bytes and keeps its first
refusal/read ordering. Every malformed state G2 admits still satisfies the
physical-slot sum and eligibility invariant. The removed checked reason13 edge
was unreachable under those component preconditions. Candidate index read and
sentinel decision still precede resident word2 read. No public File reachability,
ABI, machine/library stack or actual compilation result follows from this proof.

## Source work and unchanged owners

`components.json` contains independently expanded primitive source boundaries;
`complete-upper-ledger.json.gz` expands every recipe into unique owned events and
an exact-once partition. Every group contains at most16 scalar events or exactly
one complete copy of at most128 bytes. No copy pooling, cross-owner scalar
packing, unused-capacity, optimizer or other-owner work credit is used. Fixed
array Index20 and fat-slice Index21 retain their expression operands and receiver
edges. Range indexing retains both Range fields and both received slice fields.
IndexMut17 is not invoked by the changed merge/G5 source; the selected unchanged
G2 proof retains its actual mutable boundaries. Full Option16 transfers in
unchanged code remain charged by their selected proofs. Niche Option references
use all8 bytes; tuple32 and array64/array8 transfers remain distinct.

The templates include operands, received arguments/receivers, entry, checks,
address formation, returned references, full payloads, scalar designated/received
returns and target uses. Scalar assignments, their unit/statement continuation,
completed if units/continuations, lexical entries/exits, array-constructor and
caller/control endpoints are separate. A scalar destination store is never used
as its following unit/control result. Some impossible simultaneous branches and
sequential endpoints are deliberately unioned for a conservative upper; these
are upper traces, not a claim that all counted events share one execution.

There are64 seed timestamp reads unconditionally. Each later pass consumes all64
input positions exactly once, so it loads at most64 real timestamps; a false
head predicate is shorter than the full eligible-head template. All320 later
output choices are bounded by the21-scalar real-pair choice; absent/exhausted
choices are shorter. Exactly two sides exhaust per run, for62 sentinel stores.
There are31 two-initial-head blocks,26 literal endpoint resets, five source
views, and six complete output arrays/copies. G5 has at most64 full iterations;
both break routes and the final false test are covered by a separate same-owner
terminal union, even though they cannot all happen on a single path.

| Owner | Explicit equation | Scalars | Separate copies | Groups / cap |
| --- | --- | ---: | ---: | ---: |
| G3 | 160 setup +64*40 seed heads +32*21 seed choices +320*66 later heads +320*21 choices +5*8 head initialization +31*3 head blocks +62*3 exhaustion stores |31551|393|2365 /2568|
| G4 |32*14 seed emit +5*51 complete source views +320*27 emit +6*49 array/copy boundaries +2 second initializer +6*4 output block controls +5*8 pointer initialization +26*12 resets +2 callee unit/return|10017|28|655 /768|
| G5 |80 prelude +64*122 full iterations +27 final/break union|7915|66|561 /640|

G3 copies are9 complete setup transfers plus64 seed and320 later array8 reads.
G4 copies are10 complete fixed-view Option8 transfers plus18 complete array64
transfers. Each output includes array constructor to designated block value,
designated array to named output and actual output64 to Candidate64 separately.
G5 copies are two as_chunks tuple32 transfers and at most64 array8 reads.

Ownership follows the predecessor's actual G4 `width1.second-initializer` and
five `p*.source-range` sites: second initialization and the complete input index
source-view chain stay G4. G3 retains head decoding/choices and the standalone
head-only blocks. The G6-owned thin merge borrow/argument/entry and caller unit
are unchanged; merge's callee implicit unit/return are G4. The six final
sq(c,10..15) stores are G6, with their entire helpers and argument/control edges.
No cap or owner is reassigned to make any bound fit.

`source-inheritance.json` removes exactly the old/new merge, G2 and G5 regions
from the selected C3 source and compares every remaining byte. Thus all other
helpers/callers and outer scopes are exactly unchanged. The selected scoped G2
2494 bound, C3 G1=94/G7=178/SS=188/SF=227/G128=14/F42 route=26 remain scoped to
those exact unchanged source operations. Corrected G6 production512/private514
still covers the identical G6 body/caller operations; this is explicitly
reconciled, not automatic whole-source inheritance. G2 new loans and G5 inner
loans end before their subsequent G6 stores. The final six-call argument
variables have exactly the old types and lexical extents. No new G6 helper body
or caller payload appears. Combined proposed production G1..G7 work is6859
within the prepaid7680; independent selection of the complete proposal remains
pending.

## Whole lexical role inventory

The selected exact C3 lifetime proof is bound via
`C3-lifetime-selection.json`, its frozen producer/independent seals and actual
source. Only byte-identical regions are retained. The old G2, merge and prefix
rows are replaced with selected typed-G2 rows and this new source schedule.
Retaining the full old1201 Control overbound even for unchanged phases is
conservative; it is never spent as spare capacity.

`whole-lifetimes.json` lists every one of1879 named merge value owners. The
source checker maps every actual let declaration, including semicolons in array
types. Each named destination is reserved from declaration through actual
lexical block end, including its initializer. Shadowed initial-head `index`
owners both survive to their block end. No scalar, reference, array or caller
local is retired at last use. The full named merge peak is191 Control bytes.
The complete active caller base is512 bytes: original walk/progress/call sources,
Loan16, semantic StepBudget16, full semantic argument/parameter48+48, w/f16,
eleven outer scalars88, body8, miss cell8 and distinct merge argument/parameter8+8.

Each new API schedule retains this caller, all191 named merge bytes, two extra
complete array64 constructor/designated values128, and its full endpoint union.
The output64 received owner is already in the named191. Actual phases are
smaller; keeping sequential array/view states together strengthens the bound.
Split_at_mut257, as_chunks265, Range/fixed/Option/expect299, Index/LE249,
copy_from_slice242 and primitive50 endpoint unions include full receivers,
arguments, operands, returns and target/source objects. The largest merge
superphase is1130 Control bytes. References alias the one retained Candidate
payload; no second2048-byte object or timestamp/index arena payload is created.
Index arrays are Control metadata and remain within Control; no other role's
space supplies a credit.

The G5 schedule retains all82 prefix bytes, including a deliberately early
reservation for feasible, against the semantic488 plus miss-cell8 base and each
actual API union. Its maximum is843 Control. Inner arena_words/base/i/slot_byte/
slot/bytes owners end at their explicit block; headroom/remaining/mask/
destination/feasible persist through all six G6 stores. That caller plus the
complete selected sq/st424 endpoint union is953 Control. All other C3 phases,
complete early Err488 paths, full constructor/received aggregates and report
slots retain their selected unchanged source schedules. Paid24 remains Wire;
config80 remains Setup. Existing Report fields are contained in the complete
aggregate/Result capacities, not additional payloads.

The proposed whole added peaks are Control1220 (selected typed G2), Wire152,
Setup160 and Report2688. Each fits its unchanged1280/256/256/2896 allowance.
The full inherited24656-byte inventory is kept on every new phase, without
retiring any inherited capacity. Fixed role union29344, reservation41984 and
global ceiling65536 are unchanged; the unassigned margin is unused. This is an
authored-source logical role bound with the selected predecessor caller scope,
not a compiler ABI/machine-stack/libstd/allocator/kernel/RSS measurement and not
an arbitrary-depth application forwarding bound.

## Executable corroboration and boundaries

10,486 separate merge cases cover all masks/rank vectors over {0,1,MAX} through
five active slots plus full64-slot fixed and seeded families. A different stable
key-order oracle checks each result; cursor pointers must finish at exact run
endpoints and never emit256. The bit-reversal all-eligible witness visits
32/48/56/60/62/63 comparisons and64 timestamp loads per pass. 9,256 checked versus
ordinary prefix comparisons check full values and read traces, including pinned
occupied rows, empty masks, early breaks, no destination and complete u64::MAX
totals. These finite checks corroborate the universal source arguments; they
cannot replace them. Fourteen negative controls reject changed source heads/
endpoints/cursor aggregate/subtraction, unstable ties, MAX-as-sentinel, duplicate
eligible prefixes, stale sizes, source drift, lost lexical owners and invalid
work partitions. `authoring-attempts.json` retains the producer's earlier
preliminary correction history; only latest-run.json names the final command.

No public File reachability, new real binding, actual Rust/compiler/VM/native/
device, UI, signing/store/customer/operational, immutable published-package
FieldLog or GA qualification is claimed. No canonical source, old verification
packet, root metadata or Git state is changed. Only this new packet is written.
The two bounded sequential checker children are reaped. No native or capture
process is started and no process inventory is performed. There is no owned
external scratch to clean; other projects' processes/data are untouched. Native
checks remain pending under the current explicit pause.
