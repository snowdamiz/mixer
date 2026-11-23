#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
stage=${1:?read-only f4a7fca378 Stage}
fieldlog=${2:?local FieldLog mirror}
tools=${3:?stock local origin and CLI}
work=${4:?new absolute scratch directory}
recipe="$PWD/tests/integration/fieldlog-d8-f11-signed"
test "$(git -C "$stage" rev-parse f4a7fca378^{commit})" = f4a7fca378737786642647939ea61d17df80327d
test "$(shasum -a 256 "$tools/mixer" | cut -d ' ' -f 1)" = 337d054c7f16dd38f3c9b4befeeba6e821d3f6697045d602cfd6af7ddf2c0a08
test "$(shasum -a 256 "$tools/stock-mixer-service" | cut -d ' ' -f 1)" = f759e2f60670bd39d8aa52cfa54b58b9c3011ebf4740dabbc272df07cf082dcb
mkdir "$work"
umask 077
export GIT_NO_LAZY_FETCH=1 GIT_NO_REPLACE_OBJECTS=1 GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0 GIT_OPTIONAL_LOCKS=0 CARGO_NET_OFFLINE=true CARGO_INCREMENTAL=0 CARGO_PROFILE_RELEASE_DEBUG=0
mkdir "$work"/{source,lib,guest,tmp,pair-recipe}
export TMPDIR="$work/tmp"
export PATH="$HOME/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin:$PATH"
git archive 4bcfe774f7 vm sdk updates capability-activation runtime-identity experimental-capability-runtime | tar -xf - -C "$work/source"
git archive ccb5221cba:tests/integration/fieldlog-pair25-android/rust-runtime-notices prepare-successor.py fieldlog-l07-notices.patch fieldlog-packaging.patch | tar -xf - -C "$work/pair-recipe"
python3 - "$work/pair-recipe/prepare-successor.py" "$fieldlog" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1])
text = p.read_text()
old = 'fieldlog["url"], fieldlog["revision"]'
assert text.count(old) == 1
p.write_text(text.replace(old, repr(sys.argv[2]) + ', fieldlog["revision"]'))
PY
python3 -B "$work/pair-recipe/prepare-successor.py" --mixer "$PWD" "$work/pair" >&2
app="$work/pair/fieldlog"
for name in fieldlog-ios-settings-bounded-7b2b98f0 fieldlog-android-settings-elapsed-7b2b98f0; do
    git show "73717993d6:verification/receipts/$name.patch" | git -C "$app" apply --index --unidiff-zero --whitespace=error -
done
test "$(git -C "$app" write-tree)" = 9c2d665c31a6f3f2bfabc42bdfffaf72c6661731
package="$work/source/capability-activation"
cp -R "$app/Sources/FieldLogModels" "$app/Sources/FieldLogStorage" "$package/Sources/"
for name in swift-crypto swift-asn1; do
    version=$(jq -r --arg name "$name" '.pins[] | select(.identity == $name) | .state.revision' "$work/source/sdk/Package.resolved")
    cache=("$HOME/Library/Caches/org.swift.swiftpm/repositories/$name-"*)
    test "${#cache[@]}" = 1
    mkdir "$work/source/$name"
    git --git-dir="${cache[0]}" archive "$version" | tar -xf - -C "$work/source/$name"
done
sed -i '' 's|.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")|.package(path: "../swift-crypto")|' "$work/source/sdk/Package.swift" "$work/source/updates/Package.swift"
rm "$package/Package.resolved"

mkdir "$package/Sources/F11Control" "$package/Sources/FieldLogFeatures"
cp "$app/Integrations/GeneratedReport/Sources/FieldLogFeatures/"{EntryEditor,EntrySaveDecision}.swift "$package/Sources/FieldLogFeatures/"
cp "$recipe/Control.swift" "$package/Sources/F11Control/"
digest=$(shasum -a 256 "$package/Sources/FieldLogStorage/WorkspaceRepository.swift" | cut -d ' ' -f 1)
python3 -B "$recipe/journey.py" --release-source "$digest" > "$package/Sources/F11Control/Release.swift"
cat >> "$package/Package.swift" <<'SWIFT'
package.targets.append(contentsOf: [
    .target(name: "FieldLogModels"),
    .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"]),
    .target(name: "FieldLogFeatures", dependencies: ["FieldLogModels", .product(name: "MixerCore", package: "sdk")]),
    .executableTarget(name: "F11Control", dependencies: [
        "MixerCapabilityActivation", "FieldLogModels", "FieldLogStorage", "FieldLogFeatures",
        .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
        .product(name: "MixerUpdates", package: "updates"),
        .product(name: "MixerCapabilities", package: "sdk"),
        .product(name: "MixerGuest", package: "sdk"),
        .product(name: "MixerUI", package: "sdk"),
    ]),
])
SWIFT

cargo build --offline --locked --release --lib --features experimental-capability-native \
    --manifest-path "$work/source/vm/Cargo.toml" --target-dir "$work/rust" -j 10 >&2
vm="$work/rust/release/libmixer_vm.a"
ln -s "$vm" "$work/lib/libmixer_vm_capability_experimental.a"
export SWIFTCI_USE_LOCAL_DEPS=1 SWIFTPM_MODULECACHE_OVERRIDE="$work/modules"
swift build --package-path "$package" --scratch-path "$work/swift" --cache-path "$work/cache" \
    --config-path "$work/config" --security-path "$work/security" --disable-dependency-cache \
    --disable-prefetching --disable-index-store --jobs 10 -Xswiftc -gnone \
    -Xswiftc -DMIXER_PRIVATE_FIELDLOG_EDITOR -Xcc "-I$work/source/vm/include" \
    -Xlinker "-L$work/lib" --product F11Control >&2
python3 -B "$recipe/fixtures.py" "$stage" "$fieldlog" "$work/guest" > "$work/fixture.json"
wasm="$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin"
mkdir "$work/guest/private"
build_guest() {
    local destination=$1
    shift
    "$wasm/clang" --target=wasm32-unknown-none -Oz -ffreestanding -fno-builtin -I "$work/guest" \
        "$@" -c "$recipe/Guest.c" -o "$destination.o"
    "$wasm/wasm-ld" --no-entry --gc-sections --strip-all -z stack-size=16384 --max-memory=65536 \
        --export=mixer_guest_ui_start_v1 --export=mixer_guest_ui_hydrate_v1 \
        --export=mixer_guest_ui_event_v1 --export=mixer_guest_capability_ready_v1 \
        "$destination.o" -o "$destination.wasm"
}
build_guest "$work/guest/prior"
build_guest "$work/guest/successor" -DF11_SUCCESSOR
build_guest "$work/guest/private/successor" -DF11_SUCCESSOR -DF11_PRIVATE
cp "$work/guest/prior.wasm" "$work/guest/private/"
swift --version > "$work/swift-version"
cargo --version > "$work/cargo-version"
"$wasm/clang" --version > "$work/clang-version"
python3 -B "$recipe/verify.py" "$stage" "$tools" "$work" "$SECONDS"
