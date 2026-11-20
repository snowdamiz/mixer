#!/bin/zsh
set -eu
source "${0:A:h}/environment.zsh"
case "$2" in
cli)
    export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
    exec /usr/bin/swift build --package-path "$work/mixer/cli" --scratch-path "$work/cli-build"         --cache-path "$work/cli-cache" --config-path "$work/cli-config" --security-path "$work/cli-security"         --disable-dependency-cache --disable-prefetching --force-resolved-versions --product mixer --jobs 8 ;;
engine)
    export DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer
    exec python3 -B "$work/mixer/experimental-capability-runtime/build-vm.py"         --revision 5dea19db36610e312b51918b384364ba590b6ef8 --target android         --ndk "$ANDROID_HOME/ndk/27.1.12297006" --rustc "$(rustup which rustc)" --output "$work/android-engine" ;;
esac
