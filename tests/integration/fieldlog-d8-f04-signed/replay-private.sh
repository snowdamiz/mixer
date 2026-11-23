#!/usr/bin/env bash
set -euo pipefail
umask 077
ulimit -c 0

recipe="$(cd "$(dirname "$0")" && pwd -P)"
if [[ "${1:-}" != --worker ]]; then
    exec python3 -B "$recipe/run-offline.py" "$@"
fi
shift

stage=$1
local_pair=$2
work=$3
stage_revision=6c069d95f509e197433118f65b7f39fb3a454412
producer_revision=4bcfe774f70794b86c014680a351a5f1dbfff3f1
pin=d245b325e3f6ad08bf29a254db49dfc2f2ed2579
test_dir=tests/integration/fieldlog-d8-f04-signed
mkdir "$work"/{source,lib,guest,tmp,pair-recipe,cargo}
export TMPDIR="$work/tmp" SWIFTCI_USE_LOCAL_DEPS=1 SWIFTPM_MODULECACHE_OVERRIDE="$work/modules"
export CLANG_MODULE_CACHE_PATH="$work/clang-modules"
export CARGO_INCREMENTAL=0 CARGO_PROFILE_RELEASE_DEBUG=0
rust_bin="${F04_RUST_BIN:-$HOME/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin}"
export PATH="$rust_bin:$PATH"
cargo_cache="${CARGO_HOME:-$HOME/.cargo}"
export CARGO_HOME="$work/cargo"
mkdir "$CARGO_HOME/registry"
cp -cR "$cargo_cache/registry/cache" "$cargo_cache/registry/index" "$CARGO_HOME/registry/"

stage_git() { git -C "$stage" "$@"; }
sha256() { shasum -a 256 "$1" | cut -d' ' -f1; }

stage_tree="$(stage_git rev-parse "$stage_revision^{tree}")"
test "$stage_tree" = 4a33d9cb6c1c4d9c5befac67251b223b36ee8d6d
overlay="$recipe/task-retry-replay.patch"
overlay_sha="$(sha256 "$overlay")"
test "$overlay_sha" = 851f70692271d0600930e3c51831fcfd68c884bfb6598f6e54a51da13c58110f
source="$work/source"
stage_git archive "$stage_revision" vm sdk updates capability-activation runtime-identity \
    experimental-capability-runtime contracts "$test_dir" | tar -xf - -C "$source"
git -C "$source" init --quiet --template=
git -C "$source" add -f .
git -C "$source" apply --index --unidiff-zero --whitespace=error "$overlay"
overlay_tree="$(git -C "$source" write-tree)"
# Verify the built modules and contracts against the producer's exact Git subtrees.
while read -r name tree; do
    test "$(git -C "$source" rev-parse "$overlay_tree:$name")" = "$tree"
done <<'TREES'
vm 0a47857d67ec5bd187e5b13df6295d1b0b822642
sdk 98a9ddf957ab4edc7a921f0a6fe690bf148fff30
updates db0ad4cc12626146d94fb0b72bfa18788d60028b
capability-activation 0727cc8d3a071b282f8cf2a60358ddd9d7a9a320
runtime-identity 18db5611dda2427c495ddedefe551d1a53da0e26
experimental-capability-runtime 690408e37f4aadf9a9202dc054f7319e27121b60
contracts 59a544eb4c4a98bf45f198a7702bb1da37267524
TREES
git -C "$source" apply --unidiff-zero --whitespace=error "$recipe/replay-observations.patch"
control_recipe="$source/$test_dir"
contract="$(sha256 "$source/contracts/private-fieldlog-task-retry-v1.json")"
test "$contract" = 7f1d259ded126ff9cbf13d445a28909823e322e9ed79d22307dd2fb5e38efdc1
for name in swift-crypto swift-asn1; do
    version=$(jq -r --arg name "$name" '.pins[] | select(.identity == $name) | .state.revision' "$work/source/sdk/Package.resolved")
    cache=("$HOME/Library/Caches/org.swift.swiftpm/repositories/$name-"*)
    test "${#cache[@]}" = 1
    mkdir "$work/source/$name"
    git --git-dir="${cache[0]}" archive "$version" | tar -xf - -C "$work/source/$name"
done
sed -i '' 's|.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")|.package(path: "../swift-crypto")|' \
    "$work/source/sdk/Package.swift" "$work/source/updates/Package.swift"

stage_git archive ccb5221cbacbe54d382d5eab762bcac57ea594c2:tests/integration/fieldlog-pair25-android/rust-runtime-notices \
    prepare-successor.py fieldlog-l07-notices.patch fieldlog-packaging.patch | tar -xf - -C "$work/pair-recipe"
python3 - "$work/pair-recipe/prepare-successor.py" "$local_pair" <<'PYLOCAL'
import sys
from pathlib import Path
p = Path(sys.argv[1])
text = p.read_text()
old = 'fieldlog["url"], fieldlog["revision"]'
if text.count(old) != 1:
    raise ValueError("Pinned Pair25 recipe changed")
p.write_text(text.replace(old, repr(sys.argv[2]) + ', fieldlog["revision"]'))
PYLOCAL
python3 -B "$work/pair-recipe/prepare-successor.py" --mixer "$stage" "$work/pair" >&2
app="$work/pair/fieldlog"
for name in fieldlog-ios-settings-bounded-7b2b98f0 fieldlog-android-settings-elapsed-7b2b98f0; do
    stage_git show "73717993d6eea1d968b51f86f701e02406436d41:verification/receipts/$name.patch" |
        git -C "$app" apply --index --unidiff-zero --whitespace=error -
done
test "$(git -C "$app" write-tree)" = 9c2d665c31a6f3f2bfabc42bdfffaf72c6661731
stage_git show 0e42f858c7bf184cb7681c1ab6d81e32559a4443:verification/local/f04-pair25-stable-lease/pair25-f04-candidate.patch > "$work/pair25.patch"
test "$(shasum -a 256 "$work/pair25.patch" | cut -d' ' -f1)" = 3cbc3455943be884d8b149bad2815f8a7fca21bebc570573d79c47ede8ad4f73
git -C "$app" apply --index --whitespace=error "$work/pair25.patch"
pair_tree="$(git -C "$app" write-tree)"
test "$pair_tree" = 858e86750570e36cc59f882d4bf21dcd0d9935d1
repository_blob="$(git -C "$app" rev-parse "$pair_tree:Sources/FieldLogStorage/WorkspaceRepository.swift")"
test "$repository_blob" = 9caf7b54aa66a2cb4e4c150b689709b28fadcc8d

package="$work/source/capability-activation"
cp -R "$app/Sources/FieldLogModels" "$app/Sources/FieldLogStorage" "$package/Sources/"
mkdir "$package/Sources/F04Control"
cp "$control_recipe"/{Control,Storage,Release}.swift "$recipe/CompactEditorControl.swift" "$package/Sources/F04Control/"
cat >> "$package/Package.swift" <<'SWIFT'
package.targets.append(contentsOf: [
    .target(name: "FieldLogModels"),
    .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"]),
    .executableTarget(name: "F04Control", dependencies: [
        "MixerCapabilityActivation", "FieldLogModels", "FieldLogStorage",
        .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
        .product(name: "MixerUpdates", package: "updates"),
        .product(name: "MixerCapabilities", package: "sdk"),
        .product(name: "MixerGuest", package: "sdk"),
        .product(name: "MixerUI", package: "sdk"),
    ]),
])
SWIFT
stage_git show "$pin:tests/integration/fieldlog-task-calculation/guest/TaskWire.swift" |
    sed '/private var offset = 0/a\
    var index: Int { offset }
' > "$work/guest/TaskWire.swift"
stage_git show "$pin:tests/integration/fieldlog-saved-draft/guest/CapabilityImports.c" > "$work/guest/CapabilityImports.c"
wasm="${F04_WASM_TOOLS:-$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin}"
(
    cd "$work/guest"
    "$wasm/clang" --target=wasm32-unknown-none -ffreestanding -Oz -c CapabilityImports.c -o capability.o
    python3 - "$control_recipe/Guest.swift" <<'PYGUEST'
import sys
from pathlib import Path
source = Path(sys.argv[1]).read_text()
index = source.rindex("    output.append(field.key)")
Path("misbound.swift").write_text(source[:index] + source[index:].replace(
    "    output.append(field.key)",
    '    if field == .responsible { output.append("misbound") } else { output.append(field.key) }', 1))
Path("wrong-key.swift").write_text(source.replace('"key":"task"', '"key":"other"', 1))
PYGUEST
    for variant in prior successor misbound wrong-key; do
        define=FIELDLOG_BASELINE
        source="$control_recipe/Guest.swift"
        if [[ "$variant" != prior ]]; then define=FIELDLOG_UPDATED; fi
        if [[ "$variant" == misbound || "$variant" == wrong-key ]]; then source="$variant.swift"; fi
        "$wasm/swiftc" -target wasm32-unknown-none-wasm -enable-experimental-feature Embedded \
            -enable-experimental-feature Extern -whole-module-optimization -Osize -parse-as-library \
            -Xfrontend -disable-stack-protector -D "$define" -module-cache-path modules \
            -emit-object "$source" TaskWire.swift -o "$variant.o"
        "$wasm/wasm-ld" --no-entry --gc-sections --strip-all -z stack-size=16384 --max-memory=65536 \
            --export=mixer_guest_ui_start_v1 --export=mixer_guest_ui_hydrate_v1 \
            --export=mixer_guest_ui_event_v1 --export=mixer_guest_capability_ready_v1 \
            "$variant.o" capability.o -o "$variant.wasm"
    done
)
test "$(shasum -a 256 "$work/guest/successor.wasm" | cut -d' ' -f1)" = 11b66e1fa6b5c56e87ff07609871910cb5097ded3efb806dbafee16d08af351b
cargo build --offline --locked --release --lib --features experimental-capability-native \
    --manifest-path "$work/source/vm/Cargo.toml" --target-dir "$work/rust" >&2
vm="$work/rust/release/libmixer_vm.a"
ln -s "$vm" "$work/lib/libmixer_vm_capability_experimental.a"
# The dependency sources above are pinned local archives. The original remote lock
# would make SwiftPM materialize remote checkouts even for these local manifests.
rm "$package/Package.resolved"
swift build --disable-sandbox --package-path "$package" --scratch-path "$work/swift" --cache-path "$work/cache" \
    --config-path "$work/config" --security-path "$work/security" --jobs 10 -Xswiftc -gnone \
    -Xswiftc -DMIXER_PRIVATE_FIELDLOG_EDITOR -Xcc "-I$work/source/vm/include" -Xlinker "-L$work/lib" --product F04Control >&2
control="$work/swift/out/Products/Debug/F04Control"
fixtures="$package/Tests/MixerCapabilityActivationTests/Fixtures"
vectors="$work/source/runtime-identity/Tests/MixerRuntimeIdentityTests/Fixtures/vectors-v2.json"
vector_count="$("$control" stock-fingerprints "$vectors")"
test "$vector_count" = 11

for mode in stock private misbound wrong-key; do
    mkdir "$work/$mode"
    guest="$work/guest"
    opts=(--private-retry)
    if [[ "$mode" == stock ]]; then
        opts=()
    elif [[ "$mode" != private ]]; then
        guest="$work/guest/$mode"
        mkdir "$guest"
        cp "$work/guest/prior.wasm" "$guest/prior.wasm"
        cp "$work/guest/$mode.wasm" "$guest/successor.wasm"
    fi
    "$control" prepare "$work/$mode" "$fixtures" "$guest" "$vm" "${opts[@]}"
    if [[ "$mode" == stock ]]; then
        "$control" prior "$work/stock" --direct > "$work/stock-prior.json"
    fi
    if [[ "$mode" != private ]]; then opts+=(--expect-refusal); fi
    "$control" successor "$work/$mode" --direct "${opts[@]}" > "$work/$mode.json"
    if [[ "$mode" != private ]]; then
        jq -e '.lastRecovery == "ui_protocol_after_effects"' "$work/$mode/recovery/state.json" >/dev/null
    fi
done

"$control" cold-read "$work/private" "$(jq -er .workspaceSHA256 "$work/private.json")" > "$work/cold.sha256"
"$control" compact-editor "$work/private" > "$work/compact.json"
jq -e --slurpfile prior "$work/stock-prior.json" '
    .workspaceReads == 1 and .puts == [] and .presentationAdmitted == false
    and .previousHealthyPreserved == true and .previousHealthy == $prior[0].candidate
    and .workspaceSHA256 == $prior[0].workspaceSHA256
' "$work/stock.json" >/dev/null
for mode in misbound wrong-key; do
    reads=0
    if [[ "$mode" == misbound ]]; then reads=1; fi
    jq -e --argjson reads "$reads" '
        .workspaceReads == $reads and .puts == [] and .presentationAdmitted == false
        and .healthyCandidateSeeded == false and (has("previousHealthyPreserved") | not)
    ' "$work/$mode.json" >/dev/null
done

jq -n --slurpfile private "$work/private.json" --slurpfile prior "$work/stock-prior.json" \
    --slurpfile stock "$work/stock.json" --slurpfile misbound "$work/misbound.json" \
    --slurpfile wrongKey "$work/wrong-key.json" --slurpfile compact "$work/compact.json" \
    --rawfile cold "$work/cold.sha256" --argjson stockVectors "$vector_count" \
    --arg stageCommit "$stage_revision" --arg stageTree "$stage_tree" \
    --arg producerCommit "$producer_revision" --arg overlaySHA256 "$overlay_sha" \
    --arg exportedOverlayTree "$overlay_tree" --arg contractSHA256 "$contract" \
    --arg vmSHA256 "$(sha256 "$vm")" --arg repositoryBlob "$repository_blob" \
    --arg pairTree "$pair_tree" --arg wasmSHA256 "$(sha256 "$work/guest/successor.wasm")" \
    --arg swift "$(swift --version | head -n 1)" --arg cargo "$(cargo --version)" \
    --arg wasmSwift "$("$wasm/swiftc" --version | head -n 1)" --arg git "$(git --version)" \
    '{
        stage: {commit: $stageCommit, tree: $stageTree, readOnly: true},
        overlay: {producerCommit: $producerCommit, sha256: $overlaySHA256,
                  exportedTree: $exportedOverlayTree, contractSHA256: $contractSHA256,
                  vmArchiveSHA256: $vmSHA256},
        pair25: {candidateTree: $pairTree, repositoryBlob: $repositoryBlob,
                 successorWasmSHA256: $wasmSHA256},
        tools: {swift: $swift, cargo: $cargo, embeddedSwift: $wasmSwift, git: $git},
        privateRetry: $private[0], stockPrior: $prior[0], stockRefusal: $stock[0],
        misbound: $misbound[0], wrongKey: $wrongKey[0], compactEditor: $compact[0],
        coldSHA256: ($cold | rtrimstr("\n")), stockVectors: $stockVectors
    }'
