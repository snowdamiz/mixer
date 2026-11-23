# Replay S4 feature ownership on macOS

Run from the Mixer checkout on arm64 macOS with Xcode 27.2. Set `S4_RUSTC`
to an absolute path to Rust 1.99.0 with its matching `llvm-tools` component.
Use a fresh directory under `verification/local/`.

```sh
s4="$PWD/verification/local/s4-b-prime-replay"
mkdir -p verification/local
mkdir "$s4"
mkdir "$s4/tmp" "$s4/swift-cache" "$s4/swift-config" "$s4/swift-security"
python3 -B experimental-capability-runtime/build-vm.py \
  --revision e12a6856335a133555f03829758e3cc99feef99c \
  --target host --rustc "$S4_RUSTC" --output "$s4/engine"
TMPDIR="$s4/tmp" CLANG_MODULE_CACHE_PATH="$s4/clang-cache" \
  SWIFTPM_MODULECACHE_OVERRIDE="$s4/manifest-module-cache" \
  swift test --package-path capability-activation \
  --scratch-path "$s4/swift-build" --cache-path "$s4/swift-cache" \
  --config-path "$s4/swift-config" --security-path "$s4/swift-security" \
  --only-use-versions-from-resolved-file --no-parallel \
  --filter S4FeatureOwnershipTests \
  -Xcc "-I$s4/engine/include" -Xlinker "-L$s4/engine/lib"
```

The test opens seven successive owners through `CapabilityGuestUIRuntime.open`.
It stages development-signed documents and Wasm through the public download
methods. The VM runs the guest. The test compares sorted JSON encodings of
documents admitted by `MixerUIHost` with independently constructed bundled
documents. It verifies the durable storage bytes after the baseline save, the
failed first frames, and signed rollback followed by an offline owner reopen.
A callback from the retired baseline cannot reach the new owner, even when its
revision and action ID match the new frame.

The macOS test calls the internal display ticket acknowledgment after a
validated frame. It creates no window. On the failure control it claims a
second attachment before acknowledging the first frame and requires
`recoveryRequired` with the prior healthy candidate preserved. The original
host replay logged `inputEnabled=true` before acknowledgment. An iOS 26.5
test with the native receipt held reproduced a committed Save. The corrected
host and Simulator controls require the first display receipt before routing
input. [Native results](../../../verification/receipts/ui-platform-pivot-s4-native-20261123.json)
The S4 test reopens the runtime and store within one XCTest process. The
fixture uses ABI 2, a hand-authored Wasm program, and typed Swift documents.

## Root iOS handoff

Keep S4 pending. The separate Simulator theme fixture applies a fixed light
theme through an experimental `MixerNativeView` adapter. The macOS test has
no iOS app or UI test target. Its document
comparison covers the current wire and host, with `MixerSwiftUI` document
generation still pending.

For native execution, use an app scene with one `MixerGuestScreen` per
`CapabilityGuestUIRuntime` owner. The app can build on the existing FieldLog
signed route. Render the bundled document with `MixerNativeView` in the
`.nativeFallback` case. Use the public signed download methods and the real
native display probe for guest health. Reproduce the two first-frame failures
separately. An invalid startup header must leave effects closed. A failure
after effects intent must require owner close and cold reopen. On the first
usable guest frame, verify exactly when input becomes reachable relative to
the native display acknowledgment. Relaunch the app process without a
delivery endpoint, confirm the saved bytes and signed rollback selection,
and compare the bundled and guest documents and rendered shared theme.
[Existing FieldLog signed iOS preparation, root command, and cleanup](../fieldlog-ios/README.md)

The existing FieldLog selector
`FieldLogUITests/FieldLogSignedOTATests/testSignedBaselineReviewRollbackAndOfflineReopen`
can exercise the real display probe, delivery, rollback, and offline
process relaunch on its own fixture. To run that control, prepare a fresh
build with the linked guide and use an already booted root-owned Simulator
after the required preflight.

```sh
python3 -B capability-activation/verification/fieldlog-ios/run.py \
  "$FIELDLOG_BUILD" "$S4_ROOT_EVIDENCE/fieldlog-control" \
  --device "$OWNED_SIMULATOR_UDID"
```

S4 still needs native bundled fallback, first-frame failure, stale input, and
shared-theme evidence in the same app.
