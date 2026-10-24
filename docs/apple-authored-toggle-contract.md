# Authored Apple toggle carrier contract

This is an isolated replacement-carrier qualification contract for binding
product-plan sections 8.2–8.4. It changes no production adapter or harness.
Current candidate is `candidate-2-directional-pan`, which retains directional
sliding. Its result is recorded in
`verification/apple-authored-toggle-contract/candidate-2-directional-pan/receipt.json`;
source and executable app are sealed alongside it. The first button-only
candidate is preserved by `candidate-1-seal.json` and is not the selected gesture
contract. Both packets are frozen for handoff while the Mac is locked; no owned
simulator or Simulator frontend was started. Candidate 2's live lifecycle receipt
confirms the four existing iOS 27 instances remain unchanged and shut down.
A compiler pass does not qualify touch, keyboard,
VoiceOver, visual suppression, or the full Apple adapter.

## Candidate and public API basis

Use a stable `UIButton(type: .custom)` with `configuration = nil`, no title,
image, menu, default background, or touch-highlight drawing. Set
`changesSelectionAsPrimaryAction = true` and use `.primaryActionTriggered` as the
single native activation entry point. UIKit owns touch tracking, activation,
cancellation, keyboard/focus, and assistive-technology activation. Mixer owns the
authored track/thumb/overlay paint, mapping of selected state to `isOn`, and the
gate before emitting the Mixer value-change event.

Apple documents that a button with this property enabled and no menu toggles its
selected state. It also defines the public `.toggleButton` accessibility trait
for on/off/mixed state, with `.button` added for a switch-button description.
The prototype combines those traits with `super.accessibilityTraits`, preserving
UIKit's selected and disabled traits. Its `accessibilityActivate()` checks the
input gate and then calls `super`; it does not synthesize an accessibility
element or emulate activation solely by flipping a Boolean.

Official sources, accessed October 24, 2026:

- [UIButton.changesSelectionAsPrimaryAction](https://developer.apple.com/documentation/uikit/uibutton/changesselectionasprimaryaction)
- [UIAccessibilityTraits.toggleButton](https://developer.apple.com/documentation/uikit/uiaccessibilitytraits/togglebutton)
- [UIButton](https://developer.apple.com/documentation/uikit/uibutton/)
- [UIScrollView.touchesShouldCancel(in:)](https://developer.apple.com/documentation/uikit/uiscrollview/touchesshouldcancel(in:))
- [UIScrollView.canCancelContentTouches](https://developer.apple.com/documentation/uikit/uiscrollview/cancancelcontenttouches)

The installed official UIKit SDK headers are retained in `official-sdk/` as API
evidence. `changesSelectionAsPrimaryAction` is available on iOS 15+, and the public
toggle accessibility trait on iOS 17+. The independently owned source closure is
in `source/`; no Patch/Skip source or general-purpose dependency is used.

## Integration interface for root review

The proposed stable native carrier API is:

```swift
@MainActor final class AppearanceToggleV2: UIButton {
    var isOn: Bool { get }                 // native isSelected
    func setOn(_ value: Bool, animated: Bool)
    var authoredPressed: Bool { get }      // native isHighlighted
    var authoredAccessibility: [String: String]
    var inputAllowed: (() -> Bool)?
    var stateChanged: (() -> Void)?
    func cancelAuthoredInteraction()
    func participateInVerticalScroll(_ scrollView: UIScrollView?)
    // .valueChanged is emitted once by the accepted native-primary target.
}
```

`setOn` updates both the retained binding and native selected state without
emitting any action. UIKit changes selection before its primary-action target.
The target checks `isEnabled` and `inputAllowed`; rejection restores the retained
value and emits no `.valueChanged`. Acceptance retains the new native selected
value and emits exactly one `.valueChanged`. Consumers listen only to that
event, avoiding duplicate touch-up plus primary-action delivery. Programmatic
`sendActions(for:)` is not a substitute for actual native activation tests.

The input gate must retain the renderer's existing generation, attachment,
window/key-window, foreground-scene, ancestor visibility, disabled, environment,
and callback-lifetime checks. The carrier checks at native touch begin and again
at primary dispatch, plus before native accessibility activation. Late completion
after permission/generation loss is restored without a guest action. Disabling a
held carrier invokes public `cancelTracking(with:)` and cancels any active public
pan through `isEnabled`; pressed paint must end and release must cause no action.
The renderer must call `cancelAuthoredInteraction()` when invalidating active
input, rather than waiting for a later user move/release to discover a stale gate.

Authored label/hint/value/identifier remain independent metadata overrides. When
no explicit accessibility value exists, UIKit's native toggle/selected semantics
remain authoritative. An authored string value must not erase the native toggle
role, selected state, activation, disabled state, or focus order.

Native identity belongs to the existing reconciliation identity generation.
Binding, theme, direction, text-size, ancestor placement, and environment updates
must reuse the native carrier. Retirements must clear closures and reject delayed
native delivery. The prototype proves same-object mutations; the production
reconciliation and retirement gates still require adapter-level evidence.

## Geometry and removal of the cover prototype

The candidate has a 63×44 input rectangle and draws the exact existing closed
63×28 track and 37×24 thumb paths, vertically centered. Checked thumb placement
uses `UIAppearanceGeometryV2.thumbOrigin`; direction is logical and RTL is
explicit. Normal, pressed overlay, disabled, on/off, light/dark, and focus colors
come from `UIAppearanceDescriptorCodecV2.mixerDefaultV2()` in the sealed owned
source. The direct prototype path consumer uses density 1024 because UIKit's
graphics context already maps points to pixels; the product's existing path
renderer may instead retain its single inverse-density conversion.

This mechanism has no `UISwitch`, zero-area layer mask, opaque sibling cover,
12-point cover expansion, rasterization, private APIs, subview walking, or KVC.
Consequently, the old cover's opaque-surface and neighbor/label/group-clearance
constraints are obsolete for this candidate. Ordinary authored bounds, minimum
hit targets, clipping, nonoverlapping row input envelopes, and full-group geometry
remain required. Removing a failed workaround must not remove those requirements.

Files root would need to change after freezing this interface:

| File | Required integration implication |
| --- | --- |
| `sdk/Sources/MixerApple/AppearanceNativeViewsV2.swift` | Replace `AppearanceSwitchV2`, remove its press observer and `toggleCover*` state and masked-switch construction. Retain exact authored path paints, value-change gate, metadata, identity, and same-object commit behavior. Use native highlight/focus observations. |
| `sdk/Sources/MixerApple/AppearanceNativeLayoutV2.swift` | Retain track/label/hit geometry and `setOn`; remove cover creation, cover-specific groups, 12-point padding and opaque-surface requirements, and cover overlap pass. |
| `sdk/Sources/MixerApple/AppearanceNativeGeometryV2.swift` | Remove or archive only cover-specific validation after its callers are gone; preserve ordinary frame, baseline, group and hit guards. |
| `sdk/Sources/MixerApple/AppearanceNativeRendererV2.swift` | Retain native input gating and identity selection. Revisit only cover-induced toggle context exclusions; each newly admitted context needs executable layout/runtime evidence. |
| `AppearanceNativeViewsV2.swift` list construction | Use a `UIScrollView` subclass whose public `touchesShouldCancel(in:)` returns true for this toggle carrier; keep native pan arbitration and `canCancelContentTouches = true`. Apple's default excludes UIControl. Bind/unbind the current scroll view through `participateInVerticalScroll(_:)`; the pan's public dynamic failure delegate makes that scroll pan wait for horizontal admission failure without leaving permanent relationships to an old parent. |
| `native/apple/appearance-v2/main.swift` | Replace obsolete “native UISwitch/mask/cover” assertions with the actual custom-toggle class/configuration, native role/state/action, hold/cancel, stale/disabled, drag and scroll evidence. Keep all unrelated adapter regressions. |
| `native/apple/appearance-v2/CoverGeometryRegression.swift` | Preserve sealed old failure evidence; retire obsolete workaround-specific tests from the live harness instead of treating cover arithmetic as product acceptance. |
| Apple appearance/staging documentation | State the actual native UIButton toggle role and supported gestures, not “UISwitch preserved.” |

## Directional gesture contract

The preserved first candidate's unconfigured UIKit toggle button supports native tap/release-inside activation,
pressed-state tracking, drag-out cancellation, return-inside behavior, keyboard
and accessibility activation. It does not implement UISwitch's thumb-following,
direction-dependent sliding selection. A horizontal release inside a button
toggles its selection regardless of which side the user approached. A release
outside cancels instead of committing a side-selected UISwitch value.

Root explicitly retained directional sliding to preserve the existing switch
interaction and Android native Switch behavior. Candidate 2 adds one owned
`UIPanGestureRecognizer` to the native UIButton and uses UIKit gesture delivery,
touch cancellation and failure arbitration. This retains directional behavior
without claiming private UISwitch implementation or class equivalence.

The admission policy requires UIKit's native pan recognition plus at least 6
points of horizontal translation and strictly more than 1.2 times the vertical
translation magnitude. An initially vertical gesture fails this recognizer and
yields to the current UIScrollView's native pan. A dynamic public
`shouldBeRequiredToFailBy` delegate establishes that dependency per attempt using
only the explicitly bound current scroll pan; parent moves rebind or clear the
weak reference. No public gesture state is synthesized and no recognizer
subclass-only touch methods are called.

Once horizontal pan begins, `cancelsTouchesInView = true` cancels UIButton touch
delivery, so touch-up cannot emit a duplicate primary action. Authored pressed
state combines native button highlight and active pan. The preview thumb follows
native-point translation from the retained endpoint, clamped to physical x=2...24
points. The checked logical endpoint is trailing in LTR and leading in RTL. The
track's preview paint follows that side while accessibility's native selected
state remains committed until gesture completion.

On ended, the midpoint x=13 selects the prior value on an exact tie; either side
maps explicitly through direction. A changed side emits exactly one value-change
event; returning to the retained side emits zero. Horizontal outside release is
allowed and commits the clamped side. A final y outside the 44-point hit envelope
expanded vertically by 22 points cancels. These are explicit bounded authored
drag semantics, not a claim that every UISwitch threshold is reproduced.

Cancelled/failed recognition, disabled input, stale gate, binding replacement,
direction replacement or parent-scroll rebinding restores committed selected
state, clears preview and emits zero value changes. The gesture records a binding
generation at begin and rechecks it at changed/ended. Programmatic bindings cancel
the active interaction and update that generation. Keyboard and accessibility
continue through UIButton's own primary activation rather than this drag path.

Official public gesture sources:

- [UIPanGestureRecognizer](https://developer.apple.com/documentation/uikit/uipangesturerecognizer)
- [UIGestureRecognizer](https://developer.apple.com/documentation/uikit/uigesturerecognizer)
- [gestureRecognizerShouldBegin(_:)](https://developer.apple.com/documentation/uikit/uiview/gesturerecognizershouldbegin(_:))
- [Dynamic failure requirements](https://developer.apple.com/documentation/uikit/uigesturerecognizerdelegate/gesturerecognizer(_:shouldberequiredtofailby:))

The candidate's actual `TogglePanPolicy` and `AppearanceNativePathsV2` pass 19
executable macOS policy/CoreGraphics cases. This covers boundary admission,
intermediate/clamped preview, midpoint tie, both directions, release corridor and
exact threefold pixel path bounds. It does not prove UIKit gesture delivery,
scroll arbitration, compositor output, keyboard, or VoiceOver.

## Executable qualification matrix

Build without booting a device:

```sh
python3 verification/apple-authored-toggle-contract/candidate-2-directional-pan/build.py
python3 verification/apple-authored-toggle-contract/candidate-2-directional-pan/policy-check.py
```

Use one owned iOS 26.5 instance only while runtime testing and CUA are available:

```sh
python3 verification/apple-authored-toggle-contract/candidate-2-directional-pan/runtime.py install
python3 verification/apple-authored-toggle-contract/candidate-2-directional-pan/runtime.py command self-tests
python3 verification/apple-authored-toggle-contract/candidate-2-directional-pan/runtime.py collect
```

Only CUA supplies actual native tap, hold, drag, keyboard and accessibility UI
input. `runtime.py command` changes explicit test-harness state, and `held` merely
waits for native highlighted/tracking state before collecting it and a compositor
screenshot. It never synthesizes touch input. During a CUA timed hold, run:

```sh
python3 verification/apple-authored-toggle-contract/candidate-2-directional-pan/runtime.py held cancel-case --after-held-command disable
```

| Gate | Required observation |
| --- | --- |
| Binding | Repeated `setOn` emits zero events; same identity persists. |
| Native activation | Actual tap emits one accepted primary action and one value change with the new native selected state; second tap reverses once. |
| Pressed paint | Actual held native touch has `tracking`/`highlighted` true and an authored pressed screenshot; no Liquid Glass or toolkit default escapes the track/input bounds. |
| Cancellation | Cancel/disable during the actual hold ends native tracking and pressed paint; release changes neither state nor action count. |
| Drag | Both horizontal directions, LTR/RTL, intermediate thumb-follow preview, release inside/horizontally outside/vertically outside, return-to-prior-side, mid-pan disabled/stale/binding changes show the documented directional semantics and no duplicate primary action. |
| Scroll | Vertical drag starting on the toggle scrolls the native list and cancels toggle tracking without activation. |
| Disabled | Actual tap and accessibility activation cannot change state or emit an action; native disabled trait persists. |
| Stale input | Revoke `inputAllowed` during a held touch; release restores the prior binding and emits no action. Also reject a new touch while stale. |
| Keyboard/focus | Actual keyboard focus reaches the native toggle in order and native Space activation emits once; focus moves to the next native control. |
| Native accessibility | Simulator AX exposes switch/toggle role and native on/off selected state, label/hint and disabled state. Native `super.accessibilityActivate()` emits once. Actual physical VoiceOver focus/announcements/actions remain pending. |
| Paint states | Light/dark, on/off, normal/pressed/disabled and RTL use canonical closed geometry/colors and remain within authored bounds. |
| Reconciliation | Same-generation node preserves native identity, state, focus and cancellation ownership through parent moves/property changes; stale/retired callback delivery rejects. Requires product integration tests beyond the prototype. |
| Cleanup | Shutdown/delete only the recorded owned instance, preserve all four existing iOS 27 device IDs/states, and stop only a Simulator frontend started by this lane. |

Always finish the owned instance, including failed runs:

```sh
python3 verification/apple-authored-toggle-contract/candidate-2-directional-pan/runtime.py cleanup
```

No physical phone run/discovery, reconnect request, Android instance, production
publication, full-Apple acceptance, FieldLog release qualification, or GA gate is
implied by this prototype.
