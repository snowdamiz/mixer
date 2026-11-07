# Whole-sort view: source-only G4 obstacle

The exact `explored-merge.txt` is an uncompiled design over frozen correction2
`cache_state.rs` SHA256
`6f128e861478c4c871460115397976b39e6cd3a4807a8825b5b04959e1930a00`.
It forms one mutable eight-byte-word view over the existing Candidate for the
whole sort and uses direct indexed word assignment instead of `copy_within`.
No product source, prior packet or seal is changed.

This exploration stops at a concrete G4 source-model obstacle, as root directed.
Even granting one eight-byte payload copy per assignment, the favorable lower
core contains18 scalar operations per output: ten for the two checked indexes,
two source/destination additions, two chosen-cursor update operations, two
output-cursor update operations and two successful loop-test/branch operations.
Across384 outputs, even pooling scalar blocks globally gives432 scalar groups
plus384 copy groups =816, against the selected768. This excludes side selection,
final loop tests, one-time view construction and other administration.

The primary finer map separates address scaling from address addition:20 core
scalars/output and864 groups across384 outputs. The favorable18 result combines
only those two address operations; it never combines pointer/length components
into one fat-reference scalar. If a compound increment is instead one operation,
the favorable core falls to16, but each output still has at least the left-half
exhaustion predicate, its branch and the chosen-side branch. This sensitivity
also fails the same copy-plus-scalar bound under the disclosed grain.

These are qualified source-model lower/core results, not measured overruns,
compiler instruction counts, a universal impossibility proof or independent
acceptance. The binding passage defines16 named scalar operations per group and
separate bounded copies; it does not completely define an instruction grammar.
`primitive-grain.md` makes the chosen component accounting explicit. Review may
challenge the model, but no convenient whole-reference primitive is silently
introduced to obtain a fit. No group cap changes and no credits move between
G3, G4, G1 or another semantic group.

The G3 comparison inventory has44 named scalars and four separate array-copy
groups, or seven groups in its disclosed conversion-leaf model. That is not a
complete whole-G3 bound: the actual one-time chunk helper/setup work remains
unclosed and is explicitly outside the comparison map. G4 administration is
listed separately and only increases the obstacle. No repair is selected for
implementation. Source accounting, lifetime and runtime qualification remain
false.

`range-order-proof.md` proves the design's intended ranges, load order, MAX
short circuits and stable ties. `local-places-and-lifetimes.md` inventories the
authored fragment's places and the unclosed platform-helper boundary; it is not
a fresh compiler layout or the full29,344-byte role-union proof. The direct
assignment discussion grants the cheaper one-copy interpretation for the
obstacle without using optimizer elision to erase a distinct named local.

Only source-analysis Python runs. It hashes original454, correction1-814,
correction2-570, proposal3-16 and admitted review2-13 members; fetches official
platform source for identity only; and checks finite integer arithmetic. It
does not import/compile/execute Rust, fixtures, models, independent tests/oracles/
glue, native runtimes, UI/capture, hosted surfaces or process inventory. No Git
mutation, build product or scratch directory is created.

Use `python3 -B verify_proposal.py` from this directory for read-only verification.
Run the overwriting source-only reproducer only in a separate copy of a frozen
packet. Root must separately select any further product or design correction.
