# API 28 comparator handoff

The native Swift journey cross-builds as an AArch64 API 28 ELF. Use the
standalone executable to check the six snapshots before integrating both modes
into one measuring process. The Swift ELF build and the earlier VM launches
provide separate evidence. [API 28 VM receipt](../../../verification/receipts/ui-platform-pivot-s2b-api28-20261123.json)

## Build the native arm

Use the installed Swift 6.3.3 Android SDK and its NDK r27d. Build from the
repository root.

```sh
work="$PWD/verification/local/s2-native-android"
mkdir -p "$work/tmp" "$work/modules"
export TMPDIR="$work/tmp"
export DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer
s2_sources=compiler/experiments/swiftui-full-guest
s2_swift="$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swiftc"
s2_sdk="$HOME/.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android"
s2_ndk="$s2_sdk/android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64/bin"
"$s2_swift" -target aarch64-unknown-linux-android28 -sdk "$s2_sdk/ndk-sysroot" \
  -resource-dir "$s2_sdk/swift-resources/usr/lib/swift-aarch64" -tools-directory "$s2_ndk" \
  -module-cache-path "$work/modules" -module-name FieldLogSpike -parse-as-library -Osize -gnone \
  -Xclang-linker -fuse-ld=lld -Xlinker -z -Xlinker max-page-size=16384 \
  "$s2_sources/FieldLog.swift" "$s2_sources/NativeJourney.swift" -o "$work/fieldlog-native-api28"
"$s2_ndk/llvm-readelf" --file-header --program-headers --notes --dynamic-table \
  "$work/fieldlog-native-api28"
```

Use the NDK API 28 system libraries and the Swift SDK runtime directory
`swift-resources/usr/lib/swift-aarch64/android` to resolve the ELF's
`DT_NEEDED` entries and their dependencies, including Foundation and
Observation. The existing Android benchmark's `inspect_elf` shows how to
collect that closure. Stage the runtime in the private packet's `lib` directory
and launch with `LD_LIBRARY_PATH=./lib`. Compare the six stdout lines in order
with the pinned S2 oracle. [Android benchmark builder](../fieldlog-guest-benchmark/android_cross_build.py)

## Pair the arms in one process image

Link the pinned VM tree and the native journey into one shell executable or
one Android app. Dispatch `native` to the Swift journey and `ui256` to the
Rust replay with the same packaged Swift runtime dependencies in both modes.
Preserve the `30_000` ms guest deadline measurement and record the 60-second
profile as a separate diagnostic. Use distinct fresh processes on the same
owned API 28 emulator. Emit monotonic time from native main, an RSS sample
before dispatch, another after an idle second with the loaded journey retained,
and the process peak from `getrusage(RUSAGE_SELF)`. Convert Android's
`ru_maxrss` from KiB to bytes before reporting deltas. Keep standalone ELF
snapshots and metrics scoped to the native command until the matched shell or
app runs both arms.
