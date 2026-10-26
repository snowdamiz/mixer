# Operation-cost definition and limits

This is a source-derived proof proposal, not a runtime measurement and not an
independently accepted replacement for the selected contract. The binding work
unit is in `docs/swift-semantic-adapter-prerequisite.md`244–265: every
micro-operation, loop guard, fixed copy, LE conversion, full Result and caller
move must map once; a scalar block has at most16 named operations and one copy
unit has one fixed copy of at most128 bytes. The same passage fixes G6 at640 and
forbids borrowing another group's spare credit. The source hash and excerpt
ranges are bound in `input-bindings.json` and `proofs/source-seams.json`.

The following explicit atomization is deliberately favorable to the old claim:

- One scalar arithmetic expression is one operation; a constant is not a load.
- An indexed array access has an index-bound check, indexed element address and
  element read. These are three distinct operations. For `CELLS[i]` none is a
  copy of the restored eight payload bytes.
- Constructing an entire `Range<usize>` is charged only one scalar operation,
  even though its complete16-byte source/received movements may require more.
- A range access has two separate predicates, `start<=end` and `end<=len`.
  The exact same checked slice persists, but proving these predicates true is
  not permission to omit their actual source work through optimizer elision.
- Creating a full shared/exclusive view/borrow is charged only one operation.
  Its complete fat-reference transfer is not expanded in the18-operation core.
- A `copy_from_slice` has a source/destination length guard. Its payload movement
  is one separate fixed-copy group. The length guard is not that payload copy.
- The18-operation core omits all loop, binding, argument, return/received-unit,
  constant-region-read and complete-Range-movement costs. These omissions only
  lower its cost; they are not a proposal that such work is free in a full proof.

The scalar-block/site rule used for the645 derivation is explicit: each
helper-call or loop-iteration scalar site requires its own integral number of
blocks. Fixed-copy/helper/iteration boundaries do not transport partially filled
scalar-block capacity to another site. This matches the selected ledger's
per-comparison8/per-transfer2/per-prefix10/per-clear-and-restore-iteration source
partition. It is a qualification requiring independent review; this supplement
does not claim645 under an alternative globally pooled scalar-operation model.
The fixed-copy rule likewise counts the actual distinct source copy operations,
not their aggregate byte count as one fictitious128-byte copy.

For the non-restore rows, the lower bound uses only the necessary two LE-array
movements and a nonempty scalar site for each `st`/`sq`, or one direct copy and a
nonempty scalar site for each direct-copy/clear iteration. It does not assert
that those scalar sites fit one block. Any additional block raises the result.
No initial-prior staging, semantic guard/probe, sort/prefix, reply, projection,
or lifetime cost is silently assigned to the zero administrative allowance.
Those costs remain in their own selected group or explicitly open here.

With this model,18 scalar operations require at least two scalar groups. A
restore has one distinct8-byte payload copy, hence at least3 groups. Twelve
iterations therefore need at least36, before any omitted loop/transfer work.
This is sufficient to refute the specific24-group restore proof under the
stated model. It is not evidence of a wall-clock, native, stack/RSS or actual
runtime step-counter overrun.
