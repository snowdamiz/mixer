# Source-only fixture cache-state proposal

Only the accompanying proposal and this directory are owned. Nothing here
implements or selects the product analyzer. The input snapshotter and verifier
are newly authored finite source/custody/arithmetic tools; they never import or
execute copied code, historical models/harnesses, Rust, the engine or a target.

The immutable input manifest identifies exact consulted source bytes and the
shared-checkout context revision. The source-seam inventory freezes successful
source spans independently of current live VM state. `contract.json` and
`test-design.json` are proposed interfaces/bounds and **future** executable test
expectations; they are not actual semantic tests or measurements.

Run the owned source checks with:

```
python3 -B verification/swift-semantic-adapter-prerequisite/verify_proposal.py
```

`commands/` retains exact invocations, tool identity, stdout/stderr and result
receipts. `seal.json` names only this proposal's owned members and the companion
document. It excludes the seal pair itself. Source input snapshots and all
historical packets remain evidence; no old classification changes.

Computer use/capture/native runtimes/phones remain paused. No process discovery,
scratch build, product execution, commit or push was performed by this lane.
Root owns contract acceptance, implementation selection, delivery and CI audit.
