# Apple reference-first focus diagnostic v2 independent review

The classifier consistency repair passes independent review: **137 of 137 controls pass**, with no unresolved finding in this repair scope. The exact earlier 74-control reviewer was replayed against v2, and 63 additional checks cover repair/history bindings, frozen regressions and strict JSON edge cases. The historical v1 review remains failed and immutable. This acceptance is limited to the pure classifier; runtime provenance and packet selection remain separate.

Reviewed v2 handoff: `07776c2af95bcc58e126b4ceb0f0dee39dec1138ea96bc9e33bc8a4a0393a3a0`. The v1 producer handoff remains `9f066db167168e8ab0c78b2147f857ba3980d965a69b681e566e5e185f6a0d3c`, and its failed independent review remains `d70da20d45323be52138a6efdbd2d53c74efbd521620584b228bf9f03e3eedbb`. Every frozen member and tree digest was rehashed before and after the controls.

## Repair and executable evidence

The reviewer read the v2 classifier, test adapter, host runner, freezer and both patches before execution. Both retained patches exactly reproduce the current v1-to-v2 source differences. All original 26 producer tests remain identical except the two declared read-only archive path references. The 34-test producer receipt, owned source hashes and output hashes match its frozen evidence. The read-only v2 `freeze.py verify --attempt 1` path passes.

The [earlier 74-control receipt](../verification/apple-focus-reference-diagnostic-v2-independent-review/earlier-74-controls-receipt.json) records reuse of the unchanged frozen reviewer source. Only its output directory and pure classifier dependency were redirected: every other check retained its original code, oracle, fixture, manifest and source/product inputs. All 74 now pass, including the eight controls that failed in v1. This replay again verifies the exact two-file Swift overlay, complete original source restoration, full original authored-first failure verdict, compiler argv/output/tool bindings, complete product archive, packaging derivation and scratch cleanup. The original failure still has exactly `actualNativeFocusTraversal` false.

The [exact frozen regressions](../verification/apple-focus-reference-diagnostic-v2-independent-review/exact-frozen-regression-outcomes.json) separately replay all seven retained altered-verdict triples from the historical review. Each now returns `invalid-or-incomplete-evidence`, false diagnostic success and unknown injection count. The exact `before.uptime = 10 ** 1000` mutation also returns structured `OverflowError` evidence. This verifies the repairs against frozen inputs rather than newly approximated examples.

The additional [strict JSON outcomes](../verification/apple-focus-reference-diagnostic-v2-independent-review/strict-json-edge-outcomes.json) and [review receipt](../verification/apple-focus-reference-diagnostic-v2-independent-review/receipt.json) cover:

- Recursive value/type agreement; missing and extra object members; list order and length; nested type changes; strict distinctions between booleans, integers and floats; and rejection of non-string object keys, tuples, sets and byte strings.
- Rejection of NaN and both infinities, including nested values. Object key insertion order remains irrelevant to decoded JSON value consistency.
- Structured rejection of huge timestamps and frame values, incorrect outer reporting types, integer predicates, invalid premise identifiers/counts, unequal AX number representations, and deeply nested malformed verdict data. The deep-data case retains a structured `RecursionError` outcome.
- The three diagnostic branches, original oracle strictness, duplicate evidence, witness/binding/time-order checks and immutable app replay remain covered by the earlier 74 controls. Synthetic consistency success cannot change cursor completion, full-case, native keyboard, carrier, `runPassed` or GA flags.

## Consistency and provenance are separate

The repaired function checks the internal consistency of decoded evidence. It neither authenticates a run nor proves that a key was injected into a selected simulator. Self-consistent synthetic data can pass repeatedly; the independent controls verify that this still grants no native or qualification credit.

A separately reviewed runtime importer must establish unique authoritative attachments, selected method/run/device/source/product identity, freshness, ordering and duplicate/foreign evidence rejection before invoking this classifier for native interpretation. Raw JSON parsing and its lexical validation also belong to that importer. The pure comparison is exact about decoded JSON value types and values; it is not a file-byte or attachment-origin verifier. No selected-run importer exists in this repair, and the independent review does not select packet assembly or dispatch.

## Retained compilation and cleanup

The reused preparation remains `e71f226c97182e2f8b8b8cd0f2f5e07ffa43e54d540c34189516123e21fb9ed1`; the exact 39-source tree remains `696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a`. The source archive remains `c1e59b3e950acfe4afa46ae69e8eed29e6c8e1816e1d845e1c40548833201294`. The product archive remains `0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8`, with complete product tree `e3d60e7c69dcbe6e75e7089840b62dd4dd475f4a9db4fe87465543f822b39e20`.

These are retained v1 compiler artifacts, not a v2 compile. The review rechecked their bytes and current tool file hashes without invoking compiler binaries. The compile scratch remains absent; process-group cleanup remains the historical producer observation. Only the nine-file pure oracle dependency closure was materialized for host execution, and every reviewer-owned temporary directory is absent afterward. No native inventory or process query was performed.

The final independent review ran on Python 3.14.8 and macOS 27.0.1 arm64. Its inherited source revision label is `ba9ad4372f94463ba4d363cdfd76dd565c96413f`; exact frozen hashes identify the reviewed tree. [review.stdout.log](../verification/apple-focus-reference-diagnostic-v2-independent-review/review.stdout.log) lists all controls; the final stderr log is empty. An initial reviewer harness assumed frame numbers were floats and stopped at fixture selection; it was corrected to exercise the actual integer-to-float representation change. A second harness output pass preceded a metadata-only correction that removed a replay receipt's self-reference. Both earlier stdout/stderr pairs are preserved as historical harness logs; the final 137-control receipt binds the final executed reviewer source. Neither harness issue was a producer finding.

The exact final command is recorded in the receipt:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-diagnostic-v2-independent-review/review.py
```

The reviewer refuses to overwrite a final receipt. The [independent handoff](../verification/apple-focus-reference-diagnostic-v2-independent-review/handoff.json) freezes all review sources, evidence and this document. Its file-only verification command is:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-diagnostic-v2-independent-review/freeze_review.py verify
```

No producer file, compiler, simulator/device, UI/capture, service, Git or hosted authority/catalog lane was changed or invoked. Native execution remains false and runtime selection remains pending. Original authored-first failure, physical phones, comparator/full keyboard cases, FieldLog release qualification, signing, store, operational and GA requirements remain open. Physical phones remain disconnected and deferred.
