# Unselected G3 macro amendment using unwrap

This source-only proposal preserves the exact24-copy correction2 target and the
first8-member proposal. It incorporates the frozen13-member G3 review
SHA4773adbb72299087ba2c7ee1f060186e373d1091b8d8eeac07b059099584e6c6.
No proposed source is implemented, compiled or executed.

The amendment keeps the comparator-local expression macro but writes
`let at: usize = $offset` and uses `.unwrap()` in place of `.expect(message)`.
Every offset is evaluated once. All four checked8-byte reads, LE conversions,
a/b load order, bMAX then aMAX guards, TA then TB order and stable <= result are
preserved. No global ld definition or other caller changes. There is no new
runtime function, closure, callback, public/private API or guard.

The explicit value-flow table adds both A/B initializer→identifier binding
edges. It also accounts for each old explicit static str16 argument and removes
it only in the proposed unwrap syntax. Under the same favorable, qualified
primitive grammar, the proposed core is64 scalar operations plus four distinct
8-byte array movements. Four source-order scalar blocks contain16 operations
each; S1 includes A/binding and B's first offset operation, S2 continues B and its
guard, S3 contains a's guard and TA, and S4 contains TB and the final result.
No operation is assigned twice, no fixed copy is a scalar group, and no credit
comes from G4 or another semantic group. Short paths use33/35 scalars and two
array copies; actual tail paths remain G4.

This is a proposed partition requiring root/independent admission, with no
headroom for any omitted scalar. Range16/index-argument and captured shared-c
Index/range-view source/received edges remain explicit favorable primitives;
the binding contract does not define that atomization. If another required
receiver/coercion/return transfer is separate, it must be added and the64 bound
fails. We do not repair it by compressing an unnamed edge. The old76 scalar
table adds the newly explicit binding/message edges under this same proposal's
grammar; earlier70 figures are lower cores, not complete upper bounds.

The macro captures c by lexical hygiene, not a runtime capture object. The shared
Index receiver/reborrow is named in the view operation and typed place table.
Offset sources and `at` are usize8. A/B initializer sources and bindings, TA's
operand while TB evaluates, Range/view/Option/reference/array sources and
received places are explicit. Local conservative typed occupancy is merge120
and helper144, within the existing144/192 producer subroles, but this does not
prove the full29344 product union or other helper/Option/wire lifetimes.

On the admitted path, successful `at..at+8` indexing yields exactly8 bytes,
therefore first_chunk::<8> is Some. Both old expect and proposed unwrap check
that tag. Bounds panic behavior remains, and an impossible-short-chunk None
would still panic; its panic text changes from the explicit user message to
standard unwrap text. That difference is disclosed and needs root selection.
No panic-only formatting or internal message argument is credited as a normal
path saving: only the old unconditional explicit caller message transfer is
removed. There is no claim about standard panic wording or target execution.

`operation-partition.json`, `value-lifetime-and-panic.json` and
`local-place-map.json` are reproducible from the provided builder. Current
product source remains6f128e861478c4c871460115397976b39e6cd3a4807a8825b5b04959e1930a00.
G1/G2/G4/G5/G6/G7, ADMIN, st/sq and full caller/resource proof remain independent
open obligations. Root must select a new correction3 before implementation and
fresh API/layout/behavior controls. Native/UI/capture/process inventory stays
paused.
