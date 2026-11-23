#!/usr/bin/env bash
set -euo pipefail
umask 077
# Invoke from the Mixer checkout with a new, empty, owned verification/local directory.
work=${1:?absolute scratch path}
fieldlog=${2:?retained FieldLog checkout}
recipe="$PWD/tests/integration/fieldlog-d8-f09-signed"
pin=d245b325e3f6ad08bf29a254db49dfc2f2ed2579
history=552559d2d3278abb9b1aa7dcf0288102c09a202b
export GIT_NO_LAZY_FETCH=1 GIT_NO_REPLACE_OBJECTS=1 SWIFTCI_USE_LOCAL_DEPS=1 CARGO_NET_OFFLINE=true CARGO_INCREMENTAL=0 CARGO_PROFILE_RELEASE_DEBUG=0
export TMPDIR="$work/tmp" SWIFTPM_MODULECACHE_OVERRIDE="$work/modules"
mkdir "$work"/{source,lib,guest,tmp}
test "$(git rev-parse "$pin^{tree}")" = be1ea6f69f516473a4e259d51234df428755bd28
test "$(git -C "$fieldlog" rev-parse "$history^{tree}")" = 1b62520f35c7e57a01b568291078686574f627c4
git archive "$pin" vm sdk updates capability-activation runtime-identity experimental-capability-runtime |
    tar -xf - -C "$work/source"
for name in swift-crypto swift-asn1; do
    version=$(jq -er --arg name "$name" '.pins[] | select(.identity == $name) | .state.revision' "$work/source/sdk/Package.resolved")
    caches=("$HOME/Library/Caches/org.swift.swiftpm/repositories/$name-"*)
    test "${#caches[@]}" = 1
    mkdir "$work/source/$name"
    git --git-dir="${caches[0]}" archive "$version" | tar -xf - -C "$work/source/$name"
done
sed -i '' 's|.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")|.package(path: "../swift-crypto")|' \
    "$work/source/sdk/Package.swift" "$work/source/updates/Package.swift"
package="$work/source/capability-activation"
for source in FieldLogModels/Workspace.swift FieldLogStorage/WorkspaceRepository.swift; do
    mkdir -p "$package/Sources/$(dirname "$source")"
    git -C "$fieldlog" show "$history:Integrations/GeneratedReport/Sources/$source" > "$package/Sources/$source"
done
test "$(git hash-object "$package/Sources/FieldLogModels/Workspace.swift")" = 91615788bea186663fbb8a23231e304802366f8a
test "$(git hash-object "$package/Sources/FieldLogStorage/WorkspaceRepository.swift")" = c3aa7a10eae986efa52c1bdfb28d3c4c61bc8153
mkdir "$package/Sources/F09Control"
cp "$recipe"/{Control,Storage}.swift "$package/Sources/F09Control/"
python3 -B "$recipe/journey.py" --release-source > "$package/Sources/F09Control/Release.swift"
cat >> "$package/Package.swift" <<'SWIFT'
package.targets.append(contentsOf: [
    .target(name: "FieldLogModels"),
    .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"]),
    .executableTarget(name: "F09Control", dependencies: [
        "MixerCapabilityActivation", "FieldLogModels", "FieldLogStorage",
        .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
        .product(name: "MixerUpdates", package: "updates"),
        .product(name: "MixerCapabilities", package: "sdk"),
        .product(name: "MixerGuest", package: "sdk"),
        .product(name: "MixerUI", package: "sdk"),
    ]),
])
SWIFT
cargo build --jobs 10 --offline --locked --release --lib --features experimental-capability-native \
    --manifest-path "$work/source/vm/Cargo.toml" --target-dir "$work/rust"
ln -s "$work/rust/release/libmixer_vm.a" "$work/lib/libmixer_vm_capability_experimental.a"
swift build --package-path "$package" --scratch-path "$work/swift" --cache-path "$work/cache" \
    --config-path "$work/config" --security-path "$work/security" --disable-dependency-cache --disable-prefetching --disable-index-store --jobs 10 -Xswiftc -gnone \
    -Xcc "-I$work/source/vm/include" -Xlinker "-L$work/lib" --product F09Control

git show "$pin:tests/integration/fieldlog-task-calculation/guest/TaskWire.swift" |
    sed 's/let rowCount = 3/let rowCount = 23/' > "$work/guest/TaskWire.swift"
git show "$pin:tests/integration/fieldlog-saved-draft/guest/CapabilityImports.c" > "$work/guest/CapabilityImports.c"
wasm="$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin"
cd "$work/guest"
"$wasm/clang" --target=wasm32-unknown-none -ffreestanding -Oz -c CapabilityImports.c -o capability.o
for variant in prior exact; do
    define=FIELDLOG_BASELINE
    if [[ "$variant" == exact ]]; then define=FIELDLOG_UPDATED; fi
    "$wasm/swiftc" -target wasm32-unknown-none-wasm -enable-experimental-feature Embedded \
        -enable-experimental-feature Extern -whole-module-optimization -Osize -parse-as-library \
        -Xfrontend -disable-stack-protector -D "$define" -module-cache-path modules \
        -emit-object "$recipe/Guest.swift" TaskWire.swift -o "$variant.o"
    "$wasm/wasm-ld" --no-entry --gc-sections --strip-all -z stack-size=16384 --max-memory=65536 \
        --export=mixer_guest_ui_start_v1 --export=mixer_guest_ui_hydrate_v1 \
        --export=mixer_guest_ui_event_v1 --export=mixer_guest_capability_ready_v1 \
        "$variant.o" capability.o -o "$variant.wasm"
done
