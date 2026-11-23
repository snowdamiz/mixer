# Android accessibility observation policy

`NativeEnvironmentV2.Observer.forCompose` reads the environment of an attached, Activity-owned `FrameLayout` outside the Compose view. UP4 applies these inputs when it renders the shared theme. The public View host continues to use its API 36 observer and strict appearance admission.

## API matrix

`KNOWN` means a supported read returned a defined value. A missing or invalid required value is `UNDEFINED`. An exception from a supported read is `READ_FAILED`. The Compose observer refuses a new environment in either case and preserves the original exception for `READ_FAILED`. The host waits for a valid environment before its next presentation. A valid configuration may explicitly report `FONT_WEIGHT_ADJUSTMENT_UNDEFINED`. Compose records it as `UNSET_PREFERENCE` and uses the shared typography weights. An observation that is unavailable by API level has the fallback below.

| API | Required window and text scale | Exact bars and cutout | Font weight adjustment | Effective animator scale | System contrast | High-contrast text |
| --- | --- | --- | --- | --- | --- | --- |
| 28–29 | Known | Unavailable semantics | Unavailable API | Unavailable API | Unavailable API | Unavailable API |
| 30 | Known | Known | Unavailable API | Unavailable API | Unavailable API | Unavailable API |
| 31–32 | Known | Known | Known | Unavailable API | Unavailable API | Unavailable API |
| 33 | Known | Known | Known | Known | Unavailable API | Unavailable API |
| 34–35 | Known | Known | Known | Known | Known | Unavailable API |
| 36 and later | Known | Known | Known | Known | Known | Known |

| Observation | Known behavior | Fallback when unavailable | Change source |
| --- | --- | --- | --- |
| Root frame, density, locale, direction, light or dark | Use the live viewport, density, locale, direction, and theme scheme. | Required on every supported API. | The observer owns root attachment, layout, and window focus listeners. The Activity owns configuration delivery. |
| Body text scale | Map Android's effective 17sp conversion to the nearest shared typography profile. Compose uses the resulting metrics once and reflows text with that profile. | Required on every supported API. | Activity configuration callback, with a fresh read of display metrics. |
| System bars and display cutout | Intersect the union of the root window's typed bars and cutout with the host container. Convert to logical leading and trailing edges and apply the inset once. | Keep decor fitting enabled on API 28–29. Use the system-fitted content frame with zero additional safe-area padding. | Root inset callback on API 30 and later. Layout, focus, and attachment track the system-fitted root on API 28–29. |
| Font weight adjustment | Add the signed adjustment to each shared text role's weight and clamp to 1–1000. A positive adjustment sets `boldText`. | Use the shared typography weights. | Activity configuration callback. |
| Effective animator scale | Zero suppresses nonessential motion. A positive scale leaves motion enabled and Compose applies Android's scale once. | Suppress nonessential motion. | `ValueAnimator` duration-scale listener, delivered on the main thread. |
| System contrast | A positive value selects the increased-contrast palette. Zero or a negative value keeps the base palette unless high-contrast text selects the increased palette. | Use the other contrast observation when available. Use the base palette if neither observation selects the increased palette. | `UiModeManager` contrast listener on the main executor. |
| High-contrast text | Enabled selects the increased-contrast palette even if system contrast is neutral or negative. Disabled leaves the palette to system contrast. | Use the system contrast observation when available. | `AccessibilityManager` high-contrast text listener on the main executor. |

The observer uses an exclusive inset-listener slot on API 30 and later. The host container is separate from the Compose view's inset listener. The host owns IME handling. On detach, close the observer before replacing its container. Close retires the observer before removing the exact registrations it acquired. Late callbacks have no effect. The observation generation changes on invalidation. The Compose host reads again before presenting a prepared frame and checks that the environment still applies.

[Font weight adjustment](https://developer.android.com/reference/android/content/res/Configuration#fontWeightAdjustment), [system contrast](https://developer.android.com/reference/android/app/UiModeManager#getContrast()), [high-contrast text](https://developer.android.com/reference/android/view/accessibility/AccessibilityManager#isHighContrastTextEnabled()).

## Increased contrast and bold text

The increased-contrast palette uses the shared theme's light or dark scheme and retains the same sizes, spacing, and semantic roles. Keep a semantic color pair if it reaches 7:1 for text against its actual backdrop or 3:1 for active control boundaries and focus indicators against adjacent colors. When a pair misses its floor, use opaque black on white in light mode or white on black in dark mode for that component. Preserve focus and pressed distinctions with shared outlines or other visible shape changes. Evaluate the final composited colors in each control state.

Bold text applies the weight adjustment to labels, titles, controls, editable text, and placeholders. The family, type size profile, and role hierarchy remain shared. Resolve the weight once. Pass the base weight to a Compose font resolver that already applies the captured platform adjustment. Refresh that resolver when the adjustment changes. A resolver without automatic adjustment uses the computed weight. The [AndroidX resolver installs the platform weight interceptor](https://github.com/androidx/androidx/blob/androidx-main/compose/ui/ui-text/src/androidMain/kotlin/androidx/compose/ui/text/font/FontFamilyResolver.android.kt).

## Observation probe

The probe launches a blank Activity and runs the production Compose observer. It checks the startup API matrix, configuration changes, motion and contrast transitions on supported images, and listener removal and replacement. It saves and restores the changed settings. Use a fresh disposable emulator because instrumentation interruption can prevent restoration. The probe covers observation and policy selection. UP4 owns rendering and screenshot verification.

On API 28 the probe confirms foreground user 0 before touching settings and uses unqualified commands for the system user. Android 9 rejects `--user` on `settings delete`. The newer matrix images use `--user current` for each operation. [Android 9 Settings service](https://android.googlesource.com/platform/frameworks/base/+/android-9.0.0_r1/packages/SettingsProvider/src/com/android/providers/settings/SettingsService.java#259), [Android 15 Settings service](https://android.googlesource.com/platform/frameworks/base/+/android-15.0.0_r1/packages/SettingsProvider/src/com/android/providers/settings/SettingsService.java#254).

Build the probe from the repository root with JDK 25, the Android 37.0 platform, and build-tools 37.0.0. Pass a fresh output directory.

```sh
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export JAVA_HOME=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home
mkdir -p verification/local/up2-root
sh native/android/tests/environment-observation-probe/build.sh \
  verification/local/up2-root/build
```

Run on one root-owned disposable ARM64 AVD at a time. The matrix uses these SDK packages.

| API | System image package |
| --- | --- |
| 28 | `system-images;android-28;default;arm64-v8a` |
| 35 | `system-images;android-35;google_apis;arm64-v8a` |
| 36 | `system-images;android-36;google_apis;arm64-v8a` |
| 37 | `system-images;android-37.0;google_apis;arm64-v8a` |

After boot, set `owned_adb_port` and `owned_serial` to the exact private server port and emulator serial for the current run. Confirm the expected SDK and a completed boot. Use a 90-second outer deadline for instrumentation and keep the output for each API.

```sh
adb="$ANDROID_HOME/platform-tools/adb"
"$adb" -P "$owned_adb_port" -s "$owned_serial" shell getprop ro.build.version.sdk
"$adb" -P "$owned_adb_port" -s "$owned_serial" shell getprop sys.boot_completed
"$adb" -P "$owned_adb_port" -s "$owned_serial" install verification/local/up2-root/build/probe.apk
"$adb" -P "$owned_adb_port" -s "$owned_serial" shell am instrument -w -r \
  dev.mixer.android.environmentprobe/dev.mixer.android.EnvironmentObservationProbe
```

A pass includes the expected `api`, `status=passed`, the applicable transitions, `settings restored`, and `INSTRUMENTATION_CODE: -1`. The `settings_restore` result records each restore command, its stdout, the saved value, and the exact `settings get` readback. An originally absent setting requires a valid delete acknowledgement and a `null` readback. A saved numeric value must read back exactly as saved. A command acknowledgement or readback mismatch fails the probe and includes those fields in the failure. Record the image revision and exact serial with the output.

On the original API 36 Google APIs ARM64 run, the replacement observer saw `font_scale=1.0` and then timed out waiting for `font_weight_adjustment=0`. The diagnostic probe keeps that ordering and the five-second observation deadline. The probe requires a Settings value different from the target before each transition. A transition still requires both a new observer invalidation and the expected Compose environment.

Android Settings writes `300` for bold text on and `0` for off. Android 16's activity task manager observes the secure setting on a handler and can skip a configuration update if the global adjustment already equals the requested value. A successful `settings get` readback establishes the stored value. The Activity callback and its resource configuration establish app delivery. [Android 16 Settings toggle](https://android.googlesource.com/platform/packages/apps/Settings/+/refs/heads/android16-release/src/com/android/settings/accessibility/FontWeightAdjustmentPreferenceController.java#53), [Android 16 activity task manager](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android16-release/services/core/java/com/android/server/wm/ActivityTaskManagerService.java#5064).

Keep `transition_observations` and `failure` from the same instrumentation result. The probe records the starting Settings text and the Activity's raw font scale and weight adjustment on both sides of each transition. It records the last `Activity.onConfigurationChanged` payload and counts observer invalidations that came through `Observer.onConfigurationChanged`. On timeout it reads the setting again and reports the Compose environment and predicate result.

| Timeout evidence for `font_weight_adjustment=0` | What it establishes |
| --- | --- |
| `settingsAtTimeout` differs from `0` after an acknowledged write | The stored preference changed again before the timeout read. |
| Settings reads `0` and the Activity's raw adjustment stays at `300` | The Activity resources have yet to reflect the preference. |
| The raw adjustment reaches `0` and the Activity reports that configuration, with no new observer configuration invalidation | The probe saw Activity delivery. Inspect the observer's registered callback path. |
| A configuration invalidation arrives and the raw adjustment reaches `0`, but the Compose predicate remains false | The failure is in the observer's read or policy path. |

After a settled run, uninstall the probe and request shutdown on the exact owned serial.

```sh
"$adb" -P "$owned_adb_port" -s "$owned_serial" uninstall dev.mixer.android.environmentprobe
"$adb" -P "$owned_adb_port" -s "$owned_serial" emu kill
```

Reap the owned emulator before stopping its private ADB server with `"$adb" -P "$owned_adb_port" kill-server`. Delete the verified disposable AVD and its scratch after both processes settle. Preserve resources with unresolved custody.
