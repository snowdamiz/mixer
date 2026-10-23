# Bound guest presentation evidence

The authoritative scoped run is
`2026-10-23-candidate-6/receipt.json`. Its frozen SDK/UI-only package excludes the
mutable signed activation coordinator and native runtime. The receipt records
all source hashes, source revision, tool versions, complete commands, output
hashes and the actual emitted mobile module hashes. `verify.py` reproduces this
small package without building another native VM archive.

Debug and Release each execute twelve original tests; the positive visible-window
qualification is explicitly skipped. ThreadSanitizer executes eleven model tests.
The cases cover effects confirmation, no receipt from host update, synchronous
single-event admission, unchanged-frame result consumption, exact-exchange stale
callbacks despite repeated numeric generations, fresh hosts, stop during
publication, consumer/model/exchange lifetimes, prebind and live attachment invariants, stale
revision tickets, and queued/running/delivered event results when close wins
after a presentation claim. A test deliberately advances its private native host
through the existing reconciler API to execute the actual consumer's host-update
failure branch, proving that view retirement preserves the unseen terminal event
until the final stop claim. It adds no production hook or receipt injection.
Native detached and hidden-window checks execute in
both normal host modes. The root integrator separately owns the counted task's
actual join before coordinator fallback/close completes.

iOS arm64 module compilation includes the actual UIKit hosting wrapper, active
foreground-window checks, native appearance/layout, committed Core Animation
transaction, and subsequent display-link interval. This is compilation evidence;
those native lifecycle and display-link paths have not executed on an iOS
simulator or physical device in this lane. Official Swift 6.3.3 Android API 28
arm64 compilation covers the portable unsupported-platform binding. It does not
provide Android rendering.

The positive Mac check requires
`MIXER_GUEST_UI_VISIBLE_WINDOW=1 swift test --package-path
.build/guest-ui-presentation --scratch-path .build/guest-ui-presentation/build
--filter visibleNativeWindow`. Attempts 4–10 failed to obtain a native receipt.
Instrumented attempts 8–9 established that the window was ordered and attached,
with nonempty renderer bounds, while `occlusionState` was 8192 and lacked
`NSWindow.OcclusionState.visible` (2). The production probe correctly rejected it.
An independently launched intermediate application with a real `NSApplication.run` loop
(`GuestUIPresentationWindowHarness.swift`) reproduced that result; see
`window-harness-attempt-1.json` and its compile/launch logs. It earned no receipt
and exposed no AX control labels. Positive native display and intended-control
AX/screenshot evidence therefore remain pending; a skipped check is not a pass.

The Mac implementation calls AppKit's native layout/display path, then rechecks
the exact ticket and live visible window. Apple's
[displayIfNeeded documentation](https://developer.apple.com/documentation/appkit/nsview/displayifneeded%28%29)
and [needsDisplay documentation](https://developer.apple.com/documentation/appkit/nsview/needsdisplay)
describe the native drawing call and cleared dirty flag used for that check.
Native display-cycle observation is not a compositor, delivered-pixel or human
perception claim. The iOS transaction/display-link path remains separate.

Earlier failed build logs are preserved: attempt 1 used an inaccessible private
generation property; attempts 2–3 accidentally copied unrelated root-owned
activation files into the temporary review package. The actual root sources were
not edited. The final driver copies an explicit owned file list and rejects
extra production files, so those failures do not enter the scoped passing run.
The first driver invocation also retained its failure when an unchanged SDK C
header was absent from the SDK receipt's Swift-only manifest; the final driver
checks such unchanged files against Git and records them in its own manifest.
Candidate 3's driver started before the SDK candidate 4 receipt existed and
retained that dependency-file failure. Candidates 2, 4 and 5 are passing
intermediate receipts; candidate 6 adds all final repairs and tests and links the
sealed SDK candidate 4 source/evidence.

This lane supplies no physical-device, signed facade end-to-end, immutable
published package/FieldLog consumer, customer, store, production or GA evidence.
No phones were probed and no native archive pin was changed.
