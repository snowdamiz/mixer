# Selected absent-state correction: host implementation evidence

Fresh isolated host qualification passes for the exact root-selected envelope source2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef and unchanged parent1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b. This is producer evidence pending root's independent behavior review and final acceptance. No product, replay, release or GA gate is promoted.

The immutable35-member proposal seal remains3da07ea9c308c9bee798cf7c891a8f9dfd2a170e85b43341c30caa38cdb9b04c. Independent accounting sealc9191a26ed0c5081e9c2ad97082fc61cee3f6eeb94ea49c4be5028b0f54536e4 supports121 rows,108 unchanged copy edges and the selected amounts. Root selectionae90b289519d0588a27cae4db0a7ce4a74ce3016c9c2f790fd962775ec4fd2e0 explicitly selects G112 ownership for one terminal absent/invalid-entry-spent/present-underfunded path bounded7/7/112. Main-paid W24 owns caller handling independently of private debit0. Every successful main B471 retains public425; the public formula remains534*S_paid+47*F_paid+425*N_B.

The authoritative evidence is [final-receipt.json](/Users/andreyyurlov/Documents/dev/mixer/verification/swift-envelope-absent-state-correction/implementation/final-receipt.json) and [source-test-model-binding.json](/Users/andreyyurlov/Documents/dev/mixer/verification/swift-envelope-absent-state-correction/implementation/source-test-model-binding.json).

## Results and first failure

Run-1 freshly executes all70 unchanged method bodies:44 framing and26 envelope, all passed, none ignored. The same run makes21,714 new-source comparisons against directly referenced immutable selected425 oracle inputs (16,170 complete and5,544 threshold cases). The Python model is not reevaluated. All32 actual complete layouts match the fixed declarations; public128, reply128, Progress144, aggregate/Result232 and complete unit Result40 remain unchanged.

The first focused run passes7/8 and retains one failure. Its new test expected replay_spent1884 after four B471 charges, omitting that the actual Budget::setup(534) also invokes replay(534); actual2418 is correct. The exact one-line new-test expectation becomes534+4*471. Both test snapshots, the failing stdout/stderr and the source-backed analysis remain in run-1 and failure-analysis-run-1.json. No selected source, fixture, expected semantic reply, contract or production debit changed.

Run-2 recompiles the identical selected source with the corrected new assertion, freshly passes all8 focused methods and one positive plus8 expected-negative public API compiles. The unchanged70 results are directly verified from run-1, rather than replayed for this isolated new-test expectation fix. There is no claim that run-1 was entirely green.

| Focused control | Executed cases |
| --- | ---: |
| Length0/32/7,731,055 across credits0/1/424/425/426; poison0 and no budget/arena/candidate mutation | 15 |
| All credits0..424, first/later prior states, lengths7,731,056 and8,388,608; actual Steps0 projection before malformed record | 1,700 |
| Normal funded425 exact reply and whole arena/candidate mutation canaries | 2 |
| Nonzero entry spent across absent/readable lengths; private no mutation and caller rejection | 125 |
| Finite caller poststate debit matrix including reserved/extent canaries | 18,144 |
| Actual guard result installation/validator/latch seams;24 successful B events,6 actual leaves,24 finalizer branches | 6 |
| Incoherent zero replies and paid mixed-poison marker terminal handling | 12 |
| Actual framing counter: decode/coordinate failure and latched skip retain paid425 | 3 |

The caller predicate is a poststate debit check for the selected private helper reply forms. It has no historical before-budget input and does not validate arbitrary state shape or give fabricated paid replies authority. The existing paid425/remaining0/spent425 predicate is preserved. Coherent zero poison accepts any remaining, while zero Steps requires remaining below425; inconsistent debit forms become terminal poison. Existing poison priority, state checks, private constructors and false acceptance flags remain fixed. The disclosed fabricated paid status1/nonzero nonpoison reason scheduling limit remains outside this qualification.

## Source, command and cleanup custody

Rust1.99.0 (aarch64-apple-darwin, LLVM23.1.1), Python3.14.8 and Apple Git2.54.0 are recorded with exact paths, hashes and version output. Both product source copies and the compiled test envelope are exact selected bytes. The test framing shim is the exact parent prefix plus an include of the unchanged private-IO test module. Owned wrappers directly include the six immutable original fixture sources and add the focused child module. Forty-four immutable fixture/model/historical inputs are hashed before and after each attempt; raw upstream archives are not duplicated. Actual source/input manifests, exact argv, dedicated owned process groups, deadlines and file-backed stdout/stderr are retained.

All27 qualification child commands returned and were reaped. The separate bounded offline finalizer has its own receipt. There were no timeouts; the eight expected API compiler rejections are successful negative controls. Owned binaries are hashed then removed, temporary oracle links and scratch are removed after child completion, and reports/first-failure files are retained as described in [cleanup.json](/Users/andreyyurlov/Documents/dev/mixer/verification/swift-envelope-absent-state-correction/implementation/cleanup.json). No unowned process or data was changed.

Historical R2 remains a confirmed failure of the old source. Original producer, review and proposal packets remain byte-identical; this new implementation evidence does not rewrite them. No frozen collector, forbidden hosted inspector or broad harness was imported/executed. No engine/CLI/CI/root metadata was edited and no commit/push was made. Native/UI/capture/process discovery and physical-device runs remain paused, phones remain disconnected, and no Swift/native device, signing, store, FieldLog or GA receipt is claimed.
