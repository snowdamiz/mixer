#!/usr/bin/env bash
set -euo pipefail

fixture=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$fixture/../../../.." && pwd)
evidence=$(cd "${1:?Supply a fresh directory under verification/local}" && pwd)
case "$evidence" in
  "$repo/verification/local/"*) ;;
  *) echo "Build directory must be under verification/local" >&2; exit 2 ;;
esac
build="$evidence/work"
mkdir "$build"
mkdir "$build/tmp" "$build/modules" "$build/module-cache"
export TMPDIR="$build/tmp/" CLANG_MODULE_CACHE_PATH="$build/module-cache"
cd "$repo"

sdk=$(xcrun --sdk iphonesimulator --show-sdk-path)
developer=$(xcode-select -p)
relative_fixture=${fixture#"$repo"/}
{
  xcodebuild -version
  swiftc --version
  ruby -rxcodeproj -e 'puts "xcodeproj #{Xcodeproj::VERSION}"'
  printf 'Developer path %s\nSDK %s\n' "$developer" "$sdk"
  git rev-parse HEAD
  shasum -a 256 sdk/Sources/{MixerCore,MixerUI,MixerSwiftUI,MixerApple}/*.swift \
    "$relative_fixture"/{*.swift,build.sh,project.rb} > "$evidence/input-sha256.txt"
  shasum -a 256 "$evidence/input-sha256.txt"
} | tee "$evidence/toolchain.log"

flags=(-swift-version 6 -target arm64-apple-ios17.0-simulator -sdk "$sdk"
       -module-cache-path "$build/module-cache" -I "$build/modules")
build_library() {
  local module=$1
  shift
  swiftc "${flags[@]}" -parse-as-library -emit-library -static -emit-module -module-name "$module" \
    -emit-module-path "$build/modules/$module.swiftmodule" -o "$build/modules/lib$module.a" "$@"
}

(
  set -x
  build_library MixerCore -package-name Mixer sdk/Sources/MixerCore/*.swift
  build_library MixerUI -package-name Mixer sdk/Sources/MixerUI/*.swift
  build_library MixerSwiftUI -package-name Mixer sdk/Sources/MixerSwiftUI/*.swift
  build_library MixerApple -package-name Mixer sdk/Sources/MixerApple/*.swift
  build_library GC4AppleFeature "$fixture/SharedScreen.swift"
  build_library GC4MixerFeature -module-alias SwiftUI=MixerSwiftUI "$fixture/SharedScreen.swift"
  printf '%s\n' 'PASS identical SharedScreen.swift compiled with Apple SwiftUI and MixerSwiftUI'
) > "$evidence/dual-compile.log" 2>&1 || { cat "$evidence/dual-compile.log" >&2; exit 1; }

ruby "$fixture/project.rb" "$build"
command=(xcodebuild -project "$build/GC4Differential.xcodeproj" -scheme GC4Differential
         -configuration Debug -sdk iphonesimulator -destination 'generic/platform=iOS Simulator'
         -derivedDataPath "$build/derived-data" -resultBundlePath "$evidence/build.xcresult"
         build-for-testing ARCHS=arm64 IPHONEOS_DEPLOYMENT_TARGET=17.0
         "SWIFT_INCLUDE_PATHS=$build/modules" "LIBRARY_SEARCH_PATHS=$build/modules"
         "MODULE_CACHE_DIR=$build/module-cache" COMPILER_INDEX_STORE_ENABLE=NO
         ENABLE_DEBUG_DYLIB=NO CODE_SIGN_IDENTITY=- CODE_SIGNING_REQUIRED=YES CODE_SIGN_ENTITLEMENTS=)
printf '%q ' "${command[@]}" > "$evidence/build-command.txt"
printf '\n' >> "$evidence/build-command.txt"
"${command[@]}" > "$evidence/build.log" 2>&1 || { tail -n 100 "$evidence/build.log" >&2; exit 1; }

products="$build/derived-data/Build/Products"
retained="$evidence/Products"
configuration=Debug-iphonesimulator
runs=("$products/"*.xctestrun)
[[ ${#runs[@]} -eq 1 && -f "${runs[0]}" ]]
mkdir -p "$retained/$configuration"
for bundle in GC4Differential.app GC4DifferentialUITests-Runner.app; do
  ditto "$products/$configuration/$bundle" "$retained/$configuration/$bundle"
done
cp "${runs[0]}" "$retained/"
xctestrun="$retained/${runs[0]##*/}"

{
  app="$retained/$configuration/GC4Differential.app"
  runner="$retained/$configuration/GC4DifferentialUITests-Runner.app"
  tests="$runner/PlugIns/GC4DifferentialUITests.xctest"
  for signed in "$app" "$runner" "$tests"; do
    codesign --verify --deep --strict --verbose=2 "$signed"
    codesign -d --verbose=2 "$signed"
  done
  for signed in "$app" "$tests"; do
    executable=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$signed/Info.plist")
    [[ $(xcrun lipo -archs "$signed/$executable") == arm64 ]]
    build_version=$(xcrun vtool -show-build "$signed/$executable")
    printf '%s\n' "$build_version"
    [[ "$build_version" == *'platform IOSSIMULATOR'* ]]
    [[ "$build_version" == *'minos 17.0'* ]]
    shasum -a 256 "$signed/$executable"
  done
  plutil -p "$xctestrun"
  shasum -a 256 "$xctestrun"
  printf 'PASS strict signatures, arm64 Simulator products and iOS 17.0 deployment target\n'
} 2>&1 | tee "$evidence/product-identity.log"

rm -rf "$build"
printf 'Signed test products %s\n' "$retained"
