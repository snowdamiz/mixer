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

## Build the maintained FieldLog app with the capability VM

Use the same Xcode, local mirror, and fresh-state setup as above. This recipe
pins public Mixer to `6bc461f4fc7c29771718c7c5ce5a2a39b78f4d2d` and reconstructs
FieldLog product tree `85e6fbe362c50553a781daba1e467c6829eb668c` from public
FieldLog commit `552559d2d3278abb9b1aa7dcf0288102c09a202b`. Run from the root
of a Mixer checkout containing this guide and the relocated-export receipt.
Start with an empty scratch directory. The reconstruction step reads the
ordered recipe from `5fd075d6df49ccf2b2e4699a7bc2e59c7b3fd2e8` with `git show`.
[Matched compiler inputs](../../verification/receipts/fieldlog-d2-combined-85e6fbe3-compiler-inputs.json)

Before the first `use_fresh_state` call, resolve Rust 1.99.0 from your
installed toolchain. The pinned VM has no Cargo registry dependencies.

```bash
cargo_bin="$(rustup which --toolchain 1.99.0 cargo)"
rustc_bin="$(rustup which --toolchain 1.99.0 rustc)"
test -x "$cargo_bin"
test -x "$rustc_bin"
test -d "$("$rustc_bin" --print target-libdir --target aarch64-apple-ios-sim)"
receipt="$PWD/verification/receipts/fieldlog-d2-combined-85e6fbe3-relocated-ios-export.json"
test -f "$receipt"
```

### Reconstruct the FieldLog source

Set `mixer_rev` to the Mixer pin in this section. Verify that
`git rev-parse "$mixer_rev^{tree}"` returns
`d888b6a1ef9331079b98a0dc21c3a1b8ee482894`. Add `capability-activation`,
`experimental-capability-runtime`, and `vm` to the paths in the Mixer
`git archive` command. Use the two bare mirrors from the v80 procedure and
verify both the commit and tree for each mirror.

| Package | Tag | Commit | Tree |
| --- | --- | --- | --- |
| swift-crypto | `5.0.3` | `c2cbadd7263439d8015189668f96ff5b5be565ce` | `841fdfd88fed694e6532a3200a91b0f85595c340` |
| swift-asn1 | `1.7.3` | `3b6410f7dee09eb33cdd26260c5fd47fda19b0e2` | `e7ed2e8c1483426c349b678e7d10940509f9d39c` |

Use the following commands in place of the FieldLog tar download and extract.
Run the fetch before restricting Git transport to the local mirrors, or set
`GIT_ALLOW_PROTOCOL=https` for the fetch as shown.

```bash
recipe=5fd075d6df49ccf2b2e4699a7bc2e59c7b3fd2e8
fieldlog_rev=552559d2d3278abb9b1aa7dcf0288102c09a202b
source_repo="$work/prep/fieldlog-git"
app="$work/prep/FieldLog"
git init -q "$source_repo"
GIT_ALLOW_PROTOCOL=https git -C "$source_repo" fetch -q --depth=1 --no-tags \
    https://github.com/snowdamiz/fieldlog.git "$fieldlog_rev"
git -C "$source_repo" checkout -q --detach FETCH_HEAD
test "$(git -C "$source_repo" rev-parse HEAD)" = "$fieldlog_rev"
test "$(git -C "$source_repo" write-tree)" = 1b62520f35c7e57a01b568291078686574f627c4
git show "$recipe:verification/receipts/fieldlog-d2-combined-85e6fbe3-compiler-inputs.json" \
    > "$work/prep/compiler-inputs.json"

python3 -B - "$source_repo" "$work/prep/compiler-inputs.json" <<'PY'
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

source = Path(sys.argv[1])
recipe = json.loads(Path(sys.argv[2]).read_text())
for item in recipe["fieldLog"]["orderedMaterial"]:
    spec = item["objectRevision"] + ":" + item["path"]
    data = subprocess.check_output(["git", "show", spec])
    assert sha256(data).hexdigest() == item["sha256"], spec
    if item["path"].endswith(".patch"):
        subprocess.run(["git", "apply", "--index", "--whitespace=nowarn"],
                       cwd=source, input=data, check=True)
    else:
        assert item["path"].endswith("/EntrySaveDecision.swift"), spec
        path = "Integrations/GeneratedReport/Sources/FieldLogFeatures/EntrySaveDecision.swift"
        (source / path).write_bytes(data)
        subprocess.run(["git", "add", "--", path], cwd=source, check=True)
    tree = subprocess.check_output(["git", "write-tree"], cwd=source, text=True).strip()
    assert tree == item["observedTree"], spec
PY

test "$(git -C "$source_repo" write-tree)" = 85e6fbe362c50553a781daba1e467c6829eb668c
git -C "$source_repo" checkout-index --all --prefix="$app/"
```

### Prepare the export and link the VM

Build the unmodified pinned CLI and run `mixer create` as above. Copy the
resulting `mixer.yml`, `mixer.lock`, and `Generated/MixerSDK` into FieldLog.
Keep the SDK snapshot byte-for-byte. Make these path changes in the preparation
app before export.

1. In the root `Package.swift`, change `../mixer/sdk` to `Generated/MixerSDK`
   and change the `package: "sdk"` product lookups to `package: "MixerSDK"`.
2. Under `Generated`, copy the pinned `capability-activation`,
   `experimental-capability-runtime`, `runtime-identity`, and `updates` packages.
   Copy each package's `Package.swift`, `Sources`, `Tests`, and
   `Package.resolved` where present.
3. In the copied activation and runtime manifests, change `../sdk` to
   `../MixerSDK` and the `package: "sdk"` lookups to `package: "MixerSDK"`.
4. In `ios/FieldLog.xcodeproj/project.pbxproj`, set the activation package
   reference to `../Generated/capability-activation`. Copy the SDK
   `Package.resolved` to the root and Xcode workspace lock paths as above.

Use Rust 1.99.0 with the installed `aarch64-apple-ios-sim` target. Build the
pinned VM offline and add its headers and archive to the preparation app.

```bash
vm="$app/Generated/CapabilityVM"
cargo_target="$work/prep/cargo-target"
mkdir -p "$vm" "$work/prep/cargo-home"
SDKROOT="$(xcrun --sdk iphonesimulator27.2 --show-sdk-path)" \
CARGO_HOME="$work/prep/cargo-home" RUSTC="$rustc_bin" \
"$cargo_bin" build --manifest-path "$work/prep/mixer/vm/Cargo.toml" \
    --offline --locked --release --features experimental-capability-native \
    --lib --target aarch64-apple-ios-sim --target-dir "$cargo_target" --jobs 6
cp -R "$work/prep/mixer/vm/include" "$vm/"
cp "$cargo_target/aarch64-apple-ios-sim/release/libmixer_vm.a" \
    "$vm/libmixer_vm_capability_experimental.a"
```

Export and move the prepared tree. Compare every relative path and regular
file's mode and bytes across preparation, export, and relocation.

```bash
export_path="$work/export"
relocated="$work/relocated/FieldLog"
inventory() {
    python3 -B - "$1" <<'PY'
from hashlib import sha256
import json
from pathlib import Path
import stat
import sys

root = Path(sys.argv[1])
entries = {}
for path in root.rglob("*"):
    mode = path.lstat().st_mode
    key = path.relative_to(root).as_posix()
    if stat.S_ISDIR(mode):
        entries[key] = ["d"]
    elif stat.S_ISREG(mode):
        data = path.read_bytes()
        entries[key] = ["f", oct(stat.S_IMODE(mode)), len(data), sha256(data).hexdigest()]
    else:
        raise SystemExit(f"Unexpected entry type: {key}")
print(json.dumps(entries, sort_keys=True, separators=(",", ":")))
PY
}

inventory "$app" > "$work/preparation.json"
"$cli" export "$export_path" --directory "$app"
inventory "$export_path" > "$work/export.json"
cmp "$work/preparation.json" "$work/export.json"
mv "$export_path" "$relocated"
inventory "$relocated" > "$work/relocated.json"
cmp "$work/export.json" "$work/relocated.json"
rm -rf -- "$work/prep"
test ! -e "$app"
test ! -e "$cli"
```

Build with fresh state, the two local mirrors, and the relocated VM headers
and archive.

```bash
use_fresh_state "$work/ci"
(
    cd "$relocated"
    vm="$relocated/Generated/CapabilityVM"
    xcodebuild -project ios/FieldLog.xcodeproj -scheme FieldLog -configuration Debug \
        -sdk iphonesimulator27.2 -destination 'generic/platform=iOS Simulator' \
        -derivedDataPath "$work/ci/derived" \
        -clonedSourcePackagesDirPath "$work/ci/packages" -packageCachePath "$work/ci/package-cache" \
        -resultBundlePath "$work/ci/build.xcresult" -disablePackageRepositoryCache \
        -scmProvider system -onlyUsePackageVersionsFromResolvedFile \
        -disableAutomaticPackageResolution -skipPackageUpdates -jobs 4 \
        CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO ARCHS=arm64 ONLY_ACTIVE_ARCH=NO \
        ENABLE_DEBUG_DYLIB=NO "HEADER_SEARCH_PATHS=\$(inherited) $vm/include" \
        "LIBRARY_SEARCH_PATHS=$vm" LD_GENERATE_MAP_FILE=YES build
)
```

Check the relocated inventory and locks after Xcode. The only permitted
additions are the empty SwiftPM directories listed in the receipt.

```bash
inventory "$relocated" > "$work/post-build.json"
python3 -B - "$work/relocated.json" "$work/post-build.json" "$receipt" <<'PY'
import json
from pathlib import Path
import sys

before, after, receipt = [json.loads(Path(name).read_bytes()) for name in sys.argv[1:]]
locks = {
    "mixer.lock",
    "Package.resolved",
    "Generated/MixerSDK/Package.resolved",
    "ios/FieldLog.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved",
}
if any(before.get(path, [None])[0] != "f" for path in locks):
    raise SystemExit("Expected project, SDK, and app package locks")
if any(after.get(path) != entry for path, entry in before.items()):
    raise SystemExit("Changed or removed export entry, including package locks")
allowed = set(receipt["export"]["xcodeOnlyAddedEmptyDirectories"])
added = after.keys() - before.keys()
if added - allowed or any(after[path] != ["d"] for path in added):
    raise SystemExit(f"Unexpected export additions: {sorted(added)}")
PY

bundle="$work/ci/derived/Build/Products/Debug-iphonesimulator/FieldLog.app"
test "$(plutil -extract CFBundleIdentifier raw "$bundle/Info.plist")" = dev.mixer.fieldlog
test "$(plutil -extract CFBundleExecutable raw "$bundle/Info.plist")" = FieldLog
test "$(xcrun lipo -archs "$bundle/FieldLog")" = arm64
xcrun vtool -show-build "$bundle/FieldLog" > "$work/macho-build.txt"
grep -Eq '^[[:space:]]*platform[[:space:]]+IOSSIMULATOR$' "$work/macho-build.txt"
test ! -e "$bundle/_CodeSignature"
test ! -e "$bundle/embedded.mobileprovision"
xcrun nm -U "$bundle/FieldLog" > "$work/app-symbols.txt"
link_map="$work/ci/derived/Build/Intermediates.noindex/FieldLog.build/Debug-iphonesimulator/FieldLog.build/FieldLog-LinkMap-normal-arm64.txt"
python3 -B - "$bundle" "$work/app-symbols.txt" "$link_map" "$receipt" <<'PY'
from hashlib import sha256
import json
from pathlib import Path
import re
import stat
import sys

bundle, symbols, link_map, receipt = map(Path, sys.argv[1:])
receipt = json.loads(receipt.read_bytes())
definitions = {line.split()[-1] for line in symbols.read_text().splitlines() if line.split()}
expected = set(receipt["linkedBundle"]["definedSymbols"].values())
if not expected <= definitions:
    raise SystemExit(f"Missing definitions: {sorted(expected - definitions)}")
lines = link_map.read_bytes()
objects = dict(re.findall(rb"^\[\s*(\d+)\]\s+(.+)$", lines.split(b"# Sections:", 1)[0], re.M))
archive = b"libmixer_vm_capability_experimental.a("
archive_objects = {int(index) for index, name in objects.items() if archive in name}
for symbol in receipt["linkedBundle"]["vmSymbolArchiveMembers"]:
    pattern = rb"^0x[0-9a-fA-F]+\s+0x[0-9a-fA-F]+\s+\[\s*(\d+)\]\s+" + re.escape(symbol.encode()) + rb"$"
    if not archive_objects.intersection(int(index) for index in re.findall(pattern, lines, re.M)):
        raise SystemExit(f"Link map does not attribute {symbol} to the VM archive")

for folder, expected in receipt["export"]["placeholderResources"].items():
    root = bundle / folder
    if {entry.name for entry in root.iterdir()} != expected.keys():
        raise SystemExit(f"Unexpected guest resources: {folder}")
    for name, entry in expected.items():
        path = root / name
        mode = path.lstat().st_mode
        if not stat.S_ISREG(mode):
            raise SystemExit(f"Expected a regular placeholder: {path}")
        data = path.read_bytes()
        if ["f", oct(stat.S_IMODE(mode)), len(data), sha256(data).hexdigest()] != entry:
            raise SystemExit(f"Changed guest placeholder: {path}")
PY
```

The checks cover the ordinary app, shared repository and checklist, VM, and
placeholder-only guest folders. The CLI metadata declares an empty
capabilities list. The companion iPhoneOS receipt verifies a separately
packaged synthetic Entry Commit. Installed execution and native signing
remain open for this export. Remove disposable scratch after verifying
command closure. [Simulator export receipt](../../verification/receipts/fieldlog-d2-combined-85e6fbe3-relocated-ios-export.json) · [Companion iPhoneOS receipt](../../verification/receipts/fieldlog-d2-combined-85e6fbe3-iphoneos.json)
