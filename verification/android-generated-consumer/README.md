# Generated Android consumer verification

Run `python3 verification/android-generated-consumer/verify.py` from this repository.
It uses only installed official Swift/Android/NDK/JDK tools and the owned CLI,
SDK, renderer and JNI implementation. It never discovers, signs, installs, launches
or queries a device. Generated projects and APKs remain under ignored
`verification/local/`; text logs and receipts are retained here.

The CLI supports:

```sh
swift build --package-path cli
cli/.build/debug/mixer create MyApp --platform android --directory /tmp/MyApp
cli/.build/debug/mixer test --directory /tmp/MyApp
swift test --package-path /tmp/MyApp/Platforms/Android
cli/.build/debug/mixer build --platform android --directory /tmp/MyApp
```

`--platform android` creates both the existing iOS starter and an Android host.
Creation without that option retains the iOS starter and truthfully declares only
its generated iOS host. Both use the generated AppModels/AppFeatures source package.
Android's draft/add/toggle document and reducer live in shared AppFeatures; the
existing iOS starter retains its read-only `document(entries:revision:)` surface.

`--android-adapter-path` (or `MIXER_ANDROID_ADAPTER_PATH`) identifies the owned
Android source distribution. Creation copies its exact Java renderer, JNI C/header,
profile and reusable Swift runtime into a source-locked Generated/MixerAndroid
package. It excludes the repository's ChecklistEngine/example instrumentation.
A custom source path receives the same immutable lock. Generated native platform
files are app-owned; build compiles their edits without regenerating them.

Configure installed tool paths with MIXER_SWIFT, MIXER_SWIFT_SDKS_PATH,
MIXER_ANDROID_ARTIFACT_PATH, MIXER_JDK and ANDROID_HOME before creation. The
supported local tool combination is Swift 6.3.3, its official Android SDK/NDK r27d,
arm64/API28, Android platform37.0/build-tools37.0.0, JDK25 and Python3. Creation locks
versions, tool hashes, metadata and complete Swift/JDK/Android distribution trees;
build refuses drift. Nothing is downloaded. Android packaging uses owned Python
stdlib code and platform aapt2/d8/zipalign/Clang tools; no Gradle plugin is used.
Directory symlinks in installed distributions must resolve within the hashed root.
The direct exported driver validates application names and configuration before
deriving or removing output paths. A before/after source digest and rechecked SDK/
adapter locks reject observed concurrent changes. This detects local mutation;
it does not create immutable inputs, an isolated build sandbox or an attestation.

Runtime state must preserve value semantics without shared mutable references.
Factory/render/reducer callbacks run synchronously under a non-reentrant registry
lock and must not perform I/O, asynchronous work or external side effects.
Sendable alone does not make arbitrary reference graphs/effects transactional.

The executable evidence covers:

- Shared Swift draft/add/toggle state and original-source compiler diagnostics.
- Application-owned C session dispatch with stale/oversized/duplicate-key rejection,
  bounded handles, destruction and no commit when the output buffer is too small.
- The unchanged Java wire validator, actual arm64 Swift/JNI cross-compilation,
  complete native-library dependency closure, aapt2 identity/activity/ABI inspection,
  dex class inspection and AppModels/AppFeatures/C ABI symbol inspection.
- SDK/adapter/toolchain drift rejection, explicit rejection of unsupported native
  capabilities and resources, and no success after an actual Swift compiler error.
- Distribution-directory symlink escape rejection, direct-driver path-name safety,
  and observed concurrent-source-mutation rejection with the final APK removed.
- An edited shared feature appearing in a rebuilt native library while app-owned
  manifest and native entry edits survive. Export preserves locked source snapshots;
  the exported shared package passes host tests.
- The existing unsigned iOS Simulator build still compiles; no simulator is launched.

`receipt.json` identifies the exact implementation input tree, commands, versions,
outputs, APK hashes and limitations. Build receipts include per-APK-entry hashes,
a normalized content digest, complete native library hashes/dependencies and the
compiler/Java/packaging/inspection command outputs. The source revision before the
run is recorded alongside a manifest of the actual source tree under verification.

These are local source-consumer and cross-build receipts. The APK is unsigned and
has no installability or device-behavior claim. Phones remain disconnected. Physical
iOS/Android, lifecycle/process restoration/persistence, IME/accessibility, performance,
resource/capability hosts, clean-machine/independent CI export, published immutable
package consumption from a separate FieldLog repository, signing, store acceptance,
independent review and GA remain pending.
