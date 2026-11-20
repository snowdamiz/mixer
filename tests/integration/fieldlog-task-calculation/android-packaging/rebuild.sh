#!/bin/bash
set -euo pipefail
umask 077

if [[ $# != 2 || "$1" != /* || "$2" != /* ]]; then
    echo "Usage: $0 /absolute/NEW_WORK /absolute/NEW_HANDOFF" >&2
    exit 2
fi
work=$1
output=$2
recipe=$(cd "$(dirname "$0")" && pwd -P)
inputs=$recipe/rebuild-inputs
repo=$(git -C "$recipe" rev-parse --show-toplevel)
calc=$recipe/..
pair=$calc/../fieldlog-android-engine-pair
mixer=5dea19db36610e312b51918b384364ba590b6ef8
fieldlog=552559d2d3278abb9b1aa7dcf0288102c09a202b
sdk=/opt/homebrew/share/android-commandlinetools
ndk=$sdk/ndk/27.1.12297006
java=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home
swift=$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin
bundle=$HOME/.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle
rustc=$HOME/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc

export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
export LC_ALL=C GIT_TERMINAL_PROMPT=0 GIT_LFS_SKIP_SMUDGE=1 GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
export GIT_NO_LAZY_FETCH=1
export ANDROID_HOME="$sdk" JAVA_HOME="$java" MIXER_JDK="$java" MIXER_SWIFT="$swift/swift"
unset SDKROOT TOOLCHAINS SWIFT_EXEC GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_CONFIG_COUNT
unset JAVA_TOOL_OPTIONS _JAVA_OPTIONS JDK_JAVA_OPTIONS DEVELOPER_DIR FIELDLOG_XCODE

# Reject existing paths and nested output before any checkout or compiler runs.
python3 -B - "$work" "$output" <<'PYTHON'
from pathlib import Path
import sys

work, output = map(Path, sys.argv[1:])
for path in (work, output):
    if path.exists() or path.is_symlink() or not path.parent.is_dir() or path != path.resolve():
        raise SystemExit(f"Expected a new canonical directory: {path}")
if work == output or work in output.parents or output in work.parents:
    raise SystemExit("Work and handoff directories must be separate")
PYTHON
mkdir "$work" "$output"
mkdir "$work"/{tmp,logs,mixer,fieldlog,swift-sdks,templates}
export TMPDIR="$work/tmp" XDG_CACHE_HOME="$work/xdg-cache"
run() {
    python3 -B "$recipe/run.py" "$work" "$output" "$@"
}
run preflight 90 python3 -B "$recipe/provenance.py" check "$work" "$output"
ln -s "$bundle" "$work/swift-sdks/"
cp "$inputs"/{identity-template.json,calculation-seed.json,mixer-first-open-trace.patch} "$work/templates/"
cp "$pair/inputs/manifest.json" "$work/templates/"

git -C "$work/fieldlog" init --quiet --template=
run source-fetch 45 git -C "$work/fieldlog" -c http.lowSpeedLimit=1 -c http.lowSpeedTime=20 \
    fetch --quiet --depth=1 https://github.com/snowdamiz/fieldlog.git "$fieldlog"
run source-checkout 30 git -C "$work/fieldlog" checkout --quiet --detach FETCH_HEAD
run source-check 90 python3 -B "$calc/android-source-check.py" "$work/fieldlog"
run mixer-export 45 /bin/bash -o pipefail -c '
    git -C "$1" archive "$2" sdk capability-activation runtime-identity updates experimental-capability-runtime \
        native/android/app/src native/android/signed-guest-ui verification/android-binding-stage4/host-bridge |
        tar -xf - -C "$3"
' _ "$repo" "$mixer" "$work/mixer"
GIT_CEILING_DIRECTORIES="$work" run mixer-overlay 30 git -C "$work/mixer" apply --whitespace=error \
    "$work/templates/mixer-first-open-trace.patch"
generated=$work/project/Generated/MixerAndroid
mkdir -p "$generated/app/assets/MixerAppearanceV2"
run appearance-export 30 /bin/bash -c '
    git -C "$1" show "$2:verification/android-default-appearance-packaging/run-1/created-descriptor.json" \
        > "$3/app/assets/MixerAppearanceV2/descriptor.json" &&
    git -C "$1" show "$2:cli/Sources/MixerBuild/Resources/android-build.py" > "$3/android-build.py"
' _ "$repo" "$mixer" "$generated"

builder=$work/mixer/experimental-capability-runtime/build-vm.py
git_dir=$(git -C "$repo" rev-parse --absolute-git-dir)
for target in android host; do
    extra=()
    if [[ "$target" == android ]]; then
        extra=(--ndk "$ndk")
    fi
    GIT_DIR="$git_dir" DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer \
        run "vm-$target" 420 python3 -B "$builder" --revision "$mixer" --target "$target" \
        --rustc "$rustc" --output "$work/$target-engine" "${extra[@]+"${extra[@]}"}"
done
CLANG_MODULE_CACHE_PATH="$work/android-clang" SWIFTPM_MODULECACHE_OVERRIDE="$work/android-modules" \
    run app-build 750 /bin/zsh -f "$recipe/build-native.zsh" "$work" "$work/payload"
run java-build 120 /bin/zsh -f "$recipe/build-java.zsh" "$work/fieldlog" "$work/mixer" "$work/java"
run build-guests 90 /bin/bash "$recipe/build-guests.sh" "$calc" "$work"
run host-build 600 /bin/zsh -f "$recipe/build-host.zsh" "$work"
run package 240 python3 -B "$recipe/package.py" --work "$work" --templates "$work/templates" --output "$output" \
    --engine-pair "$pair" --android-sdk "$sdk" --swift-android-sdk "$bundle/swift-android" --java-home "$java"
run replay-host 180 python3 -B "$recipe/replay-host.py" "$output" "$work/host-build/debug/Probe" "$work/host-replay"
python3 -B "$recipe/provenance.py" finish "$work" "$output"
