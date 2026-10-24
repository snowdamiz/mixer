# Private pan-commit runtime checkpoint

The private authored iOS toggle now passes final-pan callback reentry checks and
its existing input regressions on an iPhone 17 Pro simulator running iOS 26.5
(23F77). Official XCTest reports **43 passed, zero failed, zero skipped**;
`xcodebuild` exits normally with code 0. Root replays all 46 capture verdicts:
45 real native input actions and one result containing 36 direct semantic
callback components. All 1,286 verdict predicates and 324 additional root
touch-origin predicates pass. There are no bridge failures.

The carrier guards the final pan transition against synchronous binding changes,
stale input, disable, explicit cancellation, direction changes and nested primary
or accessibility activation. A rejected transition preserves a newer binding or
restores the prior value and emits no value event. An accepted transition emits
one value event before its informational observer. A later observer binding write
remains silent. Both starting values are exercised for eight callback cases,
alongside thirteen prior native actions and sixteen interruption actions.

The accepted app source closure is
`f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46`.
The app archive is
`b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393`;
the runner tree is
`741d8adef8bcd17d60819cb25f4caa4a9883620e090e62c06bd2f2f32cd897e9`.
These are identical to the first failed attempt. The corrected harness seal is
`f4410706adc7eae9e2c2367888b4ee6055d67a8028a28b008d1d202e5fe4b41d`.
The original build used Xcode 26.6 (17F113), Swift 6.3.3 and simulator SDK 26.5;
its minimum deployment target remains iOS 26.0.

The first run remains failed: 26 methods passed and 17 failed. Sixteen verdicts
incorrectly required attached-view geometry in startup history; one observation
read raced an atomic file replacement and produced no action verdict. The new
harness preserves all original bytes and failures, distinguishes startup shape
from attached input states, and uses bounded stable observation reads. Its 37
host controls pass both producer and root runs. Historical capture replays are
diagnostic only; acceptance comes from the new complete native run.

The original nineteen direct diagnostic checks still contain four failures in
the plain UIKit reference expectations. They remain separately recorded as
failed. They are not part of the accepted 36 authored semantic components and
are not relabeled by the successful scoped XCTest method.

All five independent cleanup operations pass. Owned simulator
`AE4DEC6A-F1C6-44DF-888A-C4DB7A44AB89` and its temporary capability workspace are
absent. Existing simulator states and frontend processes are preserved.

Evidence:

- [Root selection and host verification](../verification/apple-toggle-pan-commit-harness-v2-root-review/selection.json)
- [Root native replay and exact evidence bindings](../verification/apple-toggle-pan-commit-harness-v2-root-review/runtime-review.json)
- [Official XCTest summary](../verification/apple-toggle-pan-commit-harness-v2/runtime/xctest-summary.json)
- [Cleanup lifecycle](../verification/apple-toggle-pan-commit-harness-v2/runtime/lifecycle.json)
- [Original failed attempt](../verification/apple-toggle-pan-commit-root-review/failed-runtime-review.json)

This accepts a private simulator development slice. Native keyboard/focus,
remaining lifecycle retirement cases, compositor parity, live Apple adapter
integration, physical VoiceOver/final phone matrix, immutable external FieldLog
consumption and GA remain pending. The next preparation follows the
[keyboard/focus contract](apple-toggle-keyboard-focus-contract.md).
