#!/bin/bash
set -euo pipefail

mixer=$(cd -- "${1:?Pass the Mixer Git checkout}" && pwd -P)
here=$(cd -- "$(dirname -- "$0")" && pwd -P)
mixer_rev=6bc461f4fc7c29771718c7c5ce5a2a39b78f4d2d
fieldlog_rev=552559d2d3278abb9b1aa7dcf0288102c09a202b
work=$(cd -- "${2:?Pass a fresh owned work directory}" && pwd -P)
mkdir "$work"/{fieldlog,mixer,tmp,swift-crypto,swift-asn1}
export TMPDIR="$work/tmp" SWIFTCI_USE_LOCAL_DEPS=1
export SWIFTPM_MODULECACHE_OVERRIDE="$work/module-cache" CLANG_MODULE_CACHE_PATH="$work/module-cache"
app="$work/fieldlog"

fetch() {
    local owner=$1 package=$2 revision=$3 digest=$4
    curl --fail --silent --show-error --location --max-time 30 --max-filesize 20000000 \
        "https://codeload.github.com/$owner/$package/tar.gz/$revision" -o "$work/$package.tgz"
    printf '%s  %s\n' "$digest" "$work/$package.tgz" | shasum -a 256 -c
    tar -xzf "$work/$package.tgz" -C "$work/$package" --strip-components 1
}
fetch snowdamiz fieldlog "$fieldlog_rev" 75d2ce2663ade805ca40831b17a460c248e88c62a7689d5a671182bbf0ed7840
git -C "$app" init -q
git -C "$app" -c core.autocrlf=false add -f -- .
check_tree() {
    local observed
    observed=$(git -C "$app" write-tree)
    [[ "$observed" == "$1" ]] || { printf 'Expected tree %s, observed %s\n' "$1" "$observed" >&2; exit 1; }
}
check_tree 1b62520f35c7e57a01b568291078686574f627c4

apply_pin() {
    git -C "$mixer" show "${mixer_rev}:tests/integration/$1" | git -C "$app" apply --index
}
apply_pin fieldlog-saved-draft/android/audited-patches/rollback-floor.patch
apply_pin fieldlog-saved-draft/android/audited-patches/optional-successor.patch
apply_pin fieldlog-saved-draft/android/android-app-composition.patch
apply_pin fieldlog-entry-save/entry-save-decision.patch
decision=Integrations/GeneratedReport/Sources/FieldLogFeatures/EntrySaveDecision.swift
git -C "$mixer" show "${mixer_rev}:tests/integration/fieldlog-entry-save/EntrySaveDecision.swift" > "$app/$decision"
git -C "$app" add -- "$decision"
apply_pin fieldlog-entry-save/android-editor/fieldlog-editor.patch
check_tree e518fa0702a90ee5bd9e9f067de9fd9b0f09cc64
apply_pin fieldlog-entry-save/apple-editor/fieldlog-apple-editor.patch
check_tree 1534ac8af1bda5a76a81a7fc3c70cef26ae5e606
apply_pin fieldlog-entry-save/apple-editor/fieldlog-apple-editor-correction.patch
check_tree 12986b06d22c8480cf0406c36698ae3ccb6c624f
apply_pin fieldlog-entry-save/apple-editor/fieldlog-apple-editor-dismissal.patch
check_tree 515684732fb55e9e48e15e55651f7931fd72b8e6
apply_pin fieldlog-entry-save/apple-editor/fieldlog-apple-editor-queued-close.patch
check_tree 380e764598c31181d16ef2fbb91c95bf95693375
git -C "$app" apply --index "$here/initial-candidate.patch"
check_tree 1fb23eb6096ce5d3eb170d47808ab4119e3659c4
cmp "$app/Sources/FieldLogFeatures/TaskEditorPresentation.swift" \
    "$app/Integrations/GeneratedReport/Sources/FieldLogFeatures/TaskEditorPresentation.swift"
git -C "$app" apply --index "$here/cross-package-correction.patch"
check_tree eb08569c13b5f65e25edd0dfde1fe70fc8278ece
cmp "$app/Sources/FieldLogFeatures/TaskEditorPresentation.swift" \
    "$app/Integrations/GeneratedReport/Sources/FieldLogFeatures/TaskEditorPresentation.swift"
printf 'Verified reviewed, initial-candidate, and corrected app trees\n'


[[ "$(git -C "$mixer" rev-parse "${mixer_rev}^{tree}")" == d888b6a1ef9331079b98a0dc21c3a1b8ee482894 ]]
git -C "$mixer" archive "$mixer_rev" sdk | tar -xf - -C "$work/mixer"
fetch apple swift-crypto c2cbadd7263439d8015189668f96ff5b5be565ce c050c318c6c6fa86dcc64be17593496f2469410b0179707c37e078d29de12c12
fetch apple swift-asn1 3b6410f7dee09eb33cdd26260c5fd47fda19b0e2 90c66e2d1efba093afc1bfee861d2208c43d122340218ce5558b3cebd1252b26
