#!/bin/zsh
# Build the signed-capable payload from the composed FieldLog and pinned Mixer sources.
set -eu
if (( $# < 2 || $# > 3 )); then
    print -u2 'Usage: build-native.zsh WORK OUTPUT [LINK_MAP]'
    exit 2
fi
recipe=${0:A:h}
work=${1:A}
payload=${2:A}
cd "$work"
source "$recipe/offline-swiftpm.zsh"
export TMPDIR="$work/tmp"
export DEVELOPER_DIR=${FIELDLOG_XCODE:-/Applications/Xcode_26.6.app/Contents/Developer}
export SDKROOT="$DEVELOPER_DIR/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk"
sdk=${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}
ndk="$sdk/ndk/27.1.12297006/toolchains/llvm/prebuilt/darwin-x86_64/bin"
swift="${MIXER_SWIFT:-$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift}"

generated="$work/fieldlog/Integrations/GeneratedReport"
app="$generated/Platforms/Android"
binding="$work/mixer/native/android/signed-guest-ui/binding/include"
transport="$work/mixer/native/android/signed-guest-ui/transport"
host="$work/mixer/verification/android-binding-stage4/host-bridge"
engine="$work/android-engine"
mkdir -p android-package/Sources/FieldLogAndroid
mkdir "$payload"
cp "$recipe/Package.swift" "$recipe/Package.resolved" android-package/
for module in FieldLogModels FieldLogStorage FieldLogFeatures; do
    ln -sfn "$generated/Sources/$module" "android-package/Sources/$module"
done
ln -sfn "$work/fieldlog/Integrations/InstalledGuest" android-package/Sources/FieldLogInstalledGuest
for source in "$generated/Sources/FieldLogAndroid/"*.swift; do
    ln -sfn "$source" "android-package/Sources/FieldLogAndroid/${source:t}"
done


objects=()
link_map=()
if (( $# == 3 )); then
    link_map=(-Xlinker -Map -Xlinker "${3:A}")
fi
for source in "$transport/transport.c" "$transport/platform_android.c" "$app/Bridge/PublicBridge.c" "$app/Bridge/ChecklistBridge.c" "$app/Bridge/CalculationTrace/CalculationTrace.c"; do
    object="$payload/${source:t:r}.o"
    "$ndk/aarch64-linux-android28-clang" -fPIC -std=gnu11 -Wall -Wextra -Werror -I"$binding" -I"$host" -c "$source" -o "$object"
    objects+=(-Xlinker "$object")
done
"$swift" build --package-path "$work/android-package" --scratch-path "$work/android-build" \
    --cache-path "$work/android-cache" --config-path "$work/android-config" --security-path "$work/android-security" \
    --disable-dependency-cache --disable-prefetching --skip-update --force-resolved-versions \
    --swift-sdks-path "$work/swift-sdks" --swift-sdk aarch64-unknown-linux-android28 --jobs 8 --disable-index-store --build-system native \
    --product mixer_public_android_jni -Xswiftc -DFIELDLOG_SIGNED_CHECKLIST -Xswiftc -DFIELDLOG_CALCULATION_FIXTURE -Xswiftc -DFIELDLOG_CALCULATION_TRACE -Xswiftc -gnone -Xcc -g0 \
    -Xcc "-I$app/Bridge/CalculationTrace" -Xcc "-I$app/Bridge" -Xcc "-I$engine/include" -Xcc "-I$binding" -Xcc "-I$host" \
    -Xlinker "-L$engine/lib" "${objects[@]}" -Xlinker -landroid -Xlinker -llog -Xlinker -z -Xlinker defs \
    -Xlinker -z -Xlinker max-page-size=16384 "${link_map[@]}"
cp "$work/android-build/aarch64-unknown-linux-android28/debug/libmixer_public_android_jni.so" "$payload/"
