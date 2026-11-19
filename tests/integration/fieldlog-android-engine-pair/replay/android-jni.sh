#!/bin/zsh
set -euo pipefail
app="${1:A}"
label="$2"
archive="${3:A}"
cd "$app"
source offline-env.sh
export TMPDIR="$app/tmp" CLANG_MODULE_CACHE_PATH="$app/clang-cache"
export XDG_CACHE_HOME="$app/xdg-cache" SWIFTPM_MODULECACHE_OVERRIDE="$CLANG_MODULE_CACHE_PATH"
export DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer
export SDKROOT=$DEVELOPER_DIR/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk
ndk=/opt/homebrew/share/android-commandlinetools/ndk/27.1.12297006/toolchains/llvm/prebuilt/darwin-x86_64/bin
swift="${SWIFT_EXEC%/*}/swift"
binding="$app/mixer/native/android/signed-guest-ui/binding/include"
transport="$app/mixer/native/android/signed-guest-ui/transport"
host="$app/mixer/verification/android-binding-stage4/host-bridge"
bridge="$app/fieldlog/Integrations/GeneratedReport/Platforms/Android/Bridge"
mkdir "$app/$label"
ln -s "$archive" "$app/$label/libmixer_vm_capability_experimental.a"
if [[ "$label" = old ]]; then
  for src in "$transport/transport.c" "$transport/platform_android.c" "$bridge/PublicBridge.c" "$bridge/ChecklistBridge.c"; do
    "$ndk/aarch64-linux-android28-clang" -fPIC -std=gnu11 -Wall -Wextra -Werror -I"$binding" -I"$host" -c "$src" -o "lib-android/${src:t:r}.o"
  done
fi
"$swift" build --package-path android-package --scratch-path "$app/android-build" \
  --cache-path "$app/android-cache" --config-path "$app/android-config" --security-path "$app/android-security" \
  --disable-dependency-cache --disable-prefetching --skip-update --force-resolved-versions \
  --swift-sdks-path "${MIXER_RECIPE_SWIFT_SDKS_PATH:?}" \
  --swift-sdk aarch64-unknown-linux-android28 --jobs 6 --disable-index-store --build-system native \
  --product mixer_public_android_jni -v -Xswiftc -DFIELDLOG_SIGNED_CHECKLIST -Xswiftc -gnone -Xcc -g0 \
  -Xcc "-I$app/mixer/vm/include" -Xcc "-I$binding" -Xcc "-I$host" \
  -Xlinker "-L$app/$label" -Xlinker "$app/lib-android/transport.o" \
  -Xlinker "$app/lib-android/platform_android.o" -Xlinker "$app/lib-android/PublicBridge.o" \
  -Xlinker "$app/lib-android/ChecklistBridge.o" -Xlinker -landroid -Xlinker -z -Xlinker defs \
  -Xlinker -z -Xlinker max-page-size=16384 \
  -Xlinker "--why-extract=$app/$label/archive-extraction.tsv" -Xlinker "-Map=$app/$label/linker.map"
cp "$app/android-build/aarch64-unknown-linux-android28/debug/libmixer_public_android_jni.so" "$app/$label/"
