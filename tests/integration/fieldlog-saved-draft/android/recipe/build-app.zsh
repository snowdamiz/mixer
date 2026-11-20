#!/bin/zsh
set -eu
source "${0:A:h}/environment.zsh"
export DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer
export SDKROOT="$DEVELOPER_DIR/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk"
case "$2" in
host)
    exec /bin/zsh -f "$recipe/run-host-proof.zsh" "$work" ;;
sealer|guests)
    exec /bin/zsh -f "$recipe/build-$2.zsh" "$work" ;;
prepare)
    exec python3 -B "$work/fieldlog/Integrations/GeneratedReport/scripts/build-android.py" --prepare-only         --mixer "$work/cli-build/debug/mixer" --sdk-checkout "$work/mixer-checkout"         --android-adapter-path "$work/mixer-checkout/native/android" --output "$work/prepared" ;;
java)
    exec /bin/zsh -f "$recipe/build-java.zsh" "$work/fieldlog" "$work/prepared" "$work/java" ;;
native)
    exec /bin/zsh -f "$recipe/build-payload.zsh" "$work" "$work/prepared" "$work/payload" ;;
esac
