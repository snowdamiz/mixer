# Independent Swift bulk-memory review evidence

`receipt.json` records the decision and fresh/reused evidence boundary.
`source-diff.json` names the exact nine changed source paths.
`commands/` retains argv, environment, revision/source manifests, tool versions,
stdout/stderr and executable hashes. Logs may be gzip-compressed without changing
the receipt's hash of their uncompressed bytes.

`matrix-results.json` is the fresh sealed-source 16-test/four-configuration matrix.
`adversarial-tests.rs`, the archived instrumented sources and
`adversarial-results.json` preserve independent byte-oracle, pinned-caller and
chunk-cancellation executions. `fresh-mir-*.mir.gz` and
`canonical-results.json` preserve fresh compiler inventories and exact old-label
deltas. `identity-results.json` preserves fresh Frozen expansion and source-owner
identity. `layout-results.json` and two layout source archives preserve four
fresh typed probes. `accounting-results.json` replays all 16 producer raw layout
outputs and complete additive bounds. `historical-failures.json` and saved script
versions retain seven excluded review harness failures. `cleanup.json` records
owned scratch removal; no native/device tools were used.

Run `python3 -B verification/swift-bulk-memory-review/verify.py` for read-only
replay. It does not compile, extract sources, mutate the VM or require the live
checkout to remain the baseline after root integration.
