# UP4 native Compose renderer

This standalone API 28 module renders the ten SDK UIDocument kinds in the V4 Android profile, including horizontal and vertical text fields. It validates the SDK's schema version 1 JSON, preserves Swift node generations, and emits the existing `UIEventEnvelope`. Compose Foundation supplies the native layout, controls, accessibility semantics, and text input.

The module uses the measured shared system-sans typography profiles, light and dark colors, and editor control geometry. It reuses the mounted Compose viewport and editor state when a same-owner update preserves the tree and its editor state. An incompatible viewport gets a provisional surface over the accepted one, so cancellation restores the accepted surface. Lists use keyed lazy rows. A list anywhere beneath another list is refused during preparation, including inside a section or stack. Exact grouped-list geometry, custom theme resources, UP2 contrast and inset integration, signed guest integration, and CLI and worker selection remain pending.

## Build and verify

Use JDK 25, Gradle 9.8.1, Android SDK Platform 37.1 revision 1, and Build Tools 37.0.0. Kotlin 2.3.0, Android Gradle Plugin 9.3.1, Compose BOM 2026.11.01, and Activity 1.13.0 come from the signed S5 fixture at `18fef233e6`. Give the build an owned output directory. It creates a disposable debug signing key there for the smoke APK pair.

```sh
export ANDROID_HOME=/absolute/path/to/android-sdk
export JAVA_HOME=/absolute/path/to/jdk25
compose_work="$PWD/verification/local/up4-compose-build"
native/android/compose/build.sh "$compose_work"
```

The build runs the JVM authority and wire checks, then assembles the debug app and instrumentation APKs under `$compose_work/build/outputs/apk`. On a host with Swift, the SDK wire check can also use canonical bytes emitted by the real Swift SDK.

```sh
native/android/compose/check-swift.sh "$compose_work"
MIXER_COMPOSE_SDK_FIXTURE="$compose_work/swift/sdk-document.json" \
    native/android/compose/build.sh "$compose_work"
```

The buildscript and project lockfiles pin dependency resolution. Gradle verifies the resolved artifacts against `gradle/verification-metadata.xml`. To replay offline, copy `caches/modules-2` from a cache provisioned on the same host platform into `$compose_work/gradle-home/caches`. Use the work directory and debug key from the build above.

```sh
MIXER_COMPOSE_WORK="$compose_work" GRADLE_USER_HOME="$compose_work/gradle-home" \
    ANDROID_USER_HOME="$compose_work/android-user" TMPDIR="$compose_work/tmp" \
    "${MIXER_GRADLE:-gradle}" --offline --no-daemon --no-build-cache --no-watch-fs \
    --project-dir native/android/compose --project-cache-dir "$compose_work/project-cache" \
    "-Pkotlin.project.persistent.dir=$compose_work/kotlin" \
    --dependency-verification strict -Pandroid.builder.sdkDownload=false \
    authorityCheck assembleDebug assembleDebugAndroidTest
```

The AAPT2 entry pins the Linux x86-64 JAR at `e772a3dae8354764f1b0793903218427f483982445207f2e4ffc8c2026755bd4`. The downloaded JAR's SHA-256 matched Google's sidecar. Its POM still hashes to `edb82dcbe738ca78b31612cb307bf99e5f02f25c8125048f933e792fd7778beb`. The locked build ran on macOS arm64. Linux dependency cache provisioning remains unverified. [Google Maven JAR](https://dl.google.com/dl/android/maven2/com/android/tools/build/aapt2/9.3.1-15703166/aapt2-9.3.1-15703166-linux.jar), [SHA-256 sidecar](https://dl.google.com/dl/android/maven2/com/android/tools/build/aapt2/9.3.1-15703166/aapt2-9.3.1-15703166-linux.jar.sha256), [POM](https://dl.google.com/dl/android/maven2/com/android/tools/build/aapt2/9.3.1-15703166/aapt2-9.3.1-15703166.pom).

Run the smoke on one owned API 28 AVD. Set `owned_adb_port` and `owned_serial` to that instance's private ADB server and serial. Supply a 90-second outer deadline for instrumentation.

```sh
adb="$ANDROID_HOME/platform-tools/adb"
app_apk="$compose_work/build/outputs/apk/debug/MixerComposeHost-debug.apk"
instrumentation_apk="$compose_work/build/outputs/apk/androidTest/debug/MixerComposeHost-debug-androidTest.apk"
"$adb" -P "$owned_adb_port" -s "$owned_serial" shell getprop ro.build.version.sdk
"$adb" -P "$owned_adb_port" -s "$owned_serial" shell getprop sys.boot_completed
"$adb" -P "$owned_adb_port" -s "$owned_serial" install "$app_apk"
"$adb" -P "$owned_adb_port" -s "$owned_serial" install "$instrumentation_apk"
"$adb" -P "$owned_adb_port" -s "$owned_serial" shell am instrument -w -r \
    dev.mixer.compose.up4.test/dev.mixer.compose.ComposeSmoke
```

A pass prints `PASS UP4 Compose smoke` and `INSTRUMENTATION_CODE: -1`. The smoke checks a vetoed draw, a refused replacement on a second surface, retained editable Unicode and Save after refusal, stable viewport on the retained Compose view, disabled and revision-bound events, and detach. The smoke uses a debug bridge double. The signed owner and host join is a separate runtime check.

The separate held-input control uses an accessibility Save click and the focused Compose view's Android `InputConnection` for selection, composing text, and editor submit while a candidate is composed and window traversal is vetoed. Build the instrumentation APK with the alternate runner, reinstall the APK, and apply the same outer instrumentation deadline.

```sh
ORG_GRADLE_PROJECT_mixerHeldInputSmoke=true native/android/compose/build.sh "$compose_work"
"$adb" -P "$owned_adb_port" -s "$owned_serial" install -r "$instrumentation_apk"
"$adb" -P "$owned_adb_port" -s "$owned_serial" shell am instrument -w -r \
    dev.mixer.compose.up4.test/dev.mixer.compose.HeldInputSmoke
```

## Swift owner join

Use `@_spi(ComposeHost) import MixerAndroid` and the owner's `AndroidComposePresentation<Outcome>(validator:isOnExecutor:)` on the installed serialized executor. Pass the producer's validator and its existing `UIRenderSnapshot` to `prepare(owner:snapshot:handle:)`. Swift retains the exact snapshot and handler `(UIEventEnvelope, RoutedUIAction) throws -> Outcome`.

1. Associate the owner UUID issued by Swift with one `host.newStageOwner(ownerUUID)` handle. Pass the returned `AndroidComposeFrame.documentUTF8` to `host.prepare` with the original receipt values and generations from `frame.snapshot.identity(for:)` in root-first depth-first order. Pass every Swift `UInt64` as its `Int64(bitPattern:)` JNI `jlong` equivalent. Kotlin compares unsigned values and emits them as unsigned JSON integers. Call `host.present` on the UI thread. If preparation or presentation is refused, cancel the exact proposal in Swift.
2. Retain the Kotlin `PrepareReceipt` object returned by `prepare`. The provisional draw and its controls capture it. The host waits for a draw of the attached Compose content at the current viewport and verifies a per-trial marker in the actual window buffer with PixelCopy before calling `ComposeSwiftBridge.didDraw(receipt, replacing)`. Restore the exact `AndroidComposePrepareReceipt` from the callback object's original `owner`, `sequenceBits`, `documentRevisionBits`, and `opaqueId` and call `acknowledgeDraw(_:)` on the new Swift owner first. If acknowledgment fails, return false and keep the prior Swift snapshot and handlers selected. If acknowledgment succeeds and `replacing` supplies the exact prior receipt from a different owner lifetime, call `retire(owner:)` on that prior Swift owner before returning true. The host exposes candidate input as soon as this call succeeds. The first draw and same-owner updates pass null for `replacing`.
3. During a held same-surface update, an unchanged control can use its captured accepted receipt and node binding. This requires matching generation, enabled state, action IDs, and control properties. An editor may echo the current draft while preserving its selection and composition. Candidate-only or changed controls wait for acknowledgment. Decode `offer` bytes as the existing `UIEventEnvelope` and call `dispatch(_:from:)` with the receipt supplied by the callback. The bridge returns true when dispatch admits the event. Use `Outcome` to carry handler failures if needed so admission remains distinguishable from a failed action. When Swift admits an accepted-frame event and supersedes its pending proposal before running the handler, Kotlin also drops the pending trial. Its later draw and callbacks stay stale.
4. Keep input fenced during a switch between Swift owner lifetimes. Use the fields captured by the receipt on `discard` to call `cancel(_:)` and use the exact accepted receipt on `retire` to retire its Swift owner on detach. Rollback uses a fresh owner lifetime. Bridge calls finish synchronously on the UI thread and never reenter the Kotlin host. Schedule guest work separately.

The receipt fields and node generations are presentation metadata. The document and event JSON use the existing SDK wire. The macOS host replay exercises the Swift receipt API over the S5 fixture transport. [Run the Swift and Compose runtime fixture](../../../verification/up4-compose-android-join/README.md).

The buffer proof uses S5's API 28 PixelCopy approach and a temporary low-contrast marker. The held-input control exercises Android's editor connection directly. A separately installed IME service and signed effects remain outside this control.
