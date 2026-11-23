#!/usr/bin/env bash
set -euo pipefail
work=${1:?owned guest scratch directory}
recipe="$(cd "$(dirname "$0")" && pwd)"
pin=d245b325e3f6ad08bf29a254db49dfc2f2ed2579
export GIT_NO_LAZY_FETCH=1
git -C "$recipe" show "$pin:tests/integration/fieldlog-task-calculation/guest/TaskWire.swift" > "$work/TaskWire.swift"
git -C "$recipe" show "$pin:tests/integration/fieldlog-saved-draft/guest/CapabilityImports.c" > "$work/CapabilityImports.c"
wasm="$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin"
cd "$work"
"$wasm/clang" --target=wasm32-unknown-none -ffreestanding -Oz -c CapabilityImports.c -o capability.o
for variant in prior exact; do
    define=FIELDLOG_BASELINE
    if [[ "$variant" == exact ]]; then define=FIELDLOG_UPDATED; fi
    "$wasm/swiftc" -target wasm32-unknown-none-wasm -enable-experimental-feature Embedded \
        -enable-experimental-feature Extern -whole-module-optimization -Osize -parse-as-library \
        -Xfrontend -disable-stack-protector -D "$define" -module-cache-path modules \
        -emit-object "$recipe/Guest.swift" TaskWire.swift -o "$variant.o"
    "$wasm/wasm-ld" --no-entry --gc-sections --strip-all -z stack-size=16384 --max-memory=65536 \
        --export=mixer_guest_ui_start_v1 --export=mixer_guest_ui_hydrate_v1 --export=mixer_guest_ui_event_v1 \
        --export=mixer_guest_capability_ready_v1 "$variant.o" capability.o -o "$variant.wasm"
done
