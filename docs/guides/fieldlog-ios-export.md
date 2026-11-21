# Build the exported FieldLog iOS app

Use Apple silicon, Python 3, and Xcode 27.2 (27B52) with the iOS Simulator 27.2 SDK.
Run the commands in one Bash shell from a Mixer checkout that has the v80
commit. The initial fetch uses public GitHub repositories. The relocated build
uses the export and two verified local Swift package mirrors.

## Fetch and verify the pins

```bash
set -euo pipefail
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0
export LC_ALL=C
unset GIT_CONFIG_COUNT GIT_CONFIG_PARAMETERS SDKROOT SWIFT_EXEC TOOLCHAINS
mixer_rev=5f4277e12e4872df43483307ec607a65e87dbae1
fieldlog_rev=552559d2d3278abb9b1aa7dcf0288102c09a202b
mkdir -p verification/local
work=$(mktemp -d "$PWD/verification/local/fieldlog-ios-export.XXXXXXXX")
printf 'Build scratch %s\n' "$work"
mkdir -p "$work/prep/mixer" "$work/prep/FieldLog" "$work/deps" "$work/relocated"
git archive -o "$work/prep/mixer.tar" "$mixer_rev" cli sdk updates runtime-identity
tar -xf "$work/prep/mixer.tar" -C "$work/prep/mixer"
curl -q -fLsS --max-time 60 --max-filesize 5000000 \
    "https://codeload.github.com/snowdamiz/fieldlog/tar.gz/$fieldlog_rev" \
    -o "$work/prep/fieldlog.tar.gz"
printf '%s  %s\n' 75d2ce2663ade805ca40831b17a460c248e88c62a7689d5a671182bbf0ed7840 \
    "$work/prep/fieldlog.tar.gz" | shasum -a 256 -c
tar -xzf "$work/prep/fieldlog.tar.gz" --strip-components 1 -C "$work/prep/FieldLog"

mirror_package() {
    local repo=$1 tag=$2 revision=$3 mirror="$work/deps/$1.git"
    local remote="https://github.com/apple/$repo.git"
    GIT_ALLOW_PROTOCOL=https git clone --bare --single-branch --depth 1 \
        --branch "$tag" "$remote" "$mirror"
    test "$(git -C "$mirror" rev-parse HEAD)" = "$revision"
    local uri
    uri=$(python3 -B -c 'import pathlib, sys; print(pathlib.Path(sys.argv[1]).as_uri())' "$mirror")
    git config --file "$work/deps/gitconfig" "url.$uri.insteadOf" "$remote"
}
mirror_package swift-crypto 5.0.3 c2cbadd7263439d8015189668f96ff5b5be565ce
mirror_package swift-asn1 1.7.3 3b6410f7dee09eb33cdd26260c5fd47fda19b0e2
export GIT_CONFIG_GLOBAL="$work/deps/gitconfig" GIT_ALLOW_PROTOCOL=file

use_fresh_state() {
    local state=$1
    mkdir -p "$state"/{home,tmp,clang,swift-modules,cache}
    export HOME="$state/home" CFFIXED_USER_HOME="$state/home" TMPDIR="$state/tmp/"
    export CLANG_MODULE_CACHE_PATH="$state/clang" SWIFTPM_MODULECACHE_OVERRIDE="$state/swift-modules"
    export XDG_CACHE_HOME="$state/cache"
}
```

## Prepare and export the original Xcode app

Use `mixer create` to obtain `mixer.yml`, `mixer.lock`, and the exact SDK
snapshot. Copy those three inputs into FieldLog. In the root `Package.swift`,
select the local SDK at `Generated/MixerSDK` and use its `MixerSDK` package
identity for product lookups. Keep the native Xcode project and app sources
from the FieldLog pin. Its app target has an empty resource phase. The
repository's verification PNGs remain in the export.

```bash
use_fresh_state "$work/prep/host"
swift build --package-path "$work/prep/mixer/cli" --scratch-path "$work/prep/cli-build" \
    --cache-path "$work/prep/cli-cache" --config-path "$work/prep/cli-config" \
    --security-path "$work/prep/cli-security" --manifest-cache local \
    --disable-dependency-cache --only-use-versions-from-resolved-file --jobs 6 --product mixer
cli="$work/prep/cli-build/debug/mixer"
app="$work/prep/FieldLog"
carrier="$work/prep/export-metadata"
project=ios/FieldLog.xcodeproj
workspace_lock="$project/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
"$cli" create FieldLog --platform ios --application dev.mixer.fieldlog \
    --directory "$carrier" --sdk-path "$work/prep/mixer/sdk"
cp "$carrier/mixer.yml" "$carrier/mixer.lock" "$app/"
mkdir "$app/Generated"
cp -R "$carrier/Generated/MixerSDK" "$app/Generated/"
python3 -B - "$app/Package.swift" <<'PY'
from pathlib import Path
import sys

manifest = Path(sys.argv[1])
source = manifest.read_bytes()
old = b'.package(url: "https://github.com/snowdamiz/mixer.git", revision: "56ff14c925168284761c5aca4f0bd4129cf3c995")'
if source.count(old) != 1 or source.count(b'package: "mixer"') != 5:
    raise SystemExit("Unexpected FieldLog dependency declarations")
manifest.write_bytes(source.replace(old, b'.package(path: "Generated/MixerSDK")')
                     .replace(b'package: "mixer"', b'package: "MixerSDK"'))
PY
for lock in Package.resolved "$workspace_lock"; do
    cp "$app/Generated/MixerSDK/Package.resolved" "$app/$lock"
done

export_path="$work/export"
relocated="$work/relocated/FieldLog"
"$cli" export "$export_path" --directory "$app"
diff -rq "$app" "$export_path"
mv "$export_path" "$relocated"
rm -rf -- "$work/prep"
test ! -e "$app"
test ! -e "$cli"
```

## Build the relocated export with Xcode

```bash
use_fresh_state "$work/ci"
inventory() {
    (cd "$relocated" && find . -type f -exec shasum -a 256 {} + | LC_ALL=C sort)
}
inventory > "$work/before-build.sha256"
(
    cd "$relocated"
    xcodebuild -project "$project" -scheme FieldLog -configuration Debug \
        -sdk iphonesimulator27.2 -destination 'generic/platform=iOS Simulator' \
        -derivedDataPath "$work/ci/derived" \
        -clonedSourcePackagesDirPath "$work/ci/packages" -packageCachePath "$work/ci/package-cache" \
        -disablePackageRepositoryCache -scmProvider system \
        -onlyUsePackageVersionsFromResolvedFile -disableAutomaticPackageResolution \
        -jobs 4 CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO ARCHS=arm64 build
)
inventory > "$work/after-build.sha256"
cmp "$work/before-build.sha256" "$work/after-build.sha256"
bundle="$work/ci/derived/Build/Products/Debug-iphonesimulator/FieldLog.app"
test "$(plutil -extract CFBundleIdentifier raw "$bundle/Info.plist")" = dev.mixer.fieldlog
test "$(plutil -extract CFBundleExecutable raw "$bundle/Info.plist")" = FieldLog
test ! -e "$bundle/_CodeSignature"
test ! -e "$bundle/embedded.mobileprovision"
xcrun vtool -show-build "$bundle/FieldLog"
xcrun nm "$bundle/FieldLog.debug.dylib" | xcrun swift-demangle > "$work/app-symbols.txt"
grep -m 1 -F 'FieldLog.FieldLogApp.body.getter' "$work/app-symbols.txt"
grep -m 1 -F 'FieldLogStorage.WorkspaceRepository.exportReport' "$work/app-symbols.txt"
```

Expect an arm64 `IOSSIMULATOR` binary. Xcode skips bundle signing. The arm64
linker still adds an ad hoc Mach-O signature with no team or sealed resources.
After the build exits and you finish inspecting the bundle, remove the
disposable `$work` directory.

This verifies the local build and bundle for §16.3 and §22.2.15. Install,
launch, and independent hosted CI remain separate checks.
[Verification receipt](../../verification/receipts/fieldlog-ios-independent-export-v80.json)
