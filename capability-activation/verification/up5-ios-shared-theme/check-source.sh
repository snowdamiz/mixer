#!/bin/sh
set -eu
fixture=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo=$(CDPATH= cd -- "$fixture/../../.." && pwd)
run=$(CDPATH= cd -- "$1" && pwd)
case "$run" in "$repo"/verification/local/*) ;; *) exit 2;; esac
mkdir "$run/tmp"
export TMPDIR="$run/tmp/"
compiler=$(xcrun --find swiftc)
sdk=$(xcrun --sdk macosx --show-sdk-path)
"$compiler" --version
compile() {
  "$compiler" -sdk "$sdk" -target arm64-apple-macosx14.0 -swift-version 6 -package-name Mixer \
    -module-cache-path "$run/modules" "$@"
}
sources="$repo/sdk/Sources"
compile -emit-library -emit-module -module-name MixerCore -o "$run/libMixerCore.dylib" "$sources"/MixerCore/*.swift
compile -emit-library -emit-module -module-name MixerUI -I "$run" -L "$run" -lMixerCore \
  -o "$run/libMixerUI.dylib" "$sources"/MixerUI/*.swift
compile -module-name UP5ThemeSourceChecks -I "$run" -L "$run" -lMixerCore -lMixerUI \
  -Xlinker -rpath -Xlinker "$run" -o "$run/theme-source-checks" \
  "$sources/MixerApple/MixerNativeTheme.swift" "$sources/MixerApple/MixerNativeView.swift" \
  "$sources/MixerApple/FeatureDisplayCompletion.swift" "$fixture/FixtureTheme.swift" "$fixture/SourceChecks.swift"
"$run/theme-source-checks"
