#!/bin/sh
# Run once, offline, with verified archives mounted read-only and a new volume.
set -eu

cd /toolchain
mkdir sdk jdk
tar --no-same-owner -xf /archives/swift-android.tar.gz -C sdk
tar --no-same-owner --strip-components=1 -xf /archives/jdk25-linux-arm64.tar.gz -C jdk
artifact=/toolchain/sdk/swift-6.3.3-RELEASE_android.artifactbundle/swift-android
unzip -q /archives/android-ndk-r27d-linux.zip -d "$artifact"
export ANDROID_NDK_HOME="$artifact/android-ndk-r27d"
"$artifact/scripts/setup-android-sdk.sh"
ndk="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64"
test -r "$ndk/sysroot/usr/lib/aarch64-linux-android/28/crtbegin_so.o"
test -r "$ndk/sysroot/usr/include/linux/netfilter/xt_RATEEST.h"
test -r "$ndk/sysroot/usr/include/linux/netfilter/xt_rateest.h"
/usr/bin/swift --version
"$ndk/bin/aarch64-linux-android28-clang" --version
"$ndk/bin/llvm-readelf" -h "$artifact/ndk-sysroot/usr/lib/swift/android/aarch64/swiftrt.o" | grep AArch64
/toolchain/jdk/bin/java --version
sha256sum "$artifact/swift-resources/usr/lib/swift-aarch64/android/lib_FoundationICU.so"
