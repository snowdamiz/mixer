# R1 terminal/projection correction

This is a separate bounded contract-model proposal. It changes no old sealed
packet, product source, API/report, limit or execution metadata. Independent
review and root selection remain pending. `terminal-contract.json` freezes the
ordered classifier, all32 fields and unchanged ceilings. `expected-cases.json`
contains literal32-word/outerErr expectations authored before `classifier.py`.
`source-normalization-cases.json` separately fixes exact child-result mappings.

Run only the new checks with:

```
python3 -B verification/swift-semantic-adapter-terminal-correction/run_checks.py
```

These execute finite Python **contract-model checks** and source/custody checks.
They do not execute Rust, a semantic analyzer, old models/harnesses or a target.
Actual Rust work/moves/Result/lifetime/layout and API/actual-File/runtime tests
remain pending. No CI qualification follows from this packet.

The input manifest names13 consulted files, their exact snapshots and three
preserved old seals (152+35+21 members). Review/preaccess members resolve against
their declared seal-parent bases; proposal members resolve against repository
root. The initial incorrect path-base preparation failure remains recorded in
`preparation-failure-1.json`. Attempts and raw streams are never overwritten.
`final-receipt.json` identifies the last passing bounded check attempt;
`seal.json` names only this directory and its companion correction document.

Computer use/capture/native runtimes/phones remain paused. No scratch build,
process discovery, old code import/execution, commit or push occurs in this lane.
