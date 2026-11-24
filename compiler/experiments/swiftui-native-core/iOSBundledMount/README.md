# Build and replay the UP5 iOS bundled starter

The starter uses the same `StarterFeature.swift` in both compile checks. The
bundled app links the build where `import SwiftUI` resolves to
`MixerSwiftUI`. The app shell imports Apple SwiftUI and displays the bundled
feature through `MixerBundledFeatureMount` and `MixerNativeView`.

## Build for a generic iOS Simulator

Use Xcode and the Ruby `xcodeproj` gem from the Mixer checkout root. The build
links checked-out SDK sources and produces ad hoc signed arm64 test products
with an iOS 17.0 deployment target.

```sh
mkdir -p verification/local
build=$(mktemp -d "$PWD/verification/local/up5-bundled-mount.XXXXXXXX")
fixture=compiler/experiments/swiftui-native-core/iOSBundledMount
bash "$fixture/build.sh" "$build" > "$build/build.log" 2>&1
```

The SDK package integration adds `MixerSwiftUI` to the `MixerApple` target's
dependencies in both manifests. The fixture builds the same module boundary
with `swiftc` so it can keep the alias local to the starter and use a separate
integration patch for the manifests.

## Replay on the owned Simulator

Root runs the generated `UP5Bundled_*.xctestrun` on an already booted, owned
Simulator after the repository Accessibility preflight.

```sh
xcodebuild test-without-building -xctestrun "$xctestrun" \
  -destination "platform=iOS Simulator,id=$owned_uuid" \
  -parallel-testing-enabled NO -resultBundlePath "$root_result"
```

`BundledUITests.testNativeStarter` waits for the actual native display receipt,
taps the button, types into the text field, and closes the feature. The hosted
`BundledMountTests` explicitly deliver receipts to control timing. They exercise
pre-display input, replays, foreign native surfaces, stale and mismatched display
receipts, and cancellation with a display outstanding.
