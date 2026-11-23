# S1 SwiftUI module naming

The fixture recompiles one shared feature that imports `SwiftUI` and uses `SwiftUI.Text` in its public return type and implementation. Its engine imports a second source-built target, `TitleSupport`. The Apple shell declares an Apple `SwiftUI.App` and passes the shared feature's result into Apple `SwiftUI.Text`.

## Replay the compiler build and export

From the repository root, run this command on macOS arm64.

```sh
python3 compiler/experiments/swiftui-module-naming/replay.py
```

The replay uses the installed Swift 6.3.3 Android and full-Swift WASI SDKs from the [release toolchain manifest](../../../release/toolchain-candidate.json). It uses Xcode 26.6 for the cross-compiler's host tools and Node to run WASI Preview 1. The Apple build was tested with Xcode 27.2 (27B52). Use `--apple-xcode /path/to/Xcode.app` to select the Apple toolchain per invocation. The release manifest names Xcode 27.1 (27A9275).

The runner builds the local CLI, places the fixture in a fresh stock project, and invokes `mixer export`. It checks that the exported Swift sources match the originals and rebuilds Android, WASI, and iOS after deleting the original project. The exported fixture rebuilds through the compiler commands in the replay. Wiring the equivalent target settings into the stock project generator belongs to UP5.

On Android and WASI the engine compiles as `SwiftUI`. The replay checks that the arm64 Android API 28 build links a `SwiftUI.Text` symbol and that both WASI builds print `Mixer: S1`. On iOS it compiles the engine as `MixerSwiftUI` and applies `-module-alias SwiftUI=MixerSwiftUI` to the engine and feature invocations. The Apple shell uses the SDK's `SwiftUI`. Dependency scans check module paths, including the local engine dependency and the Apple Swift interface. The iOS binary checks verify the iOS 17.0 load command, the Apple SwiftUI framework link, and symbol references for both `Text` types.

The runner prints the receipt path under `verification/local/`. `commands.jsonl` records exact commands and process outcomes. `result.json` records tool versions, SDK metadata hashes, source hashes, dependency resolution, and binary checks. It removes its own build directories after settled runs. A command with unverified custody produces `HOLD.json` and retains its scratch.

## Reproduce SwiftPM's alias propagation

The initial SwiftPM build on Xcode 27.2 passed the product-edge alias to the consuming `AppleShell` target. The shell's references to `SwiftUI.App`, `SwiftUI.Scene`, and `SwiftUI.WindowGroup` resolved against `MixerSwiftUI` and failed. Use target-level compiler settings for the iOS feature when integrating the passing configuration. The scoped compiler flag follows the frontend design in [SE-0339](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0339-module-aliasing-for-disambiguation.md).

```sh
mkdir -p verification/local
s1_run=$(mktemp -d "$PWD/verification/local/s1-swiftpm-ios.XXXXXXXX")
mkdir "$s1_run/tmp"
export TMPDIR="$s1_run/tmp"
export SWIFTPM_MODULECACHE_OVERRIDE="$s1_run/manifest-modules"
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
ios_sdk=$(xcrun --sdk iphoneos --show-sdk-path)
S1_APPLE_ALIAS=1 gtimeout --kill-after=10s 90s xcrun swift build \
  --package-path compiler/experiments/swiftui-module-naming/Fixture \
  --scratch-path "$s1_run/build" --cache-path "$s1_run/cache" \
  --config-path "$s1_run/config" --security-path "$s1_run/security" \
  --disable-index-store --triple arm64-apple-ios17.0 --sdk "$ios_sdk" --verbose \
  > "$s1_run/build.log" 2>&1
```

The initial SwiftPM Android build selected armv7 Swift resources for the requested arm64 triple and failed to load the standard library. The replay reads the arm64 sysroot and resource directory from the exact SDK target entry. The initial SwiftPM WASI build completed with the pinned SDK.

## Scope

This is a host-only naming and link check. Apple and Android runtime acceptance, the release-candidate Apple toolchain, and builds through the future production project generator remain separate. WASI ran under Node, so its result covers naming and linking for a full-Swift WASI command and leaves the owned VM profile to S2.
