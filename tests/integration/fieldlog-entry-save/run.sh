#!/bin/zsh
set -euo pipefail
umask 077

repo=$(git -C "${0:a:h}" rev-parse --show-toplevel)
mixer_pin=$(git -C "$repo" rev-parse HEAD)
fieldlog_pin=552559d2d3278abb9b1aa7dcf0288102c09a202b
fieldlog_tree=1b62520f35c7e57a01b568291078686574f627c4
crypto_pin=c2cbadd7263439d8015189668f96ff5b5be565ce
asn1_pin=3b6410f7dee09eb33cdd26260c5fd47fda19b0e2
fixture=tests/integration/fieldlog-saved-draft
mode=${1:-rehearsal}
if [[ $mode != rehearsal && $mode != android-editor ]]; then
    print -u2 'Usage: run.sh [android-editor]'
    exit 2
fi
entry_fixture=tests/integration/fieldlog-entry-save
runner="$entry_fixture/run.sh"
runner_mode=$(stat -f '%p' "$repo/$runner")
if [[ ${0:a} != "$repo/$runner" || -L "$repo/$runner" ||
      $(git -C "$repo" ls-tree "$mixer_pin" -- "$runner") != '100755 blob '* ]] ||
   ! (( (8#$runner_mode & 8#100) != 0 )) ||
   ! git -C "$repo" cat-file blob "$mixer_pin:$runner" | cmp -s - "$repo/$runner"; then
    print -u2 -r -- "Runner bytes or executable mode differ from $mixer_pin: $runner"
    exit 1
fi
guestbin=${FIELDLOG_GUEST_BIN:-$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin}
rustbin=${FIELDLOG_RUST_BIN:-$HOME/.rustup/toolchains/stable-aarch64-apple-darwin/bin}
mkdir -p "$repo/verification/local"
scratch=$(mktemp -d "$repo/verification/local/fieldlog-entry-save-run.XXXXXXXX")
trap 'cd /; rm -rf -- "$scratch"; if [[ ! -e "$scratch" ]]; then print -r -- "replayScratchRemoved=true"; fi' EXIT
cd "$scratch"

mkdir "$scratch"/{fieldlog,Mixer,guest,material,commit-material,app,commit-app,lib,headers,temp,swift-crypto,swift-asn1}
trial="$scratch/trial"
mixer="$scratch/Mixer"
replay="$mixer/$entry_fixture"
editor="$replay/android-editor"
editor_flags=()
runtime_paths=(vm capability-activation experimental-capability-runtime runtime-identity sdk updates
    native/android/signed-guest-ui verification/android-binding-stage4/host-bridge)
sources="$trial/Sources"
downstream="$scratch/fieldlog"
mkdir -p "$sources"/{FieldLogFeatures,FieldLogInstalledGuest,Replay}
git -C "$repo" archive "$mixer_pin" "$runtime_paths[@]" "$entry_fixture" \
  "$fixture"/android/{audited-patches/rollback-floor.patch,audited-patches/optional-successor.patch,android-app-composition.patch} \
  "$fixture"/guest/{TaskWire.swift,CapabilityImports.c} "$fixture"/host/{host-observation.c,Sign.swift} |
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
git -C "$downstream" apply --index "$replay/entry-save-decision.patch"
fieldlog_sources="$downstream/Integrations/GeneratedReport/Sources"
decision="$fieldlog_sources/FieldLogFeatures/EntrySaveDecision.swift"
cp "$replay/EntrySaveDecision.swift" "$decision"
git -C "$downstream" add -- "${decision#$downstream/}"
if [[ $mode == android-editor ]]; then
    base_tree=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["fieldLogCompositionTree"])' "$editor/pins.json")
    editor_tree=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["fieldLogEditorTree"])' "$editor/pins.json")
    editor_commit=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["fieldLogEditor"])' "$editor/pins.json")
    test "$(git -C "$downstream" write-tree)" = "$base_tree"
    git -C "$downstream" apply --index "$editor/fieldlog-editor.patch"
    test "$(git -C "$downstream" write-tree)" = "$editor_tree"
    mkdir "$scratch/editor-material" "$scratch/editor-app"
    editor_flags=(-Xswiftc -DFIELDLOG_ENTRY_COMMIT_FIXTURE -Xswiftc -DFIELDLOG_ENTRY_COMMIT_HOST_TEST)
    print -r -- "FieldLog editor $editor_commit $editor_tree"
fi
print -r -- "Mixer $mixer_pin $(git -C "$repo" rev-parse "$mixer_pin^{tree}")"
print -r -- "FieldLog $fieldlog_pin $fieldlog_tree"
print -r -- "FieldLog rehearsal tree $(git -C "$downstream" write-tree)"
shasum -a 256 "$replay/EntrySaveDecision.swift" "$replay/entry-save-decision.patch"

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
build_guest() {
    local variant=$1
    shift
    local -a exports=(--export=mixer_guest_ui_start_v1 --export=mixer_guest_ui_event_v1 --export=mixer_guest_capability_ready_v1)
    if [[ $variant == decision ]]; then exports+=(--export=mixer_guest_ui_hydrate_v1); fi
    "$guestbin/swiftc" -target wasm32-unknown-none-wasm -enable-experimental-feature Embedded \
      -enable-experimental-feature Extern -whole-module-optimization -Osize -parse-as-library \
      -Xfrontend -disable-stack-protector "$@" -emit-object "$replay/Guest.swift" "$decision" "$mixer/$fixture/guest/TaskWire.swift" \
      -o "$scratch/guest/$variant.o"
    "$guestbin/wasm-ld" --no-entry --gc-sections --strip-all -z stack-size=16384 --max-memory=65536 \
      "$exports[@]" "$scratch/guest/$variant.o" "$scratch/guest/imports.o" -o "$scratch/guest/$variant.wasm"
}
build_guest decision
build_guest commit -DFIELDLOG_DURABLE_COMMIT_REPLAY
build_guest multiple -DFIELDLOG_DURABLE_COMMIT_REPLAY -DFIELDLOG_COMMIT_MULTIPLE_PUTS
build_guest unconsumed -DFIELDLOG_DURABLE_COMMIT_REPLAY -DFIELDLOG_COMMIT_MULTIPLE_PUTS -DFIELDLOG_COMMIT_WITHOUT_POLL
if [[ $mode == android-editor ]]; then
    build_guest editor-commit -DFIELDLOG_DURABLE_COMMIT_REPLAY
fi
wc -c "$scratch/guest/"*.wasm
shasum -a 256 "$archive" "$scratch/guest/"*.wasm

cp "$replay/Package.swift" "$trial/"
cp -R "$fieldlog_sources/"{FieldLogModels,FieldLogStorage} "$sources/"
cp "$fieldlog_sources/FieldLogFeatures/"{EntryEditor,TaskEditor,TaskEditorPresentation,EntrySaveDecision}.swift "$sources/FieldLogFeatures/"
cmp "$decision" "$sources/FieldLogFeatures/EntrySaveDecision.swift"
cp "$downstream/Integrations/InstalledGuest/"{FieldLogDraftStorage,SelectedDraftBinding}.swift "$sources/FieldLogInstalledGuest/"
cp "$fieldlog_sources/FieldLogAndroid/PublicFactory.swift" "$replay/Host.swift" "$replay/DurableCommit.swift" \
  "$mixer/$fixture/host/Sign.swift" "$sources/Replay/"
if [[ $mode == android-editor ]]; then
    cp "$downstream/Integrations/InstalledGuest/"{Delivery,SignedTask}.swift "$sources/FieldLogInstalledGuest/"
    cp "$fieldlog_sources/FieldLogAndroid/"{NativeEntry,SignedChecklist,SignedEntryCommit}.swift "$editor/AndroidEditorReplay.swift" "$sources/Replay/"
fi
/usr/bin/swift build --package-path "$trial" --scratch-path "$scratch/build" --cache-path "$scratch/cache" \
  --config-path "$scratch/config" --security-path "$scratch/security" --disable-dependency-cache \
  --disable-index-store --build-system native --jobs "${FIELDLOG_JOBS:-12}" --product fieldlog-entry-save \
  -Xswiftc -gnone -Xcc -g0 -Xswiftc -DFIELDLOG_SIGNED_CHECKLIST -Xswiftc -DFIELDLOG_ENTRY_SAVE_REPLAY "${editor_flags[@]}" \
  -Xcc "-I$mixer/vm/include" -Xcc "-I$binding" -Xcc "-I$host" -Xcc "-I$scratch/headers" \
  -Xlinker "-L$scratch/lib" -Xlinker "$scratch/lib/transport.o" -Xlinker "$scratch/lib/bridge.o" -Xlinker "$scratch/lib/observation.o"

bin="$scratch/build/debug/fieldlog-entry-save"
archive_hash=$(shasum -a 256 "$archive" | cut -d ' ' -f 1)
binary_hash=$(shasum -a 256 "$bin" | cut -d ' ' -f 1)
print -r -- "Host SHA-256 $binary_hash"
if [[ $mode == android-editor ]]; then
    "$bin" sign-editor "$mixer/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures" \
      "$scratch/guest" "$scratch/editor-material" "$archive_hash" "$binary_hash" "$editor_commit"
    shasum -a 256 "$scratch/editor-material/"*
    python3 -B - "$downstream/Integrations/GeneratedReport/scripts/build-signed-checklist-android.py" "$scratch/editor-material" <<'PYTHON'
from hashlib import sha256
import json
from pathlib import Path
import runpy
import sys

packager, installed = Path(sys.argv[1]), Path(sys.argv[2])
checklist_assets = runpy.run_path(str(packager))["checklist_assets"]
identity = json.loads((installed / "identity.json").read_text())
policy = identity["capability_execution"]
if (policy["maximum_requests"], policy["reservation_bytes"]) != (2, 2_097_152):
    raise SystemExit("Installed entry commit fixture does not use the approved transport limits")
pins = {path.name: sha256(path.read_bytes()).hexdigest() for path in installed.iterdir()}
lock = installed.parent / "installed-editor.sha256.json"
lock.write_text(json.dumps(pins))
assets = checklist_assets(installed, lock)
if assets != {f"assets/ChecklistRelease/{name}": (installed / name).read_bytes() for name in pins}:
    raise SystemExit("Packager changed installed fixture assets")
pins["entry-commit.wasm"] = "0" * 64
lock.write_text(json.dumps(pins))
try:
    checklist_assets(installed, lock)
except ValueError as error:
    if "SHA-256 pin" not in str(error):
        raise
else:
    raise SystemExit("Packager accepted a changed guest pin")
print(f"installedPackageInputs={len(assets)} maximumRequests=2 reservationBytes=2097152 mismatchedGuestPinDenied=true")
PYTHON
    "$bin" run-editor "$scratch/editor-material" "$scratch/editor-app"
    if [[ -n ${FIELDLOG_EDITOR_WASM_OUTPUT:-} ]]; then
        (setopt noclobber; cat "$scratch/editor-material/entry-commit.wasm" > "$FIELDLOG_EDITOR_WASM_OUTPUT")
    fi
    exit 0
fi
"$bin" sign "$mixer/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures" \
  "$scratch/guest" "$scratch/material" "$archive_hash" "$binary_hash"
shasum -a 256 "$scratch/material/decision.manifest.json" "$scratch/material/sequence-1.assignment.json"
"$bin" sign-commit "$mixer/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures" \
  "$scratch/guest" "$scratch/commit-material" "$archive_hash" "$binary_hash"
shasum -a 256 "$scratch/commit-material/"{identity.json,commit.manifest.json,sequence-1.assignment.json} \
  "$scratch/commit-material/one-slot/"{identity.json,commit.manifest.json,sequence-1.assignment.json} \
  "$scratch/commit-material/multiple-puts/"{identity.json,multiple.manifest.json,unconsumed.manifest.json,sequence-1.assignment.json,sequence-2.assignment.json}
python3 -B - "$bin" "$scratch" <<'PY'
import subprocess
import sys
from pathlib import Path

binary, scratch = sys.argv[1], Path(sys.argv[2])
for command, material, application in [("run", "material", "app"), ("run-commit", "commit-material", "commit-app")]:
    subprocess.run([binary, command, scratch / material, scratch / application], timeout=45, check=True)
PY
