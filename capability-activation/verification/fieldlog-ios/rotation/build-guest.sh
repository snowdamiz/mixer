#!/bin/bash
set -euo pipefail

recipe=$(cd "$(dirname "$0")" && pwd)
work=$(cd "$1" && pwd)
cd "$recipe/../../../.."
swift_bin=${FIELDLOG_GUEST_BIN:-$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin}
guest="$work/guest"
guest_base=3184c398ba5e5dcded110a65772d793ba9caf9f6
overlay_base=a7588b902202f11afb0989fbbe5e4435856187ed
guest_path=tests/integration/fieldlog-saved-draft/guest
overlay_path=tests/integration/fieldlog-android-engine-pair/overlays/selected-task.patch
test "$(git --no-replace-objects rev-parse "$guest_base:$guest_path")" = 7991d0ce5c8ba46e8ccb8abedd691aee6d982b20
test "$(git --no-replace-objects rev-parse "$overlay_base:$overlay_path")" = 742efd5b481482ceb1c3e83b3b0adbf96bd77e37
swift_version=$("$swift_bin/swiftc" --version)
[[ "$swift_version" == "Apple Swift version 6.3.3 (swift-6.3.3-RELEASE)"$'\n'* ]]
mkdir "$guest" "$guest/tmp" "$guest/modules"
export TMPDIR="$guest/tmp"
export CLANG_MODULE_CACHE_PATH="$guest/modules"

git --no-replace-objects archive "$guest_base:$guest_path" | tar -xf - -C "$guest"
git --no-replace-objects show "$overlay_base:$overlay_path" > "$guest/selected-task.patch"
cd "$guest"
git apply selected-task.patch
sed -i '' -e 's/"Task unavailable"/"Saved task unavailable"/' \
  -e 's/"Reload task"/"Retry saved task"/' Guest.swift

printf '%s\n' "$swift_version"
"$swift_bin/clang" --target=wasm32-unknown-none -Oz -c CapabilityImports.c -o capability.o
for variant in baseline reviewed; do
    flags=()
    if [[ "$variant" == reviewed ]]; then flags=(-D REQUIRE_REVIEW); fi
    "$swift_bin/swiftc" -target wasm32-unknown-none-wasm -enable-experimental-feature Embedded \
      -enable-experimental-feature Extern -whole-module-optimization -Osize -parse-as-library \
      -Xfrontend -disable-stack-protector -Xfrontend -disable-incremental-llvm-codegen \
      -module-cache-path "$guest/modules" -emit-object "${flags[@]+"${flags[@]}"}" \
      Guest.swift TaskWire.swift -o "$variant.o"
    "$swift_bin/wasm-ld" --no-entry --gc-sections --strip-all -z stack-size=16384 --max-memory=65536 \
      --export=mixer_guest_ui_start_v1 --export=mixer_guest_ui_hydrate_v1 \
      --export=mixer_guest_ui_event_v1 --export=mixer_guest_capability_ready_v1 \
      "$variant.o" capability.o -o "$variant.wasm"
done
shasum -a 256 Guest.swift TaskWire.swift CapabilityImports.c baseline.wasm reviewed.wasm
printf '%s  %s\n' \
  092b575d92f174ca2e8602b3bbee1de0d9a5471d73cfc839b719974c24b214dc Guest.swift \
  80dd9995544b3380d59214e1a8abb215f1d19e71997e4e776c68a44a2bc42beb TaskWire.swift \
  6c8b96d5607a5f31260014b365b005120b01cef5c27d645ad7cd333afd3ea7b7 CapabilityImports.c |
  shasum -a 256 -c
python3 -B "$recipe/prepare.py" "$work" --payloads "$guest"
