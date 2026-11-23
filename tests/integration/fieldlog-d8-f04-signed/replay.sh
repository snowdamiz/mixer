#!/usr/bin/env bash
set -euo pipefail
umask 077

# Run from the Mixer repo. Argument 1 is the sealed F10 packet directory.
# Argument 2 is a new, absolute, owned scratch directory under verification/local.
recipe="$PWD/tests/integration/fieldlog-d8-f04-signed"
packet="${1:?F10 packet directory required}"
work="${2:?Owned scratch directory required}"
pin=d245b325e3f6ad08bf29a254db49dfc2f2ed2579
mkdir "$work"
mkdir "$work"/{source,lib,guest,tmp,pair-recipe}
export TMPDIR="$work/tmp" SWIFTCI_USE_LOCAL_DEPS=1 SWIFTPM_MODULECACHE_OVERRIDE="$work/modules"
export CARGO_INCREMENTAL=0 CARGO_PROFILE_RELEASE_DEBUG=0
(cd "$packet" && awk '$2 == "tools/mixer" || $2 == "tools/stock-mixer-service"' MEMBERS.sha256 | shasum -a 256 -c)

git archive "$pin" vm sdk updates capability-activation runtime-identity experimental-capability-runtime |
    tar -xf - -C "$work/source"
for name in swift-crypto swift-asn1; do
    version=$(jq -r --arg name "$name" '.pins[] | select(.identity == $name) | .state.revision' "$work/source/sdk/Package.resolved")
    cache=("$HOME/Library/Caches/org.swift.swiftpm/repositories/$name-"*)
    test "${#cache[@]}" = 1
    mkdir "$work/source/$name"
    git --git-dir="${cache[0]}" archive "$version" | tar -xf - -C "$work/source/$name"
done
sed -i '' 's|.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")|.package(path: "../swift-crypto")|' \
    "$work/source/sdk/Package.swift" "$work/source/updates/Package.swift"

git archive ccb5221cba:tests/integration/fieldlog-pair25-android/rust-runtime-notices \
    prepare-successor.py fieldlog-l07-notices.patch fieldlog-packaging.patch | tar -xf - -C "$work/pair-recipe"
python3 -B "$work/pair-recipe/prepare-successor.py" --mixer "$PWD" "$work/pair"
app="$work/pair/fieldlog"
for name in fieldlog-ios-settings-bounded-7b2b98f0 fieldlog-android-settings-elapsed-7b2b98f0; do
    git show "73717993d6:verification/receipts/$name.patch" |
        git -C "$app" apply --index --unidiff-zero --whitespace=error -
done
test "$(git -C "$app" write-tree)" = 9c2d665c31a6f3f2bfabc42bdfffaf72c6661731
git show 0e42f858c7:verification/local/f04-pair25-stable-lease/pair25-f04-candidate.patch > "$work/pair25.patch"
test "$(shasum -a 256 "$work/pair25.patch" | cut -d' ' -f1)" = 3cbc3455943be884d8b149bad2815f8a7fca21bebc570573d79c47ede8ad4f73
git -C "$app" apply --index --whitespace=error "$work/pair25.patch"
test "$(git -C "$app" write-tree)" = 858e86750570e36cc59f882d4bf21dcd0d9935d1

package="$work/source/capability-activation"
cp -R "$app/Sources/FieldLogModels" "$app/Sources/FieldLogStorage" "$package/Sources/"
mkdir "$package/Sources/F04Control"
cp "$recipe"/{Control,Storage,Release}.swift "$package/Sources/F04Control/"
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
cargo build --offline --locked --release --lib --features experimental-capability-native \
    --manifest-path "$work/source/vm/Cargo.toml" --target-dir "$work/rust"
vm="$work/rust/release/libmixer_vm.a"
ln -s "$vm" "$work/lib/libmixer_vm_capability_experimental.a"
swift build --package-path "$package" --scratch-path "$work/swift" --cache-path "$work/cache" \
    --config-path "$work/config" --security-path "$work/security" --jobs 8 -Xswiftc -gnone \
    -Xcc "-I$work/source/vm/include" -Xlinker "-L$work/lib" --product F04Control

git show "$pin:tests/integration/fieldlog-task-calculation/guest/TaskWire.swift" |
    sed '/private var offset = 0/a\
    var index: Int { offset }
' > "$work/guest/TaskWire.swift"
git show "$pin:tests/integration/fieldlog-saved-draft/guest/CapabilityImports.c" > "$work/guest/CapabilityImports.c"
wasm="$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin"
(
    cd "$work/guest"
    "$wasm/clang" --target=wasm32-unknown-none -ffreestanding -Oz -c CapabilityImports.c -o capability.o
    for variant in prior successor; do
        define=FIELDLOG_BASELINE
        if [[ "$variant" == successor ]]; then define=FIELDLOG_UPDATED; fi
        "$wasm/swiftc" -target wasm32-unknown-none-wasm -enable-experimental-feature Embedded \
            -enable-experimental-feature Extern -whole-module-optimization -Osize -parse-as-library \
            -Xfrontend -disable-stack-protector -D "$define" -module-cache-path modules \
            -emit-object "$recipe/Guest.swift" TaskWire.swift -o "$variant.o"
        "$wasm/wasm-ld" --no-entry --gc-sections --strip-all -z stack-size=16384 --max-memory=65536 \
            --export=mixer_guest_ui_start_v1 --export=mixer_guest_ui_hydrate_v1 \
            --export=mixer_guest_ui_event_v1 --export=mixer_guest_capability_ready_v1 \
            "$variant.o" capability.o -o "$variant.wasm"
    done
)
python3 -B "$recipe/journey.py" "$work/swift/out/Products/Debug/F04Control" \
    "$package/Tests/MixerCapabilityActivationTests/Fixtures" "$work/guest" "$vm" \
    "$packet/tools/stock-mixer-service" "$packet/tools/mixer" "$work/run"
jq '{status, refusal, phases, originCleanup, hold}' "$work/run/receipt.json"
