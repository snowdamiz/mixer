#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ $# != 3 ]]; then
  echo "Usage: prepare.sh MIXER_CHECKOUT FIELDLOG_CHECKOUT NEW_DIRECTORY" >&2
  exit 2
fi
delivery="$(cd "$(dirname "$0")" && pwd -P)"
mixer="$(cd "$1" && pwd -P)"
fieldlog="$(cd "$2" && pwd -P)"
mkdir "$3"
out="$(cd "$3" && pwd -P)"
work="$out/work"
app="$work/app"
sdk="$work/mixer"
mkdir -p "$app" "$sdk" "$work/tmp"
export TMPDIR="$work/tmp/"

fieldlog_pin=552559d2d3278abb9b1aa7dcf0288102c09a202b
consumer_pin=938431f3bd3c9d07d9cacefa9448e9abdfa77160
sdk_pin=46c322994620fe2a9e4a5622a4a3ef14d18207ab
test "$(xcodebuild -version)" = "$(printf 'Xcode 27.2\nBuild version 27B52')"
test "$(git -C "$fieldlog" rev-parse "$fieldlog_pin^{tree}")" = 1b62520f35c7e57a01b568291078686574f627c4
test "$(git -C "$mixer" rev-parse "$sdk_pin^{tree}")" = 4f23e4d96771e60ea247fe9ea62e641cf9e8de1d
git -C "$fieldlog" archive "$fieldlog_pin" | tar -xf - -C "$app"
git -C "$mixer" archive "$sdk_pin" Package.swift Package.resolved sdk/Sources sdk/Tests | tar -xf - -C "$sdk"
git -C "$app" init -q --template=
git -C "$app" add --all
test "$(git -C "$app" write-tree)" = 1b62520f35c7e57a01b568291078686574f627c4

apply() {
  test "$(shasum -a 256 "$1" | cut -d' ' -f1)" = "$2"
  git -C "$app" apply --index "$1"
  test "$(git -C "$app" write-tree)" = "$3"
}
fixture=tests/integration/fieldlog-task-sync
backend=verification/fieldlog-entry-sync/fieldlog-552559d2-local-backend.patch
git -C "$mixer" show "$consumer_pin:$fixture/fieldlog-task-conflict.patch" > "$work/conflict.patch"
git -C "$mixer" show "$consumer_pin:$backend" > "$work/backend.patch"
git -C "$mixer" show "$consumer_pin:$fixture/fieldlog-saved-task-sync.patch" > "$work/saved-sync.patch"
apply "$work/conflict.patch" 89533e6972772c787ff0ba53d6b55eb40e42cbe6e6005f00dd0a3113a0a0a6fd ea2be47768a94647fd1f5a283a1aeb1137ccb730
apply "$work/backend.patch" 4ef0c920f5948b71caa890bab78aa574fc968fe72775cbdd538faee211146c0d 131a64b7cd5e37da32f85cc3260c9e0d8112f85a
apply "$work/saved-sync.patch" 4978dd9f2c524d7870fdb1039b18d34f9eb8edfcaee31671ac8cbec146cf3ef8 8f3797522b9cbb4e359f63cc1a70cb7e7e074ced
apply "$delivery/fieldlog-ios-task-sync.patch" dc0b094f9052be6b8693db1d7613fc7a6a8b40fbde62d7880f4f26a8d3d54e0a 1592529b48b54ba156a678e3aa3548c0a66a7200

apply "$delivery/restore-task-project.patch" 8ad0238e6b91c549c9c593c3012c9e2d3225056a060be94a402d15c9d9ec5717 cf223341f461a9788fefed75d05f2a5cfe7bdcd1

lock="$app/ios/FieldLog.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
sed -i '' 's|.package(url: "https://github.com/snowdamiz/mixer.git", revision: "56ff14c925168284761c5aca4f0bd4129cf3c995")|.package(name: "mixer", path: "../mixer")|' "$app/Package.swift"
grep -Fq '.package(name: "mixer", path: "../mixer")' "$app/Package.swift"
cp "$sdk/Package.resolved" "$lock"
git -C "$app" add -- Package.swift "$lock"
git -C "$app" write-tree > "$out/build-overlay.tree"

python3 -B "$app/verification/host/replay-saved-task-sync.py" "$work/host" > "$work/host.log" 2>&1
tail -1 "$work/host.log" > "$out/public-host-replay.json"
xcodebuild -project "$app/ios/FieldLog.xcodeproj" -scheme FieldLog -configuration Debug \
  -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' -derivedDataPath "$work/derived" \
  -clonedSourcePackagesDirPath "$work/packages" -packageCachePath "$work/package-cache" \
  -skipPackageUpdates -disablePackageRepositoryCache -disableAutomaticPackageResolution \
  ARCHS=arm64 ONLY_ACTIVE_ARCH=NO CODE_SIGN_IDENTITY=- AD_HOC_CODE_SIGNING_ALLOWED=YES \
  CLANG_MODULE_CACHE_PATH="$work/clang-modules" SWIFT_MODULE_CACHE_PATH="$work/swift-modules" \
  COMPILER_INDEX_STORE_ENABLE=NO build-for-testing > "$work/ios-build.log" 2>&1
grep -Fq '** TEST BUILD SUCCEEDED **' "$work/ios-build.log"
cmp "$sdk/Package.resolved" "$lock"
test "$(git -C "$work/packages/checkouts/swift-asn1" rev-parse HEAD)" = 3b6410f7dee09eb33cdd26260c5fd47fda19b0e2
test "$(git -C "$work/packages/checkouts/swift-crypto" rev-parse HEAD)" = c2cbadd7263439d8015189668f96ff5b5be565ce

ios="$out/ios"
mkdir -p "$ios/Debug-iphonesimulator" "$out/host" "$out/fixture/Backend" "$out/fixture/verification/host"
products="$work/derived/Build/Products"
cp "$products/FieldLog_iphonesimulator27.2-arm64.xctestrun" "$ios/"
for bundle in FieldLog.app FieldLogUITests-Runner.app; do
  product="$ios/Debug-iphonesimulator/$bundle"
  ditto "$products/Debug-iphonesimulator/$bundle" "$product"
  codesign --verify --deep --strict "$product"
done
cp "$work/host"/{SavedTaskSyncReplay,libFieldLogModels.dylib,libFieldLogStorage.dylib} "$out/host/"
cp "$app/Backend/local_entry_sync.py" "$out/fixture/Backend/"
cp "$app/verification/host"/{replay-saved-task-sync,replay-task-conflict}.py "$out/fixture/verification/host/"
cp "$delivery/journey.py" "$out/"
python3 -B "$out/journey.py" --inspect > "$out/ios-build.json"
python3 -B "$out/journey.py" --host --scratch "$work/control" > "$work/control.log"
cp "$work/control/receipt.json" "$out/ui-host-control.json"
shasum -a 256 "$work"/{host,ios-build,control}.log > "$out/build-log-digests.txt"
unset TMPDIR
rm -rf -- "$work"
printf '%s\n' "$out"
