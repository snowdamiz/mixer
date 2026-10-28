# Hold synthetic release for one physical-alignment correction

One blocking source finding remains in the frozen verifier. Preserve this packet
and prepare a versioned correction before root releases its single synthetic
host test. No selected module was imported, syntax-parsed, compiled or executed;
none of the sixteen declared tests ran. No actual capture or saved-input parse
occurred.

**R01 — local rebasing is not physical alignment.** At
`source/region_certificate.py:328`, the verifier calculates
`normalized = offset + arena.rebase` and tests `normalized % alignment == 0`.
The arena schema does not supply an alignment/residue for that rebased origin.
Later, same-base relations add signed origin deltas, but those deltas are never
checked against the declared region alignments. Arithmetic rebasing can therefore
erase an alignment contradiction.

A concrete source case uses the existing R/C fixture geometry. Both regions
declare alignment 8. R has offset -13,624 and rebase 13,624; C has offset -13,640
and rebase 13,640. Each local normalized start is zero and passes. Extend R
through the child phase, as existing P10 already does, then replace only the
A_R/A_C disjoint relation with a reviewed same-base relation whose C-base minus
R-base is 1. Their physical start separation is now
`1 - 13640 + 13624 = -15`, an odd value. Both starts cannot be 8-byte aligned.
The same-base graph remains acyclic and the other geometry/coverage relations
remain consistent, so the current source lacks a guard before its numeric local
union. `alignment-witness.json` preserves the exact specification and independent
integer calculation; it is not an observed verifier result.

Tie region alignment to the actual symbolic base plus signed offset, and carry
the resulting alignment congruences through every same-base origin delta.
Refuse contradictory claims. A rebase alone must not establish base alignment;
unsupported/unknown alignment facts must suppress numeric local output. Preserve
checked signed ranges, capacities, end arithmetic and independent semantic
approval. Add P09/P10 adverse subcases for two 8-aligned starts joined by +1 and
-1 deltas, with consistent 0/8 deltas and evidenced negative-SP rebases retained
as positives. Also cover a normalized-zero coordinate that would otherwise
acquire stronger alignment than its physical base supports.

External root approval still gates actual geometry, and all whole-capacity flags
remain false. That limits authority but does not make this internal arithmetic
contradiction valid. An independently reviewed map can contain a numeric mistake;
the verifier's mechanical guards are intended to catch it.

The remaining reviewed structure is sound enough to retain: the external
Invocation digest binds exact certificate/map bytes, all input pins, independent
semantic review/seal and accepted capture/diagnostic custody. Actual mode binds
source146 and the exact four-target frontier. Bounded memory/path reading and
strict records are explicit. Complete R/C/O capacity and narrow phases are
separate from native frames; unresolved local relations suppress numeric unions.
All thirteen backing obligations and transitive/destruction gaps remain missing.
Synthetic provenance cannot be relabelled actual; candidates without actual
approval have no numeric union, and every result remains local-geometry-only
with complete capacity false. Whole-function instruction semantics still require
the planned independent review and root approval.

The host plan is otherwise contained: one exact Python `-B` synthetic invocation,
16 declared methods, fresh root-owned command/tmp, no subprocess/compiler/capture,
44-second test deadline and one 55-second total budget, output/generated bounds,
exact closure, posthash and finite-cutoff evidence. It remains unreleased. The
source review verified the exact 11-member seal, both source hashes and 38 pinned
inputs before/after with equal hashes. No syntax or test success is claimed.

No canonical product/metadata change, commit, push, process query, native/UI/
capture/device action or real physical/capacity result occurred. Actual backing
bounds, prices, root funding/custody, product integration and GA remain pending.
No child or build artifact was created and no cleanup is owed.
