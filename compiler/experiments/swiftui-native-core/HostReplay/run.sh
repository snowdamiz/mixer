#!/usr/bin/env bash
set -euo pipefail

fixture=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$fixture/../../../.." && pwd)
mode=${1:-debug}
case "$mode" in
  debug) optimization=-Onone ;;
  release) optimization=-O ;;
  ios) optimization=-Onone ;;
  *) echo "Usage: $0 [debug|release|ios]" >&2; exit 2 ;;
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
shared=("$fixture/SharedScreen.swift" "$fixture/SharedControls.swift")

if [[ $mode == ios ]]; then
  sdk=$(xcrun --sdk iphoneos --show-sdk-path)
  flags+=(-target arm64-apple-ios17.0 -sdk "$sdk")
  printf 'Apple target arm64-apple-ios17.0, SDK %s\n' "$sdk"
fi

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
  compiler/experiments/swiftui-native-core/HostReplay/{run.sh,*.swift} \
  | shasum -a 256

build_library MixerCore -package-name Mixer sdk/Sources/MixerCore/*.swift
build_library MixerUI -package-name Mixer sdk/Sources/MixerUI/*.swift
build_library MixerSwiftUI -package-name Mixer sdk/Sources/MixerSwiftUI/*.swift
build_library ReplayFeature -package-name ReplayFeature -module-alias SwiftUI=MixerSwiftUI \
  "${shared[@]}"

if [[ $mode == ios ]]; then
  build_library AppleReplayFeature -package-name ReplayFeature "${shared[@]}"
  printf 'PASS identical shared sources compile for iOS 17.0 with MixerSwiftUI and Apple SwiftUI\n'

  unsupported="$fixture/UnsupportedControls.swift"
  "$swiftc_bin" "${flags[@]}" -typecheck "$unsupported"
  if "$swiftc_bin" "${flags[@]}" -I "$scratch" -module-alias SwiftUI=MixerSwiftUI \
      -typecheck "$unsupported" > "$scratch/refusals" 2>&1; then
    echo "MixerSwiftUI accepted unsupported controls" >&2
    exit 1
  fi
  cat "$scratch/refusals"
  for line in $(awk '/\/\/ refused$/ { print NR }' "$unsupported"); do
    if ! grep -q "UnsupportedControls.swift:$line:[0-9]*: error:" "$scratch/refusals"; then
      echo "Missing refusal for UnsupportedControls.swift:$line" >&2
      exit 1
    fi
  done
  printf 'PASS unsupported authoring calls compile with Apple SwiftUI and fail with MixerSwiftUI\n'
  exit
fi

"$swiftc_bin" "${flags[@]}" -parse-as-library -package-name Mixer -I "$scratch" -L "$scratch" \
  -lReplayFeature -lMixerSwiftUI -lMixerUI -lMixerCore "$fixture/Replay.swift" "$fixture/ControlReplay.swift" \
  -o "$scratch/replay"
"$scratch/replay" "$@"
