# Source from the Android cross-build with CROSS set to a private build path.
# Use the recorded toolchain versions at the paths installed on this machine.
export DEVELOPER_DIR="${DEVELOPER_DIR:?Set DEVELOPER_DIR to the Xcode 26.6 Developer directory}"
export HOST_SWIFT="${HOST_SWIFT:-$DEVELOPER_DIR/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift}"
export MIXER_SWIFT="${MIXER_SWIFT:?Set MIXER_SWIFT to the Swift 6.3.3 toolchain executable}"
export MIXER_SWIFT_SDKS_PATH="${MIXER_SWIFT_SDKS_PATH:?Set MIXER_SWIFT_SDKS_PATH to the Swift SDK install directory}"
export MIXER_ANDROID_ARTIFACT_PATH="${MIXER_ANDROID_ARTIFACT_PATH:-$MIXER_SWIFT_SDKS_PATH/swift-6.3.3-RELEASE_android.artifactbundle/swift-android}"
export NDK_R27D="$MIXER_ANDROID_ARTIFACT_PATH/android-ndk-r27d"
export ANDROID_HOME="${ANDROID_HOME:?Set ANDROID_HOME to the Android SDK directory}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export MIXER_JDK="${MIXER_JDK:?Set MIXER_JDK to a JDK 25 home directory}"
export JAVA_HOME="$MIXER_JDK"
export TMPDIR="$CROSS/work/tmp"
export CLANG_MODULE_CACHE_PATH="$CROSS/work/module-cache"
export SWIFTPM_MODULECACHE_OVERRIDE="$CLANG_MODULE_CACHE_PATH"
export XDG_CACHE_HOME="$CROSS/work/xdg-cache"
export PYTHONDONTWRITEBYTECODE=1
