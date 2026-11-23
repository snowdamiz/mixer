#!/usr/bin/env bash
set -euo pipefail
umask 077
ulimit -c 0
stage=$1
fieldlog=$2
f04=$3
f11=$4
work=$5
recipe="$(cd "$(dirname "$0")" && pwd -P)"
stage_pin=1ca46eb93e
producer=4bcfe774f70794b86c014680a351a5f1dbfff3f1
source="$work/source"
package="$source/capability-activation"
phase() { printf '%s\n' "$1" > "$work/phase"; }
stage_git() { git -C "$stage" "$@"; }
phase export
mkdir "$work"/{source,lib,guest,tmp,pair-recipe,cargo}
export TMPDIR="$work/tmp" SWIFTCI_USE_LOCAL_DEPS=1 SWIFTPM_MODULECACHE_OVERRIDE="$work/modules"
export CLANG_MODULE_CACHE_PATH="$work/clang-modules" CARGO_INCREMENTAL=0 CARGO_PROFILE_RELEASE_DEBUG=0
export PATH="$HOME/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin:$PATH"
cargo_cache="${CARGO_HOME:-$HOME/.cargo}"
export CARGO_HOME="$work/cargo"
mkdir "$CARGO_HOME/registry"
cp -cR "$cargo_cache/registry/cache" "$cargo_cache/registry/index" "$CARGO_HOME/registry/"
test "$(stage_git rev-parse "$stage_pin^{tree}")" = bb485a37494a41f64026cdb6013f4a303e849cfe
test "$(shasum -a 256 "$f04/task-retry-replay.patch" | cut -d' ' -f1)" = 851f70692271d0600930e3c51831fcfd68c884bfb6598f6e54a51da13c58110f
f04_base=6c069d95f509e197433118f65b7f39fb3a454412
f04_dir=tests/integration/fieldlog-d8-f04-signed
stage_git archive "$f04_base" vm sdk updates capability-activation runtime-identity \
    experimental-capability-runtime contracts "$f04_dir" | tar -xf - -C "$source"
git -C "$source" init --quiet --template=
git -C "$source" add -f .
git -C "$source" apply --index --unidiff-zero --whitespace=error "$f04/task-retry-replay.patch"
test "$(git -C "$source" write-tree)" = d7c53c7dba790ba4635efdcda73aea3ad2263e9a
stage_git archive ccb5221cba:tests/integration/fieldlog-pair25-android/rust-runtime-notices     prepare-successor.py fieldlog-l07-notices.patch fieldlog-packaging.patch | tar -xf - -C "$work/pair-recipe"
phase pair25
python3 - "$work/pair-recipe/prepare-successor.py" "$fieldlog" <<'PYLOCAL'
import sys
from pathlib import Path
p = Path(sys.argv[1])
old = 'fieldlog["url"], fieldlog["revision"]'
text = p.read_text()
assert text.count(old) == 1
p.write_text(text.replace(old, repr(sys.argv[2]) + ', fieldlog["revision"]'))
PYLOCAL
python3 -B "$work/pair-recipe/prepare-successor.py" --mixer "$stage" "$work/pair" >&2
app="$work/pair/fieldlog"
for name in fieldlog-ios-settings-bounded-7b2b98f0 fieldlog-android-settings-elapsed-7b2b98f0; do
    stage_git show "73717993d6:verification/receipts/$name.patch" | git -C "$app" apply --index --unidiff-zero --whitespace=error -
done
test "$(git -C "$app" write-tree)" = 9c2d665c31a6f3f2bfabc42bdfffaf72c6661731
cp -R "$app/Sources/FieldLogModels" "$app/Sources/FieldLogStorage" "$package/Sources/"
phase fixture
python3 -B "$f11/fixtures.py" "$stage" "$fieldlog" "$work/guest" > "$work/fixture.json"
cp "$source/$f04_dir/Release.swift" "$work/Release.swift"
python3 -B "$recipe/prepare.py" "$source" "$work" "$recipe"
phase dependencies
for name in swift-crypto swift-asn1; do
    version=$(jq -r --arg name "$name" '.pins[] | select(.identity == $name) | .state.revision' "$source/sdk/Package.resolved")
    cache=("$HOME/Library/Caches/org.swift.swiftpm/repositories/$name-"*)
    test "${#cache[@]}" = 1
    mkdir "$source/$name"
    git --git-dir="${cache[0]}" archive "$version" | tar -xf - -C "$source/$name"
done
sed -i '' 's|.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")|.package(path: "../swift-crypto")|'     "$source/sdk/Package.swift" "$source/updates/Package.swift"
rm "$package/Package.resolved"
phase cargo
cargo build --offline --locked --release --lib --features experimental-capability-native     --manifest-path "$source/vm/Cargo.toml" --target-dir "$work/rust" -j 10 >&2
vm="$work/rust/release/libmixer_vm.a"
ln -s "$vm" "$work/lib/libmixer_vm_capability_experimental.a"
phase swift
swift build --disable-sandbox --package-path "$package" --scratch-path "$work/swift" --cache-path "$work/cache"     --config-path "$work/config" --security-path "$work/security" --disable-dependency-cache     --disable-prefetching --disable-index-store --jobs 10 -Xswiftc -gnone     -Xswiftc -DMIXER_PRIVATE_FIELDLOG_EDITOR -Xcc "-I$source/vm/include"     -Xlinker "-L$work/lib" --product F11Vertical >&2
control="$work/swift/out/Products/Debug/F11Vertical"
phase guests
wasm="$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin"
fixtures="$package/Tests/MixerCapabilityActivationTests/Fixtures"
vectors="$source/runtime-identity/Tests/MixerRuntimeIdentityTests/Fixtures/vectors-v2.json"
"$control" stock "$vectors" "$work/guest/editable.json" > "$work/stock.json"
for mode in valid wrong-field wrong-action; do
    mkdir -p "$work/$mode/packet"
    definition=${mode//-/_}
    "$wasm/clang" --target=wasm32-unknown-none -Oz -ffreestanding -fno-builtin -I "$work/guest" \
        "-D$definition" -c "$recipe/Guest.c" -o "$work/guest/$mode.o"
    "$wasm/wasm-ld" --no-entry --gc-sections --strip-all -z stack-size=16384 --max-memory=65536 \
        --export=mixer_guest_ui_start_v1 --export=mixer_guest_ui_hydrate_v1 \
        --export=mixer_guest_ui_event_v1 --export=mixer_guest_capability_ready_v1 \
        "$work/guest/$mode.o" -o "$work/$mode/packet/successor.wasm"
    cp "$work/$mode/packet/successor.wasm" "$work/$mode/packet/prior.wasm"
    phase "signed $mode"
    "$control" prepare "$work/$mode" "$fixtures" "$work/$mode/packet" "$vm" "$work/guest/seed.json"
    "$control" "$mode" "$work/$mode" > "$work/$mode.json"
done
phase receipt
stock_receipt=verification/receipts/l08-d8-f11-signed-host-4aa67a21.json
stage_git show "$stage_pin:$stock_receipt" | jq '.followUpFailures' > "$work/historical-failures.json"
jq -n --arg stage "$(stage_git rev-parse "$stage_pin")" --arg tree "$(stage_git rev-parse "$stage_pin^{tree}")" \
    --arg producer "$producer" --arg swift "$(swift --version | head -1)" --arg rust "$(cargo --version)" \
    --arg wasmClang "$("$wasm/clang" --version | head -1)" --arg vmSHA256 "$(shasum -a 256 "$vm" | cut -d' ' -f1)" \
    --slurpfile stock "$work/stock.json" --slurpfile fixture "$work/fixture.json" --slurpfile overlay "$work/overlay.json" \
    --slurpfile valid "$work/valid.json" --slurpfile field "$work/wrong-field.json" --slurpfile action "$work/wrong-action.json" \
    --slurpfile historical "$work/historical-failures.json" \
    '{status:"observed_signed_f11_vertical_edit", stage:$stage, stageTree:$tree, producer:$producer, vmSHA256:$vmSHA256,
      tools:{swift:$swift,cargo:$rust,wasmClang:$wasmClang}, fixture:$fixture[0], overlay:$overlay[0], stock:$stock[0],
      valid:$valid[0], wrongField:$field[0], wrongAction:$action[0], historicalStockFailures:$historical[0]}'
