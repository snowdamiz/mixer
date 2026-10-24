# Native toggle diagnostic checkpoint

The Android private component fixture now completes 39 of its original 45 cases.
Both vertical and diagonal scroll cases deliver the original nine events to the
Activity, observe one actual parent interception and child CANCEL, scroll by
365 pixels, and retain zero proposals and no pressed state. Fresh scroll
containers start at zero offset with 6,000 pixels of content in a 2,622-pixel
viewport. All six added setup checks pass. The run stops at case 40 because
`requestFocus()` returns false: 189 assertion attempts include six setup checks
and 183 original checks; this is not 189 passing assertions.

The host collector also rejects the two added counter fields against its old
closed schema. That parser defect is separate from the native focus failure.
The frozen results, failure forwarding, 162-entry scroll trace and cleanup are
bound by [root review](../verification/android-toggle-scroll-reset-root-review/runtime-review.json).
The next fixture records focus preconditions, enters keyboard mode through one
ordinary directional key pair, and checks an unchanged native Button before
the original toggle focus assertion. Production focus policy and all original
case assertions remain required. Full component acceptance and integration of
the three reviewed Android candidate source files remain pending.

On the owned iOS 26.5 simulator, the exact original app rebuilt with SDK 26.5
still reports ten true and two false direct API checks; one subsequent check
remains vacuous. The separate strict diagnostic reports eleven true and eight
false checks out of nineteen. Both the authored carrier and plain UIKit Button
fail the direct primary/accessibility selection expectations. Actual system
accessibility-element clicks change each button's state. Those observations
must not be conflated with a passing direct-call contract.

Both the standalone native pan control and authored carrier received only
begin/end events from the computer-use drag calls, with no movement events.
The blank-list scroll call produced no trace or offset change. These calls
therefore do not qualify drag or scroll behavior. The [root comparison](../verification/apple-toggle-diagnostic-root-review/runtime-review.json)
retains those results, tool interruptions and exact app identities. A separate
official XCUITest harness is being prepared to supply timed native movements
and retain actual callback, scroll and state evidence. Keyboard, pressed-paint,
full accessibility, shared appearance parity and adapter integration remain open.

Both owned native instances are stopped and the disposable Apple simulator is
deleted. The Android extraction removed 187 files / 173,027,566 bytes. Existing
unrelated Apple simulator states were preserved. Physical phones remain deferred
to final acceptance; these simulator/emulator results support development only.

The latest pushed checkpoint, `bbed074d`, passes all three Engine CI jobs and
38 steps. Its exact 73-input Phoenix closure passes 149 tests and packaged
release checks, with two namespace fixtures explicitly skipped. Production
webhook transport remains inactive. The private Linux resource profile is
[selected for implementation](../verification/stripe-webhook-resource-ingress-root-review/selection.json);
all thirty resource, trailer and ingress runtime cases remain pending.

The independent Swift optimized-type audit distinguishes exact inferred types
from invalid equal-size substitutions. Root selected finite compiler-derived
layout evidence for explicitly enumerated otherwise inaccessible types and
closures, including 96 newly inventoried TLS closure positions. This is an
implementation method, not final accounting acceptance. Complete body/type
coverage, additive bounds, original reservations and independent review remain
required before the private dispatcher can qualify. No GA or dogfood gate is
closed by this checkpoint.
