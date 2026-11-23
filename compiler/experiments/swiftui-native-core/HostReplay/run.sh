#!/usr/bin/env bash
set -euo pipefail

fixture=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$fixture/../../../.." && pwd)
mode=${1:-debug}
case "$mode" in
  debug) optimization=-Onone ;;
  release) optimization=-O ;;
  *) echo "Usage: $0 [debug|release]" >&2; exit 2 ;;
esac

if (( $# )); then shift; fi

cd "$repo"
mkdir -p verification/local
scratch=$(mktemp -d "$repo/verification/local/up5-native-core-replay.XXXXXXXX")
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/tmp" "$scratch/modules"
export TMPDIR="$scratch/tmp"
swiftc_bin=${SWIFTC:-swiftc}
flags=(-swift-version 6 -warnings-as-errors "$optimization" -module-cache-path "$scratch/modules")

build_library() {
  local module=$1
  shift
  "$swiftc_bin" "${flags[@]}" -parse-as-library -emit-library -static -emit-module \
    -module-name "$module" -emit-module-path "$scratch/$module.swiftmodule" \
    -I "$scratch" -o "$scratch/lib$module.a" "$@"
}

"$swiftc_bin" --version
printf 'Mode %s, source base %s, inputs ' "$mode" "$(git rev-parse HEAD)"
shasum -a 256 sdk/Sources/{MixerCore,MixerUI,MixerSwiftUI}/*.swift \
  compiler/experiments/swiftui-native-core/HostReplay/{run.sh,SharedScreen.swift,Replay.swift} \
  | shasum -a 256

build_library MixerCore -package-name Mixer sdk/Sources/MixerCore/*.swift
build_library MixerUI -package-name Mixer sdk/Sources/MixerUI/*.swift
build_library MixerSwiftUI -package-name Mixer sdk/Sources/MixerSwiftUI/*.swift
build_library ReplayFeature -package-name ReplayFeature -module-alias SwiftUI=MixerSwiftUI \
  "$fixture/SharedScreen.swift"
"$swiftc_bin" "${flags[@]}" -parse-as-library -package-name Mixer -I "$scratch" -L "$scratch" \
  -lReplayFeature -lMixerSwiftUI -lMixerUI -lMixerCore "$fixture/Replay.swift" -o "$scratch/replay"
"$scratch/replay" "$@"
