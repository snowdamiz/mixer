#!/bin/bash
set -euo pipefail

guest_bin="${FIELDLOG_SWIFT_BIN:?Set FIELDLOG_SWIFT_BIN to the Embedded Swift toolchain bin directory}"
if [[ $# -ne 1 ]]; then
    echo "Usage: build-guests.sh FRESH_OUTPUT_DIRECTORY" >&2
    exit 2
fi
output="$1"
mkdir "$output"
editor="$(cd "$(dirname "$0")" && pwd)"
entry="$(dirname "$editor")"
draft="$(dirname "$entry")/fieldlog-saved-draft/guest"
"$guest_bin/clang" --target=wasm32-unknown-none -ffreestanding -Oz \
    -c "$draft/CapabilityImports.c" -o "$output/imports.o"
for variant in entry-commit entry-commit-multiple entry-commit-unconsumed baseline corrected optional; do
    inputs=("$draft/Guest.swift")
    exports=(--export=mixer_guest_ui_start_v1 --export=mixer_guest_ui_event_v1 --export=mixer_guest_capability_ready_v1)
    case "$variant" in
        entry-commit*)
            defines=(-D FIELDLOG_DURABLE_COMMIT_REPLAY)
            if [[ "$variant" != entry-commit ]]; then
                defines+=(-D FIELDLOG_COMMIT_MULTIPLE_PUTS)
            fi
            if [[ "$variant" == entry-commit-unconsumed ]]; then
                defines+=(-D FIELDLOG_COMMIT_WITHOUT_POLL)
            fi
            inputs=("$entry/Guest.swift" "$entry/EntrySaveDecision.swift")
            ;;
        baseline) defines=(-D BASELINE) ;;
        corrected) defines=(-D CORRECTED) ;;
        optional) defines=(-D OPTIONAL_FIELD) ;;
    esac
    if [[ "$variant" != entry-commit* ]]; then
        exports+=(--export=mixer_guest_ui_hydrate_v1)
    fi
    "$guest_bin/swiftc" -target wasm32-unknown-none-wasm -enable-experimental-feature Embedded \
        -enable-experimental-feature Extern -whole-module-optimization -Osize -parse-as-library \
        -Xfrontend -disable-stack-protector "${defines[@]}" -emit-object "${inputs[@]}" "$draft/TaskWire.swift" \
        -o "$output/$variant.o"
    "$guest_bin/wasm-ld" --no-entry --gc-sections --strip-all -z stack-size=16384 --max-memory=65536 \
        "${exports[@]}" "$output/$variant.o" "$output/imports.o" -o "$output/$variant.wasm"
done
shasum -a 256 "$output/"*.wasm
