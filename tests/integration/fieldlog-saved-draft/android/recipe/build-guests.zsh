#!/bin/zsh
set -eu
source "${0:A:h}/environment.zsh"
guest="${MIXER_SWIFT:h}"
src="$recipe/guest"
out="$work/guests"
mkdir "$out"
"$guest/clang" --target=wasm32-unknown-none -ffreestanding -Oz     -c "$src/CapabilityImports.c" -o "$out/imports.o"
for variant in baseline optional; do
    if [[ "$variant" == baseline ]]; then define=BASELINE; else define=OPTIONAL_FIELD; fi
    "$guest/swiftc" -target wasm32-unknown-none-wasm         -enable-experimental-feature Embedded -enable-experimental-feature Extern         -whole-module-optimization -Osize -parse-as-library -Xfrontend -disable-stack-protector         -D "$define" -emit-object "$src/Guest.swift" "$src/TaskWire.swift" -o "$out/$variant.o"
    "$guest/wasm-ld" --no-entry --gc-sections --strip-all -z stack-size=16384 --max-memory=65536         --export=mixer_guest_ui_start_v1 --export=mixer_guest_ui_event_v1 --export=mixer_guest_ui_hydrate_v1         --export=mixer_guest_capability_ready_v1 "$out/$variant.o" "$out/imports.o" -o "$out/$variant.wasm"
done
