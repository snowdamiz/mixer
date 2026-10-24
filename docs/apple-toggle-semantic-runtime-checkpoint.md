# iOS semantic toggle activation and native interruption checkpoint

The private authored UIButton now owns one guarded semantic selected-state
transition. Native primary input and direct accessibility activation use that
same transition. Disabled, stale, reentrant or superseded operations cannot
emit a value event or restore an older binding. Automatic UIButton selection
is disabled. Native input dispatch, geometry, paint and corrected pan admission
remain in place. The live Apple adapter is not changed in this checkpoint.

The exact semantic candidate passes all thirteen existing real touch/drag
actions: ten XCTest methods, 167 native predicates and 36 independent origin
checks. Xcodebuild exits zero. Its separate direct callback capture passes all
36 new cases, including both value directions, disabled/stale gates, reentry
and binding/gate changes during callbacks.

The original direct suites remain failed: 15/19 diagnostic and 10/12 comparator
checks pass. The authored carrier's four previously failing primary/accessible
transitions now pass; the unchanged reference retains its direct-call failures.
Both XCTest methods report failure in captured output. Xcodebuild then hangs
after reporting the failed suite and is terminated at the 600-second bound
(process exit -15). No official result summary is exported. Complete raw
observations and this runner failure are retained; passing component callbacks
do not turn that run into a pass. The cause of the post-suite hang is unproved.

A separate fixture keeps the semantic carrier byte-for-byte unchanged and
passes sixteen new real public XCTest drags: four held-pan accessibility
activations, two cancellations, two disables, two stale-input invalidations,
two silent binding replacements, and four no-change releases. All 480 native
predicates and 144 independent origin checks pass. The official result reports
16 passed, zero failed/skipped, and Xcodebuild exits zero. Native pan state and
touch count establish that interruption occurs during a real gesture; after
XCTest releases it, no duplicate value event appears. Two read-only preparation
verifier failures are preserved separately; neither launched a simulator.

All three runs use iPhone 17 Pro simulators running iOS 26.5 (23F77), built with
Xcode 26.6 / Swift 6.3.3, SDK 26.5, deployment minimum 26.0. All fifteen cleanup
operations succeed across the runs. The three exact owned simulators and
temporary capability workspaces are absent; baseline instances and Simulator
frontends are preserved. Physical phones remain disconnected and deferred.

Source/build seals and root reviews:

- `verification/apple-toggle-semantic-activation/packet-seal.json`
- `verification/apple-toggle-semantic-activation-root-review/runtime-review.json`
- `verification/apple-toggle-semantic-activation-root-review/direct-review.json`
- `verification/apple-toggle-native-interruption/packet-seal.json`
- `verification/apple-toggle-native-interruption-root-review/runtime-review.json`

Direct accessibility calls during actual drags do not establish physical
VoiceOver delivery. Keyboard/focus input, remaining lifecycle and reentrant pan
commit cases, compositor parity, live adapter integration, minimum/current/future
OS qualification, final physical testing and immutable external FieldLog release
consumption remain pending. Full carrier and all GA gates remain open.

Both prior pushed checkpoints (`a490761` and `a0382b0`) have terminal successful
VM, Swift and services CI jobs. GitHub returned incomplete/inconsistent detailed
step arrays, which are retained without treating missing steps as passes. Those
jobs provide host/cross-build evidence only.
