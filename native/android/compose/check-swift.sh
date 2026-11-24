#!/bin/sh
set -eu
case "${1:-}" in
    /*) ;;
    *) echo 'Usage: check-swift.sh <owned absolute output directory>' >&2; exit 2 ;;
esac
project=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH='' cd -- "$project/../../.." && pwd)
out="$1/swift"
mkdir -p "$out/tmp" "$out/cache"
export TMPDIR="$out/tmp"
export CLANG_MODULE_CACHE_PATH="$out/cache"
swiftc -swift-version 6 -package-name Mixer -module-cache-path "$out/cache" \
    -emit-module -emit-module-path "$out/MixerCore.swiftmodule" -emit-library -static \
    -module-name MixerCore "$root"/sdk/Sources/MixerCore/*.swift -o "$out/libMixerCore.a"
swiftc -swift-version 6 -package-name Mixer -module-cache-path "$out/cache" -I "$out" \
    -emit-module -emit-module-path "$out/MixerUI.swiftmodule" -emit-library -static \
    -module-name MixerUI "$root"/sdk/Sources/MixerUI/*.swift -o "$out/libMixerUI.a"
swiftc -parse-as-library -swift-version 6 -module-cache-path "$out/cache" -I "$out" -L "$out" -lMixerUI -lMixerCore \
    "$project/src/bridge/CanonicalFixture.swift" \
    -o "$out/canonical-fixture"
"$out/canonical-fixture" "$out/sdk-document.json"
