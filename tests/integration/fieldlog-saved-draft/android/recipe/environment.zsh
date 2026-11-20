recipe=${0:A:h}
work=${1:A}
source "$recipe/offline-swiftpm.zsh"
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export MIXER_JDK=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home
export JAVA_HOME="$MIXER_JDK"
export MIXER_SWIFT="$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"
export MIXER_SWIFT_SDKS_PATH="$HOME/Library/org.swift.swiftpm/swift-sdks"
export MIXER_ANDROID_ARTIFACT_PATH="$MIXER_SWIFT_SDKS_PATH/swift-6.3.3-RELEASE_android.artifactbundle/swift-android"
export TMPDIR="$work/tmp/"
export CLANG_MODULE_CACHE_PATH="$work/clang-cache"
export SWIFTPM_MODULECACHE_OVERRIDE="$work/module-cache"
export XDG_CACHE_HOME="$work/xdg-cache"
export PYTHONDONTWRITEBYTECODE=1
unset SDKROOT TOOLCHAINS SWIFT_EXEC
