#!/bin/bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
run=$1
stage=$2
assembly=$3
input=d4c99c2f5327ecff22711c66ef99de770dc1651b
engine=6bc461f4fc7c29771718c7c5ce5a2a39b78f4d2d
appTree=74cdeca2ed0d4b0eb6b1bc1a6c5fa278b8ee498a
export GIT_OPTIONAL_LOCKS=0 GIT_NO_LAZY_FETCH=1 GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
export PYTHONUNBUFFERED=1
ulimit -c 0

test "$(git -C "$stage" rev-parse "$input^{tree}")" = 9e3f19f2c66185b6a8f77eaf75a2af0b9908ab1f
test "$(git -C "$stage" rev-parse "$engine^{tree}")" = d888b6a1ef9331079b98a0dc21c3a1b8ee482894
test "$(git -C "$stage" rev-parse "$engine:sdk")" = faabd24e953377801106ea597aa0fed672eea46c
test "$(git -C "$stage" rev-parse "$engine:vm")" = d92bb09472d2aa448e6162541726daca8711fbd0
for pin in \
    combined-app-host-and-ios-native:308d0ed174406ed8c915c0bb65fce2d9f4004f0d148e87bce85f3a19186b8e58 \
    shared-project-detail-host:4f93155d042611b6dd8e7374a8b9d7ab3b42302338cbb3e20f2cd8141dbbb721 \
    shared-workspace-transaction-host:8bf358b8b98c5a43fb03f16d245608542a5985f85a430cccb7531f3dd1d4b927; do
    IFS=: read -r name hash <<< "$pin"
    for rev in "$input" f4a7fca378737786642647939ea61d17df80327d; do
        actual=$(git -C "$stage" show "$rev:verification/receipts/l08-d2-$name-20261123.patch.b64" | shasum -a 256 | cut -d' ' -f1)
        test "$actual" = "$hash"
    done
done
printf 'SOURCE input=%s mixer=%s sdk=%s vm=%s\n' "$input" "$engine" \
    "$(git -C "$stage" rev-parse "$engine:sdk")" "$(git -C "$stage" rev-parse "$engine:vm")"
sw_vers
git --version
python3 --version
DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer /usr/bin/xcodebuild -version
DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer /usr/bin/swift --version

w="$run/work"
mkdir "$w"
export TMPDIR="$run"
bash "$assembly" "$w"
app="$w/fieldlog"
test "$(git -C "$app" write-tree)" = "$appTree"
git -C "$app" diff --quiet
source_commit=$(
    GIT_AUTHOR_NAME='Mixer Local Replay' GIT_AUTHOR_EMAIL='replay@example.invalid' \
    GIT_COMMITTER_NAME='Mixer Local Replay' GIT_COMMITTER_EMAIL='replay@example.invalid' \
    GIT_AUTHOR_DATE='2026-11-23T00:00:00Z' GIT_COMMITTER_DATE='2026-11-23T00:00:00Z' \
    git -C "$app" commit-tree "$appTree" -m 'Reconstructed FieldLog D2 host replay input'
)
test "$(git -C "$app" rev-parse "$source_commit^{tree}")" = "$appTree"
printf 'SOURCE disposableFieldLogCommit=%s fieldLogTree=%s\n' "$source_commit" "$appTree"
export TMPDIR="$w/tmp"
git -C "$stage" archive "$input" tests/integration/fieldlog-saved-draft | tar -xf - -C "$w/mixer"

# Use the Android application module roster and build flags. Change only the
# package path for the host projection and link the real Swift/C entry points.
mkdir -p "$w/ordinary" "$w/host/Sources/"{ReplayedApp,FieldLogInstalledGuest,FieldLogHostTest/include}
report="$app/Integrations/GeneratedReport"
cp -R "$report/Sources" "$w/ordinary/Sources"
sed 's|"Generated/MixerSDK"|"../mixer/sdk"|g; s|package: "MixerSDK"|package: "sdk"|g' \
    "$report/Platforms/Android/ApplicationPackage.swift" > "$w/ordinary/Package.swift"
cp "$here/Package.swift" "$w/host/"
cp "$app/Integrations/InstalledGuest/"*.swift "$w/host/Sources/FieldLogInstalledGuest/"
cp "$report/Sources/FieldLogAndroid/"*.swift "$w/host/Sources/ReplayedApp/"
cp "$here/Replay.swift" "$w/host/Sources/ReplayedApp/"
cp "$here/ReplayWitness.c" "$w/host/Sources/FieldLogHostTest/"
cp "$here/FieldLogHostTest.h" "$w/host/Sources/FieldLogHostTest/include/"
for file in "$w/host/Sources/FieldLogInstalledGuest/"*.swift; do
    cmp "$file" "$app/Integrations/InstalledGuest/${file##*/}"
    printf 'OWNER %s %s\n' "${file##*/}" "$(shasum -a 256 "$file" | cut -d' ' -f1)"
done
for name in SignedChecklist NativeEntry PublicFactory SignedEntryCommit; do
    cmp "$report/Sources/FieldLogAndroid/$name.swift" "$w/host/Sources/ReplayedApp/$name.swift"
    printf 'OWNER %s.swift %s\n' "$name" "$(shasum -a 256 "$w/host/Sources/ReplayedApp/$name.swift" | cut -d' ' -f1)"
done
# Reuse the pinned signer with the same canonical v3 wire format, a
# production bundle ID and a host-specific identity version.
sed -e 's/import FieldLogDraftIntegration/import FieldLogInstalledGuest/' \
    -e 's/dev.mixer.fieldlog.saveddraft/dev.fieldlog.generatedr90/' \
    -e 's/fieldlog-saved-draft-host/fieldlog-d2-macos-owner/' \
    "$w/mixer/tests/integration/fieldlog-saved-draft/host/Sign.swift" > "$w/host/Sources/ReplayedApp/Sign.swift"
bash "$here/prepare-host.sh" "$run" "$stage"
bash "$here/build-host.sh" "$run"
file -L "$run/swift-build/debug/fieldlog-d2-host"
python3 -B "$here/execute.py" "$run" "$source_commit"
