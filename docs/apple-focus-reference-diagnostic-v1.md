# Apple reference-first focus diagnostic v1

This is a separately named, one-Tab diagnostic derived from the retained authored-first failure. Its source overlay passes 26 executable host controls, and the pinned generic simulator compiler builds both the app and XCTest runner. Native execution and a runnable packet are unselected; the preparation is frozen for root review. The original failure remains unchanged and does not gain acceptance credit.

The frozen input packet is `d7c4c0f146434eeb7323036809acb5b4a80d41ff10f596eed8c25bdaa314e783`. Its retired scratch is not restored and its preparation command is not replayed. The derivative reads the retained 39-source accepted archive and 29-file selected-runtime archive as immutable data. It imports only the nine-file pure oracle dependency closure for host replay, in a temporary directory removed afterward. No hosted authority, catalog inspector, native orchestration, service, simulator inventory, UI, capture or physical-phone operation is invoked in preparation or host controls.

## Exact change and preserved predicates

The [source diff](../verification/apple-focus-reference-diagnostic-v1/source.patch) changes two archived source members:

1. `source/Prototype/main.swift:283` changes only `preferredFocusEnvironments` from `[toggle]` to `[referenceButton]`. The existing plain UIButton, carrier code, layout, geometry and observer remain unchanged.
2. `harness/UITests/ToggleUITests.swift:355` adds an optional required starting-focus parameter. Immediately after the existing authoritative before AX sample at original line 360, the new branch attaches the complete reference premise and throws on failure before the public key call. The separately named `test010ReferenceFirstTab` launches `keyboard-enabled-off` from off, then calls the existing `key("acquire", "tab", requiredFocusBefore: "plain-uibutton-reference")` exactly once. It invokes neither the acquisition loop nor any semantic-key phases. The original six methods, including `test010EnabledFromOff`, retain their exact declarations and bodies.

The existing acquisition oracle legitimately supports a reference start. The original keyboard oracle at lines 123 and 143–144 requires the toggle's fresh off/enabled/allowed premise, silent semantic routes, and a real change to one of the three observed fixed targets. It does not require the initial focus to be the authored carrier. The unchanged v2 wrapper at lines 31–40 still requires paired authored app/AX focus agreement, stable metadata and an app focus signal when authored focus changes. Every original oracle byte is retained, and host replay reproduces the complete original failure with `actualNativeFocusTraversal` as its sole false predicate.

The selected method contract is `test000PublicSettingsFullKeyboardAccess` plus `test010ReferenceFirstTab`. The inherited `keyboard-enabled-off` case and `acquire` phase identify the unchanged predicate contract; they do not assert completion of that keyboard case. Native `Cursor` completion must remain false. The derivative never advances a cursor artificially and gives no six-case, full-runtime, carrier, keyboard or GA credit. The original `runPassed` field remains false.

## Diagnostic outcome contract

The pure [reference contract](../verification/apple-focus-reference-diagnostic-v1/reference_contract.py) distinguishes these outcomes:

- A complete, false authoritative reference premise records `failed-reference-precondition`, zero key injections, no original verdict and diagnostic failure.
- A complete, true premise with exactly one returned public Tab witness and exactly one original oracle result records `one-original-oracle-result`. The complete original verdict is replayed against its before/after app observations and retained verbatim. Its original strict pass or failure determines `singleTabDiagnosticEvidencePassed`.
- A true premise without a returned witness remains `incomplete-after-passing-precondition`. Injection count is unknown; absence of a verdict never proves zero injections.
- Missing, duplicate, reordered, contradictory or malformed evidence fails closed. An omitted predicate, mismatched witness binding or absent app replay pair cannot become diagnostic success.

The premise is captured before the injection and records `actionInjectionCount: 0` at that point. A passing premise alone proves no later input outcome. Three-target AX reads remain sequential, neither atomic nor continuous. The existing bounded non-authoritative timing observer and focus-only follow-up cannot choose or replace the authoritative sample. No broad AX inventory is added.

The later runtime environment remains pinned to Xcode 26.6 (17F113), iOS 26.5 (23F77), iPhone 17 Pro, the unchanged public `XCUIElement.typeKey(_:modifierFlags:)` call, command observer V2 and existing budgets: 600-second selected command, 12-second witness, 250-ms focus-only follow-up and 30/45-second XCTest allowances. Public Settings setup remains unchanged. Runtime assembly must use fresh owned paths and a separately reviewed selection; the original packet cannot be dispatched.

## Reproduction and evidence

From the repository root, source preparation and host controls are:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-diagnostic-v1/prepare.py prepare
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-diagnostic-v1/verify_host.py
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-diagnostic-v1/prepare.py verify
```

The first command is once-only and refuses to overwrite retained preparation. [prepared.json](../verification/apple-focus-reference-diagnostic-v1/prepared.json) binds source archives, member hashes/modes, input hashes, original packet identity, inherited revision label, diff and environment contract. Its SHA-256 is `e71f226c97182e2f8b8b8cd0f2f5e07ffa43e54d540c34189516123e21fb9ed1`; the derivative 39-source tree digest is `696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a`. [host-receipt.json](../verification/apple-focus-reference-diagnostic-v1/host-receipt.json) records the exact command, Python version, owned source hashes, output hashes, 26 tests with zero failures/errors/skips, unchanged frozen failure replay and temporary-file cleanup. Synthetic reference transitions are host controls, not native observations.

Generic compilation was separately authorized and restricted to `build-for-testing` with `generic/platform=iOS Simulator`, unsigned app/runner products and the pinned compiler. The [build script](../verification/apple-focus-reference-diagnostic-v1/build.py) has no test execution or instance control operation. It requires the exact reviewed source digest and preserves each compiler attempt's commands/output/tool bindings.

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-diagnostic-v1/build.py --attempt 1 --reviewed-source e71f226c97182e2f8b8b8cd0f2f5e07ffa43e54d540c34189516123e21fb9ed1
```

The [compiler receipt](../verification/apple-focus-reference-diagnostic-v1/compile-attempt-1/receipt.json) reports core, UI, app and runner exit codes all zero on the first attempt. The live tools report Xcode 26.6 (17F113), Apple Swift 6.3.3 and simulator SDK 26.5; Python is 3.14.8. Command logs retain existing UIKit deprecation warnings and XCTest actor-isolation warnings; compilation succeeds and no source repair or retry occurs. The source archive remains byte-identical after compilation. The 8,826,557-byte product archive has SHA-256 `0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8`; its complete product-tree digest is `e3d60e7c69dcbe6e75e7089840b62dd4dd475f4a9db4fe87465543f822b39e20`.

Every product byte, mode and link is checked against the archive before [cleanup](../verification/apple-focus-reference-diagnostic-v1/compile-attempt-1/cleanup.json). All owned compiler process groups are absent. The owned compile scratch is removed after verification (164,590,153 file bytes), and no explicit simulator or device command is issued. This is compilation evidence; it does not establish an available runtime, simulator behavior or native focus result. The [frozen handoff manifest](../verification/apple-focus-reference-diagnostic-v1/handoff.json) binds the final preparation, command logs, tools, products and documentation. Runtime assembly, independent review and root selection remain separate steps.

A passing reference transition could narrow the authored-first loss; it would not establish a carrier cause. A failed reference transition remains failure evidence. Physical phones remain disconnected and deferred. Comparator behavior, all six complete keyboard cases, physical-phone parity, published FieldLog packages, signing, store, operational and GA requirements remain open.
