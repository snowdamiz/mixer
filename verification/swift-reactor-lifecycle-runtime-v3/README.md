V3 is prepared for root source/compiler review. Only the selected SL13 test body
changes from sealed V2: ticket deltas +1,+2,+0 and live cache entries0,1,3,3.
The other checks, deadline and consuming retirement remain. Runtime is unrun.

Four pinned compiler contexts, 39 exact Frozen methods, complete ordered raw
position/role proof and owned scratch cleanup passed. The finite maps await
root selection. All original SL coverage gaps and broader qualification remain
pending. Review `candidate.diff`, `receipt.json`, `unchanged-runtime-proof.json`,
the full retained proof/raw attempts, and
`../../docs/swift-reactor-lifecycle-runtime-v3.md`.

```sh
python3 -B verification/swift-reactor-lifecycle-runtime-v3/verify_pre_runtime.py
```

This replay reads evidence only. The 30-command runtime runner is prepared and
requires a new root selection bound to the candidate and `pre-runtime-freeze.json` hash.
