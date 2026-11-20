#!/bin/bash
set -euo pipefail
umask 077
ulimit -c 0

if [[ $# != 1 || "$1" != /* ]]; then
    echo "Usage: $0 /absolute/NEW_CAMPAIGN" >&2
    exit 2
fi
launcher=$(cd "$(dirname "$0")" && pwd -P)
revision=b144c2c2042a4499365d1186f46d43fba1832143
fieldlog=552559d2d3278abb9b1aa7dcf0288102c09a202b
campaign=$1
work=$campaign/work
packet=$campaign/handoff
next=$work/successor
stock=$work/stock-source

export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
export LC_ALL=C GIT_TERMINAL_PROMPT=0 GIT_LFS_SKIP_SMUDGE=1 GIT_NO_LAZY_FETCH=1
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export JAVA_HOME=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home
export MIXER_JDK="$JAVA_HOME"
export MIXER_SWIFT="$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"
unset SDKROOT TOOLCHAINS SWIFT_EXEC DEVELOPER_DIR FIELDLOG_XCODE GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_CONFIG_COUNT
unset JAVA_TOOL_OPTIONS _JAVA_OPTIONS JDK_JAVA_OPTIONS

repo=$(git -C "$launcher" rev-parse --show-toplevel)
recipe_revision=$(git -C "$repo" rev-parse HEAD)
git --no-replace-objects -C "$repo" merge-base --is-ancestor "$revision" "$recipe_revision"
git_dir=$(git -C "$repo" rev-parse --absolute-git-dir)
recipe_path=${launcher#"$repo/"}
git --no-replace-objects -C "$repo" show "$recipe_revision:$recipe_path/current_abi_recipe.py" |
    python3 -IBS - "$repo" "$recipe_revision" "$campaign"
recipe="$work/recipe-source/$recipe_path"
calc="$recipe/../fieldlog-task-calculation/android-packaging"
mkdir -p "$work"/{tmp,logs,mixer,fieldlog,swift-sdks} "$packet" "$next"/{tmp,swift-sdks} "$stock"
# The stock CLI resolves its nested Android driver through /usr/bin/env.
mkdir "$work/isolated-python"
cat > "$work/isolated-python/python3" <<'SH'
#!/bin/sh
exec /opt/homebrew/bin/python3 -IBS "$@"
SH
chmod 700 "$work/isolated-python/python3"
export TMPDIR="$work/tmp" XDG_CACHE_HOME="$work/xdg-cache" GIT_CEILING_DIRECTORIES="$work"
bundle="$HOME/.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle"
ln -s "$bundle" "$work/swift-sdks/"
ln -s "$bundle" "$next/swift-sdks/"
ln -s "$work/mixer" "$next/"

run() {
    python3 -IBS "$calc/run.py" "$work" "$packet" "$@"
}
join_jobs() {
    local failed=0
    for job in "$@"; do
        wait "$job" || failed=1
    done
    return "$failed"
}

run preflight 60 python3 -EBS "$calc/provenance.py" check "$work" "$packet" "$repo"
git -C "$work/fieldlog" init --quiet --template=
run fieldlog-fetch 55 git -C "$work/fieldlog" -c http.lowSpeedLimit=1 -c http.lowSpeedTime=20 \
    fetch --quiet --depth=1 https://github.com/snowdamiz/fieldlog.git "$fieldlog" &
fetch=$!
run mixer-export 90 /bin/bash -o pipefail -c '
    git -C "$1" archive "$2" sdk capability-activation runtime-identity updates experimental-capability-runtime \
        native/android/app/src native/android/signed-guest-ui verification/android-binding-stage4/host-bridge |
        tar -xf - -C "$3"
' _ "$repo" "$revision" "$work/mixer" &
mixer=$!
run stock-export 90 /bin/bash -o pipefail -c '
    git -C "$1" archive "$2" cli sdk runtime-identity updates native/android |
        tar -xf - -C "$3"
' _ "$repo" "$revision" "$stock" &
stock_source=$!
run build-guests 100 /bin/bash "$calc/build-guests.sh" "$calc/.." "$work" &
guests=$!
join_jobs "$fetch" "$mixer" "$stock_source" "$guests"

run fieldlog-checkout 30 git -C "$work/fieldlog" checkout --quiet --detach FETCH_HEAD
run fieldlog-baseline 90 python3 -IBS "$calc/../android-source-check.py" "$work/fieldlog"
run fieldlog-clone 45 git clone --quiet --no-local "$work/fieldlog" "$next/fieldlog"
run fieldlog-successor-base 90 python3 -IBS "$calc/../android-source-check.py" "$next/fieldlog"
run fieldlog-https-overlay 30 git -C "$next/fieldlog" apply --index --whitespace=error \
    --exclude=Integrations/GeneratedReport/Platforms/Android/AndroidManifest.xml "$recipe/android-successor.patch"
run mixer-trace-overlay 30 git -C "$work/mixer" apply --whitespace=error "$calc/rebuild-inputs/mixer-first-open-trace.patch"
run adapter-inputs 45 python3 -EBS "$recipe/current-abi.py" adapter-pins "$repo" "$work/current-adapter-pins.json"

rustc="$HOME/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc"
builder="$work/mixer/experimental-capability-runtime/build-vm.py"
GIT_DIR="$git_dir" DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer \
    run vm-android 420 python3 -IBS "$builder" --revision "$revision" --target android --rustc "$rustc" \
    --output "$work/android-engine" --ndk "$ANDROID_HOME/ndk/27.1.12297006" &
android_vm=$!
GIT_DIR="$git_dir" DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer \
    run vm-host 420 python3 -IBS "$builder" --revision "$revision" --target host --rustc "$rustc" \
    --output "$work/host-engine" &
host_vm=$!
run java-old 120 /bin/zsh -f "$calc/build-java.zsh" "$work/fieldlog" "$work/mixer" "$work/java" "$work/current-adapter-pins.json" &
old_java=$!
run java-successor 120 /bin/zsh -f "$calc/build-java.zsh" "$next/fieldlog" "$work/mixer" "$next/java" "$work/current-adapter-pins.json" &
next_java=$!
stock_build() {
    CLANG_MODULE_CACHE_PATH="$work/$1-clang" SWIFTPM_MODULECACHE_OVERRIDE="$work/$1-modules" \
        run "build-$1" 550 /bin/bash -c '
        source "$1/offline-swiftpm.zsh"
        exec /usr/bin/swift build --package-path "$2" --scratch-path "$3" \
            --cache-path "$3-cache" --config-path "$3-config" --security-path "$3-security" \
            --disable-dependency-cache --disable-prefetching --skip-update --force-resolved-versions \
            --disable-index-store --product "$4"
    ' _ "$calc" "$stock/$2" "$work/$1-build" "$3"
}
stock_build stock cli mixer &
inspector=$!
stock_build update updates mixer-update &
verifier=$!
join_jobs "$android_vm" "$host_vm" "$old_java" "$next_java" "$inspector" "$verifier"
ln -s "$work/android-engine" "$work/host-engine" "$next/"

CLANG_MODULE_CACHE_PATH="$work/android-clang" SWIFTPM_MODULECACHE_OVERRIDE="$work/android-modules" \
    run native-old 650 /bin/zsh -f "$calc/build-native.zsh" "$work" "$work/payload" "$work/link.map" &
old_native=$!
CLANG_MODULE_CACHE_PATH="$next/android-clang" SWIFTPM_MODULECACHE_OVERRIDE="$next/android-modules" \
    run native-successor 650 /bin/zsh -f "$calc/build-native.zsh" "$next" "$next/payload" "$next/link.map" &
next_native=$!
run host-old 420 /bin/zsh -f "$calc/build-host.zsh" "$work" &
old_host=$!
run host-successor 420 /bin/zsh -f "$calc/build-host.zsh" "$next" "$recipe/SealPair.swift" &
next_host=$!
run stock-project 70 /usr/bin/env "PATH=$work/isolated-python:$PATH" \
    "$work/stock-build/debug/mixer" create FieldLog --directory "$work/stock-project" \
    --application dev.fieldlog.generatedr90.calculation --sdk-path "$stock/sdk" --android-adapter-path "$stock/native/android" --platform android &
stock_project=$!
join_jobs "$old_native" "$next_native" "$old_host" "$next_host" "$stock_project"
ln -s "$work/host-build/debug/Probe" "$work/storage-only-probe"

generated="$work/project/Generated/MixerAndroid"
mkdir -p "$generated/app/assets/MixerAppearanceV2"
git -C "$repo" show "$revision:verification/android-default-appearance-packaging/run-1/created-descriptor.json" \
    > "$generated/app/assets/MixerAppearanceV2/descriptor.json"
git -C "$repo" show 5dea19db36610e312b51918b384364ba590b6ef8:cli/Sources/MixerBuild/Resources/android-build.py \
    > "$generated/android-build.py"
run package 240 python3 -EBS "$recipe/current-abi.py" package "$work" "$packet"
run host-replay 150 python3 -EBS "$recipe/replay-android-pair.py" "$campaign"
run inspect 220 python3 -EBS "$recipe/inspect-current-abi.py" "$work" "$packet"
python3 -EBS "$recipe/current-abi.py" seal "$work" "$packet" --recipe-revision "$recipe_revision" --recipe-repo "$repo"
(cd "$packet" && shasum -a 256 -c SHA256SUMS)
