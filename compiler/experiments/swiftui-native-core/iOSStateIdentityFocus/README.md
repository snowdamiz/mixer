# GC4 iOS state, identity, and focus differential

One UI test launches the same app twice. The first launch shows
`SharedScreen.swift` in Apple SwiftUI. The second shows the feature compiled
with `SwiftUI=MixerSwiftUI` through the public `MixerBundledFeatureMount.view()`.
The app shell imports Apple SwiftUI on both launches. Only the feature's
Mixer build receives the alias.

The test increments a counter, moves keyed siblings, and checks their visual
order and counters before and after the move. It taps the native text field
once, requires the software keyboard, and types `abc` and `def` in separate
batches. The second batch requires the field to retain keyboard focus.
The test compares the native field value with the rendered draft after each
batch. A separate button copies the accepted draft into a readback label.

Both launches must satisfy their assertions and produce the same eight
checkpoints. The traces preserve the observed row order, displayed text, raw
field value and placeholder, field count, and keyboard visibility. The test
also attaches the final screen and accessibility tree for each launch.
Programmatic focus via `@FocusState` is outside the shared subset. This replay
exercises native user focus acquired by tapping and retained while editing.

## Build for a generic iOS Simulator

From the checkout root, use Xcode and Ruby with the `xcodeproj` gem.

```sh
fixture=compiler/experiments/swiftui-native-core/iOSStateIdentityFocus
mkdir -p verification/local
build=$(mktemp -d "$PWD/verification/local/gc4-native.XXXXXXXX")
bash "$fixture/build.sh" "$build" > "$build/build-driver.log" 2>&1
bash compiler/experiments/swiftui-native-core/HostReplay/run.sh debug > "$build/host-replay.log" 2>&1
```

The generic build links the checked-out SDK sources. It compiles the same
authored file twice for arm64 Simulator with an iOS 17.0 deployment target.
`Products/` contains the generated xctestrun, the signed app, and the signed
UI test runner and bundle. `product-identity.log` records the xctestrun
SHA-256, bundle signature details, executable hashes, and deployment target.
`input-sha256.txt`, `toolchain.log`, `dual-compile.log`, `build-command.txt`,
`build.log`, and `build.xcresult` record the inputs and build.

## Run one native pair

Root runs the repository Accessibility preflight and selects an already
booted, owned iOS 26.5 iPhone Simulator with its software keyboard enabled.
Keep the complete `Products/` layout together. Set `xctestrun` to its exact
generated file and `owned_uuid` to the selected device UUID.

```sh
run=$(mktemp -d "$PWD/verification/local/gc4-replay.XXXXXXXX")
mkdir "$run/tmp"
TMPDIR="$run/tmp/" xcodebuild test-without-building -xctestrun "$xctestrun" \
  -destination "platform=iOS Simulator,id=$owned_uuid" \
  -only-testing:GC4DifferentialUITests/DifferentialUITests/testStateIdentityFocus \
  -destination-timeout 15 -parallel-testing-enabled NO \
  -test-timeouts-enabled YES -maximum-test-execution-time-allowance 240 \
  -resultBundlePath "$run/differential.xcresult" > "$run/xcodebuild.log" 2>&1
xcrun xcresulttool get test-results summary --path "$run/differential.xcresult" > "$run/summary.json"
xcrun xcresulttool export attachments --path "$run/differential.xcresult" --output-path "$run/attachments"
```

Verify that the summary records exactly one passed test on the selected UUID
and OS. Use the attachment manifest to find both `GC4 … trace` JSON files.
The test checks their equality in-process. On failure, preserve both traces
and the final screens and trees for diagnosis. Record the source and
xctestrun digests, outcome, and owned-device cleanup in the root receipt.

For the `AnyView` lifetime comparison, use
`GC4DifferentialUITests/DifferentialUITests/testErasedTypeLifetime` as the
selector. Each mode records six visible counter values. Updating a label
keeps the counter at the same value. Switching the wrapped concrete type
resets it, including when the same explicit key appears inside both types.
