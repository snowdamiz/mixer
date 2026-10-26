# Exact row-probe source: G5 necessary obstruction

The exact proposed source `a43397ec7cbbec398502acae5911394fced7ed8d220fee096589940eafb49fb1`
cannot satisfy the unchanged G5 cap640 under the selected authored-source
grammar. A concrete64-victim path has a necessary subtrace of **7,199 scalar
operations plus192 distinct complete payload copies**:

`ceil(7199/16) + 192 = 450 + 192 = 642 > 640`.

This is a lower bound, at least2groups over cap, with positive source work
deliberately omitted. It is not a complete G5 upper, a measured runtime cost,
or an implementation/GA acceptance. G3/G4 complete uppers and the changed
whole-source lifetime union were not built after this decisive obstruction.
The selected corrected G2=2494 and scoped Control1220 remain separate.

## Actual source and path

`source-g5.rs.txt` is exact proposed-source lines14789..14815. The witness has
64occupied/unpinned rows, distinct functions0..63, each byte size1, timestamp0,
and zero reserved words; its configured pin is empty. Prior count/bytes are
64/64, prior pins0 and next nonce65. The requested defined function64 has a
matching compiled plan. Fixture base0, capacity64, entry64 and requested64
satisfy the actual miss-plan guards and give headroom0. G2 computes total64,
first_empty=ABSENT and all64eligibility bits.

The separately transcribed merge model follows the actual seeded width1
pass to Candidate B1024, then widths2/4/8/16/32 to A512/B1024/A512/B1024/A512.
Stable left preference on equal timestamps yields indices0..63. The reference
tuple sort is checked independently. Every prefix iteration starts with
remaining64..1, so the first `remaining<=headroom` operand is false, the
destination RHS is unexecuted, the slot is not255, and checked subtraction
returns Some. Each source row size is1; after64iterations, remaining0,
maskMAX, destination63 and feasible=true. The final while test is false.

`witness.json` is a source-level state and `witness-path.json` retains every
prefix step. The checker validates the actual semantic prepay/config checks,
all G2 row/pin/post predicates, requested-function definition and miss plan/
request predicates needed to reach this scope. It does not execute Rust,
the public File caller, or the full envelope FSM, and does not claim a proven
public-File reachability receipt. The external caller's loan remains an
explicit precondition of this authored-source witness.

## Necessary source accounting

Every scalar source, received operand, result and target below is named in
the expanded ledger. Fixed array Index20 is paid with its actual index
expression. The `arena_words` receiver is a fat slice and pays Index21,
including its received length. Width8 scaling remains explicit. The array8
argument and both full Option16 transfers are separate copies.

| Executed source component, each iteration | Scalars | Copies |
| --- | ---: | ---: |
| `while i < 64` true condition | 6 | 0 |
| Prefix break condition, short-circuited false | 7 | 0 |
| `c[512+i]` source expression and fixed Index20 | 24 | 0 |
| Non-sentinel `slot_byte == MAX` condition | 6 | 0 |
| Slot zero extension to u64 | 3 | 0 |
| Actual arena offset, fat Index21 and LE decode | 38 | 1x8 |
| Successful checked subtraction and Some pattern | 13 | 2x16 |
| `remaining = next` | 1 | 0 |
| `mask |= 1 << slot` | 7 | 0 |
| `destination = slot` | 1 | 0 |
| `i += 1` | 4 | 0 |
| While body unit and back control | 2 | 0 |
| Each of64iterations | **112** | **3** |

The headroom expression additionally has31scalars: both actual fixture field
projections, two subtractions, and `w[13]`'s literal/fixed Index20. Thus
`64*112+31=7199`scalars and `64*(array8+Option16+Option16)=192`copies.

The checked Option constructor-to-designated-return16 and designated-return-
to-caller16 are distinct complete payload transfers, as required by corrected
G2's selected Option rule. Neither is reduced to an active tag/payload, a
scalar, an optimizer-elided temporary, or an8-byte copy. No copy is pooled.
The ledger packs each scalar at most16/group and every copy alone, at most128B.
There is no cross-group capacity or unused-G2 credit.

Positive omissions include all three remaining/mask/destination initializers,
the complete `as_chunks` receiver/tuple/return/pattern boundary, its width
checks and quotient/remainder, the full Region24 source and base division,
the i initializer, final false while test, named scope entries/exits, both
if-unit/continuation joins, the successful let-else continuation, final loop
unit/continuation and the complete final feasible expression. These can only
increase G5's complete source cost. No refusal-path reply cost is needed.

G5 ends after `feasible`. The six final `sq(c,10..15)` calls remain G6 under
root's explicit ownership clarification. Their complete text is retained in
`source-G6-six-calls.rs.txt` and checked byte-identical to selected exactC3.
That equality does not inherit G6's complete upper or caller/lifetime approval
for the changed whole source. G6's call to merge and its argument/return
boundaries also remain G6; no G3/G4 operation is charged in this G5 witness.

## Reproduction and packet scope

From repository root:

```
python3 -B verification/swift-cache-state-row-probe-remaining-accounting/run.py
python3 -B verification/swift-cache-state-row-probe-remaining-accounting/freeze.py
python3 -B verification/swift-cache-state-row-probe-remaining-accounting/freeze.py --verify
```

Normal and optimized Python3.14.8 checks pass. Nine negative controls reject
a17-scalar group,129Bcopy, narrowed Option16, omitted designated Option16
transfer, duplicate event, omitted fat-slice received length, changed exact
source, invalid aggregate state and changed-headroom witness. Explicit `need`
checks remain active under `-O`. No producer Python is imported or executed.
Source SHA and exact manual-audit scope, rather than syntax matching alone,
bind the authored semantics. Official safe API behavior is modeled at source
level; standard-library internals, machine stack and compiler ABI are outside
this proof.

Only this new verification directory was written. No product source, root
metadata, old packet, Git, frozen hosted catalog/authority/rejected WorkerV2,
broad harness, compiler, Rust execution, native instance, UI, capture, phone,
process inventory, publication, credential or customer action was performed.
No runtime/capture instance was started or needed cleanup; other projects'
processes and data were preserved. Native checks remain paused and pending.
`next-design-direction.json` is an explicitly unselected proposal direction,
with no source change and no proof/acceptance borrowed by this obstruction.
