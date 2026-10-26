# Independent scalar-cursor source/model review

The bounded decision is to accept the exact proposed source for further root
selection under the independent conservative work and logical-lifetime bounds
below. The producer's claimed exact source counts are not selected. Root still
must select this correction; this packet changes no canonical implementation.

The reviewed proposal seal is
`3779a6ee9e8b38c2558e54ea4c8ae2e730ceb163b3ab154e7ee4003ef997475d`;
the full Rust source is
`f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b`.
All 41 packet-relative members, 3,437,955 bytes, and every listed external
source/selection input are verified by hash. The reviewer imports or executes
no producer code. This is a source and primitive-API model review. A lexical
matcher binds the reviewed source; it grants no OTA authority.

## Universal source argument

The independent schema matcher accounts for every production token in the
merge: all 64 distinct literal mask bits, all 32 seed pairs, five scalar cursor
scopes, 320 later output expressions, 26 endpoint resets, 31 initial two-head
blocks, all index/timestamp reads, and the alternating source/destination
regions. Test-only atomics are preserved in the proposal and excluded from the
production model. No optimizer, register, machine-stack, last-use, or
cross-owner credit is used.

The state relation maps each old cursor field to its same-typed scalar and maps
the old indices/timestamps fields to the shared fixed-array references. Its
initial values, literal resets, expressions, branch conditions and selected
assignment destinations are equal. Each source expression therefore preserves
the relation and the exact read sequence. The source is not compiled here;
well-typedness and actual Rust behavior remain subsequent compiler work.

For every eligibility mask and all u64 timestamp assignments, the seed run
contains each eligible physical slot exactly once and 255 for each absent slot.
Its timestamp reads are unconditional and do not define eligibility. A right
255 chooses the left; otherwise a real left with timestamp less than or equal
to the right wins. Equal real timestamps prefer the lower physical slot in
the initial ascending order. Timestamp MAX remains ordinary data.

For a width-w run, lp..le and rp..re are disjoint adjacent input intervals.
Each head is its next input index or 256 exactly when its pointer is exhausted.
An index 255 is an actual absent input value; 256 is never an input value. With
ri>=255 the predicate chooses left exactly when li!=256. Otherwise it chooses
left exactly when li<255 and lt<=rt. It ignores cached timestamps whenever the
corresponding head is absent/exhausted. A stale cached timestamp after a 255
load or reset is thus immaterial. A selected side consumes exactly one input
position and reloads its next byte, or installs 256 at its endpoint. Before the
run's final output both sides cannot be exhausted, because the number of
consumed positions equals the number of prior outputs. No output is 256.

Induction within a run proves a stable permutation, with real values ordered
by timestamp and absent 255 values last. Induction across widths 2,4,8,16,32
proves the final array is the eligible physical slots sorted by
`(timestamp,slot)`, each exactly once, followed by the required count of 255.
This argument quantifies over all 2^64 masks and all 64-tuples of timestamps;
the finite cases below are corroboration. Each later pass reads exactly 64
input indices and at most 64 real timestamps, including its initial heads.
It executes exactly 64 output choices and two exhaustion stores per run. The
fixed input loan ends with its output-constructor block, before the destination
copy. The seed copy and the five alternating copies use the independently
verified actual source ranges, ending in Candidate bytes 512..576.

The G2 region is byte-identical to the exact selected row-probe source. On a
successful scan, every occupied row contributes its strictly positive byte
size to checked total, and the result equals prior_total. Each eligibility bit
means one physical row was occupied and had zero pins. Empty rows contribute
zero. Duplicate nonrequested function identities, arbitrary generations, and
G2-admitted unusual pin relationships do not duplicate physical slots or
invalidate this sum. No stronger per-row pin bijection or identity-uniqueness
assumption is needed. In particular, only the requested function's duplicate
check is assumed, exactly as the source implements it.

Before G5, the exclusive arena loan and immutable configuration are component
preconditions. No source callback or arena write occurs between G2's scan and
G5: plan staging and merge mutate Candidate only, and merge has no arena
argument. G2's arena loans end before G5's loan begins. Consequently a G5 size
read equals its G2 contribution. This is not proof of new public File admission.

Let P be the consumed set of eligible physical slots. Initially
`remaining=sum(bytes[j] for occupied j)` by the checked G2 sum. Maintain
`remaining=sum(bytes[j] for occupied j not in P)`. The next non-255 merge output
is a distinct eligible occupied slot not in P. Its positive size is one term of
that remaining sum, so `remaining>=bytes`; ordinary subtraction cannot
underflow and preserves the invariant. Early headroom/sentinel breaks only
shorten P. The earlier successful `base.checked_add(request)` guard proves
`base+request<=capacity<=MAX`; both left-associated headroom subtractions are
therefore nonnegative, including full-u64 boundary totals.

For malformed states refused before G5, all source bytes and lazy reads are
unchanged. For malformed but G2-admitted states, the proof uses only the actual
checked sum, physical eligibility and arena stability above. It does not assume
a stronger external validity predicate. G5 still tests headroom, reads the
Candidate index, tests 255, then reads resident word2 in that order. The removed
checked reason13 route is unreachable under these component preconditions.
No other refusal or read order is changed.

## Complete conservative source-work upper

The independent event builder names operand source/received places, primitive
operators, results and targets, let continuations, assignments, implicit units,
statement/conditional/block control, API receiver/argument/return boundaries,
complete arrays and complete Options. Every charge instance has one owner and
its group partition is checked exactly once. The21 identified conservative
Option8 duplicate payload charges deliberately charge the same source pointer
transfer twice; no exact-once actual-source-event claim is made. Scalar groups contain at most 16 events;
every payload copy is independent and at most 128 bytes. Index20 plus its
actual index expression/receiver is retained; fat indexing adds its length
field. IndexMut17 is unused in the changed merge/G5 source and remains in the
exact selected G2 proof. Array8 from_le_bytes arguments and Option16 copies in
unchanged G2/checked helpers remain complete.

| Owner | Independent complete conservative upper | Groups / unchanged cap |
| --- | --- | --- |
| G3 | 33,799 scalars + 395 separate copies | 2508 / 2568 |
| G4 | 10,677 scalars + 33 separate copies | 701 / 768 |
| G5 | 7,915 scalars + 66 separate copies | 561 / 640 |

G3 is `168 +64*43 +32*25 +320*68 +320*25 +40 +31*3 +62*3`
scalars. It has 11 setup copies, 64 seed array8 copies, and at most 320 later
array8 copies. Each eligibility-valued if retains selected-arm value transfers,
arm exit and if-to-binding transfer rather than shortcutting the literal to
its final destination. Each choice retains the selected expression, arm and
if value transfers, arm exit, join and named binding. Later heads also retain
the actual timestamp arm's implicit unit and exit before its completed if.
These are real source nodes, unioned conservatively across branches. Each full
eligible head bounds a 255 head; the 25-scalar choice bounds every real-pair,
sentinel, exhausted and short-circuit branch. Source invariants above bound
their invocation counts, including all sparse masks and MAX timestamps.

G4 is `32*14 +5*55 +320*29 +6*49 +2 +6*4 +5*8 +26*12 +2`
scalars, plus 15 complete view Options and 18 complete array64 transfers. The
selected advance-if arm retains its implicit unit and block exit in addition
to the if unit/continuation. The original G4 second initializer and all five
complete source-view chains remain G4. Each view retains the selected grammar's
complete8-byte niche Option scalar pointer transfers: constructor to designated
return, designated return to caller received, and caller source to expect's
received self. The reviewer additionally charges one complete8-byte copy for
each such pointer transfer, explicitly as a conservative duplicate charge.
Both G3 setup fixed views receive the same treatment. The21 duplicate charges
are labeled by the already present pointer event in the ledger; they are not
newly discovered mandatory source copies. Both static message descriptor source
fields and both expect received fields are explicit scalar events. This
conservative decomposition replaces the producer's exact totals; it changes
neither the selected niche grammar nor an event's owner.

G5 is `80 +64*122 +27` scalars and `2 +64` copies. A full iteration includes
while/header controls, headroom short circuit, index-expression operands,
Candidate Index20, sentinel, casts, full arena Index21 and composite expression,
complete LE array8 argument, subtraction, mask, destination, increment and
loop-body unit/back edge. The terminal union retains the final false test and
both break routes even though they cannot all execute together. There are at
most 64 entered bodies; an iteration that breaks is shorter than a full body.
Final feasible is covered. The six following sq(c,10..15) calls remain G6.

Independent templates and every expanded owned charge instance are in
components.json and complete-upper-ledger.json.gz. Independent grouping is by owner only;
G2 slack, partial necessary traces, separate witness traces, a different cap,
or other ledger labels supply no credit.

## Whole changed lexical inventory and bounded inheritance

The independent positioned tokenizer maps all 1879 merge named owners and
agrees with the actual declaration/scope endpoints. Their peak is 191 Control
bytes, including the named output64, thin shared array references8 and the
actual scalar widths. Both shadowed initial-head index locals survive to their
common lexical block end. All six fixed-array reference declarations with
array-type semicolons and all ordinary bracket/brace scopes are parsed. No named value
retires at its last use. The G2 mapping has 45 named owners, resident peak336;
its exact selected complete lifetime schedules remain Control1220. G5 maps all
11 names; their deliberately early simultaneous union is82. Its inner arena
and loop locals end before G6's stores; headroom, remaining, mask, destination
and feasible remain live through those stores.

The merge caller is512 bytes: retained Progress144, cache_inputs source and
received24+24, walk source/received16+16, fixture source/received8+8, outer arena
reference8, Loan16, StepBudget16, semantic source/received48+48, w/f16, eleven
outer scalars88, body8, miss cell8, merge argument and parameter8+8. Candidate
is the one already inherited2048-byte object; its reference descriptors and
contained timestamp/index regions create no second payload object.

Every new merge schedule retains that entire512 caller, all191 named merge
bytes, both extra complete constructor/designated array64 values128, and a
complete primitive API endpoint union. Split_at_mut257, as_chunks265,
Range/fixed/expect299, Index/LE249, copy_from_slice242 and primitive50 retain
actual source, received and designated values. Source16+received16 receiver
inventory covers the distinct reborrow8 plus fat receiver16; thin fixed-array
borrow endpoints remain8 each. complete Options retain full capacity on every
arm, without active-variant narrowing.

The reviewer additionally retains120 explicitly named bytes from the actual
nested `ld(c,640)` chain: b16/at8 source arguments and b16/at8 received
parameters48; at+8 left/right source, received and result40; full expect Option8
source/received16; fixed-reference dereference source/received addresses16.
These values are source/call objects, not a generic spare allowance. They are
conservatively retained on every merge endpoint even when sequential or already
bounded by other active endpoints. The resulting merge Control upper is1250.
G5 additionally retains its complete RESIDENT Region24 source with every
endpoint; its maximum is867. G6's six-store reconciliation remains953. Each
fits its fixed Control1280 allowance.

Exact C3 source
`0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8`
is compared after removing exactly the changed merge/G2/G5 regions. Every
remaining byte matches, including all helpers, outer callers, six final sq
calls, argument types, success/failure exits, setup/finish and public return
construction. This establishes bounded inheritance of only those spans:

- Exact selected G2 remains2494 groups and Control1220. Its three fixed views
  already have the niche Option8 designated-return correction, caller-received
  pointer and expect-self pointer events, and all four static-message
  source/received scalar fields. Its `view.first_chunk_expect` lifetime row
  already retains Option constructor/designated/received8 each, expect self
  source/received8 each and message source/received16 each. No missing G2
  event is inherited and no mandatory copy convention is introduced. The new
  review's extra duplicate payload charges strengthen only its new merge
  upper. The Control1250 whole peak is the conservative new merge forwarding
  schedule, not an increase to G2's1220 bound.
- G1=94, G7=178, SS=188, SF=227, G128=14, pre-SF=26 remain the exact unchanged
  operations selected by C3-remaining-work-selection.json.
- The G6 body/caller, six final calls, types and their lexical scopes remain
  exact. All new head/view/scope work is explicitly G3/G4 and new prefix work
  G5. G6 therefore retains its selected512 production/514 private-fault groups;
  this is a source-span reconciliation rather than automatic whole-file reuse.
  Its ld template explicitly retains complete niche pointer source/received,
  expect self and all message descriptor fields. The remaining-work ld
  template has the same existing endpoint inventory. Exact operation labels
  and G2 lifetime rows are bound in inherited-niche-reconciliation.json. These
  selected proofs already cover the scalar-niche convention; optional duplicate
  charges in the new review do not change that convention globally.
- The exact root C3 lifetime selection, including all18 independent corrective
  schedules, is retained for unchanged spans. The original producer inventory's
  `whole_union_proved:false` is not reinterpreted as an acceptance.
- Early error return uses complete public Result488 source and received
  capacities, not active Err32. All five inherited232 plus added256 aggregate
  slots remain full488. SemanticReply24 source/designated/received,
  complete Option16 source/designated/received, Report aggregates, Setup80 and
  Paid24 keep their selected capacities. Contained fields add no duplicate
  payload. Complete Candidate2048 remains inherited independently of its loan.

The corrected added peaks are Control1250, Wire152, Setup160, Report2688. Their
unchanged allowances are1280/256/256/2896. Retaining the entire inherited24656
on every new phase plus those allowances gives the same fixed29344 union;
reservation41984 and ceiling65536 are unchanged, and no global margin is used.
This proves an authored-source logical role inventory within the selected
caller boundary. It does not assert machine-stack/ABI/library/allocator/RSS or
arbitrary-depth forwarding bounds. Production G1..G7 independent work totals
7048 within prepaid7680; semantic7680 plus old471 remains8151 within8192.
The full570-member candidate and predecessor closure are not replayed. This
review binds the exact allowed cache_state source, selected root decisions and
the specific inherited template/lifetime rows it uses; it does not expand that
scope into a new review of frozen hosted tools or a new public integration.

## Executable corroboration, failures and limits

Separate reviewer models check10486 stable merges and9256 checked-versus-
ordinary prefix value/read comparisons in normal Python and `-O`. Fourteen
controls cover source sentinel/swaps, MAX data, stable ties, duplicate/stale
prefixes,17-scalar groups,129-byte copies, omitted/cross-owner events, last-use
retirement, Err narrowing, fat-receiver narrowing and missing C3 supplements.
They do not substitute for the universal arguments above.

The first reviewer run used an ineffective duplicate-victim negative fixture:
after its first victim, remaining reached headroom and the source correctly
broke before the duplicate. Both failed outputs and the exact checker version
are preserved under commands/. The corrected fixture retains an additional
occupied pinned row so the second duplicate is reached and rejected. The
Python raw-string spelling warning was also corrected. No producer source or
packet was repaired or changed.

Only this reviewer directory is written. No canonical runtime, root metadata,
Git state, dependency, production deployment, credentials or external message
is changed. Both sequential Python children are reaped; no native/capture
process, process inventory or external scratch is started. Other projects'
processes and data are untouched. Compiler implementation checks, Rust actual
execution, public File reachability, phones, simulator/emulator runtime, native
UI, signing/store/customer/operational qualification, immutable published-package
FieldLog and all GA acceptance remain pending or unproved. Native runtime and
capture work remain paused by the user.
