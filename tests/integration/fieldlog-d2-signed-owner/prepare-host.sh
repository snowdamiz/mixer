#!/bin/bash
set -euxo pipefail
run=$1
w=$run/work
stage=$2
pin=6bc461f4fc7c29771718c7c5ce5a2a39b78f4d2d
export GIT_OPTIONAL_LOCKS=0 GIT_ALLOW_PROTOCOL=file GIT_NO_LAZY_FETCH=1
export TMPDIR="$w/tmp" CARGO_HOME="$run/cargo-home"
export PATH="$HOME/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin:$PATH"
guest="$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin"
git -C "$stage" archive "$pin" native/android/signed-guest-ui verification/android-binding-stage4/host-bridge | tar -xf - -C "$w/mixer"
binding="$w/mixer/native/android/signed-guest-ui/binding/include"
host="$w/mixer/verification/android-binding-stage4/host-bridge"
recipe="$w/mixer/tests/integration/fieldlog-saved-draft"
mkdir -p "$run"/{lib,guests} "$w"/{swift-crypto,swift-asn1}
git -C "$HOME/Library/Caches/org.swift.swiftpm/repositories/swift-crypto-7e0614ea" archive c2cbadd7263439d8015189668f96ff5b5be565ce | tar -xf - -C "$w/swift-crypto"
git -C "$HOME/Library/Caches/org.swift.swiftpm/repositories/swift-asn1-7065ad2c" archive 3b6410f7dee09eb33cdd26260c5fd47fda19b0e2 | tar -xf - -C "$w/swift-asn1"
# Resolve the same two pins offline in the disposable package projection.
for package in sdk updates; do
    sed -i '' 's|\.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")|.package(path: "../../swift-crypto")|' "$w/mixer/$package/Package.swift"
done
rustc --version
"$guest/swiftc" --version
cargo build --manifest-path "$w/mixer/vm/Cargo.toml" --offline --locked --release --jobs 4 \
    --features experimental-capability-native --lib --target-dir "$run/rust-build"
ln -s "$run/rust-build/release/libmixer_vm.a" "$run/lib/libmixer_vm_capability_experimental.a"
flags=(-fPIC -std=c11 -Wall -Wextra -Werror -DMIXER_UI_TRANSPORT_TESTING -DMIXER_UI_WITNESS_TESTING -D_DARWIN_C_SOURCE -mmacosx-version-min=15.0 "-I$binding" "-I$host")
/usr/bin/clang "${flags[@]}" -c "$w/mixer/native/android/signed-guest-ui/transport/transport.c" -o "$run/lib/transport.o"
/usr/bin/clang "${flags[@]}" -Dmxis_apply=mxis_host_apply -c "$host/host_bridge.c" -o "$run/lib/bridge.o"
/usr/bin/clang "${flags[@]}" -Dmxis_apply=mxis_recorded_apply -c "$recipe/host/host-observation.c" -o "$run/lib/observation.o"
src="$recipe/android/recipe/guest"
"$guest/clang" --target=wasm32-unknown-none -ffreestanding -Oz -c "$src/CapabilityImports.c" -o "$run/guests/imports.o"
"$guest/swiftc" -target wasm32-unknown-none-wasm -enable-experimental-feature Embedded \
    -enable-experimental-feature Extern -whole-module-optimization -Osize -parse-as-library \
    -Xfrontend -disable-stack-protector -D OPTIONAL_FIELD -emit-object "$src/Guest.swift" "$src/TaskWire.swift" \
    -o "$run/guests/optional.o"
"$guest/wasm-ld" --no-entry --gc-sections --strip-all -z stack-size=16384 --max-memory=65536 \
    --export=mixer_guest_ui_start_v1 --export=mixer_guest_ui_event_v1 --export=mixer_guest_ui_hydrate_v1 \
    --export=mixer_guest_capability_ready_v1 "$run/guests/optional.o" "$run/guests/imports.o" -o "$run/guests/optional.wasm"
