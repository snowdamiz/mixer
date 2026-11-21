#!/bin/bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 FIELDLOG_CHECKOUT SWIFT_CRYPTO_CHECKOUT SWIFT_ASN1_CHECKOUT" >&2
    exit 2
fi

here="$(cd "$(dirname "$0")" && pwd)"
mixer="$(git -C "$here" rev-parse --show-toplevel)"
fieldlog="$(cd "$1" && pwd)"
crypto="$(cd "$2" && pwd)"
asn1="$(cd "$3" && pwd)"
revision=dbb9275d58e1a2824c35870767551d2d9c8588bb
fieldlog_pin=552559d2d3278abb9b1aa7dcf0288102c09a202b
rust_bin="${FIELDLOG_RUST_BIN:-$HOME/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin}"
export FIELDLOG_SWIFT_BIN="${FIELDLOG_SWIFT_BIN:-$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin}"
export PATH="$rust_bin:$PATH" GIT_ALLOW_PROTOCOL=file GIT_NO_LAZY_FETCH=1 SWIFTCI_USE_LOCAL_DEPS=1

mkdir -p "$mixer/verification/local"
work="$(mktemp -d "$mixer/verification/local/fieldlog-signed-rollback-save.XXXXXXXX")"
cleanup() {
    rm -rf -- "$work"
    [[ ! -e "$work" ]]
    echo 'scratchRemoved=true'
}
trap cleanup EXIT
export TMPDIR="$work/tmp" CLANG_MODULE_CACHE_PATH="$work/clang-cache"
mkdir "$TMPDIR" "$work"/{recipe,mixer,swift-crypto,swift-asn1,lib,material}
sources="$work/host-package/Sources/Replay"
mkdir -p "$sources"

packages=(sdk updates runtime-identity capability-activation experimental-capability-runtime vm)
git -C "$mixer" archive "$revision" "${packages[@]}" | tar -xf - -C "$work/mixer"
git -C "$mixer" archive "$revision" tests/integration/fieldlog-entry-save tests/integration/fieldlog-saved-draft |
    tar -xf - -C "$work/recipe"
git -C "$crypto" archive c2cbadd7263439d8015189668f96ff5b5be565ce | tar -xf - -C "$work/swift-crypto"
git -C "$asn1" archive 3b6410f7dee09eb33cdd26260c5fd47fda19b0e2 | tar -xf - -C "$work/swift-asn1"
recipe="$work/recipe/tests/integration"
editor="$recipe/fieldlog-entry-save/apple-editor"
git init -q "$work/fieldlog"
git -C "$work/fieldlog" fetch -q --depth=1 --no-tags "$fieldlog" "$fieldlog_pin"
git -C "$work/fieldlog" checkout -q --detach FETCH_HEAD
fieldlog="$work/fieldlog"
check_tree() {
    local actual
    actual="$(git -C "$fieldlog" write-tree)"
    if [[ "$actual" != "$1" ]]; then
        echo "Expected FieldLog tree $1, found $actual" >&2
        exit 1
    fi
}
check_tree 1b62520f35c7e57a01b568291078686574f627c4
for file in \
    fieldlog-saved-draft/android/audited-patches/rollback-floor.patch \
    fieldlog-saved-draft/android/audited-patches/optional-successor.patch \
    fieldlog-saved-draft/android/android-app-composition.patch \
    fieldlog-entry-save/entry-save-decision.patch; do
    git -C "$fieldlog" apply --index "$recipe/$file"
done
decision=Integrations/GeneratedReport/Sources/FieldLogFeatures/EntrySaveDecision.swift
cp "$recipe/fieldlog-entry-save/EntrySaveDecision.swift" "$fieldlog/$decision"
git -C "$fieldlog" add -- "$decision"
git -C "$fieldlog" apply --index "$recipe/fieldlog-entry-save/android-editor/fieldlog-editor.patch"
check_tree e518fa0702a90ee5bd9e9f067de9fd9b0f09cc64
git -C "$fieldlog" apply --index "$editor/fieldlog-apple-editor.patch"
check_tree 1534ac8af1bda5a76a81a7fc3c70cef26ae5e606
git -C "$fieldlog" apply --index "$editor/fieldlog-apple-editor-correction.patch"
check_tree 12986b06d22c8480cf0406c36698ae3ccb6c624f
git -C "$fieldlog" apply --index "$editor/fieldlog-apple-editor-dismissal.patch"
check_tree 515684732fb55e9e48e15e55651f7931fd72b8e6
git -C "$fieldlog" apply --index "$editor/fieldlog-apple-editor-queued-close.patch"
candidate=380e764598c31181d16ef2fbb91c95bf95693375
check_tree "$candidate"
git -C "$fieldlog" diff --quiet
echo "mixer=$revision mixerTree=$(git -C "$mixer" rev-parse "$revision^{tree}") fieldlog=$fieldlog_pin fieldlogTree=$candidate"
sw_vers
xcodebuild -version
swift --version
rustc --version
"$FIELDLOG_SWIFT_BIN/swiftc" --version

for package in sdk updates; do
    sed -i '' 's|\.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")|.package(path: "../../swift-crypto")|' \
        "$work/mixer/$package/Package.swift"
done
cargo build --manifest-path "$work/mixer/vm/Cargo.toml" --offline --locked --release \
    --features experimental-capability-native --lib --target-dir "$work/cargo-host"
archive="$work/cargo-host/release/libmixer_vm.a"
ln -s "$archive" "$work/lib/libmixer_vm_capability_experimental.a"
bash "$editor/build-guests.sh" "$work/guests"
cp "$editor/ReplayPackage.swift" "$work/host-package/Package.swift"
cp "$editor/Sign.swift" "$here/RollbackSave.swift" "$sources/"
patch -s -F 0 -d "$sources" -p1 < "$here/signer-assignments.patch"
ln -s "$fieldlog/Integrations/InstalledGuest/FieldLogDraftStorage.swift" "$sources/"
for name in WorkspaceModel SelectedDraftGuestBinding InstalledDraftGuest; do
    ln -s "$fieldlog/ios/FieldLog/$name.swift" "$sources/"
done
swift build --package-path "$work/host-package" --scratch-path "$work/swift-host" \
    --cache-path "$work/cache" --config-path "$work/config" --security-path "$work/security" \
    --disable-dependency-cache --disable-index-store --jobs "${FIELDLOG_SWIFT_JOBS:-8}" \
    -Xswiftc -enable-testing -Xcc "-I$work/mixer/vm/include" -Xlinker "-L$work/lib"

binary="$work/swift-host/debug/Replay"
engine="$(shasum -a 256 "$archive" | cut -d ' ' -f 1)"
source="$(git -C "$mixer" ls-tree -r "$revision" vm | shasum -a 256 | cut -d ' ' -f 1)"
link="$(
    {
        git -C "$fieldlog" ls-tree -r "$candidate" Package.swift Sources ios \
            Integrations/InstalledGuest Integrations/GeneratedReport/Sources/FieldLogFeatures &&
        git -C "$mixer" ls-tree -r "$revision" "${packages[@]}"
    } | shasum -a 256 | cut -d ' ' -f 1
)"
echo "hostSHA256=$(shasum -a 256 "$binary" | cut -d ' ' -f 1) engineSHA256=$engine engineSourceSHA256=$source linkSHA256=$link"
"$binary" sign "$work/mixer/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures" \
    "$work/guests" "$work/material" "$engine" "$source" "$link" "$revision" "$editor/host-signing-metadata.json"
"$binary" save "$work/material" "$work/workspace" "$work/checkpoint.json"
"$binary" cold "$work/material" "$work/workspace" "$work/checkpoint.json"
