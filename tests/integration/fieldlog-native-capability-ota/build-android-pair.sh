#!/bin/bash
set -euo pipefail
umask 077

recipe=$(cd "$(dirname "$0")" && pwd -P)
calc=$recipe/../fieldlog-task-calculation/android-packaging
if [[ $# != 1 || "$1" != /* ]]; then
    echo "Usage: $0 /absolute/NEW_CAMPAIGN" >&2
    exit 2
fi
campaign=$1
work=$campaign/work
calculation=$campaign/calculation
packet=$campaign/handoff
export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
export LC_ALL=C GIT_NO_LAZY_FETCH=1 GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export JAVA_HOME=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home
export MIXER_JDK="$JAVA_HOME"
export MIXER_SWIFT="$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"
unset SDKROOT TOOLCHAINS SWIFT_EXEC DEVELOPER_DIR FIELDLOG_XCODE GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_CONFIG_COUNT
unset JAVA_TOOL_OPTIONS _JAVA_OPTIONS JDK_JAVA_OPTIONS
mkdir "$campaign"
"$calc/rebuild.sh" "$work" "$calculation"
(cd "$calculation" && shasum -a 256 -c SHA256SUMS)
mkdir "$packet"
export TMPDIR="$work/tmp" XDG_CACHE_HOME="$work/xdg-cache"
stage() {
    python3 -B "$calc/run.py" "$work" "$packet" "$@"
}
stage https-source 30 python3 -B "$recipe/package-android-pair.py" compose "$campaign"
CLANG_MODULE_CACHE_PATH="$work/android-clang" SWIFTPM_MODULECACHE_OVERRIDE="$work/android-modules" \
    stage https-native 300 /bin/zsh -f "$calc/build-native.zsh" "$work" "$work/https-payload"
stage https-java 120 /bin/zsh -f "$calc/build-java.zsh" "$work/fieldlog" "$work/mixer" "$work/https-java"
stage https-host 180 /bin/zsh -f "$recipe/build-pair-host.zsh" "$work" "$calc"
stage https-package 180 python3 -B "$recipe/package-android-pair.py" package "$campaign"
stage https-replay 130 python3 -B "$recipe/replay-android-pair.py" "$campaign"
python3 -B "$recipe/package-android-pair.py" seal "$campaign"
(cd "$packet" && shasum -a 256 -c SHA256SUMS)
