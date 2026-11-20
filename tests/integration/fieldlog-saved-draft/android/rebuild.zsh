#!/bin/zsh
set -eu -o pipefail
umask 077
if (( $# != 2 && $# != 3 )) || [[ $# == 3 && $3 != --prepare-only ]]; then
    print -u2 'Usage: zsh -f rebuild.zsh MIXER_GIT_REPOSITORY NEW_OUTPUT_DIR [--prepare-only]'
    exit 2
fi

source_dir=${0:A:h}
mixer_repository=${1:A}
out=${2:A}
work="$out/work"
packet="$out/packet"
mixer_revision=5dea19db36610e312b51918b384364ba590b6ef8
fieldlog_revision=552559d2d3278abb9b1aa7dcf0288102c09a202b
mirror_dir="$HOME/Library/Caches/org.swift.swiftpm/repositories"

(cd "$source_dir" && shasum -a 256 -c prepare.sha256)
git -C "$mixer_repository" merge-base --is-ancestor "$mixer_revision" d82b78782ae1a9bcccdbc2e3d5890a78ba27413c
test "$(git -C "$mixer_repository" rev-parse "$mixer_revision^{tree}")" = b0a6a2fed1837169edc655da6b17ef3ccf58afec
test "$(git -C "$mirror_dir/swift-crypto-7e0614ea" rev-parse 'refs/tags/5.0.3^{commit}')" = c2cbadd7263439d8015189668f96ff5b5be565ce
test "$(git -C "$mirror_dir/swift-asn1-7065ad2c" rev-parse 'refs/tags/1.7.3^{commit}')" = 3b6410f7dee09eb33cdd26260c5fd47fda19b0e2
test "$(shasum -a 256 "$source_dir/reference/rebuild-identity.json" | cut -d ' ' -f 1)" = c62fadc82115d501e409d7994d31f4e058c725076ccf14b62ce1549c9ab36f64

mkdir "$out"
mkdir -p "$work"/{tmp,logs,mixer} "$packet"
git init -q "$work/fieldlog"
if [[ -n ${FIELDLOG_PINNED_GIT_REPOSITORY:-} ]]; then
    git -C "$work/fieldlog" -c protocol.file.allow=always fetch --no-tags --depth 1 "$FIELDLOG_PINNED_GIT_REPOSITORY" "$fieldlog_revision"
else
    GIT_TERMINAL_PROMPT=0 git -C "$work/fieldlog" -c credential.helper= -c 'credential.helper=!gh auth git-credential' \
        fetch --no-tags --depth 1 https://github.com/snowdamiz/fieldlog.git "$fieldlog_revision"
fi
test "$(git -C "$work/fieldlog" rev-parse FETCH_HEAD)" = "$fieldlog_revision"
git -C "$work/fieldlog" -c advice.detachedHead=false checkout --detach FETCH_HEAD
(
    cd "$work/fieldlog"
    git apply --index "$source_dir/audited-patches/rollback-floor.patch"
    test "$(git write-tree)" = b81afd281ab00dbd1dc06d7ce0605b7f360aada6
    git apply --index "$source_dir/audited-patches/optional-successor.patch"
    test "$(git write-tree)" = eed0ea9f778a0b570c7abd1effe94aec7aa11fbb
    git apply --index "$source_dir/android-app-composition.patch"
    test "$(git write-tree)" = 3e456ac47f590b5749f465dad193d6551b9c1804
)

git -C "$mixer_repository" archive "$mixer_revision" cli sdk native/android vm updates     experimental-capability-runtime capability-activation runtime-identity     verification/android-binding-stage4/host-bridge | tar -x -C "$work/mixer"
git init -q "$work/mixer"
git init -q "$work/mixer-checkout"
objects=$(git -C "$mixer_repository" rev-parse --path-format=absolute --git-path objects)
print -r -- "$objects" > "$work/mixer/.git/objects/info/alternates"
print -r -- "$objects" > "$work/mixer-checkout/.git/objects/info/alternates"
git -C "$work/mixer-checkout" sparse-checkout set --cone sdk native/android
git -C "$work/mixer-checkout" -c advice.detachedHead=false checkout --detach "$mixer_revision"

recipe="$source_dir/recipe"
export FIELDLOG_SEAL_BUILD=sealer2
run() {
    local label=$1
    shift
    print -r -- "$label"
    "$@" > "$work/logs/$label.log" 2>&1 || {
        tail -60 "$work/logs/$label.log"
        return 1
    }
}

run cli /bin/zsh -f "$recipe/build-input.zsh" "$work" cli
run engine /bin/zsh -f "$recipe/build-input.zsh" "$work" engine
run sealer /bin/zsh -f "$recipe/build-app.zsh" "$work" sealer
run prepare /bin/zsh -f "$recipe/build-app.zsh" "$work" prepare
cmp "$source_dir/pair24-mixer.lock" "$work/prepared/mixer.lock"
git -C "$work/fieldlog" apply --index "$source_dir/fieldlog-press-trace.patch"
test "$(git -C "$work/fieldlog" write-tree)" = deac0a5ca9f491236cf3b7220baddd27efbf525d
git -C "$work/fieldlog" apply --index "$source_dir/fieldlog-android-storage-owner.patch"
test "$(git -C "$work/fieldlog" write-tree)" = 8d37af63e780cbcffeb97f5f8c8ede2bf0e19f9f
git -C "$work/mixer" apply "$source_dir/mixer-press-trace.patch"
renderer="$work/prepared/Generated/MixerAndroid/app/src/dev/mixer/android/NativeAppearanceViewsV2.java"
test "$(git hash-object "$renderer")" = f1bedcc9beecac5b509c78e96f3f615aec58ff1c
test "$(shasum -a 256 "$renderer" | cut -d ' ' -f 1)" = a429a85c7c395c0df8d72c737a2b8b73ecb39de16188a5ba839293e7782e7f56
git -C "$work/mixer" apply --include=native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java "$source_dir/android-pending-drawable.patch"
cp "$work/mixer/native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java" "$renderer"
test "$(git hash-object "$renderer")" = cdfe03195e500c703d5dc869dcb99664709a5ae9
test "$(shasum -a 256 "$renderer" | cut -d ' ' -f 1)" = 34feafa32dcf94f5fb235e01b7f9515704e50664f39508ead18aaad35d009f65
run first-frame-source python3 -B "$source_dir/apply-first-frame.py" "$work"
run java /bin/zsh -f "$recipe/build-app.zsh" "$work" java
run guests /bin/zsh -f "$recipe/build-app.zsh" "$work" guests
run host /bin/zsh -f "$recipe/build-app.zsh" "$work" host
if [[ ${3:-} == --prepare-only ]]; then
    exit 0
fi
exec /bin/zsh -f "$source_dir/finish-rebuild.zsh" "$out"
