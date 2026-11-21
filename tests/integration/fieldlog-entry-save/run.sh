#!/bin/zsh
set -euo pipefail
umask 077

here=${0:A:h}
repo=$(git -C "$here" rev-parse --show-toplevel)
mixer_pin=44aecbeb6a82a4a93321cff6a8ab86c5aa421900
fieldlog_pin=552559d2d3278abb9b1aa7dcf0288102c09a202b
fieldlog_tree=1b62520f35c7e57a01b568291078686574f627c4
crypto_pin=c2cbadd7263439d8015189668f96ff5b5be565ce
asn1_pin=3b6410f7dee09eb33cdd26260c5fd47fda19b0e2
fixture=tests/integration/fieldlog-saved-draft
guestbin=${FIELDLOG_GUEST_BIN:-$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin}
rustbin=${FIELDLOG_RUST_BIN:-$HOME/.rustup/toolchains/stable-aarch64-apple-darwin/bin}
mkdir -p "$repo/verification/local"
scratch=$(mktemp -d "$repo/verification/local/fieldlog-entry-save-run.XXXXXXXX")
trap 'rm -rf -- "$scratch"; if [[ ! -e "$scratch" ]]; then print -r -- "replayScratchRemoved=true"; fi' EXIT

mkdir "$scratch"/{fieldlog,Mixer,guest,material,app,lib,headers,temp,swift-crypto,swift-asn1}
trial="$scratch/trial"
mixer="$scratch/Mixer"
sources="$trial/Sources"
downstream="$scratch/fieldlog"
mkdir -p "$sources"/{FieldLogFeatures,FieldLogInstalledGuest,Replay}
git -C "$repo" archive "$mixer_pin" vm capability-activation experimental-capability-runtime runtime-identity   sdk updates native/android/signed-guest-ui verification/android-binding-stage4/host-bridge   "$fixture"/android/{audited-patches/rollback-floor.patch,audited-patches/optional-successor.patch,android-app-composition.patch}   "$fixture"/guest/{TaskWire.swift,CapabilityImports.c} "$fixture/host/host-observation.c" |
  tar -xf - -C "$mixer"

git -C "$downstream" init -q
if [[ -n ${FIELDLOG_PINNED_GIT_REPOSITORY:-} ]]; then
    git -C "$downstream" -c protocol.file.allow=always fetch --no-tags --depth=1 "$FIELDLOG_PINNED_GIT_REPOSITORY" "$fieldlog_pin"
else
    GIT_TERMINAL_PROMPT=0 git -C "$downstream" -c credential.helper= -c 'credential.helper=!gh auth git-credential'       -c http.lowSpeedLimit=1 -c http.lowSpeedTime=30 fetch --no-tags --depth=1 https://github.com/snowdamiz/fieldlog.git "$fieldlog_pin"
fi
test "$(git -C "$downstream" rev-parse FETCH_HEAD)" = "$fieldlog_pin"
test "$(git -C "$downstream" rev-parse FETCH_HEAD^{tree})" = "$fieldlog_tree"
git -C "$downstream" checkout -q --detach FETCH_HEAD
overlay="$mixer/$fixture/android"
git -C "$downstream" apply --index "$overlay/audited-patches/rollback-floor.patch"
test "$(git -C "$downstream" write-tree)" = b81afd281ab00dbd1dc06d7ce0605b7f360aada6
git -C "$downstream" apply --index "$overlay/audited-patches/optional-successor.patch"
test "$(git -C "$downstream" write-tree)" = eed0ea9f778a0b570c7abd1effe94aec7aa11fbb
git -C "$downstream" apply --index "$overlay/android-app-composition.patch"
test "$(git -C "$downstream" write-tree)" = 3e456ac47f590b5749f465dad193d6551b9c1804
git -C "$downstream" apply --index "$here/entry-save-decision.patch"
fieldlog_sources="$downstream/Integrations/GeneratedReport/Sources"
decision="$fieldlog_sources/FieldLogFeatures/EntrySaveDecision.swift"
cp "$here/EntrySaveDecision.swift" "$decision"
git -C "$downstream" add -- "${decision#$downstream/}"
print -r -- "Mixer $mixer_pin $(git -C "$repo" rev-parse "$mixer_pin^{tree}")"
print -r -- "FieldLog $fieldlog_pin $fieldlog_tree"
print -r -- "FieldLog rehearsal tree $(git -C "$downstream" write-tree)"
shasum -a 256 "$here/EntrySaveDecision.swift" "$here/entry-save-decision.patch"

curl -qfsSL --max-time 60 "https://codeload.github.com/apple/swift-crypto/tar.gz/$crypto_pin" |
  tar -xzf - --strip-components=1 -C "$scratch/swift-crypto"
curl -qfsSL --max-time 60 "https://codeload.github.com/apple/swift-asn1/tar.gz/$asn1_pin" |
  tar -xzf - --strip-components=1 -C "$scratch/swift-asn1"
for package in sdk updates; do
    sed -i '' 's|\.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")|.package(path: "../../swift-crypto")|' "$mixer/$package/Package.swift"
done

export TMPDIR="$scratch/temp" CLANG_MODULE_CACHE_PATH="$scratch/clang-cache"
export SWIFTPM_MODULECACHE_OVERRIDE="$scratch/swift-module-cache" SWIFTCI_USE_LOCAL_DEPS=1
export GIT_ALLOW_PROTOCOL=file GIT_NO_LAZY_FETCH=1 CARGO_HOME="$scratch/cargo-home" PATH="$rustbin:$PATH"
/usr/bin/sw_vers
/usr/bin/swift --version
"$guestbin/swiftc" --version
"$rustbin/rustc" --version
"$rustbin/cargo" build --manifest-path "$mixer/vm/Cargo.toml" --offline --locked --release \
  --features experimental-capability-native --lib --target-dir "$scratch/cargo"
archive="$scratch/cargo/release/libmixer_vm.a"
ln -s "$archive" "$scratch/lib/libmixer_vm_capability_experimental.a"

binding="$mixer/native/android/signed-guest-ui/binding/include"
host="$mixer/verification/android-binding-stage4/host-bridge"
printf 'module FieldLogHostTest { header "%s/host_test.h" header "witness.h" export * }\n' "$host" > "$scratch/headers/module.modulemap"
cat > "$scratch/headers/witness.h" <<'C'
#include <stdint.h>
#include "mixer_ui_binding.h"
uint64_t mxfield_recorded_probe(uint64_t);
uint32_t mxfield_host_packet(uint64_t, uint64_t, uint8_t *, uint32_t);
C
cflags=(-fPIC -std=c11 -Wall -Wextra -Werror -mmacosx-version-min=14.0 -DMIXER_UI_TRANSPORT_TESTING
        -DMIXER_UI_WITNESS_TESTING -D_DARWIN_C_SOURCE "-I$binding" "-I$host")
/usr/bin/clang $cflags -c "$mixer/native/android/signed-guest-ui/transport/transport.c" -o "$scratch/lib/transport.o"
/usr/bin/clang $cflags -Dmxis_apply=mxis_host_apply -c "$host/host_bridge.c" -o "$scratch/lib/bridge.o"
/usr/bin/clang $cflags -c "$mixer/$fixture/host/host-observation.c" -o "$scratch/lib/observation.o"

"$guestbin/clang" --target=wasm32-unknown-none -ffreestanding -Oz -c "$mixer/$fixture/guest/CapabilityImports.c" -o "$scratch/guest/imports.o"
"$guestbin/swiftc" -target wasm32-unknown-none-wasm -enable-experimental-feature Embedded \
  -enable-experimental-feature Extern -whole-module-optimization -Osize -parse-as-library \
  -Xfrontend -disable-stack-protector -emit-object "$here/Guest.swift" "$decision" "$mixer/$fixture/guest/TaskWire.swift" \
  -o "$scratch/guest/decision.o"
"$guestbin/wasm-ld" --no-entry --gc-sections --strip-all -z stack-size=16384 --max-memory=65536 \
  --export=mixer_guest_ui_start_v1 --export=mixer_guest_ui_event_v1 --export=mixer_guest_ui_hydrate_v1 \
  --export=mixer_guest_capability_ready_v1 "$scratch/guest/decision.o" "$scratch/guest/imports.o" -o "$scratch/guest/decision.wasm"
wc -c "$scratch/guest/decision.wasm"
shasum -a 256 "$archive" "$scratch/guest/decision.wasm"

cp "$here/Package.swift" "$trial/"
cp -R "$fieldlog_sources/"{FieldLogModels,FieldLogStorage} "$sources/"
cp "$fieldlog_sources/FieldLogFeatures/"{EntryEditor,TaskEditor,TaskEditorPresentation,EntrySaveDecision}.swift "$sources/FieldLogFeatures/"
cmp "$decision" "$sources/FieldLogFeatures/EntrySaveDecision.swift"
cp "$downstream/Integrations/InstalledGuest/"{FieldLogDraftStorage,SelectedDraftBinding}.swift "$sources/FieldLogInstalledGuest/"
cp "$fieldlog_sources/FieldLogAndroid/PublicFactory.swift" "$here/Host.swift" "$repo/$fixture/host/Sign.swift" "$sources/Replay/"
/usr/bin/swift build --package-path "$trial" --scratch-path "$scratch/build" --cache-path "$scratch/cache" \
  --config-path "$scratch/config" --security-path "$scratch/security" --disable-dependency-cache \
  --disable-index-store --build-system native --jobs "${FIELDLOG_JOBS:-12}" --product fieldlog-entry-save \
  -Xswiftc -gnone -Xcc -g0 -Xswiftc -DFIELDLOG_SIGNED_CHECKLIST -Xswiftc -DFIELDLOG_ENTRY_SAVE_REPLAY \
  -Xcc "-I$mixer/vm/include" -Xcc "-I$binding" -Xcc "-I$host" -Xcc "-I$scratch/headers" \
  -Xlinker "-L$scratch/lib" -Xlinker "$scratch/lib/transport.o" -Xlinker "$scratch/lib/bridge.o" -Xlinker "$scratch/lib/observation.o"

bin="$scratch/build/debug/fieldlog-entry-save"
archive_hash=$(shasum -a 256 "$archive" | cut -d ' ' -f 1)
binary_hash=$(shasum -a 256 "$bin" | cut -d ' ' -f 1)
print -r -- "Host SHA-256 $binary_hash"
"$bin" sign "$mixer/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures" \
  "$scratch/guest" "$scratch/material" "$archive_hash" "$binary_hash"
shasum -a 256 "$scratch/material/decision.manifest.json" "$scratch/material/sequence-1.assignment.json"
python3 -B - "$bin" "$scratch/material" "$scratch/app" <<'PY'
import subprocess
import sys

binary, material, application = sys.argv[1:]
subprocess.run([binary, "run", material, application], timeout=45, check=True)
PY
