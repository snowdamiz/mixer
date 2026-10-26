# Scalar-local cursor source proposal

This isolated source/model packet proposes removing actual FixedArrayMergeCursor
field projections, retaining the existing shared fixed-array references and
using eight scalar cursor/head locals in each later pass. The source SHA-256 is
`f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b`.
The full source, minimal diff and exact unchanged prefix/suffix bindings are
included. The ordinary G5 subtraction and its conditional universal safety
argument are preserved.

Proposed complete conservative source bounds are G3 **2365<=2568**, G4
**655<=768** and G5 **561<=640**. Each copy remains separate; each scalar group
has at most16 edges. Owners and caps are unchanged. The selected G2 bound and
byte-identical C3 helper/caller regions are explicitly reconciled. Proposed
whole added peaks Control1220/Wire152/Setup160/Report2688 fit their fixed roles;
full role union remains29344 with no unassigned-margin credit.

Normal Python and Python -O pass10,486 merge-oracle cases,9,256 prefix read/value
comparisons and14 rejection controls. `latest-run.json` names exact commands,
tool identity, checker/source/input digests, stdout/stderr and child cleanup.
The source argument, component equations and lexical schedules are in
`source-proof.md`, `components.json`, `upper-bounds.json`,
`complete-upper-ledger.json.gz` and `whole-lifetimes.json`. The latter retains all
1879 named merge owners to their actual lexical scope ends, not last use.
Earlier authoring corrections are retained separately and are not final claims.

These are producer proposal bounds, requiring fresh independent review and root
selection. No product implementation, compiler, target, public File, native,
device, OTA, FieldLog release or GA acceptance follows. Canonical/root/old packet
and Git edits are absent. No UI/capture/native/simulator/emulator/phone/process
inventory or hosted/credential/publication action occurred. Only this packet
was written; two sequential bounded Python children are reaped, with no owned
external products. Native checks remain pending under the explicit pause.

To reproduce finite checks use `python3 -B .../check.py` and
`python3 -O -B .../check.py`; these deterministically reproduce owned evidence.
Do not regenerate run receipts over a frozen packet. `freeze.py --verify`
verifies custody without changing any member.
