#!/bin/bash
set -euo pipefail

if [[ $# != 4 || ! "$1" =~ ^(host|prepare-native|public)$ ]]; then
  echo "Usage: replay.sh {host|prepare-native|public} MIXER FIELDLOG NEW_SCRATCH" >&2
  exit 2
fi
mode="$1"
delivery="$(cd "$(dirname "$0")" && pwd -P)"
mixer="$(git -C "$2" rev-parse --show-toplevel)"
fieldlog="$(git -C "$3" rev-parse --absolute-git-dir)"
umask 077
mkdir -m 700 "$4"
scratch="$(cd "$4" && pwd -P)"
fieldlog_pin=552559d2d3278abb9b1aa7dcf0288102c09a202b
fixture_pin=6ad5a08722c53f1589a8989d0b43eeca78c50294
sdk_pin=56ff14c925168284761c5aca4f0bd4129cf3c995
export GIT_ALLOW_PROTOCOL=file GIT_NO_LAZY_FETCH=1 GIT_NO_REPLACE_OBJECTS=1 GIT_TERMINAL_PROMPT=0
mkdir "$scratch"/{public-mixer,tmp}
export TMPDIR="$scratch/tmp/"
export CLANG_MODULE_CACHE_PATH="$scratch/clang-cache"
export SWIFT_MODULE_CACHE_PATH="$scratch/swift-module-cache"
export SWIFTPM_MODULECACHE_OVERRIDE="$SWIFT_MODULE_CACHE_PATH"
public="$scratch/public-mixer"
patches="$public/verification/fieldlog-entry-sync"

test "$(git --git-dir="$fieldlog" rev-parse "$fieldlog_pin^{tree}")" = 1b62520f35c7e57a01b568291078686574f627c4
test "$(git -C "$mixer" rev-parse "$fixture_pin^{tree}")" = 42ea4b87cebe47af7ae29746f272ad7d704bc085
git -C "$mixer" archive "$fixture_pin" \
  tests/integration/fieldlog-entry-sync verification/fieldlog-entry-sync | tar -xf - -C "$public"
if [[ "$mode" == public ]]; then
  python3 -B "$public/tests/integration/fieldlog-entry-sync/resume.py" "$fieldlog" \
    --receipt "$scratch/public-receipt.json"
  exit
fi

mkdir "$scratch"/{app,host}
git --git-dir="$fieldlog" archive "$fieldlog_pin" | tar -xf - -C "$scratch/app"
git -C "$scratch/app" init -q --template=
git -C "$scratch/app" add --all
test "$(git -C "$scratch/app" write-tree)" = 1b62520f35c7e57a01b568291078686574f627c4

apply_patch() {
  local actual
  actual="$(shasum -a 256 "$2")"
  test "${actual%% *}" = "$1"
  git -C "$scratch/app" apply --index "$2"
  test "$(git -C "$scratch/app" write-tree)" = "$3"
}
apply_patch 3f387b06a7e11682833d798ddd5c8d325452d760d518029a6d12db9fa2323189 \
  "$patches/fieldlog-552559d2-entry-sync.patch" 9005f9d85ed5202980de9ebad1416a1bb23dd8cb
apply_patch 4ef0c920f5948b71caa890bab78aa574fc968fe72775cbdd538faee211146c0d \
  "$patches/fieldlog-552559d2-local-backend.patch" 9bf29ebe2c7aeef326e8e98aa2b5be1dba2b1c19
apply_patch 96fc38e2ac5cdb9ef664d8c47f3c82c1f3c6ee035ea2477eb322800a8927efd2 \
  "$patches/fieldlog-552559d2-photo-resume.patch" d054936acbb3ed9af7afe3a9129a026d4614f957
apply_patch 8f46097265fa0a50dba76b518e00a63ec58d23796d84d011aada4ea6ce266815 \
  "$delivery/fieldlog-ios-entry-sync-resume.patch" a75d5e84dbe4403f56199220267b8b68996592f7
if [[ "$mode" == prepare-native ]]; then
  apply_patch da1f8d589239fd9ab41e62abfcf3e7ab494cb942a9d4a5ec7984ee0a4cbbc827 \
    "$delivery/fieldlog-ios-entry-sync-resume-xctest.patch" 5e85d700b70afa8b6089001520cd95251da1cd7c
fi
test "$(git -C "$scratch/app" hash-object Backend/local_entry_sync.py)" = 22d9fe05e1aa9e098050a82d6fed9cc53a4a2360

cat > "$scratch/host/Package.swift" <<'SWIFT'
// swift-tools-version: 6.0
import PackageDescription

let package = Package(
  name: "FieldLogQueueReplay",
  platforms: [.macOS(.v14)],
  targets: [
    .target(name: "FieldLogModels"),
    .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"]),
    .executableTarget(name: "QueueJourney", dependencies: ["FieldLogModels", "FieldLogStorage"],
      path: "QueueJourney", swiftSettings: [.define("FIELDLOG_LOCAL_ENTRY_SYNC")]),
  ])
SWIFT
ln -s "$scratch/app/Sources" "$scratch/host/Sources"
mkdir "$scratch/host/QueueJourney"
cp "$delivery/QueueJourney.swift" "$scratch/app/ios/FieldLog/"{DeviceQueue,WorkspaceModel}.swift "$scratch/host/QueueJourney/"

swift_flags=(
  --cache-path "$scratch/swift-cache" --config-path "$scratch/swift-config"
  --security-path "$scratch/swift-security" --disable-dependency-cache
)
swift build --package-path "$scratch/host" --scratch-path "$scratch/host-build" \
  "${swift_flags[@]}" --product QueueJourney > "$scratch/host-build.log" 2>&1 || {
    tail -50 "$scratch/host-build.log" >&2
    exit 1
  }
if [[ "$mode" == host ]]; then
  python3 -B "$delivery/journey.py" "$scratch" | tee "$scratch/host-receipt.jsonl"
  exit
fi

mkdir "$scratch/mixer" "$scratch/build-app"
test "$(git -C "$mixer" rev-parse "$sdk_pin^{tree}")" = 75989099938ed5256c4144cbc9e62979ee323183
git -C "$mixer" archive "$sdk_pin" Package.swift sdk/Sources sdk/Tests | tar -xf - -C "$scratch/mixer"
git -C "$scratch/app" checkout-index --prefix="$scratch/build-app/" -a
cd "$scratch/build-app"
python3 - <<'PY'
from pathlib import Path

manifest = Path("Package.swift")
source = manifest.read_text()
pin = '.package(url: "https://github.com/snowdamiz/mixer.git", revision: "56ff14c925168284761c5aca4f0bd4129cf3c995")'
assert source.count(pin) == 1
manifest.write_text(source.replace(pin, '.package(name: "mixer", path: "../mixer")'))
Path("Package.resolved").unlink()
Path("ios/FieldLog.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved").unlink()
PY
git init -q --template=
git add --all
git write-tree > "$scratch/build-overlay.tree"
swift test --scratch-path "$scratch/test-build" "${swift_flags[@]}" > "$scratch/package-tests.log" 2>&1 || {
  tail -50 "$scratch/package-tests.log" >&2
  exit 1
}
grep 'Test run with' "$scratch/package-tests.log"
xcodebuild -project ios/FieldLog.xcodeproj -scheme FieldLog -configuration FieldLogLocalSync \
  -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' -derivedDataPath "$scratch/derived" \
  -clonedSourcePackagesDirPath "$scratch/packages" -packageCachePath "$scratch/ios-cache" \
  -disableAutomaticPackageResolution -skipPackageUpdates -disablePackageRepositoryCache \
  CODE_SIGNING_ALLOWED=NO CLANG_MODULE_CACHE_PATH="$CLANG_MODULE_CACHE_PATH" \
  SWIFT_MODULE_CACHE_PATH="$SWIFT_MODULE_CACHE_PATH" COMPILER_INDEX_STORE_ENABLE=NO \
  build-for-testing > "$scratch/ios-build.log" 2>&1 || {
    tail -50 "$scratch/ios-build.log" >&2
    exit 1
  }
grep -F '** TEST BUILD SUCCEEDED **' "$scratch/ios-build.log"
printf '%s\n' "$scratch"
