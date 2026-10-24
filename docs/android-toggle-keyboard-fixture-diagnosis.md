# Android toggle keyboard fixture diagnosis

The frozen reset attempt remains failed. Its native fixture completed cases 1–39, then `requestFocus()` returned false in case 40 (`java.lang.AssertionError: native focus admitted`). The counter was 189, comprising six scroll setup assertions and 183 original assertions including the failure; it counted 114 MotionEvents. Separately, the outer collector rejected the two new counter keys with `ValueError('supplement schema')`. Repairing that parser must expose the native failure, never convert this attempt into a pass.

Root's sealed review at `verification/android-toggle-scroll-reset-root-review/runtime-review.json` establishes both original scroll cases: zero initial offset, visible owned input endpoints, all nine injected requests delivered to the Activity, actual child DOWN/CANCEL, one true native interception, final offset 365, zero proposals and no pressed state. The 162-entry trace and cleanup are retained by reference. The old packet, APK and runtime are immutable.

The original fixture's `focus()` only requests focus and waits for idle. It neither establishes keyboard mode nor records `isFocusable()`, `isFocusableInTouchMode()`, `isInTouchMode()`, the case-40 ancestor focusability or its actual focus owner. Reset recreates the views, but does not establish a different system input mode. The two scroll cases use window input injection; the later activation keys call the individual toggle's `dispatchKeyEvent()` directly. The frozen product candidate inherits Switch focus policy and does not override `requestFocus()` or set touch-mode focusability. These source facts make lingering touch mode plausible; they do not prove the runtime cause.

Android documents that screen interaction enters touch mode and directional input leaves it; only views allowing touch-mode focus can take focus while that mode is active. Its request-focus contract also depends on focusability, visibility and ancestors that block descendant focus. These conditions must be observed independently. [Android input events](https://developer.android.com/develop/ui/views/touch-and-input/input-events#TouchMode), [ViewGroup focus contract](https://developer.android.com/reference/android/view/ViewGroup#requestFocus(int,%20android.graphics.Rect)).

Root selected a fresh private fixture that sends exactly one `KEYCODE_DPAD_DOWN` DOWN/UP pair using the public `Instrumentation.sendKeySync()` window route before each of the four existing focus helpers. The fixture waits for native idle and requires observed non-touch mode with no proposal, acknowledgement, pressed state or checked-value change. It then requests focus on an ordinary platform Button sibling as a positive control, removes that owned control, and runs the original toggle focus assertion. The single `requestFocus()` result is stored and recorded before the original `require(admitted,"native focus admitted")`; this is the same predicate and one call, with evidence retained before failure. No production view flags are changed. [Instrumentation key injection](https://developer.android.com/reference/android/app/Instrumentation#sendKeySync(android.view.KeyEvent)).

The fixture records focusability, touch mode, attachment, visibility, window focus, enabled/input gate, view and visible geometry, ancestor descendant-focusability and actual native focus owners before each setup assertion and after the toggle focus request. An observation-only Activity key hook records actual delivery, and a public touch-mode listener records window transitions. The Button is removed in `finally`, including failed setup. Five assertions per helper are classified separately from the six existing scroll assertions; injected setup keys remain separate from the unchanged MotionEvent counter.

The framework can consume the navigation DOWN while leaving touch mode and selecting focus, before Activity dispatch. Consequently, the final candidate requires a matching native Activity UP and permits an absent Activity DOWN only with observed initial touch mode and an actual window transition to non-touch mode. Both sent keys remain exported separately. A missing DOWN does not establish framework consumption by itself. The first host-built candidate's stricter Activity-DOWN requirement was superseded before any runtime. [Official Android framework source](https://android.googlesource.com/platform/frameworks/base/+/master/core/java/android/view/ViewRootImpl.java), [public mode-change listener](https://developer.android.com/reference/android/view/ViewTreeObserver.OnTouchModeChangeListener).

`Instrumentation.setInTouchMode()` is a public setup API, but Android 13+ requires the originating instrumentation process to have the internal `MODIFY_TOUCH_MODE_STATE` permission. The selected candidate exercises ordinary navigation input and verifies the resulting mode instead of depending on that permission. [Instrumentation touch-mode API](https://developer.android.com/reference/android/app/Instrumentation#setInTouchMode(boolean)).

All 45 original case bodies, original predicates, original scroll injection actions/coordinates/timestamps/schedule, 159 production classes and 18 native libraries must remain intact. Host controls and an exact class/DEX replay qualify only this fixture candidate. A fresh root-owned native run must still pass all 45 original cases and all setup controls. Physical phones, TalkBack, renderer/engine authority, Apple parity, published FieldLog packages and GA gates remain pending.

The selected build is `supplement-3`; `host-2` repeats exact fixture class/DEX output and checks the private APK signature, alignment and packaging. The finite oracle preserves every original export rule, projects out the explicit setup fields and applies the original assertion minimum to `originalAssertionCounter`. Complete acceptance requires six scroll checks, twenty keyboard checks, eight separately counted setup keys, all 32 focus observations, finite matching native key/mode evidence, and all 45 original outcomes. Partial counters are bounded and summed, but a failed native status always fails. Host controls explicitly reject the actual retained failed export after repairing its two-key schema.

Read-only host packet review:

```sh
python3 -B verification/android-toggle-keyboard-fixture-diagnosis/check.py
```

After reviewing the frozen packet, root can dispatch its one fresh bounded runtime:

```sh
JAVA_HOME=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home \
  python3 -B verification/android-toggle-keyboard-fixture-diagnosis/run.py \
  --build candidate-3 --attempt runtime-1 --execute-native
```

The wrapper changes package, fixture closure and result label in the sealed reset runner, and selects the finite new component-export oracle. Its failure, diagnostic, owned-emulator and extraction cleanup tail is exact. Without `--execute-native`, it refuses dispatch before creating a runtime directory. Preparation ran no adb, emulator, CUA, physical-device or Git commands. Runtime outputs are excluded from the finite host seal and require a separate root review.
