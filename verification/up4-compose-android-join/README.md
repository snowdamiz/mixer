# Run the UP4 Swift and Compose runtime fixture

Run the host replay on macOS with Xcode and JDK 25. It reads its Kotlin 2.3.0
compiler and JVM dependencies, including `org.json:json:20251224`, from the
Gradle cache. Set `MIXER_GRADLE_SEED` to use a different cache.

```sh
python3 verification/up4-compose-android-join/build.py \
    verification/local/up4-host-join --mode host
```

Use a fresh output directory for each run. The script projects the renderer and
Swift SDK source from the checked-out commit. The receipt records the source
revision, Git object IDs, commands, output paths, and process observations.
A host pass prints five `PASS` lines and records `result: PASS`. The replay
simulates draws and runs the original S5 JNI transport from
`18fef233e694ad9613a7427c81bdc89e9bc062dc`. The transport lives with this
verification fixture.

## Build the signed fixture

To build and inspect the arm64 API 28 APKs, use `--mode apk` with Swift 6.3.3
and its Android SDK, Gradle 9.8.1, Android SDK Platform 37.1 revision 1, and
Build Tools 37.0.0. Use `verification/local/up4-runtime-join` as the output
directory for the commands below. The build adds the runtime activity,
instrumentation, and JNI linkage to the disposable renderer projection.

The app loads the existing S5 JNI symbols and renders documents produced by
Swift through `ComposeDocumentHost`. The fixture frames the exact new receipt
and an optional cross-owner old receipt inside S5's 8,192-byte buffer.
Documents, identity generations, and input envelopes come from the SDK
protocol. The Swift executor checks the old receipt, acknowledges the new
receipt, and retires the old owner before returning success. The Boolean
returned to the renderer represents route admission. The fixture records the
handler result separately.

## Run the signed pair on the root-owned emulator

Use one owned arm64 API 28 emulator and its private ADB server. Check the SDK
and ABI before installing the pair. Set `owned_adb_port` and `owned_serial` from
the root launch receipt.

```sh
adb="$ANDROID_HOME/platform-tools/adb"
signed="$PWD/verification/local/up4-runtime-join/signed"
"$adb" -P "$owned_adb_port" -s "$owned_serial" shell getprop ro.build.version.sdk
"$adb" -P "$owned_adb_port" -s "$owned_serial" shell getprop ro.product.cpu.abi
"$adb" -P "$owned_adb_port" -s "$owned_serial" install "$signed/MixerComposeHost-debug.apk"
"$adb" -P "$owned_adb_port" -s "$owned_serial" install "$signed/MixerComposeHost-debug-androidTest.apk"
"$adb" -P "$owned_adb_port" -s "$owned_serial" shell am instrument -w -r \
    dev.mixer.compose.up4.test/dev.mixer.compose.RuntimeSmoke
```

Run instrumentation with a 90-second external deadline. A pass prints
`PASS UP4 API 28 Swift/Kotlin Compose runtime join` and
`INSTRUMENTATION_CODE: -1`. The runner checks a vetoed window draw while
Compose forwards an edit from its `InputConnection`, a Save with an admitted
handler error, a refused owner replacement, exact retirement, and visible
draft and Save readbacks produced by Swift. It uses a bundled Swift
producer. Signed guest activation remains a separate product integration check.
