#!/usr/bin/env bash
set -euo pipefail
umask 077
work=${1:?empty owned scratch path}
stage=${2:?read-only Mixer Stage}
fieldlog=${3:?pinned local FieldLog Git checkout}
recipe="$(cd "$(dirname "$0")" && pwd)"
pin=d245b325e3f6ad08bf29a254db49dfc2f2ed2579
parent=00c8fe0400bc9a06242371ce7b02cd440f64f31e
fieldlog_pin=552559d2d3278abb9b1aa7dcf0288102c09a202b
factory=Integrations/GeneratedReport/Sources/FieldLogAndroid/PublicFactory.swift
export GIT_NO_LAZY_FETCH=1 SWIFTCI_USE_LOCAL_DEPS=1 CARGO_INCREMENTAL=0 CARGO_PROFILE_RELEASE_DEBUG=0
export PATH="$HOME/.rustup/toolchains/stable-aarch64-apple-darwin/bin:$PATH"
export TMPDIR="$work/tmp" SWIFTPM_MODULECACHE_OVERRIDE="$work/modules"
mkdir "$work"/{source,lib,guest,tmp}
git -C "$stage" ls-tree "$parent" -- "$factory" | test -z "$(cat)"
test "$(git -C "$fieldlog" rev-parse "$fieldlog_pin^{tree}")" = 1b62520f35c7e57a01b568291078686574f627c4
test "$(git -C "$fieldlog" rev-parse "$fieldlog_pin:$factory")" = 73b481f6d58e46d71175ae805004ddd9ee39bd81
git -C "$fieldlog" show "$fieldlog_pin:$factory" > "$work/PublicFactory.swift"
test "$(sed -n '534,543p' "$work/PublicFactory.swift" | shasum -a 256 | cut -d' ' -f1)" = 20f2f000713ab03c5186b0c19df617d2cb10a548988658dcfebf963aae03dd37
test "$(sed -n '590,613p' "$work/PublicFactory.swift" | shasum -a 256 | cut -d' ' -f1)" = d1a660642f7236e4cf60425723e1c5d484082afa82493d144f5708f1da69a5e6
git -C "$stage" archive "$pin" vm sdk updates capability-activation runtime-identity experimental-capability-runtime |
    tar -xf - -C "$work/source"
for name in swift-crypto swift-asn1; do
    revision=$(jq -er --arg name "$name" '.pins[] | select(.identity == $name) | .state.revision' "$work/source/sdk/Package.resolved")
    caches=("$HOME/Library/Caches/org.swift.swiftpm/repositories/$name-"*)
    test "${#caches[@]}" = 1
    mkdir "$work/source/$name"
    git --git-dir="${caches[0]}" archive "$revision" | tar -xf - -C "$work/source/$name"
done
sed -i '' 's|.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")|.package(path: "../swift-crypto")|' \
    "$work/source/sdk/Package.swift" "$work/source/updates/Package.swift"
package="$work/source/capability-activation"
sources=Integrations/GeneratedReport/Sources
for item in FieldLogModels/Workspace.swift FieldLogStorage/WorkspaceRepository.swift; do
    mkdir -p "$package/Sources/$(dirname "$item")"
    git -C "$fieldlog" show "$fieldlog_pin:$sources/$item" > "$package/Sources/$item"
done
mkdir "$package/Sources/F08Control"
cp "$recipe"/{Control,Storage}.swift "$package/Sources/F08Control/"
python3 -B "$recipe/journey.py" "$stage" --release-source > "$package/Sources/F08Control/Release.swift"
sed -n '/^package.targets.append/,/^SWIFT$/p' "$stage/tests/integration/fieldlog-d8-f08-signed/build.sh" |
    sed '$d' >> "$package/Package.swift"
cargo build --offline --locked --release --lib --features experimental-capability-native \
    --manifest-path "$work/source/vm/Cargo.toml" --target-dir "$work/rust"
ln -s "$work/rust/release/libmixer_vm.a" "$work/lib/libmixer_vm_capability_experimental.a"
swift build --package-path "$package" --scratch-path "$work/swift" --cache-path "$work/cache" \
    --config-path "$work/config" --security-path "$work/security" --jobs 10 -Xswiftc -gnone \
    -Xcc "-I$work/source/vm/include" -Xlinker "-L$work/lib" --product F08Control
