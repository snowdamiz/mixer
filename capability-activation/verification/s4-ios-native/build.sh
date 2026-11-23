#!/bin/sh
set -eu

fixture=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
repo=$(CDPATH= cd -- "$fixture/../../.." && pwd -P)
cd "$repo"
mkdir -p verification/local
work=$(mktemp -d "$repo/verification/local/s4-ios-native-replay.XXXXXX")
printf 'S4 build directory: %s\n' "$work" >&2
mkdir "$work/tmp"
export TMPDIR="$work/tmp/" CLANG_MODULE_CACHE_PATH="$work/clang-cache"
export SWIFTPM_MODULECACHE_OVERRIDE="$work/swift-module-cache"

engine_revision=692f05cd2d31f218ae9b3cef7253a4e7397f8e17
rustc=$(rustup which --toolchain 1.99.0 rustc)
python3 -B experimental-capability-runtime/build-vm.py \
    --revision "$engine_revision" --target ios-simulator --rustc "$rustc" \
    --output "$work/engine" > "$work/engine-build.log" 2>&1
python3 -B "$fixture/prepare.py" "$work" > "$work/prepare.log" 2>&1

/usr/bin/xcodebuild -version > "$work/xcode-version.txt"
sdk=$(xcrun --sdk iphonesimulator --show-sdk-version)
printf '%s\n' "$sdk" > "$work/sdk-version.txt"
/usr/bin/xcodebuild -project "$work/S4Native.xcodeproj" -scheme S4Native \
    -configuration Debug -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' \
    -derivedDataPath "$work/derived-data" -clonedSourcePackagesDirPath "$work/source-packages" \
    -packageCachePath "$work/package-cache" -disablePackageRepositoryCache -scmProvider system \
    -onlyUsePackageVersionsFromResolvedFile -resultBundlePath "$work/build.xcresult" \
    build-for-testing ARCHS=arm64 "LIBRARY_SEARCH_PATHS=$work/engine/lib" \
    ENABLE_DEBUG_DYLIB=NO CODE_SIGN_IDENTITY=- CODE_SIGNING_REQUIRED=NO CODE_SIGN_ENTITLEMENTS= \
    > "$work/build.log" 2>&1
xcrun xcresulttool get build-results --path "$work/build.xcresult" > "$work/build-results.json"

products="$work/derived-data/Build/Products"
plan="$products/S4Native_iphonesimulator${sdk}-arm64.xctestrun"
test -f "$plan"
app="$products/Debug-iphonesimulator/S4Native.app"
runner="$products/Debug-iphonesimulator/S4NativeUITests-Runner.app"
{
    for binary in "$app/S4Native" "$runner/S4NativeUITests-Runner" \
        "$runner/PlugIns/S4NativeUITests.xctest/S4NativeUITests"; do
        test "$(xcrun lipo -archs "$binary")" = arm64
        macho=$(xcrun vtool -show-build "$binary")
        printf '%s\n' "$macho"
        printf '%s\n' "$macho" | grep -Eq 'platform IOSSIMULATOR$'
        printf '%s\n' "$macho" | grep -Eq 'minos 17\.0$'
    done
    for bundle in "$app" "$runner"; do
        /usr/bin/codesign --verify --deep --strict --verbose "$bundle"
        signature=$(/usr/bin/codesign -dv "$bundle" 2>&1)
        printf '%s\n' "$signature"
        printf '%s\n' "$signature" | grep -qx 'Signature=adhoc'
    done
    shasum -a 256 "$plan" "$app/S4Native" "$runner/S4NativeUITests-Runner" \
        "$runner/PlugIns/S4NativeUITests.xctest/S4NativeUITests"
} > "$work/product-verification.log" 2>&1
printf '%s\n' "$plan"
