# Reconstruct the FieldLog iOS development key rotation replay

This recipe builds fresh signed development offers for
`FieldLogUITests/ChecklistJourney/testDevelopmentKeyRotation` (L04 and L08
§22.2.11). The host replay exercises the installed verifier, local delivery,
and signed guest startup on macOS. Root owns native adoption, Accessibility
preflight, device custody, and XCTest readback.

The recipe uses public Mixer `a7588b9022` (which includes `d82b78782a`),
FieldLog `552559d2`, the ordinary checklist SDK and VM at Mixer `584cd1947e`,
and publisher tools at Mixer `fef67b64cd`. The signer's two Mixer packages
are identical at the SDK and publisher pins. The checklist patches reconstruct
the ordinary local replay and its Debug rotation observations. The staged
XCTest is byte-identical to the earlier delivered selector, including its
35-second checkpoint deadline. [Source and toolchain pins](pins.json)

## Reconstruct and check the source

From the Mixer root, use Bash with `set -e`, Python 3.12 or newer, Xcode 27.2 (27B52), Apple Swift 6.4.2, and the 27.2 SDK. Use a fresh output directory under `verification/local/`.

```bash
recipe="$PWD/capability-activation/verification/fieldlog-ios/rotation"
work="$PWD/verification/local/fieldlog-ios-rotation-fresh"
umask 077
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
test "$(xcodebuild -version)" = $'Xcode 27.2\nBuild version 27B52'
test "$(xcrun --sdk iphonesimulator --show-sdk-version)" = 27.2
xcrun swift --version | grep -Fq 'Apple Swift version 6.4.2 (swiftlang-6.4.2.1.9 clang-2100.4.1.1)'
mkdir -p "$PWD/verification/local"
python3 -B "$recipe/prepare.py" "$work"
mkdir "$work/host-tmp" "$work/xctest-modules"
(cd "$work/source/fieldlog" &&
  TMPDIR="$work/host-tmp" /bin/sh scripts/test-signed-checklist-recovery.sh)
platform="$DEVELOPER_DIR/Platforms/iPhoneSimulator.platform/Developer"
TMPDIR="$work/host-tmp" xcrun --sdk iphonesimulator swiftc -typecheck -swift-version 6 \
  -target arm64-apple-ios26.0-simulator -sdk "$platform/SDKs/iPhoneSimulator27.2.sdk" \
  -F "$platform/Library/Frameworks" -I "$platform/usr/lib" \
  -module-cache-path "$work/xctest-modules" \
  "$work/source/fieldlog/ios/FieldLogUITests/ChecklistJourney.swift"
```

The reconstruction checks the downloaded FieldLog archive and all 29 overlaid files. The host recovery control uses the reconstructed ordinary checklist and real `WorkspaceRepository`. It checks before-write and after-write retirement, preserved workspace state, no duplicate edit, and refusal to reopen an unverified candidate.

## Build and admit the fresh guest pair

Install the official Apple Swift 6.3.3 release toolchain. The default path is
`~/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin`.
Set `FIELDLOG_GUEST_BIN` if the same toolchain is installed elsewhere. The
script compiles freestanding Wasm with the toolchain's Swift, Clang, and LLD.

The script exports the public saved-draft guest at `3184c398ba`, applies the
public selected-task overlay from `a7588b9022`, and uses the two saved-task
fallback labels from the earlier comparison. Both variants hydrate the selected
task through FieldLog storage before publishing an initial frame. The
`REQUIRE_REVIEW` build enables the review step before a completion write.
The script verifies the source hashes, then admits both payloads only after
checking both byte counts and digests.

| Fresh variant | Bytes | SHA-256 |
| --- | ---: | --- |
| Baseline | 6133 | `8a3cdbfda08c053ee4f42865fd796ab0cf23270776783a6a6419dcd9119aa013` |
| Reviewed | 6183 | `c486d9af66c9b7aa5b44743ac87220dec811bdc1fde8e4dfa3b2a875b004e575` |

```bash
/bin/bash "$recipe/build-guest.sh" "$work"
```

The historical 5489-byte and 5521-byte Wasm pins remain recorded under
`historicalPayloads`. Their exact producer remains unavailable. The signed
manifests for this replay identify the selected-task source and use only the
fresh pins, with the same grant, execution limits, scope, and ABI.

## Generate fresh development signatures and run the host checks

Use the same shell after the pair is admitted. The signer generates six
role-separated development keys in memory and writes the signed offers and
public roots. It binds the new public-root digest into the full installed
identity and signs for the resulting runtime fingerprint. Initial roots expire
after seven days. Revoked and expired assignment controls reuse the exact
replacement artifact envelope.

```bash
packet="$work/packet"
source="$work/source"
mkdir "$work/mirrors" "$work/swift-tmp" "$work/swift-modules" "$packet/tools"
git clone --bare --depth=1 --branch 5.0.3 https://github.com/apple/swift-crypto.git \
  "$work/mirrors/swift-crypto.git"
git clone --bare --depth=1 --branch 1.7.3 https://github.com/apple/swift-asn1.git \
  "$work/mirrors/swift-asn1.git"
test "$(git -C "$work/mirrors/swift-crypto.git" rev-parse '5.0.3^{commit}')" = \
  c2cbadd7263439d8015189668f96ff5b5be565ce
test "$(git -C "$work/mirrors/swift-asn1.git" rev-parse '1.7.3^{commit}')" = \
  3b6410f7dee09eb33cdd26260c5fd47fda19b0e2
export TMPDIR="$work/swift-tmp" CLANG_MODULE_CACHE_PATH="$work/swift-modules"
export SWIFTPM_MODULECACHE_OVERRIDE="$CLANG_MODULE_CACHE_PATH"
export GIT_TERMINAL_PROMPT=0 GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=2 GIT_ALLOW_PROTOCOL=file
export GIT_CONFIG_KEY_0="url.file://$work/mirrors/swift-crypto.git.insteadOf"
export GIT_CONFIG_VALUE_0=https://github.com/apple/swift-crypto.git
export GIT_CONFIG_KEY_1="url.file://$work/mirrors/swift-asn1.git.insteadOf"
export GIT_CONFIG_VALUE_1=https://github.com/apple/swift-asn1.git

swift_build() {
  local package=$1
  local scratch=$2
  shift 2
  xcrun swift build --package-path "$package" --scratch-path "$scratch" \
    --cache-path "$work/swiftpm/cache" --config-path "$work/swiftpm/config" \
    --security-path "$work/swiftpm/security" --manifest-cache none --disable-dependency-cache \
    --disable-prefetching --force-resolved-versions --disable-index-store \
    --jobs "${FIELDLOG_SWIFT_JOBS:-4}" -Xswiftc -gnone -Xcc -g0 "$@"
}

swift_build "$packet" "$work/swiftpm/packet" --product SignRotation
"$work/swiftpm/packet/debug/SignRotation" "$packet/templates" "$packet/fixture"
swift_build "$source/publisher/updates" "$work/swiftpm/updates" --product mixer-update
swift_build "$source/publisher/cli" "$work/swiftpm/cli" --product mixer
cp "$work/swiftpm/updates/debug/mixer-update" "$work/swiftpm/cli/debug/mixer" "$packet/tools/"
mkdir "$work/go-tmp"
(cd "$source/publisher/services" &&
  TMPDIR="$work/go-tmp" \
  GOCACHE="$work/go-cache" GOMODCACHE="$work/go-mod" GOPATH="$work/go-path" GOENV=off \
  GOTOOLCHAIN=go1.27.1 go build -mod=readonly -modcacherw -o "$packet/tools/mixer-service" ./cmd/mixer-service)
python3 -B "$packet/validate-host.py" "$packet/fixture" "$work/host-validation"
cp "$work/host-validation/results.json" "$packet/host-validation.json"
python3 -B "$packet/origin.py" "$work/origin-smoke" --smoke
```

Build the archive with Rust 1.99.0 and the matching `llvm-tools-preview` component. The existing builder exports the pinned VM from Git.

```bash
vm_pin=584cd1947edd590fd9fc732197f7d737287ab36f
rust_bin="$HOME/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin"
python3 -B experimental-capability-runtime/build-vm.py --revision "$vm_pin" \
  --rustc "$rust_bin/rustc" --target host --output "$work/engine-host"
printf '%s  %s\n' bc6b286fdd17507acf073846283dc7e9f32c3a7de8d98ac2c3d6ce35a23e4f74 \
  "$work/engine-host/lib/libmixer_vm_capability_experimental.a" | shasum -a 256 -c
swift_build "$packet" "$work/swiftpm/packet" --product InstalledProbe \
  -Xcc "-I$source/mixer/vm/include" -Xlinker "-L$work/engine-host/lib"
"$work/swiftpm/packet/debug/InstalledProbe" "$packet/fixture" "$work/installed-host"
```

The verifier checks both valid assignments, independent artifact and assignment
revocation, wrong runtime, and tampered payload. Its explicit clock verifies each
initial key one second before expiry and at expiry, then accepts the valid
replacement at that same cutoff. The publication check verifies byte-identical
baseline offers after each refused publication. The origin smoke test checks
scope, the offline listener transition, exact delivery bytes, and listener
closure. The origin records a SHA-256 of each signed response body after its
complete write. Readback compares the update and artifact digests for each
phase against that phase's fixture. The revoked-assignment and replacement
phases share the artifact response and have distinct signed update responses.

The macOS probe uses the signed installed actor and FieldLog's
`WorkspaceRepository` and `FieldLogTaskStorage`. It checks byte-identical
recovery state and workspace after the actor's refusals, accepted sequences
1 and 2 across owner reopen under the same installation, `feature_started`
and a validated first frame for each guest, and clean retirement. The probe
runs headlessly. Native
first-screen health, offline reopening of a *healthy* baseline, and replacement
health with the previous healthy candidate are assertions of the unchanged
XCTest and disk readback.

## Build the generic Simulator test bundles after the host checks

Install the Rust `aarch64-apple-ios-sim` target. Root can run the generic build
after adopting this recipe. This builds for testing without choosing or starting
a device.

```bash
python3 -B experimental-capability-runtime/build-vm.py --revision "$vm_pin" \
  --rustc "$rust_bin/rustc" --target ios-simulator --output "$work/engine-simulator"
printf '%s  %s\n' f3afa1e76f3d27be572dc7d2f269763c43b6c4331231ecd308eb96ed40d5fae1 \
  "$work/engine-simulator/lib/libmixer_vm_capability_experimental.a" | shasum -a 256 -c
cp -R "$packet/fixture/Installed" "$source/fieldlog/ios/FieldLog/ChecklistRelease"
xcodebuild -project "$source/fieldlog/ios/FieldLog.xcodeproj" -scheme FieldLog \
  -configuration Debug -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath "$work/derived" -clonedSourcePackagesDirPath "$work/dependencies" \
  -packageCachePath "$work/xcode-package-cache" -disablePackageRepositoryCache \
  -skipPackageUpdates -disableAutomaticPackageResolution -scmProvider system \
  -jobs "${FIELDLOG_XCODE_JOBS:-6}" build-for-testing CODE_SIGNING_ALLOWED=NO ENABLE_DEBUG_DYLIB=NO \
  ARCHS=arm64 COMPILER_INDEX_STORE_ENABLE=NO DEBUG_INFORMATION_FORMAT=dwarf GCC_GENERATE_DEBUGGING_SYMBOLS=NO \
  "OTHER_CFLAGS=\$(inherited) -I$source/mixer/vm/include" \
  "OTHER_SWIFT_FLAGS=\$(inherited) -Xcc -I$source/mixer/vm/include" \
  "LIBRARY_SEARCH_PATHS=\$(inherited) $work/engine-simulator/lib"
products="$work/derived/Build/Products"
app="$products/Debug-iphonesimulator/FieldLog.app"
runner="$products/Debug-iphonesimulator/FieldLogUITests-Runner.app"
test_bundle="$runner/PlugIns/FieldLogUITests.xctest"
for bundle in "$test_bundle" "$runner" "$app"; do
  codesign --force --sign - --timestamp=none "$bundle"
  codesign --verify --strict --deep "$bundle"
  executable=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$bundle/Info.plist")
  test "$(xcrun lipo -archs "$bundle/$executable")" = arm64
  xcrun vtool -show-build "$bundle/$executable" | grep -q 'platform IOSSIMULATOR'
done
test "$(/usr/libexec/PlistBuddy -c 'Print :NSAppTransportSecurity' "$app/Info.plist" |
  tr -d '[:space:]')" = 'Dict{NSAllowsLocalNetworking=true}'
python3 -B "$packet/prepare-run.py" iphonesimulator "$products"
```

The static check verifies the bundle layout, embedded public material, and
whether the generated plan's filters permit the requested selector. XCTest
confirms method availability during runtime dispatch.

For a separately admitted runtime test, root can start `origin.py` and use
`prepare-run.py` with the exact owned device ID. The prepared plan and printed
dispatch command both select the rotation method. Record the actual
`xcodebuild` argument vector as a JSON array in `test-command.json` in the
evidence directory. Run `verify-readback.py` on that directory with the test
summary, attachments, origin receipt, and copied synthetic workspace. Verify
owned-device cleanup before using the native result.
