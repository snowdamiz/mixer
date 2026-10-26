# Android local development host

`mixer build --platform android` compiles the original shared AppModels/AppFeatures
package, app-owned Sources/AppAndroid entry, and locked owned runtime/Java/JNI.
Output is `.mixer/android-build/*-unsigned.apk`, with a complete build receipt.
The APK is unsigned and has not been installed or qualified on a device.
`swift test --package-path Platforms/Android` exercises this exact app's exported
session ABI on the host. Mac tests do not establish Android UI behavior.

This host uses Android native widgets with the unchanged android-profile-v1
subset. Shared ProjectFeatureState owns draft/add/toggle; the iOS starter uses
the compatible read-only document(entries:) surface. State is process-local.
There is no persistence, process restoration, navigation/back/sheets, native
capabilities, lifecycle/effects, resource copying, production signing, store,
accessibility or performance qualification. Unsupported UI/events fail closed.
The generated JNI closure includes private staged prepare/commit/abort exports;
the Activity still uses legacy exchange and does not opt into V2 rendering.
Runtime state must preserve value semantics without shared mutable references.
Callbacks run synchronously under a non-reentrant lock; they must not perform
I/O, asynchronous work or external side effects. Sendable alone cannot ensure
rollback for arbitrary reference state or effects.
App-owned manifest/package/entry/Java files are compiled as edited; builds never
regenerate them. Put optional Android Java extensions under Java/. Bundled
Generated/MixerAndroid and Generated/MixerSDK inputs are immutable source locks.

Supported installed tools: official Swift6.3.3 Android SDK arm64/API28, NDKr27d,
Android platform37.0/build-tools37.0.0, JDK25 (Java bytecode17), Python3. Tool
paths and complete distribution hashes are locked during creation. Configure
MIXER_SWIFT, MIXER_SWIFT_SDKS_PATH, MIXER_ANDROID_ARTIFACT_PATH, MIXER_JDK and
ANDROID_HOME before creation; builds require those exact distributions.
No tools are downloaded. Published immutable SDK consumption is still pending.
