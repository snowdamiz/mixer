#!/bin/bash
set -euo pipefail
recipe=$1
work=$2
swift=$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin
mkdir "$work/guests"
export TMPDIR="$work/tmp"
export GIT_CEILING_DIRECTORIES="$work"
cp "$recipe"/guest/{Guest.swift,TaskWire.swift} "$work/guests/"
cp "$recipe/../fieldlog-saved-draft/guest/CapabilityImports.c" "$work/guests/"
cd "$work/guests"
git apply --whitespace=error "$recipe/patches/row-guest-completion-preview.patch"
"$swift/clang" --target=wasm32-unknown-none -ffreestanding -Oz -c CapabilityImports.c -o capability.o
for variant in baseline reviewed; do
    if [[ "$variant" == reviewed ]]; then
        git apply --whitespace=error "$recipe/patches/completion-fix.patch"
    fi
    "$swift/swiftc" -target wasm32-unknown-none-wasm -enable-experimental-feature Embedded \
        -enable-experimental-feature Extern -whole-module-optimization -Osize -parse-as-library \
        -Xfrontend -disable-stack-protector -D FIELDLOG_UPDATED -module-cache-path modules \
        -emit-object Guest.swift TaskWire.swift -o "$variant.o"
    "$swift/wasm-ld" --no-entry --gc-sections --strip-all -z stack-size=16384 --max-memory=65536 \
        --export=mixer_guest_ui_start_v1 --export=mixer_guest_ui_hydrate_v1 --export=mixer_guest_ui_event_v1 \
        --export=mixer_guest_capability_ready_v1 "$variant.o" capability.o -o "$variant.wasm"
done
shasum -a 256 *.wasm
wc -c *.wasm
