#!/usr/bin/env bash
set -euo pipefail

experiment=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$experiment/../../.." && pwd)
cd "$repo"
mkdir -p verification/local
evidence=$(mktemp -d "$repo/verification/local/gc3-map-products.XXXXXXXX")
scratch=$(mktemp -d "$repo/verification/local/gc3-map-build.XXXXXXXX")
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/tmp"
export TMPDIR="$scratch/tmp"

revision=$(git rev-parse HEAD)
printf 'Evidence directory %s\n' "$evidence"
{
    xcodebuild -version
    swift --version
    xcrun --sdk iphonesimulator --show-sdk-version
    printf 'Checkout revision %s\n' "$revision"
    git rev-parse HEAD:sdk HEAD:updates
    (
        cd "$experiment"
        find . -type f | LC_ALL=C sort | while IFS= read -r file; do shasum -a 256 "$file"; done
    ) > "$evidence/source.sha256"
    shasum -a 256 "$evidence/source.sha256"
} 2>&1 | tee "$evidence/toolchain.log"

build=(
    xcodebuild -project "$experiment/NativeMapIsland.xcodeproj" -scheme NativeMapIsland
    -configuration Debug -destination 'generic/platform=iOS Simulator'
    -derivedDataPath "$scratch/derived" -clonedSourcePackagesDirPath "$scratch/packages"
    -packageCachePath "$scratch/cache" -disablePackageRepositoryCache
    -onlyUsePackageVersionsFromResolvedFile -skipPackageUpdates
    ARCHS=arm64 ONLY_ACTIVE_ARCH=NO COMPILER_INDEX_STORE_ENABLE=NO
    "CLANG_MODULE_CACHE_PATH=$scratch/modules"
    "GC3_SOURCE_REVISION=$revision" CODE_SIGNING_ALLOWED=YES CODE_SIGN_IDENTITY=-
    build-for-testing
)
printf '%q ' "${build[@]}" > "$evidence/build-command.txt"
printf '\n' >> "$evidence/build-command.txt"
"${build[@]}" > "$evidence/build.log" 2>&1 || { tail -n 100 "$evidence/build.log" >&2; exit 1; }

products="$scratch/derived/Build/Products"
retained="$evidence/Products"
configuration=Debug-iphonesimulator
mkdir -p "$retained/$configuration"
for bundle in NativeMapIsland.app NativeMapIslandUITests-Runner.app; do
    ditto "$products/$configuration/$bundle" "$retained/$configuration/$bundle"
done
cp "$products/"*.xctestrun "$retained/"

{
    app="$retained/$configuration/NativeMapIsland.app"
    runner="$retained/$configuration/NativeMapIslandUITests-Runner.app"
    test="$runner/PlugIns/NativeMapIslandUITests.xctest"
    for signed in "$app" "$runner" "$test"; do
        codesign --verify --deep --strict --verbose=2 "$signed"
        codesign -d --verbose=2 "$signed"
    done
    for executable in "$app/NativeMapIsland" "$test/NativeMapIslandUITests"; do
        archs=$(xcrun lipo -archs "$executable")
        printf '%s architecture %s\n' "$executable" "$archs"
        [[ "$archs" == arm64 ]]
        build_version=$(xcrun vtool -show-build "$executable")
        printf '%s\n' "$build_version"
        [[ "$build_version" == *'platform IOSSIMULATOR'* ]]
        [[ "$build_version" == *'minos 17.0'* ]]
        shasum -a 256 "$executable"
    done
    [[ $(/usr/libexec/PlistBuddy -c 'Print :MinimumOSVersion' "$app/Info.plist") == 17.0 ]]
    [[ $(/usr/libexec/PlistBuddy -c 'Print :GC3SourceRevision' "$app/Info.plist") == "$revision" ]]
    plutil -p "$retained/"*.xctestrun
    shasum -a 256 "$retained/"*.xctestrun
    printf 'PASS strict Simulator signatures, arm64 app and XCTest, iOS 17.0 Mach-O floor, fixture revision\n'
} 2>&1 | tee "$evidence/verification.log"

printf 'Signed test products %s\n' "$retained"
