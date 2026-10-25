# Apple keyboard V3: offline failure analysis

The accepted V3 failure is preserved. The immediate cause is established: the
first public acquisition Tab leaves the toggle, and the three-control witness
observes no focused member afterward. This makes `actualNativeFocusTraversal`
false. The native destination and the reason for that departure are **not
established**. The later 600-second timeout is a separate unresolved failure
after the console test suite finishes. No production focus repair is justified
by these observations alone.

This review used only retained files and bounded Python extraction. It ran no
native, simulator, device, compiler, build, network, server, Git, UI or capture
commands. It imported no selected runtime, harness or authority module. The
analysis revision `69d1672a` and run revision
`50f70a798fea43e1e77b1d95faa1bbda3fc029e0` are inherited labels, not new Git
observations. Physical phones remain disconnected and deferred. Native,
carrier, OTA, dogfood, store and GA acceptance remain ungranted.

## Observed mechanism

The retained witness is
`verification/apple-toggle-keyboard-full-case-preparation-v3/runtime/captures/0001-keyboard-witness-1.json`.
Both app `UIFocusItem.isFocused` and XCTest `hasFocus` report the toggle focused
before the key and unfocused afterward. All three fixed elements remain
present, enabled, hittable and correctly identified; the app remains foreground.
The verdict has exactly one false predicate, `actualNativeFocusTraversal`; all
paired focus, metadata, geometry and silent semantic-route predicates pass.
This is a failed traversal observation, with no Space behavior exercised.

The app records these additional focus events during the key call:

| Uptime | Toggle focused |
| --- | --- |
| `924588.0989935417` | false |
| `924588.3131013333` | true |
| `924588.320811875` | false |

The call starts at `924587.998279375` and returns at `924588.3257083751`.
There are no added touch/pan/primary/accessibility trace entries. This supports
real native focus updates during public key delivery; it does not identify their
other endpoint. The carrier's hook records only its own final `isFocused`
(`verification/apple-toggle-keyboard-focus-v9-preparation/source/Prototype/AuthoredToggleCarrier.swift:344-346`).

The complete causal chain in the harness is deterministic:

1. `acquire()` unconditionally calls `key("acquire", "tab")` even though launch
   already focused the toggle (`ToggleUITests.swift:349-354`). The app's
   `preferredFocusEnvironments` returns `[toggle]` (`main.swift:277`). This is a
   protocol/fixture interaction, not proof of an erroneous initial focus state.
2. The strict oracle maps focus only across the three fixed IDs
   (`inputs/runtime/verification/apple-toggle-keyboard-focus/keyboard_oracle.py:13,28-43`)
   and requires a changed, non-null fixed destination for every acquisition Tab
   (`:142-147`). Its v2 wrapper explicitly preserves that narrow scope
   (`inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/keyboard_oracle.py:25-47`).
3. The first verdict fails. `keyboard_bridge.py:45-47` marks its cursor failed;
   `ToggleUITests.swift:346` records an assertion and throws. The cursor cannot
   advance. `composition.py:81-87` then refuses all five later begins because
   the prior case is incomplete. Those five refusals are consequences of the
   first failure, not five independent native focus regressions.

All short source names in this section refer to the V3 preparation's bound
runtime/harness inputs, except the explicitly named V9 app source snapshot.

## What remains uncertain

| Candidate explanation | Evidence-supported assessment |
| --- | --- |
| Tab legitimately targets an element outside the three sampled controls | Plausible and unproven. The fixture contains a scroll view, title/state labels, twelve row labels and a diagnostic pan surface (`V9 main.swift:45-90`); it never confines the focus system to three IDs. The witness cannot distinguish a different focused item from no focused item. No full app AX hierarchy or app screenshot survived the selected runtime; retained AX text/PNG files are Settings-only. Do not label this ordinary navigation without observing its destination. |
| Delayed or inconsistent observation | Still possible. `ax()` reads controls sequentially, including a separate `waitForExistence` for each, then assigns one end timestamp (`ToggleUITests.swift:305-315`). The after collection ends 3.355 seconds after the key returns, but that is not a per-control timestamp or proof of 3.355 seconds of stable no-focus. Because acquisition supplies no expected focus/selection, the loop immediately accepts its first collection and performs no settling poll (`:333-339`). The three app focus changes during the call further justify recording transition endpoints. |
| Incorrect initial focus or keyboard setup | Initial focus is positively observed and matches the app's preference. Diagnostic Settings evidence observes Full Keyboard Access enabled and completes handoff; this does not establish every keyboard command mapping or native session detail. The retained public key is Tab with no modifiers. There is no evidence that setup was off, and no official exported setup attachment credit. |
| Broken native toggle focus | Not established. The toggle gains launch focus and receives native focus callbacks. Loss after Tab alone is insufficient to diagnose a focus implementation defect, particularly without the destination. The carrier delegates focus/key input to `UIButton`; its focus hook calls `super` and records state. There is no source evidence of a custom Tab handler or focus veto in this carrier. |
| Fixture/oracle defect | An observability and coverage gap is confirmed: synthetic acquisition fixtures start at the reference and land on the toggle (`test_keyboard.py:27-31`), while this run starts on the toggle and leaves the observed set. The selected contract intentionally requires real Tab acquisition and fixed membership. Skipping Tab, treating the initial focus as acquisition, accepting null, or widening membership without a reviewed contract would change that contract and would not repair this retained failure. |

## Why the command timed out

The console's final selected-suite line is
`Test Suite 'Selected tests' failed at 2026-10-24 19:50:39.800.` It reports seven
tests, seven failure assertions and six unexpected failures in 35.525 seconds.
All test teardowns have returned in that transcript. The command recorder does
not regain control until its unchanged 600-second allowance expires, then
records `600.0274745000061` seconds, `TimeoutExpired`, process exit `-15`, and
`2026-10-24T23:59:57Z`. The outer invocation exits 1. There is no normal
`xcodebuild` result, and its runner result remains null.

`orchestration.py:76-78` synchronously waits for the test command.
The bound `harness.py:119-135` uses `Popen.communicate(timeout=600)`; if the
main process is still running it terminates its owned process group and records
the interrupted output. The retained `-15` supports a still-live process that
received termination. The final console suite is not process/session completion.
There is no retained stack, pipe-EOF timeline, test-session teardown state or
result-finalization trace that establishes the specific blocker. A post-suite
session/teardown/result-finalization stall is the supported location, not a
confirmed Xcode subsystem diagnosis. The initial supported-platform and duplicate
accessibility-class warnings do not establish causation.

Attachment export cannot explain the preceding stall: it starts in
`attachment_export.py:46-58` only after `super().run` exits or raises. One
attachment export and four summary/tests export calls subsequently return 64
because `session.xcresult/Info.plist` is absent. The result bundle never becomes
official evidence. The host bridge stays available while the command is awaited;
its separate server lifetime is not evidence that it caused Xcode to wait.
All five cleanup operations pass, and the owned simulator/workspace are removed.

## Minimal proposed diagnostics and next selection

Prepare a new diagnostic derivative; preserve every sealed V3 source and failure.
Do not change production focus behavior or the strict predicate at this stage.

1. At the app controller's focus-update boundary near V9 `main.swift:277`, add a
   diagnostic-only `didUpdateFocus` override that calls `super` and records public
   context previous/next focused items, heading, class, accessibility ID, attached
   frame and uptime. Preserve null endpoints explicitly. The existing carrier
   hook at `AuthoredToggleCarrier.swift:344-346` should record the same context
   alongside its existing state signal. Record all controller transitions so a
   move between other controls is visible. Bound trace size and preserve dropped
   counts; do not request or redirect focus.
2. At `ToggleUITests.swift:305-315,323-345`, retain diagnostic per-row observation
   start/end times, a bounded public app AX hierarchy/focused-item inventory, and
   a second focus-only observation within the existing action/method budget.
   Keep the original strict witness/verdict unchanged; extra observations must
   not select a favorable sample, advance a failed cursor or extend its budget.
   Persist diagnostics through the host side channel before relying on xcresult
   export. An incomplete diagnostic capture remains incomplete.
3. At the bound command boundary `harness.py:119-135`, retain incremental stdout/
   stderr timestamps, owned main-process `poll()` and pipe-EOF state. Once the
   final selected suite is observed, make one diagnostic capture after a bounded
   grace period (for example 10 seconds), including the owned result bundle's
   completion-marker state and, only if separately selected, one short stack
   sample of the recorded owned Xcode PID. Preserve the original 600-second
   ceiling and terminate only owned resources. This distinguishes a live Xcode
   wait from a pipe held open by another owned process and identifies the blocked
   subsystem if a stack is available.

Before native execution, add meaningful host controls using the retained
toggle-to-null witness: it must still fail exactly the traversal predicate,
leave its cursor failed/incomplete and refuse the next begin. Cover an outside-ID
destination separately from an explicit null endpoint, non-atomic timestamps,
trace truncation and a pre-focused launch. Verify that diagnostics cannot grant
acceptance or alter commands. A mocked completed-suite/still-live process must
retain output, take at most one diagnostic capture, preserve the timeout and
perform cleanup. Do not import the authority driver to exercise these controls.

After review and explicit selection, the smallest useful native attempt is one
owned simulator lifecycle with exactly
`test000PublicSettingsFullKeyboardAccess` and `test010EnabledFromOff`, retaining
the unchanged first-Tab behavior and failure predicate. Stop at that first case's
failure; omit the five already-predictable refused begins. A new app/runner build
and this two-method selection need their own authorization and review. No retry,
build or native attempt is authorized or performed by this analysis.

## Source binding and reproducibility

The accepted execution seal is
`7baff6c525359b0647caa2808d0fa73b7d1e8cc54146408d904570eabd80e3b7`.
`verification/apple-toggle-keyboard-v3-failure-analysis/analysis.json` records
32 analyzed file hashes, byte counts and modes, checking selected sources against
the retained input manifest and evidence against that seal. The analyzed input
digest is `7e18e296a09de28461b6dafc68ab2ab7d942a093280d11e8942156af38bbbbaf`.
Current root-review/context files are explicitly identified as such, not claimed
to be members of the earlier execution seal. Key hashes are:

| File | SHA-256 |
| --- | --- |
| V3 `harness/UITests/ToggleUITests.swift` | `6da53dd1f1a0e5b62a60532e4ced62e1b25f5609ed5581aec1d43c2856326a93` |
| Bound original `keyboard_oracle.py` | `24419f56c21e48b1788af8944acb2427bb7e03cf6b81a7d6d5dd4ba290f63e49` |
| Bound v2-wrapper `keyboard_oracle.py` | `feefd59c5796966f68fd9b342f9eae396779cccea4ee74031f6623f203318582` |
| V9 app `main.swift` | `1abf36ab5430793ef1300a779d489d185ee81a69d906e3f4b81c14e0b0138b93` |
| V9 app `AuthoredToggleCarrier.swift` | `7849c633f69b314205ba0b293514ae45ba7b93f083b8e99c0913ea9541a27815` |
| Runtime `0001-keyboard-witness-1.json` | `6fe7c0f5959465b4241c449d6a448b43530f483203044cf57efd394a714a44e2` |
| Runtime `0001-after-1.json` | `4ff8bf462828d9c715a6cc5942645f29399fdc9176facbc11ba7a88a88307efc` |
| Runtime `commands.json` | `32eeb2a72de4e4b3d6b37cd1880869ffb5f9328b8f1bb92a65380b26b36c3b25` |

The pure extraction command is:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-toggle-keyboard-v3-failure-analysis/analyze.py
```

It passed under Python 3.14.8. Its stdout/stderr are retained beside
`analysis.json`; it imports only the Python standard library and writes only that
analysis directory. It verifies the retained failed observations, focus-event
delta, one interrupted command, five failed result exports, 881 sealed runtime
files and five cleanup passes. These are offline integrity/analysis controls,
not native, compiler, physical-phone or GA tests. No new packet seal is needed.
