# Apple toggle pan correction checkpoint

The private iOS toggle candidate now passes all ten XCTest interaction methods
on iPhone 17 Pro, iOS 26.5 (23F77). All 13 action evaluations and 167 original
predicates pass: four LTR/RTL state-changing drags, standalone pan delivery,
blank-list and carrier-origin vertical scrolling, and six native tap transitions.
Root independently replayed the raw observations and checked another 36
origin/identity/geometry/lifecycle predicates. XCTest exited normally with code 0;
its official result reports ten passed tests and no skipped tests.

The correction captures the original public native touch position in window
coordinates and uses its displacement for admission. All four drags now reach
the unchanged six-point and 1.2 horizontal-dominance rule. The recognizer's
existing translation still drives preview and release. No threshold, original
strict oracle, comparator app or live Apple adapter changed. Before native
execution, root replayed 92 Python controls and compiled and ran 58 Swift checks.
The exact candidate and acceptance scope are bound by the
[root interaction review](../verification/apple-toggle-pan-origin-root-review/runtime-review.json).

The separate direct API replay is complete and failed. The diagnostic suite
passes 11 of its original 19 checks; the comparator passes 10 of 12. Both XCTest
methods fail, with normal xcodebuild exit 65, complete official results and no
bridge errors. The original assertions remain unchanged. This resolves the
previous incomplete collection without turning the earlier or current failures
into passes. See the [direct review](../verification/apple-toggle-pan-origin-root-review/direct-review.json).

Direct `performPrimaryAction()` invokes the target but leaves selection unchanged
in both the authored carrier and the plain UIKit reference. Direct
`accessibilityActivate()` returns false and dispatches no action in either.
The observations are retained at immediate, next-main-queue and 250ms-settled
points. Real XCTest taps do change selection and dispatch once. Apple describes
[primary action invocation](https://developer.apple.com/documentation/uikit/uicontrol/performprimaryaction())
and [accessibility activation](https://developer.apple.com/documentation/objectivec/nsobject-swift.class/accessibilityactivate())
as distinct APIs; the latter requires an implementation to perform activation
and report its result. The next private design must address accessible semantic
activation explicitly and preserve native touch, keyboard, cancellation and
single-event behavior. Neither direct calls nor XCTest taps qualify physical
VoiceOver navigation, announcements or user activation.

The two native runs were sequential. Both disposable simulators were shut down
and deleted. Each run closed its bridge server and thread, removed its ephemeral
capability workspace, and preserved baseline simulator identities/states and
frontend processes. The host replay also removed its 11 temporary build files.
Physical phones remain disconnected and deferred to final acceptance.

Android's live authored toggle integration remains the accepted scoped slice at
`a490761`. That checkpoint's engine CI is still in progress at this observation;
services has reported success. Swift dispatch has an independent review in
progress; a 65-comparison edge in the selected 64-comparison bound was found and
is being repaired before final accounting and qualified runtime. The private
Linux resource harness is incomplete and has no Linux execution acceptance.

Apple adapter integration, native no-change/cancellation/disable/stale/focus/
keyboard coverage, compositor parity, final physical accessibility, immutable
external FieldLog packages and every GA/dogfood gate remain pending.
