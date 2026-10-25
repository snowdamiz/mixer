# Private lifecycle test checkpoint

Root accepted and integrated the exact three-file test delta: `lifecycle_tests.rs`,
`cache_tests.rs`, and `memory_growth_operations_tests.rs`. All production files
remain byte-identical. The complete 132-file live source closure is
`64a3d9c52ade75ec16de10191f14257fb75ff358c366666cf47809e2b9a7f0de`.

All 49 identities pass in Swift-only and all-feature Debug/Release (196 producer
executions), retaining all prior 23 identities with none ignored. Six separate
compiler-negative fixtures pass their exact diagnostic checks. Independent review
passes a fresh 49-test replay plus two controls covering eight growth/exit variants.
Root verifies 393 producer and 55 review files, then passes a fresh 49-test live
Swift Debug run. Its owned target is removed after an empty holder check.

The additions cover ownership, failed initialization, retained cleanup, growth,
cooperative interruption, cumulative budgets, WASI state and allocation refusal.
This accepts only the selected host test subset. Every SL01-SL23 row remains
partial; guest table mutation is unsupported, and SL24/full-reactor execution
remains unselected. There is no new production accounting, native, public entry,
FieldLog, signing/store, operational or GA acceptance. Failed producer attempts
and the limitation that their old binaries were not archived remain explicit.

See `verification/swift-reactor-lifecycle-remaining-root-review/acceptance.json`
and `live-receipt.json`. The independent verifier supports either the original
baseline or exact integration:

```sh
python3 -B verification/swift-reactor-lifecycle-remaining-review/verify.py
```

The producer's historical verifier intentionally requires the original live
baseline; it will report drift after this integration. Its sealed evidence has
not been edited to hide that change.
