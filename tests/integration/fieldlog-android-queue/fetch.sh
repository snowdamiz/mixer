#!/bin/bash
set -euo pipefail
umask 077
if [[ $# != 1 ]]; then
    printf 'Usage: %s NEW_SOURCE_DIRECTORY\n' "$0" >&2
    exit 2
fi
mkdir "$1"
source_dir="$(cd "$1" && pwd -P)"
export GIT_TERMINAL_PROMPT=0 GIT_NO_REPLACE_OBJECTS=1 GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_LFS_SKIP_SMUDGE=1

fetch() {
    local checkout="$1"
    shift
    git -C "$checkout" -c http.lowSpeedLimit=1 -c http.lowSpeedTime=45 fetch --depth=1 --no-tags "$@"
}

git init --bare -q --template= "$source_dir/fieldlog.git"
fetch "$source_dir/fieldlog.git" https://github.com/snowdamiz/fieldlog.git \
    552559d2d3278abb9b1aa7dcf0288102c09a202b:refs/heads/pinned

pair="$source_dir/mixer"
git init -q --template= "$pair"
git -C "$pair" remote add origin https://github.com/snowdamiz/mixer.git
git -C "$pair" config remote.origin.promisor true
git -C "$pair" config remote.origin.partialclonefilter blob:none
git -C "$pair" config http.lowSpeedLimit 1
git -C "$pair" config http.lowSpeedTime 45
fetch "$pair" --filter=blob:none origin 735ecec14e10e2dfed1e58a122c3fab08e569bef
git -C "$pair" sparse-checkout set --no-cone /sdk/ /cli/ /updates/ /native/android/
git -C "$pair" checkout --quiet --detach FETCH_HEAD

for pin in swift-crypto:5.0.3 swift-asn1:1.7.3; do
    name="${pin%:*}"
    tag="refs/tags/${pin#*:}"
    git init --bare -q --template= "$source_dir/$name.git"
    fetch "$source_dir/$name.git" "https://github.com/apple/$name.git" "$tag:$tag"
done
