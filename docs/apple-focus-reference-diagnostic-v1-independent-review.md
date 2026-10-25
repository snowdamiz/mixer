# Apple reference-first focus diagnostic v1 independent review

The frozen source derivative and generic compiler evidence are coherent. The diagnostic classifier has three findings to repair before using it to accept imported runtime evidence. This review does not select a runtime or authorize dispatch. The independent receipt retains 74 executable controls: 66 passed and eight failed. No producer file was edited.

Reviewed identities:

- Producer handoff: `9f066db167168e8ab0c78b2147f857ba3980d965a69b681e566e5e185f6a0d3c`.
- Preparation: `e71f226c97182e2f8b8b8cd0f2f5e07ffa43e54d540c34189516123e21fb9ed1`.
- Complete 39-source derivative tree: `696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a`.
- Product archive: `0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8`.

## Findings

1. **P2: Complete original verdict replay is not type exact.** In [`reference_contract.py:63`](../verification/apple-focus-reference-diagnostic-v1/reference_contract.py#L63), ordinary Python dictionary equality considers `True == 1` and `False == 0`. Independent controls separately changed `originalOraclePassed`, `pairedFocusDisagreement`, `missingAppFocusUpdateSignal`, `nativeAppFocusedBefore`, and `nativeAppFocusedAfter` from booleans to integers. Every altered verdict still returned `one-original-oracle-result` with `singleTabDiagnosticEvidencePassed: true`. The primary `passed` field and predicate booleans are checked strictly, so these controls do not show that a false original predicate can become true. They do show that the claimed complete, unchanged original verdict can be altered and accepted. Compare a type-preserving canonical serialization or use recursive type-and-value equality after stripping only explicitly permitted reporting metadata. Keep all five mutation controls as rejection tests.

2. **P2: Optional runtime identity fields are not checked as strict integers.** [`reference_contract.py:60`](../verification/apple-focus-reference-diagnostic-v1/reference_contract.py#L60) compares optional verdict `generation` and `actionIndex` using `!=`, then removes them before replay comparison. Independent controls supplied `1.0` for each original integer `1`; both were accepted as successful diagnostic evidence. Require `type(value) is int` and exact current-witness equality before removing these reporting fields. The nested original witness and premise already require strict integer types; this finding concerns inconsistent outer reporting metadata.

3. **P2: A malformed numeric timestamp escapes the result classifier.** Passing the JSON-representable integer `10 ** 1000` as premise AX `uptime` raises `OverflowError: int too large to convert to float` through the unchanged oracle's `math.isfinite` call. The exception boundary at [`reference_contract.py:67`](../verification/apple-focus-reference-diagnostic-v1/reference_contract.py#L67) does not catch it. Reject unreasonable numeric magnitudes before invoking the oracle or translate `OverflowError` to `invalid-or-incomplete-evidence`. This does not create diagnostic success, but it violates the promised structured fail-closed classification and can abort evidence import.

All seven accepted altered-verdict examples and the malformed-timestamp outcome are retained in [counterexamples.json](../verification/apple-focus-reference-diagnostic-v1-independent-review/counterexamples.json). They are explicitly synthetic host data and confer no native evidence. The review did not repair producer code or turn these failed controls into passes.

## Verified boundaries

The reviewer independently hashed every frozen member and input, checked both inherited source manifests and archive membership, and read all 39 original/derived source members plus the 29 selected-runtime archive members as data. Only `source/Prototype/main.swift` and `harness/UITests/ToggleUITests.swift` differ. Reversing the exact preferred-focus substitution, optional parameter, pre-injection guard and new diagnostic method reproduces every original runner/app byte. This also verifies the complete original six test methods and helpers, beyond comparing their declarations.

The authoritative AX sample is taken once before the new guard. A false reference premise throws before either existing public `typeKey` branch. The separately named method launches the unchanged off/enabled case and requests one acquisition Tab. It does not call the acquisition loop or semantic phases. Existing sequential three-target sampling, public key implementation, observation timing and non-authoritative follow-up remain unchanged.

The independent executable controls verify complete false premise → zero injections; true premise with no returned result → unknown injection count; duplicate premise/verdict/application-pair rejection; generation, action, premise/witness, binding, return-status, ordering and time-window rejection; complete application replay; omitted/extra/false predicates; and rejection of invented case-completion fields. The original v2 oracle and its exact nine-file pure dependency closure were loaded only in reviewer-owned temporary storage, which was removed. The full original authored-first verdict replays with exactly `actualNativeFocusTraversal` false. Synthetic one-Tab success cannot complete the original cursor or change any keyboard, carrier, six-case, runtime or GA qualification flag.

The classifier checks internal consistency, not provenance. It has no trusted selected-run identity or freshness argument. A self-consistent triple can be replayed as synthetic contract data. Before interpreting any future imported premise as authoritative, a separately reviewed runtime importer must establish its unique attachment, selected method/run/device/source/product binding and ordering, and reject duplicate or foreign evidence. The present preparation contains no such importer or runnable packet; this is an integration prerequisite, not a claim that replayed data is a native observation.

The independent compiler audit checked all eight recorded command/output bindings, exact Swift source argv for core/UI/app, the generic simulator `build-for-testing` runner argv, unsigned build settings, the pinned version outputs, and current on-disk hashes of all eight recorded tool files. Every recorded compiler exit code is zero and no command timed out. It checked every product byte, mode and link against the complete archive and manifest, and verified that packaging changes only `MinimumOSVersion` from `17.0` to `26.0`. Existing UIKit deprecation, XCTest actor-isolation and platform-framework packaging warnings remain visible in the producer logs. No compiler was rerun.

The owned compile scratch is absent and its cleanup receipt binds 164,590,153 removed file bytes. Owned compiler process-group absence is the retained producer observation; the reviewer did not query current process or native inventory. The producer handoff and every frozen member still match after the review.

## Reproduction and retained evidence

The exact review command is recorded in [receipt.json](../verification/apple-focus-reference-diagnostic-v1-independent-review/receipt.json):

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-diagnostic-v1-independent-review/review.py
```

It exits one because the eight failed controls are retained. The script refuses to overwrite an existing review receipt. [review.stdout.log](../verification/apple-focus-reference-diagnostic-v1-independent-review/review.stdout.log) lists every control and [review.stderr.log](../verification/apple-focus-reference-diagnostic-v1-independent-review/review.stderr.log) is empty. The producer's already-read `freeze.py verify` was executed only for its file verification path and passed. Its exact output is retained separately. The first reviewer harness attempt omitted the legitimate top-level archive directory from its prefix allowance; the checker was corrected, and both initial failure logs remain preserved as `harness-attempt-1.*.log`. That harness error is not a producer finding.

The [independent handoff manifest](../verification/apple-focus-reference-diagnostic-v1-independent-review/handoff.json) freezes the review source, receipts, output, counterexamples and this document. Verification is file-only:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-diagnostic-v1-independent-review/freeze_review.py verify
```

Observed host: Python 3.14.8 on macOS 27.0.1 arm64; the inherited producer revision label is `ba9ad4372f94463ba4d363cdfd76dd565c96413f`. Exact source/archive/tool hashes, rather than that historical label, identify this review. No Git, compiler, simulator/device, UI/capture, hosted authority/catalog, or service operation was performed. Physical phones remain disconnected and deferred. Original `runPassed` remains false; full keyboard, comparator, carrier, FieldLog, signing, store, operational and GA requirements remain open.
