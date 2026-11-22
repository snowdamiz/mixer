#!/bin/bash
set -euo pipefail

fixture=$(cd "$(dirname "$0")" && pwd -P)
run=$(cd "$1" && pwd -P)
stage=${2:-all}
app="$run/source/fieldlog"
sdk="$run/source/mixer"
rust=${FIELDLOG_RUST_BIN:-"$HOME/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin"}
crypto=${SWIFT_CRYPTO_GIT_STORE:-"$HOME/Library/Caches/org.swift.swiftpm/repositories/swift-crypto-7e0614ea"}
asn1=${SWIFT_ASN1_GIT_STORE:-"$HOME/Library/Caches/org.swift.swiftpm/repositories/swift-asn1-7065ad2c"}
export TMPDIR="$run/tmp/" PATH="$rust:$PATH"
mkdir -p "$run/tmp" "$run/lib"

if [[ $stage == all ]]; then
  SDKROOT=$(xcrun --sdk iphonesimulator --show-sdk-path) CARGO_PROFILE_RELEASE_DEBUG=0 \
    "$rust/cargo" build --manifest-path "$sdk/vm/Cargo.toml" --offline --locked --release \
      --features experimental-capability-native --lib --target aarch64-apple-ios-sim \
      --target-dir "$run/cargo" --jobs 8
fi
vm="$run/cargo/aarch64-apple-ios-sim/release/libmixer_vm.a"
test -f "$vm"
ln -sfn "$vm" "$run/lib/libmixer_vm_capability_experimental.a"
shasum -a 256 "$vm"

test "$(git -C "$crypto" rev-parse 'c2cbadd7263439d8015189668f96ff5b5be565ce^{tree}')" = \
  841fdfd88fed694e6532a3200a91b0f85595c340
test "$(git -C "$asn1" rev-parse '3b6410f7dee09eb33cdd26260c5fd47fda19b0e2^{tree}')" = \
  e7ed2e8c1483426c349b678e7d10940509f9d39c
export GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0 GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=2
export GIT_CONFIG_KEY_0="url.file://$(cd "$crypto" && pwd -P).insteadOf"
export GIT_CONFIG_VALUE_0=https://github.com/apple/swift-crypto.git
export GIT_CONFIG_KEY_1="url.file://$(cd "$asn1" && pwd -P).insteadOf"
export GIT_CONFIG_VALUE_1=https://github.com/apple/swift-asn1.git
lock=$(shasum -a 256 < "$sdk/Package.resolved")
[[ ${lock%% *} == e7dfdfed9b632538cd61bdff7bc705cb2a30cc7be661f31d6076f18b58d3f1ab ]]

git -C "$app" show :ios/FieldLog/WorkspaceView.swift > "$app/ios/FieldLog/WorkspaceView.swift"
git -C "$app" show :ios/FieldLogUITests/FieldLogUITests.swift > "$app/ios/FieldLogUITests/FieldLogUITests.swift"
python3 -B - "$app/ios/FieldLog/WorkspaceView.swift" "$fixture/StorageReadback.swift" <<'PY'
from pathlib import Path
import sys

view, readback = map(Path, sys.argv[1:])
source = view.read_text()
anchor = '        Text("Cloud sync isn\'t connected. Nothing in this queue has been sent to a server.")\n          .foregroundStyle(.secondary)'
if source.count(anchor) != 1:
    raise SystemExit("DeviceQueue readback anchor changed")
imports = "#if DEBUG\nimport CryptoKit\nimport ImageIO\n#endif\n"
view.write_text(imports + source.replace(
    anchor, anchor + "\n          #if DEBUG\n          .modifier(OrdinaryWitnessStorage())\n          #endif"
) + readback.read_text())
PY
cat "$fixture/OrdinaryWorkspaceWitness.swift" >> "$app/ios/FieldLogUITests/FieldLogUITests.swift"
project="$app/ios/FieldLog.xcodeproj"
cp "$sdk/Package.resolved" "$project/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"

xcodebuild -version
xcrun --sdk iphonesimulator --show-sdk-version
xcodebuild -project "$project" -scheme FieldLog -configuration Debug \
  -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath "$run/derived" -clonedSourcePackagesDirPath "$run/packages" \
  -packageCachePath "$run/package-cache" -disablePackageRepositoryCache \
  -disableAutomaticPackageResolution -onlyUsePackageVersionsFromResolvedFile -skipPackageUpdates \
  -scmProvider system -jobs 8 ARCHS=arm64 ONLY_ACTIVE_ARCH=NO CODE_SIGN_IDENTITY=- \
  ENABLE_DEBUG_DYLIB=NO COMPILER_INDEX_STORE_ENABLE=NO DEBUG_INFORMATION_FORMAT=dwarf \
  "HEADER_SEARCH_PATHS=\$(inherited) $sdk/vm/include" "LIBRARY_SEARCH_PATHS=$run/lib" \
  "CLANG_MODULE_CACHE_PATH=$run/clang-cache" build-for-testing
