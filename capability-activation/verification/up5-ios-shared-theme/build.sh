#!/bin/sh
set -eu
fixture=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
build=$(CDPATH= cd -- "$1" && pwd)
engine=$(CDPATH= cd -- "$2" && pwd)
revision=$3
mkdir "$build/tmp"
export TMPDIR="$build/tmp/" CLANG_MODULE_CACHE_PATH="$build/clang-cache"
export SWIFTPM_MODULECACHE_OVERRIDE="$build/swift-module-cache"
python3 -B "$fixture/prepare.py" "$build" "$engine" "$revision"
exec /usr/bin/xcodebuild -project "$build/UP5Theme.xcodeproj" -scheme UP5Theme \
  -configuration Debug -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath "$build/derived-data" -clonedSourcePackagesDirPath "$build/source-packages" \
  -packageCachePath "$build/package-cache" -disablePackageRepositoryCache -scmProvider system \
  -onlyUsePackageVersionsFromResolvedFile -resultBundlePath "$build/build.xcresult" \
  build-for-testing ARCHS=arm64 IPHONEOS_DEPLOYMENT_TARGET=17.0 "LIBRARY_SEARCH_PATHS=$build/lib" \
  ENABLE_DEBUG_DYLIB=NO CODE_SIGN_IDENTITY=- CODE_SIGNING_REQUIRED=NO CODE_SIGN_ENTITLEMENTS=
