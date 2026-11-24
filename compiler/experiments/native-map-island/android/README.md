# Replay the FieldLog map on the Android fixture

From the repository root, run the replay on macOS.

```sh
python3 compiler/experiments/native-map-island/android/replay.py
```

Use Python 3.12 or later, Xcode 26.6, Swift 6.3.3 with the Android SDK and NDK r27d,
OpenJDK 25, Android platform 37.1, and build tools 37.0.0. The script reads Kotlin
2.3.0 and Compose 1.11.2 from the local Gradle dependency cache. See `--help` for
tool path overrides.

The script builds the exporter from commit `b69525316a` and signs 32 cases
with that source revision. To replay the exact bytes from a previous run,
pass its `android-vectors.json` with `--vectors`. Use an export you trust.
Retained vectors may carry `c618cb7093` because the map experiment and `updates`
trees are identical at both revisions. The receipt records the exporter build
commit and the source revision in the signed mount and move manifests.

The exporter generates a new signing key each run. The build pins its public
key in both Swift libraries before the JVM submits any manifest or payload.
The Android fixture fixes the test clock at 100.

Open `receipt.json` and `host-replay.log` in the printed output directory. The
macOS JVM submits the original signed bytes through the same JNI bridge and
Swift source used in the Android build. The test checks both accepted slots,
coordinates, styles, and the retained node and provider. For each acceptance
it compares the installed grant and the authenticated release and payload
digests. All 30 refusals preserve the expected provider count and mounted frame.
Two additional cases check the JNI size limits.

## Load the fixture in a private Compose host

Use the generated `GC3ComposeFixture.aar` in an unminified arm64-v8a Android
test app with minimum API 28. Include Compose Foundation 1.11.2 and Kotlin
stdlib 2.3.0. The AAR contains the Swift admission library, the JNI bridge, the
native dependency closure, the Compose classes, and the signed cases.

Read the packaged asset before composing the fixture.

```kotlin
val cases = assets.open("gc3/signed-cases.tsv").use(::readSignedMapCases)
setContent { SignedMapFixture(cases) }
```

Use **Apply next signed case** to submit each case in order. The offline surface
draws the accepted coordinate and style below or above **Site details**.
The screen shows the refusal code for denied cases. The map keeps the last
accepted coordinate, style, and position.

The host replay covers admission and typed map state. The Android evidence
covers the arm64 API 28 library build, JNI link, Compose compilation, and API
28 DEX generation. Android execution, rendering on a device, and product
schema integration are pending.
