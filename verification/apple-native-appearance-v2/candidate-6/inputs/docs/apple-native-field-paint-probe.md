# Public UIKit field paint feasibility probe

This is positive **bounded feasibility evidence on the iOS 26.5 simulator**, not
qualified V2 `UITextField` support or an iOS 17 runtime receipt. No product code,
consumer support value, native build closure, release authority, or GA gate was
changed. Phones were not queried or used.

The independent harness is
[`verification/apple-native-field-paint-probe/source/main.swift`](../verification/apple-native-field-paint-probe/source/main.swift).
It links UIKit directly and imports no Mixer module or third-party dependency.
All interaction discovery uses the public `UITextField.interactions` and
`UITextInput.textInputView.interactions` arrays. The replacement views conform to
the public `UITextCursorView` and `UITextSelectionHighlightView` protocols and are
assigned through `UITextSelectionDisplayInteraction.cursorView/highlightView`.
There is no private selector, KVC, private-type reflection, subview search, or
manual selection-overlay insertion.

## Observed native lifecycle

On this runtime the field's public `interactions` contains one selection display
interaction whose `textInput` is that field. `textInputView.interactions` contains
none. The affiliated text input view is a public coordinate-space API; finding
the interaction only there would reject this observed field.

| Operation | Actual observed result |
| --- | --- |
| Change native managed cursor/highlight `tintColor`, retaining field tint blue | Native highlight remains RGB 204,204,255; authored tint/alpha is not consumed |
| Assign custom managed cursor/highlight views | Properties refer to the custom views, but both have no native window; old blue highlight remains visible |
| Toggle `isActivated` false/true and request/layout selection | Custom views remain detached; this does not repair attachment |
| Public `display.view.removeInteraction(display)` followed by `addInteraction(display)` on the **same interaction**, then activate/update/layout | Custom views enter the native window, old native highlight leaves it, and UIKit supplies selection rectangles and caret geometry |
| Change the native field's selected range | UIKit hides/shows the managed caret/highlight and updates caret geometry; native blue selection handles remain visible |

The first two failed driver/replacement attempts are preserved under
`evidence/initial-url-driver/` and `evidence/managed-replacement-detached/`.
The URL driver triggered SpringBoard's Open confirmation, so its compositor
images are explicitly unqualified. The final run uses a harness-only control
file polled on the native main run loop and never opens a URL. New simulators
were used to remove the contaminated system UI state. The final captures show
the simulator's initial keyboard onboarding below the field; that screen was
not treated as a real keyboard/IME interaction test.

## Independent authored paint observations

The field tint stays opaque blue throughout. Selection covers six native spaces
so an interior 11×11 pixel sample contains no text ink or handles. Colors below
are decoded directly from the actual `simctl io screenshot` PNGs, not synthesized
reference images. The native window's `drawHierarchy` PNGs are supplemental.

| Managed paint on opaque white | Native compositor RGB |
| --- | --- |
| Red caret, alpha 255 | 255,0,0 |
| Red caret, alpha 61 | 255,194,194 |
| Red caret, alpha 128 | 255,127,127 |
| Green caret, alpha 255 | 0,255,0 |
| Clear caret | 255,255,255 |
| Green selection, alpha 61 | 194,255,194 |
| Green selection, alpha 128 | 127,255,127 |
| Red selection, alpha 61 while caret paint is green | 255,194,194 |
| Clear selection | 255,255,255 |

These samples establish independent paint consumption and a single alpha
application for the tested swatches. They do not prove all colors, backgrounds,
scripts, directions, accessibility preferences, or supported operating systems.
Disabling explicitly clears both paints, disables the actual native field, and
produces no red/green field pixels.

The field identity, first responder status, selected range and text survive
installation, activation and public reinstallation in the recorded stages.
The probe also calls native `setMarkedText("にほん", selectedRange:…)`, changes
paint/font/text color while marked, commits through native `unmarkText` and
`insertText`, and deletes through `deleteBackward`. These are public native
protocol exercises; they are not a keyboard-driven Japanese IME receipt.
The same public interaction reinstallation also retained native identity, focus,
marked range, selection and text while that programmatic composition was active.
The per-stage before/after native state is retained in `observations.json`.

## Toolchain, runtime and replay

The final native source, harness driver, binding contract and AGENTS input hashes
are in [`source-lock.json`](../verification/apple-native-field-paint-probe/evidence/source-lock.json),
along with the source revision, Git tree and dirty-path snapshot. Commands,
tool versions, stdout/stderr and exit codes are retained in
[`commands.json`](../verification/apple-native-field-paint-probe/evidence/commands.json).
Xcode is 27.1 (27A9275); the installed simulator runtime is iOS 26.5 (23F77), on
a dedicated iPhone 17 Pro simulator at 3×. The only installed runtime families
observed were iOS 26.5 and 27.0. None was downloaded.

The app compiles with target `arm64-apple-ios17.0-simulator`. The compiler retained
a sysroot warning, so a separate Mach-O inspection is kept in
`post-capture-tools.json`: `LC_BUILD_VERSION` identifies platform IOSSIMULATOR,
minimum OS 17.0, SDK 27.0. This verifies the deployment target and does not execute
iOS 17. Public API availability since iOS 17 is independently recorded from the
installed UIKit headers and retained official Apple documentation in
`public-api-sources.json`.

To replay native collection, create a dedicated simulator from an **already
installed** runtime, then run:

```sh
python3 verification/apple-native-field-paint-probe/run-probe.py --simulator SIMULATOR_UDID
python3 verification/apple-native-field-paint-probe/analyze.py
```

The driver never chooses a phone. Simulator creation, shutdown and deletion IDs
are retained in `simulator-lifecycle.json`. Existing booted simulators are not
changed. Offline artifact checks use:

```sh
python3 verification/apple-native-field-paint-probe/verify-artifacts.py
python3 verification/apple-native-field-paint-probe/analyze.py
```

## Explicitly pending

The custom cursor suppresses blinking for deterministic captures; native blink
requests are logged, but blink cadence/reset behavior is not implemented or
qualified. Real keyboard/IME composition and cancellation, selection dragging,
editing menus, secure input, submit routing, VoiceOver, dynamic environment
contexts, failure-atomic product transactions, signed display authority,
physical iOS/Android comparison and iOS 17 runtime behavior remain pending.
No native consumer may advertise complete V2 field support from this probe.

The [official cursor view documentation](https://developer.apple.com/documentation/uikit/uitextselectiondisplayinteraction/cursorview)
and [highlight view documentation](https://developer.apple.com/documentation/uikit/uitextselectiondisplayinteraction/highlightview)
permit custom managed views; the observed reinstallation requirement above is a
runtime finding from this harness, not a documented cross-version guarantee.
