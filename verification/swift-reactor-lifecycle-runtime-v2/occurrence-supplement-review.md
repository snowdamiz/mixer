# Occurrence-complete correction to the frozen position proof

Root found a real proof coverage defect in the original reconciliation:
`(kind,path,promoted,local,location,calleePath)` does not distinguish multiple
constant operands at the same MIR statement. The dictionary kept only its last
record. The frozen 2,636-record proof therefore did **not** cover every raw
selected occurrence, despite its whole-body/type proofs matching. It remains
immutable as historical evidence; this supplement corrects that coverage claim.

`occurrence-complete-positions.json.gz` matches all **2,744** selected raw records
in both old and new queries. Its key includes body, promoted body, kind, exact
statement/local location and occurrence ordinal **within that location**. It
also records each operand's per-body-kind ordinal and exact index in the retained
raw query. Every repeated identical row is retained as its own occurrence.

| Context | Complete raw occurrences | Earlier dictionary | Omitted occurrences | Omitted distinct records |
| --- | ---: | ---: | ---: | ---: |
| Swift Debug | 680 | 671 | 9 | 5 |
| Swift Release | 692 | 647 | 45 | 34 |
| All Debug | 680 | 671 | 9 | 5 |
| All Release | 692 | 647 | 45 | 34 |

There were 108 omitted occurrences: 78 distinct records, 16 repeated occurrences
equal to a retained last record, and 14 additional repetitions of the distinct
omitted records (seven per Release context). All omitted rows were constant
operands. The complete raw set contains 30 duplicate occurrences beyond unique
full rows; none is discarded here. `former-key-collisions.json.gz` preserves each
full collision group and exactly which occurrence the dictionary retained.

Each old/new record pair receives the same finite allocation and hygiene proof
as the original packet, now without key collisions. Full literal/unevaluated
constant values, source spans, local sourceInfo, actual identity and complete
layout match. No additional hygiene mapping, instruction, position, actual type
or full layout difference was found. Full allocation graph/body proofs and the
macro-expansion-chain limitation remain as previously recorded.

The separate 11,760-role proof had retained ordered operand lists; this supplement
also strengthens its join. `occurrence-complete-role-joins.json.gz` explicitly
joins **all 11,760 unit roles** to an exact raw occurrence in both queries and
checks every original constant source value, location, identity and layout.
Every raw local and constant operand has its required four roles. The 498
constant occurrences join 1,992 source/argument/returned/caller role rows.
`occurrence-complete-function-item-role-joins.json.gz` joins all 324 actual FnDef
occurrences to 1,296 original four-role zero-byte function-item audits, preserving
the actual callee definition and full zero-byte layout rather than a pointer.

This is a proof supplement only. No source, numeric accounting, compiler query
or runtime was changed or rerun. The original 276-file freeze remains exact.
Root's independent occurrence-complete review and runtime selection are pending.
