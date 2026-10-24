# Private Android platform input: bounded next contract

This is a proposed verification contract, not an implemented fixture or a native
pass. Root selected the first slice below on October 24: preserve production
bytes, observe real Activity input delivery, and compare exact committed reducer
revision/state/identity. The corrected predecessor is now root-accepted for its
bounded native subset; implementation still awaits root contract acceptance. Root alone
dispatches the emulator, coordinates commits, and updates execution trackers.

The binding scope is [product plan §8.3](../mixer-product-plan.md#83-ui-instruction-contract),
including native input and the same authored shared appearance. The earlier
pause language in the [coordinator contract](android-native-v2-coordinator-contract.md)
and [implementation note](android-native-v2-coordinator.md) is historical. The
[resume receipt](../verification/native-testing-resume-2026-10-24/receipt.json)
authorizes emulator tests; physical phones remain disconnected and deferred.
The [current runtime note](android-coordinator-join-runtime-status.md) preserves
the failed attempts. This contract neither changes nor supersedes those results.

## Entry conditions and exact dependency

The selected predecessor is
`verification/android-coordinator-apk-packaging/candidate-1`: APK SHA-256
`78af8c5df197fb6f163f3010825648a1b1a50427c9ab963b1c5aeca1e513b3ba`,
105-input closure
`00c269c70199ffb376b39394db1c2367f8e9053d92ce6a863741d2a154359c04`.
Its packaging repair changes the APK container/signature only; actual Java/DEX,
JNI, Swift and installed-descriptor bytes are unchanged. The fresh
[root native acceptance](../verification/android-coordinator-join-root-review/native-join-acceptance.json)
records 64 native checks across all eight ordinary operations and independent
decoding of seven actual packets, with 56 runtime artifacts and 60 root bindings
verified. The owned PID 31099/group/ports and 177-file, 172885588-byte extraction
were cleaned. This accepts the earlier performClick/direct-connection subset;
it does not establish pointer gesture or system IME behavior. Earlier native check 27 failed
on an incorrect `performClick()` return assertion; a later run failed installation
because `resources.arsc` was compressed. Neither is accepted native evidence.
The snapshot receipt binds that acceptance and its evidence independently. The
[current acceptance note](android-coordinator-join-acceptance.md) summarizes the
observed limits.

Freeze the next harness, operation manifest, runner and artifact closure in a
new packet. Compare production source/class/native-library bytes against the
accepted predecessor and retain the comparison. Existing native+SDK inputs total
88, including 19 test inputs; do not relabel these all as production compilation
units. A harness-only DEX change requires a new private debug APK, local ZIP
offset/compression/alignment validation before any native command and again
before installation, official zipalign/apksigner checks, and exact installed APK
hash verification. Preserve every previous packet and failed attempt.

Use the real `ChecklistEngine`, `AndroidSessionRegistry`, C JNI, `NativeBridge`,
`NativeCoordinatorV2`, `NativeRenderer`, `NativeAppearanceViewsV2`, installed
descriptor and attached window. No engine leaves, substituted event sink,
support proof, synthetic environment or callback invocation qualifies this
slice. The public `MixerActivity` and signed transport stay outside its scope.

## Source-derived constraints

`NativeSwitch` overrides drawing, not touch handling. `Record.bind` installs
authored metrics and empty native thumb/track drawables; actual native `Switch`
gesture handling therefore needs testing against the authored visible geometry.
The recipe, colors, font, layout, spacing, track, thumb and label must not change
to make an input test pass. A pointer that misses the visible authored thumb is
an observed geometry/behavior failure, not permission to move it until it works.

The renderer's `Input.open` requires a current capture, the exact live record,
enabled/attached/shown view and window focus. A native checked change enters the
production listener, synchronous coordinator transaction and actual Swift
reducer; every accepted ChecklistEngine dispatch increments its UInt64 document
revision by exactly one. `validateAttachedV2` immediately precedes scalar commit
and successful commit immediately precedes `finishV2`. A rejected native
transaction retires the owners. No new observer may be inserted in that critical
boundary, reopen forwarding after rejection, or restore a composing buffer.

The existing `environmentInvalidatedV2`, `refreshEnvironment`, `close`,
`presentationCurrentV2`, `isRetired`, `hasCommittedPresentation`,
`lastNativeInputFailure`, `inspectV2`, and read-only reflection of the retained
packet/renderer/session are sufficient. No product observation seam is required
for this first slice. Do not replace checked, text, click or touch listeners.

## Environment and input delivery

Root may run one owned headless read-only/no-snapshot instance of the existing
`megpt-parity-api37` AVD, `emulator-5586`, reserved ports 5586/5587, arm64-v8a,
API37, fingerprint
`google/sdk_gphone64_arm64/emu64a:17/CE2A.260420.019/15611780:userdebug/dev-keys`.
Retain the accepted runner's exact executable hashes and sole Wi-Fi boot delta
`-feature -WiFiPacketStream`. This is a headless path without a host GUI
dependency; it does not inherit Apple's locked-Mac UI limitation.

The reference root is 1206×2622 px, density 480 / density1024=3072, light, LTR,
profile `l`, en-US, default font scale, no bold/increased contrast/reduce motion,
logical viewport 25728×55936, safe area64 top 2816 / bottom 1536 / leading 0 / trailing 0.
These are the earlier observed tuple, not a minted capture. Before each action,
record the actual freshly current concrete capture and generation; unsupported
or changed values fail closed. Never rewrite system preferences to fabricate
support. Runtime qualification applies only to the observed API37 tuple, even
though the private renderer runtime floor is API36 and Swift's link triple is 28.

Use `Instrumentation.sendPointerSync` from the instrumentation worker, never
from the main Looper. It sends into the instrumented app window and waits for
handling, but display work can remain pending. After each injected event, use a
bounded main-thread read to capture the synchronous committed packet and native
state; use a separate idle/settling observation for scrolling. All coordinates
come from current attached views using screen location and global visible rect.
Reject an obscured, clipped, unfocused or out-of-window target. The test Activity
may override `dispatchTouchEvent` only to record before/after values around
exactly one `super.dispatchTouchEvent` call, preserving its return and exceptions.
It must not consume, transform, retarget, duplicate or synthesize an event.
[Official Instrumentation semantics](https://developer.android.com/reference/android/app/Instrumentation#sendPointerSync(android.view.MotionEvent))

Use one touchscreen pointer, stable pointer ID, explicit `SOURCE_TOUCHSCREEN`,
downTime/eventTime from `SystemClock.uptimeMillis`, monotonic times, pressure 1
until release, and recycle each MotionEvent in `finally`. Compile-time API
linkage is demonstrated in the accompanying snapshot; this proves no delivery.
`UiAutomation.injectInputEvent(event,true)` is an alternative only under a later
explicit harness choice; its Boolean reports injection, not reducer acceptance.
Do not mix injectors within a candidate or inject outside the target window.
[Official UiAutomation semantics](https://developer.android.com/reference/android/app/UiAutomation#injectInputEvent(android.view.InputEvent,boolean))

Read `ViewConfiguration.getScaledTouchSlop`, minimum fling velocity, tap and
long-press timeouts on the actual target and retain them. Resolve and seal the
whole action sequence, including geometry and timings, before its first DOWN.
Do not tune an action after observing a failed outcome. Scheduled event offsets
are immutable; actual injection lateness beyond 100 ms fails the timing bound
and ends the action with a retained failure, with terminal CANCEL cleanup if
needed. Cleanup input is separately labeled and cannot make the action pass. Horizontal drags cross
the measured slop and travel between authored thumb centers, then hold still
for 150 ms before UP to avoid qualifying a fling instead of a positional drag.
If those centers cannot support the required in-bounds trajectory, fail the
precondition and retain it. [Official ViewConfiguration semantics](https://developer.android.com/reference/android/view/ViewConfiguration#getScaledTouchSlop())

## Selected first slice: pointer gestures and gates

Run P01–P05 as a five-action cycle three times on the same surviving `task.1`
record. The cycle starts and ends unchecked. Recompute coordinates from actual
geometry between actions, then seal that action before injecting it. Do not
reset checked state or directly dispatch a reducer action inside a gesture case.
Take all measurements before, after each event, and after a bounded settle.

| ID | Real sequence and condition | Required observed outcome |
| --- | --- | --- |
| P01 | Label-center DOWN, stationary UP after 80 ms, initially unchecked. Label point is inside visible label and outside track. | No acknowledgement before UP; exactly one committed revision step at UP; checked=true in native Switch and packet; record/view/generation survive. |
| P02 | Same label DOWN, hold for actual longPressTimeout + 100 ms, then UP. Timeout must be ≤1500 ms; otherwise retain an unsupported test precondition. No long-click listener is installed. | Hold alone commits nothing; UP commits exactly once to checked=false. This tests held-tap release, not a product long-press action. |
| P03 | DOWN at authored off-thumb center; eight evenly spaced horizontal MOVE events over 640 ms towards authored on-thumb center; stationary 150 ms; UP. | All preceding moves retain the old committed revision; UP acknowledges checked=true exactly once; native/packet agree; no retirement; list scrollY unchanged. |
| P04 | Reverse P03 from authored on-thumb center towards off-thumb center. | Exactly one UP acknowledgement to checked=false, with the same identity and no vertical scroll. This tuple is LTR only. |
| P05 | Off-thumb DOWN, same eight MOVE events toward on, stationary 150 ms, then ACTION_CANCEL instead of UP. | No reducer revision step, no checked-state change; capture remains current and the following cycle's P01 works where present. CANCEL ends this gesture; no UP is injected afterward. |

Cancellation must not produce the usual gesture action. The receipt must retain
the actual CANCEL delivery and outcome; a passing injection alone is insufficient.
[Official MotionEvent cancellation semantics](https://developer.android.com/reference/android/view/MotionEvent#ACTION_CANCEL)

Run the following once each, in isolated phases with their own before snapshots:

| ID | Real sequence and preparation | Required observed outcome |
| --- | --- | --- |
| P06 | Seed exactly 18 additional short tasks through the real ordinary coordinator using current packet envelopes for `draft.textChange` then `add.activate` (36 separately logged setup commits). Keep editors unfocused using the private root's focus; never edit a widget buffer for setup. Require 20 tasks and actual ScrollView overflow ≥128 px. Position a visible toggle with scroll range remaining below; seal a slow upward vertical drag starting in its visible label, outside the thumb/track, with 12 MOVE events across min(240 px, remaining visible in-bounds travel), distance >4×touchSlop, then UP. | Actual list scrollY increases >touchSlop while the touched toggle and every task value stay unchanged; zero document revision steps during the gesture; native record identities survive. This establishes label-start scroll arbitration only. Thumb-start diagonal arbitration is separate. |
| G01 | On a fresh initial screen with empty draft, tap the actual `add` button which the ordinary Swift packet marks disabled. | Native disabled state agrees with packet before input; delivered events produce zero committed revisions, no task insertion or retirement. No test `setEnabled` call is allowed. |
| G02a / G02b | Save task/view/packet; call existing `environmentInvalidatedV2` between complete gestures; verify forwarding closed; seal and inject G02a tap at the saved unchanged task coordinates. Then call `refreshEnvironment` with actual capture, verify exact retained packet reference/bytes, and separately seal/inject G02b current-coordinate tap. | Closed-gate tap has zero commits and unchanged checked value. Refresh preserves packet, record and generation; subsequent current tap commits exactly once. Explicit invalidation tests the existing closure seam, not a real configuration-change workflow. |
| G03 | Fresh owner; capture references, then `coordinator.close()` between gestures; inject a tap at the old coordinates while the Activity remains attached. | Activity receives events; renderer remains retired/closed, coordinator has no authoritative packet, saved immutable packet bytes remain unchanged, and old Switch does not change. Packet revision delta is null after retirement, never an invented zero-current-revision. Refresh rejects; no reopening. |

P06 may use ordinary setup envelopes; their success is not counted as pointer
delivery evidence. If root cannot guarantee unfocused editors or supported
overflow within the fixed 18 additions, retain a failed setup and stop; no larger
fixture or engine shortcut is implied. Setup, idle waits and cleanup are outside
the immutable gesture sequence and must be visible in the receipt.

## Measurement oracle and bounded evidence

Each action has a prewritten immutable JSON sequence and SHA-256: action ID,
repetition, source/fixture/APK/descriptor hashes, target ID/kind/generation, record
and view tokens, complete root/view/global-visible/track/thumb/label geometry,
capture tuple/generation, starting packet SHA/revision/value, scroll offset,
focus/enabled/shown/attached/window state, resolved thresholds, pointer metadata,
coordinate space, and every scheduled event/time offset. Use identity-map tokens
backed by actual Java `==`; identityHashCode alone is not proof of equality.

The observation log is separate from that sequence. For every send, retain
worker timestamps, actual eventTime/downTime/action/source/pointer/history data,
Activity entry/exit sequence number, actual raw and local coordinates and return,
exceptions, current packet reference/hash/UInt64 revision (BigInteger in Java),
all task checked values, native checked state, surviving `==` identity, current
capture/gate/retirement state and `lastNativeInputFailure`. Do not insert expected
callback events into the observed log. Record all actual historical MOVE samples;
coalescing means delivered event count need not equal requested MOVE count.
Require matched DOWN and terminal UP/CANCEL, the intended path endpoints, and
documented timing bounds; retain a discrepancy as a failure rather than masking
it with a synthetic callback.

`nativeDeliveryCount` means observed Activity dispatch entries and their actual
MotionEvent history. `commitAcknowledgementCount` means the exact authoritative
document revision delta for an action while live, justified by the actual
ChecklistEngine's one-increment dispatch rule. These are different measurements.
`directNativeCallbackCount` is **null/unobserved**: no passive production seam
currently exposes the internal checked-change/Event sink invocation count.
Do not infer that count from Activity delivery or revision deltas. Exact duplicate
accepted callbacks are detected by extra revision steps; rejected or suppressed
internal callbacks cannot be counted by this slice. Root explicitly accepted
this limitation; a direct-callback requirement needs a separately coordinated
observational seam and new production identity, not listener replacement here.

For no-commit cases, require the identical authoritative packet object/bytes
while live, unchanged values, and no contained failure. For accepted toggle
cases, require revision+1, matching `valueChange` state, no unrelated task change,
same node generation/record/view, current capture and no failure. Snapshot text
buffers, selection/composing spans, focus and native Editable identity before
and after, and require no unintended text mutation; this is not text-editing
qualification. No `performClick`, `setChecked`, `setText`, expected callback,
handcrafted input envelope or direct `dispatchTouchEvent` may stand in for any
gesture-under-test.

Bounds are: 20 total gesture actions (15 cycle actions + P06 + G01 + G02a/G02b + G03), at most 16
injected MotionEvents per action, 320 injected events total, 36 setup dispatches,
three fresh coordinator/Activity owners maximum (main cycle/scroll, fresh gate
owner, retirement owner; G01 may run before seeding), 512 assertion records,
2048 observed delivery/history rows, and 256 KiB per packet. A main-thread probe
or idle/settle gets 2 s; action wall time gets 5 s including hold/settle; setup gets 30 s;
the instrumentation run gets 180 s; boot/install/export use the accepted runner's
separate fixed deadlines. Abort on budget overflow; do not truncate into a pass.
Log up to 8 MiB JSONL and 32 MiB packet/metadata bytes; full runner logs add at most
32 MiB, with overflow a retained failure. No screenshots or video are required.
Collect immutable packets only at action/setup boundaries and deduplicate by hash.

Keep the reserved ports/owned PID/AVD/executable checks, unrelated-process
preservation, private app-only export and extraction safety checks. Stop the
owned disposable instance and remove only owned extraction after empty holder
checks on success, failure or timeout. Record cleanup independently; inability
to complete cleanup fails the attempt. Do not query physical devices or ask for
reconnection. No retry within an attempt may overwrite an input sequence,
observation, APK, failure or cleanup result.

## Explicit next matrix: text and real keyboard

No text/keyboard fixture is authorized by this pointer contract. The next small
contract should first tap an attached field to acquire native focus, record its
actual EditorInfo/InputConnection and native Editable, then test plain composing
text replacement, selection, code-point deletion and commit, one call at a time.
Use a short draft buffer so the existing active-editor binding/frame/ancestor
guard can preserve its identity; layout-changing title or submit cases can retire
and must not be silently treated as successful editing.

Public semantics to freeze then: composing text replaces the current composing
range (or selection); `setSelection` preserves the composing range;
`finishComposingText` preserves text/cursor; commit replaces composition;
deletion lengths differ between UTF-16 and code-point APIs. Verify actual buffer,
selection, spans, return values, packet echoes and generation after each step.
Selection/composition-only steps must not invent reducer dispatches. An actual
platform `sendKeySync` sequence is hardware-style key delivery, not a soft IME.
Calling `onCreateInputConnection` and methods directly is a connection test,
never system keyboard coverage. [Official InputConnection semantics](https://developer.android.com/reference/android/view/inputmethod/InputConnection)

A later real-IME slice must identify the installed IME package/version/settings,
prove the field is served and IME window visible, inject its actual keyboard
surface through a supported native route, and observe composition/selection/
commit crossing that service boundary. Do not add a fake IME, test-only keyboard,
global preference change or direct connection fallback and call it real keyboard.
If unsupported on the exact headless image, retain it pending. Accessibility
service/action/focus workflows, removed/recreated node generations, RTL drags,
thumb-start scroll arbitration, batch edits, rich spans, predictive text,
clipboard, handwriting, validation UX and complete lifecycle/process restoration
need separate contracts. ChecklistEngine can add/reverse tasks but cannot remove
and recreate one; a stale-generation lifecycle test cannot be claimed from it.

## Acceptance boundary and handoff

Root has accepted the predecessor's bounded subset. Root review next accepts this contract, then the
new harness/runner source and packaging parity, and finally the observed native
receipt and cleanup. This lane delivers only this contract, a frozen source/tool
snapshot and a public-API compile witness. It executes no emulator, UI, native
app or physical operation and changes no production source or tracker.

A future pass accepts only this private API37 development slice. Side-by-side
iOS/Android design review, final physical-phone matrix, full native IME and
accessibility, public V2 integration, signed OTA authority, immutable published
FieldLog packages from a separate repository, store/customer/operational evidence
and accountable GA review remain independent and pending. No new dependency is
introduced; official SDK/compiler tools only are used by this contract snapshot.
