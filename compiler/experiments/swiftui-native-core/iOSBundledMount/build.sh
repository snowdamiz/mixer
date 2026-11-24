#!/usr/bin/env bash
set -euo pipefail

fixture=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$fixture/../../../.." && pwd)
build=$(cd "${1:?Supply a fresh directory under verification/local}" && pwd)
case "$build/" in
  "$repo/verification/local/"*/) ;;
  *) echo "Build directory must be under verification/local" >&2; exit 2 ;;
esac
mkdir "$build/tmp" "$build/modules" "$build/module-cache"
export TMPDIR="$build/tmp/" CLANG_MODULE_CACHE_PATH="$build/module-cache"
cd "$repo"

xcodebuild -version
swiftc --version
git rev-parse HEAD
shasum -a 256 sdk/Sources/{MixerCore,MixerUI,MixerSwiftUI,MixerApple}/*.swift "$fixture"/{*.swift,build.sh,project.rb} > "$build/input-sha256.txt"
shasum -a 256 "$build/input-sha256.txt"

sdk=$(xcrun --sdk iphonesimulator --show-sdk-path)
flags=(-swift-version 6 -target arm64-apple-ios17.0-simulator -sdk "$sdk"
       -module-cache-path "$build/module-cache" -I "$build/modules")
build_library() {
  local module=$1
  shift
  swiftc "${flags[@]}" -parse-as-library -emit-library -static -emit-module -module-name "$module" \
    -emit-module-path "$build/modules/$module.swiftmodule" -o "$build/modules/lib$module.a" "$@"
}

build_library MixerCore -package-name Mixer sdk/Sources/MixerCore/*.swift
build_library MixerUI -package-name Mixer sdk/Sources/MixerUI/*.swift
build_library MixerSwiftUI -package-name Mixer sdk/Sources/MixerSwiftUI/*.swift
build_library MixerApple -enable-testing -package-name Mixer sdk/Sources/MixerApple/*.swift
build_library UP5StarterApple "$fixture/StarterFeature.swift"
build_library UP5StarterFeature -module-alias SwiftUI=MixerSwiftUI "$fixture/StarterFeature.swift"
printf '%s\n' 'PASS identical StarterFeature.swift compiled with Apple SwiftUI and MixerSwiftUI'

ruby "$fixture/project.rb" "$build"
exec xcodebuild -project "$build/UP5Bundled.xcodeproj" -scheme UP5Bundled \
  -configuration Debug -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath "$build/derived-data" -resultBundlePath "$build/build.xcresult" \
  build-for-testing ARCHS=arm64 IPHONEOS_DEPLOYMENT_TARGET=17.0 \
  "SWIFT_INCLUDE_PATHS=$build/modules" "LIBRARY_SEARCH_PATHS=$build/modules" \
  ENABLE_DEBUG_DYLIB=NO CODE_SIGN_IDENTITY=- CODE_SIGNING_REQUIRED=YES CODE_SIGN_ENTITLEMENTS=
