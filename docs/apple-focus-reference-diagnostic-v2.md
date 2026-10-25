# Apple reference-first focus diagnostic v2 classifier repair

This host-only derivative repairs the three classifier findings from the frozen [v1 independent review](apple-focus-reference-diagnostic-v1-independent-review.md). All 34 host controls pass, including the eight regression controls. The original v1 preparation, its historical failed review, the exact 39-source Swift derivative and its compiled products remain immutable. No source overlay or native behavior changes, and no compiler or runtime operation is selected in this repair.

The v1 handoff is `9f066db167168e8ab0c78b2147f857ba3980d965a69b681e566e5e185f6a0d3c`; the independent-review handoff is `d70da20d45323be52138a6efdbd2d53c74efbd521620584b228bf9f03e3eedbb`. The v2 host adapter rehashes every frozen member before loading the inspected, standalone v1 source/archive helper. That helper is used for read-only verification and the retained host controls; no original preparation action is replayed. All temporary extraction and archive-control paths are owned by v2 and removed afterward. Only the unchanged nine-file pure oracle closure is executed; hosted authority, catalog and native orchestration modules are not imported.

## Repair contract

The [classifier diff](../verification/apple-focus-reference-diagnostic-v2/classifier.patch) makes these changes while retaining the original diagnostic outcome schema and oracle:

- Complete replay comparison recursively requires the same JSON value type and value, complete object keys and list order. Booleans, integers and floats are distinct. It also requires the premise's complete before AX sample to match the witness using this comparison. Five verdict mutations from boolean to integer now fail closed instead of passing ordinary Python equality.
- Optional outer reporting `generation` and `actionIndex` must have `type(value) is int` and equal their current witness values before removal. Numerically equal floats cannot be accepted as integer reporting metadata.
- Numeric `OverflowError` is translated into the existing structured `invalid-or-incomplete-evidence` outcome. The exact premise `before.uptime = 10 ** 1000` counterexample cannot escape the classifier. Recursive-comparison depth failure is likewise a structured failure.

The classifier still distinguishes failed reference premise with zero injections, complete one-Tab original strict verdict, and a passing premise without returned evidence with unknown injection count. It preserves complete original verdicts and replays the unchanged oracle; it cannot grant cursor completion, `runPassed`, six-case, carrier, keyboard or GA acceptance. Original fixed IDs, timing, Swift sources, Settings procedure, public key call and observer V2 remain unchanged.

This classifier validates internal consistency only. Self-consistent synthetic data is not selected-run provenance. A separately reviewed runtime importer must establish unique attachment, selected method/run/device/source/product binding, freshness and ordering, and reject foreign or duplicate evidence before any imported premise is treated as authoritative. This repair neither adds that importer nor selects a runnable packet.

## Retained inputs and host evidence

The unchanged derivative source tree remains `696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a`, with v1 preparation SHA-256 `e71f226c97182e2f8b8b8cd0f2f5e07ffa43e54d540c34189516123e21fb9ed1`. The [v1 source archive](../verification/apple-focus-reference-diagnostic-v1/accepted-sources.tar.gz) remains SHA-256 `c1e59b3e950acfe4afa46ae69e8eed29e6c8e1816e1d845e1c40548833201294`. The [v1 product archive](../verification/apple-focus-reference-diagnostic-v1/compile-attempt-1/products.tar.gz) remains SHA-256 `0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8`; its complete product-tree digest remains `e3d60e7c69dcbe6e75e7089840b62dd4dd475f4a9db4fe87465543f822b39e20`. These are reused retained compilation artifacts, not a v2 compiler run.

The [tests diff](../verification/apple-focus-reference-diagnostic-v2/tests.patch) retains all 26 original controls, with only two archive path references redirected to the frozen v1 archive so temporary paths stay in v2. Eight new named regression controls reject the review's seven exact frozen altered-verdict triples plus its exact huge-integer mutation. Synthetic controls confer no native evidence. The original authored-first failure must still replay completely with `actualNativeFocusTraversal` as the sole false predicate.

Run from the repository root:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-diagnostic-v2/verify_host.py --attempt 1
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-diagnostic-v2/freeze.py freeze --attempt 1
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-diagnostic-v2/freeze.py verify --attempt 1
```

Host attempts and the frozen handoff refuse overwrite. [receipt.json](../verification/apple-focus-reference-diagnostic-v2/host-attempt-1/receipt.json) records the exact command, Python version, inherited revision label, source and output hashes, reused source/product identities and cleanup. [regression-outcomes.json](../verification/apple-focus-reference-diagnostic-v2/host-attempt-1/regression-outcomes.json) retains the eight structured rejection results. [handoff.json](../verification/apple-focus-reference-diagnostic-v2/handoff.json) binds the final repair, evidence, documentation and both immutable historical handoffs.

The first host attempt runs on Python 3.14.8 and macOS 27.0.1 arm64, with 34 tests, zero failures, zero errors and zero skips. All seven frozen altered-verdict triples now produce `invalid-or-incomplete-evidence` with diagnostic success false; the huge timestamp produces the same structured status with its `OverflowError` retained as the failure reason. Temporary oracle/archive paths are absent after the tests. Every v1 and independent-review frozen member still matches; the original authored-first verdict still replays completely with the same sole false predicate. No compiler, native instance, UI/capture, service or Git action occurs in v2.

V2 independent review remains pending. Original authored-first failure, physical phones, comparator, full keyboard cases, FieldLog release qualification, signing, store, operational and GA requirements remain open. Physical phones remain disconnected and deferred.
