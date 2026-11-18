#!/bin/zsh
set -euo pipefail

if (( $# != 3 )); then
  print -u2 'Usage: run.sh FIELDLOG_CHECKOUT SWIFT_CRYPTO_CHECKOUT SWIFT_ASN1_CHECKOUT'
  exit 2
fi

here=${0:A:h}
mixer=${here:h:h:h}
fieldlog=${1:A}
crypto=${2:A}
asn1=${3:A}
pin=552559d2d3278abb9b1aa7dcf0288102c09a202b
rustbin=${FIELDLOG_RUST_BIN:-$HOME/.rustup/toolchains/stable-aarch64-apple-darwin/bin}
guestbin=${FIELDLOG_GUEST_BIN:-$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin}
mixer_pin=fad0d0b3e65fd3be3b49675601693e5d91999fbe

tmp=$(mktemp -d "${TMPDIR:-/tmp}/fieldlog-saved-draft-XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT
mkdir "$tmp"/{temp,downstream,trial,Mixer,lib,guest,material,app,headers,swift-crypto,swift-asn1}
export TMPDIR="$tmp/temp" CLANG_MODULE_CACHE_PATH="$tmp/clang-cache"
export SWIFTPM_MODULECACHE_OVERRIDE="$tmp/swift-module-cache" SWIFTCI_USE_LOCAL_DEPS=1
export GIT_ALLOW_PROTOCOL=file GIT_NO_LAZY_FETCH=1 PATH="$rustbin:$PATH"
export CARGO_HOME="$tmp/cargo-home"

git -C "$fieldlog" archive "$pin" Sources/FieldLogModels Sources/FieldLogStorage \
  ios/FieldLog/EntryEditor.swift ios/FieldLog/WorkspaceModel.swift |
  tar -xf - -C "$tmp/downstream"
git -C "$tmp/downstream" init -q
git -C "$tmp/downstream" apply --check "$here/fieldlog-552559d2-check-saved-draft.patch"
git -C "$tmp/downstream" apply "$here/fieldlog-552559d2-check-saved-draft.patch"
git -C "$crypto" archive c2cbadd7263439d8015189668f96ff5b5be565ce | tar -xf - -C "$tmp/swift-crypto"
git -C "$asn1" archive 3b6410f7dee09eb33cdd26260c5fd47fda19b0e2 | tar -xf - -C "$tmp/swift-asn1"

git -C "$mixer" archive "$mixer_pin" vm capability-activation experimental-capability-runtime \
  runtime-identity sdk updates native/android/signed-guest-ui verification/android-binding-stage4/host-bridge |
  tar -xf - -C "$tmp/Mixer"
for package in capability-activation experimental-capability-runtime runtime-identity sdk updates; do
  mv "$tmp/Mixer/$package" "$tmp/$package"
done
for package in sdk updates; do
  sed -i '' 's|\.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")|.package(path: "../swift-crypto")|' "$tmp/$package/Package.swift"
done

cp "$here/Package.swift" "$tmp/trial/"
cp -R "$here/host" "$tmp/trial/Sources"
rm "$tmp/trial/Sources/host-observation.c"
cp "$tmp/downstream/ios/FieldLog/WorkspaceModel.swift" "$tmp/trial/Sources/"
cp -R "$tmp/downstream/Sources/"{FieldLogModels,FieldLogStorage} "$tmp/trial/"
cp -R "$tmp/downstream/Integrations/InstalledGuest" "$tmp/trial/FieldLogDraftIntegration"

binding="$tmp/Mixer/native/android/signed-guest-ui/binding/include"
host="$tmp/Mixer/verification/android-binding-stage4/host-bridge"
cat > "$tmp/headers/module.modulemap" <<MAP
module FieldLogHostTest { header "$host/host_test.h" header "witness.h" export * }
MAP
cat > "$tmp/headers/witness.h" <<'HEADER'
#include <stdint.h>
int32_t mxfield_witness(uint64_t, uint64_t, uint64_t, uint32_t);
uint64_t mxfield_recorded_probe(uint64_t);
uint32_t mxfield_host_packet(uint64_t, uint64_t, uint8_t *, uint32_t);
HEADER

/usr/bin/sw_vers
/usr/bin/swift --version
"$guestbin/swiftc" --version
"$rustbin/rustc" --version
print -r -- "Mixer $mixer_pin | FieldLog $pin"
shasum -a 256 "$here/fieldlog-552559d2-check-saved-draft.patch"

"$rustbin/cargo" build --manifest-path "$tmp/Mixer/vm/Cargo.toml" --offline --locked --release \
  --features experimental-capability-native --lib --target-dir "$tmp/cargo"
archive="$tmp/cargo/release/libmixer_vm.a"
ln -s "$archive" "$tmp/lib/libmixer_vm_capability_experimental.a"

cflags=(-fPIC -std=c11 -Wall -Wextra -Werror -DMIXER_UI_TRANSPORT_TESTING -D_DARWIN_C_SOURCE "-I$binding" "-I$host")
/usr/bin/clang $cflags -c "$tmp/Mixer/native/android/signed-guest-ui/transport/transport.c" -o "$tmp/lib/transport.o"
/usr/bin/clang $cflags -Dmxis_apply=mxis_host_apply -c "$host/host_bridge.c" -o "$tmp/lib/bridge.o"
/usr/bin/clang $cflags -c "$here/host/host-observation.c" -o "$tmp/lib/observation.o"

"$guestbin/clang" --target=wasm32-unknown-none -ffreestanding -Oz -c "$here/guest/CapabilityImports.c" -o "$tmp/guest/imports.o"
for variant in baseline corrected optional; do
  case "$variant" in
    baseline) define=BASELINE ;;
    corrected) define=CORRECTED ;;
    optional) define=OPTIONAL_FIELD ;;
  esac
  "$guestbin/swiftc" -target wasm32-unknown-none-wasm -enable-experimental-feature Embedded \
    -enable-experimental-feature Extern -whole-module-optimization -Osize -parse-as-library \
    -Xfrontend -disable-stack-protector -D "$define" -emit-object "$here"/guest/{Guest.swift,TaskWire.swift} \
    -o "$tmp/guest/$variant.o"
  "$guestbin/wasm-ld" --no-entry --gc-sections --strip-all -z stack-size=16384 --max-memory=65536 \
    --export=mixer_guest_ui_start_v1 --export=mixer_guest_ui_event_v1 --export=mixer_guest_ui_hydrate_v1 \
    --export=mixer_guest_capability_ready_v1 "$tmp/guest/$variant.o" "$tmp/guest/imports.o" -o "$tmp/guest/$variant.wasm"
done

/usr/bin/swift build --package-path "$tmp/trial" --scratch-path "$tmp/build" --cache-path "$tmp/cache" \
  --config-path "$tmp/config" --security-path "$tmp/security" --disable-dependency-cache \
  --disable-index-store --build-system native --jobs 6 --product fieldlog-host \
  -Xswiftc -gnone -Xcc -g0 -Xswiftc -DMIXER_FIELDLOG_ANDROID_TRIAL \
  -Xcc "-I$tmp/Mixer/vm/include" -Xcc "-I$binding" -Xcc "-I$host" -Xcc "-I$tmp/headers" \
  -Xlinker "-L$tmp/lib" -Xlinker "$tmp/lib/transport.o" -Xlinker "$tmp/lib/bridge.o" -Xlinker "$tmp/lib/observation.o"

bin="$tmp/build/debug/fieldlog-host"
archive_hash=$(shasum -a 256 "$archive" | cut -d ' ' -f1)
bin_hash=$(shasum -a 256 "$bin" | cut -d ' ' -f1)
print -r -- "VM SHA-256 $archive_hash | host SHA-256 $bin_hash"
"$bin" sign "$tmp/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures" \
  "$tmp/guest" "$tmp/material" "$archive_hash" "$bin_hash"
for variant in baseline corrected optional; do
  (cd "$tmp/material" && shasum -a 256 "$variant.wasm" "$variant.manifest.json")
done
"$bin" run "$tmp/material" "$tmp/app"
"$bin" offline "$tmp/material" "$tmp/app"
