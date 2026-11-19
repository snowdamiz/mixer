#!/bin/bash
set -euo pipefail

recipe=$1
repo=$2
campaign=$3
scratch=$campaign/scratch
app=$scratch/app
mixer=$app/mixer
handoff=$campaign/handoff
fieldlog=$app/fieldlog
inputs=$recipe/inputs
overlays=$recipe/overlays
fieldlog_rev=552559d2d3278abb9b1aa7dcf0288102c09a202b
host_rev=c392e762d6bb24562647fe22a2de738250ba3e7f
guest_rev=3184c398ba5e5dcded110a65772d793ba9caf9f6
service_rev=9495996b00b5185c3d7fbf310615f69eadec9624
old_base=c09f99e1648fa2b1c8dbd42dcd928440ca08cee8
old_rev=15a2c0a98593d6e2bafaa1f5c00eb045c9815944
new_rev=9fd7e7f6ebd9cadfd96d71a6c71225e6b11e33b9
old_tree=3be293c03965386581dfc20f59f22dd318f21836
new_tree=527dbfd4f7f8a5a0f9556ba870b38d15187636a2

mkdir -p "$fieldlog" "$mixer" "$scratch/host" "$scratch/tmp" "$app/swift-deps" \
    "$app/lib-android" "$app/tmp" "$app/android-package/Sources" "$handoff/replay" "$handoff/tools"
export TMPDIR="$scratch/tmp"
export GIT_TERMINAL_PROMPT=0 GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_NO_REPLACE_OBJECTS=1
export GIT_LFS_SKIP_SMUDGE=1
export GIT_CEILING_DIRECTORIES="$scratch"

public=https://github.com/snowdamiz/mixer.git
source "$recipe/replay/git-sources.sh"

apply() {
    local destination=$1 file
    shift
    for file in "$@"; do
        git -C "$destination" apply --whitespace=nowarn "$file"
    done
}

curl -fLsS --max-time 90 -o "$scratch/fieldlog.tar.gz" \
    "https://codeload.github.com/snowdamiz/fieldlog/tar.gz/$fieldlog_rev"
echo "75d2ce2663ade805ca40831b17a460c248e88c62a7689d5a671182bbf0ed7840  $scratch/fieldlog.tar.gz" | shasum -a 256 -c
tar -xzf "$scratch/fieldlog.tar.gz" --strip-components=1 -C "$fieldlog"
rm "$scratch/fieldlog.tar.gz"
pair23_rev=30846456d5d7a031b4390503e3b0afb559732a32
pair23_patch=$scratch/pair23-public-build.patch
pinned_output "$pair23_patch" "$pair23_rev:verification/fieldlog-pair23/public-build.patch" show
printf '%s  %s\n' 8a09fb83471392e16c836aa3a95a8b02d841525e2cea2ea857415e0484006749 "$pair23_patch" | shasum -a 256 -c
apply "$fieldlog" "$pair23_patch"
apply "$fieldlog" "$overlays/fieldlog-l04.patch" "$overlays/fieldlog-signed-checklist-android-packaging.patch" \
    "$overlays/fieldlog-android-checklist-refresh.patch" "$overlays/fieldlog-android-witness.patch" \
    "$overlays/recovery-by-runtime.patch"

archive "$mixer" "$host_rev" sdk capability-activation runtime-identity updates experimental-capability-runtime \
    native/android/app/src native/android/signed-guest-ui verification/android-binding-stage4/host-bridge vm/include
apply "$mixer" "$overlays/mixer-android-witness.patch"
archive "$scratch/host" "$service_rev" services
archive "$scratch/guest-source" "$guest_rev:tests/integration/fieldlog-saved-draft/guest"
apply "$scratch/guest-source" "$overlays/selected-task.patch"
archive "$scratch/pair-new" "$new_rev" vm
archive "$scratch/pair-old" "$new_rev" vm
git -C "$scratch/pair-old" apply -R "$overlays/engine-validator.patch"
pinned_output "$scratch/pair-old/vm/tests/interpreter.rs" "$old_base:vm/tests/interpreter.rs" show
for label in old new; do
    case "$label" in old) revision=$old_rev tree=$old_tree ;; new) revision=$new_rev tree=$new_tree ;; esac
    engine=$scratch/pair-$label/vm
    git -C "$engine" init --quiet --template=
    git -C "$engine" add --all --force
    observed=$(git -C "$engine" write-tree)
    test "$observed" = "$tree" || { echo "VM tree $label expected $tree, found $observed" >&2; exit 1; }
    rm -r "$engine/.git"
    printf '%s\n%s\n' "$revision" "$tree" > "$scratch/engine-$label.txt"
done

asset=verification/android-default-appearance-packaging/run-1/created-descriptor.json
destination=$app/prepared/Generated/MixerAndroid/app/assets/MixerAppearanceV2
mkdir -p "$destination"
pinned_output "$destination/descriptor.json" "$host_rev:$asset" show
cp "$inputs"/{Package.swift,Package.resolved} "$app/android-package/"
cp "$inputs"/{offline-env.sh,compile-android-java.sh} "$app/"
feature_sources=$fieldlog/Integrations/GeneratedReport/Sources
for module in FieldLogAndroid FieldLogFeatures FieldLogModels FieldLogStorage; do
    ln -s "$feature_sources/$module" "$app/android-package/Sources/$module"
done
ln -s "$fieldlog/Integrations/InstalledGuest" "$app/android-package/Sources/FieldLogInstalledGuest"

for dep in swift-crypto:5.0.3:c2cbadd7263439d8015189668f96ff5b5be565ce \
           swift-asn1:1.7.3:3b6410f7dee09eb33cdd26260c5fd47fda19b0e2; do
    name=${dep%%:*}
    tail=${dep#*:}
    tag=refs/tags/${tail%%:*}
    revision=${tail#*:}
    mirror=$app/swift-deps/$name.git
    git init -q --bare --template= "$mirror"
    git -C "$mirror" -c http.lowSpeedLimit=1 -c http.lowSpeedTime=30 fetch --quiet --depth=1 \
        "https://github.com/apple/$name.git" "$tag:$tag"
    test "$(git -C "$mirror" rev-parse "$tag^{commit}")" = "$revision"
done

cp "$recipe"/replay/{origin.py,check-readback.py} "$handoff/replay/"
echo 'Prepared both exact VM trees and pinned public consumer inputs'
