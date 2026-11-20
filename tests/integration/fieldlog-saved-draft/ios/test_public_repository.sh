#!/bin/bash
set -euo pipefail

here=$(cd -- "$(dirname -- "$0")" && pwd -P)
mixer_pin=9c14c70b5a2b8bd8b99b2b632fd5e67a590375e5
fieldlog_pin=552559d2d3278abb9b1aa7dcf0288102c09a202b
patches=tests/integration/fieldlog-saved-draft/android/audited-patches
scratch=$(mktemp -d "${TMPDIR:-/tmp}/fieldlog-ios-public-repository.XXXXXXXX")
trap 'rm -rf -- "$scratch"' EXIT
scratch=$(cd -- "$scratch" && pwd -P)
mkdir "$scratch"/{source,modules,workspace,floor,successor,tmp}
export TMPDIR="$scratch/tmp"

curl --fail --silent --show-error --location --max-time 20 --max-filesize 5000000 \
  "https://codeload.github.com/snowdamiz/fieldlog/tar.gz/$fieldlog_pin" -o "$scratch/source.tar.gz"
printf '%s  %s\n' 75d2ce2663ade805ca40831b17a460c248e88c62a7689d5a671182bbf0ed7840 \
  "$scratch/source.tar.gz" | shasum -a 256 -c

# Apply the tracked, reviewed deltas only to the disposable public source.
for patch in rollback-floor optional-successor; do
  git -C "$here" show "$mixer_pin:$patches/$patch.patch" > "$scratch/$patch.patch"
done
tar -xzf "$scratch/source.tar.gz" -C "$scratch/source" --strip-components 1
git -C "$scratch/source" init -q
git -C "$scratch/source" -c core.autocrlf=false add -f -- .

declare -a compiler=(/usr/bin/swiftc -swift-version 6 -module-cache-path "$scratch/modules")
build() {
  local stage=$1
  local product="$scratch/$stage"
  shift
  "${compiler[@]}" -parse-as-library -emit-module -emit-library -module-name FieldLogModels \
    -o "$product/libFieldLogModels.dylib" "$scratch/source/Sources/FieldLogModels/"*.swift
  "${compiler[@]}" -parse-as-library -emit-module -emit-library -module-name FieldLogStorage \
    -I "$product" -L "$product" -lFieldLogModels \
    -o "$product/libFieldLogStorage.dylib" "$scratch/source/Sources/FieldLogStorage/"*.swift
  "${compiler[@]}" -parse-as-library -I "$product" -L "$product" -lFieldLogModels -lFieldLogStorage \
    -Xlinker -rpath -Xlinker "$product" -o "$product/control" "$here/RepositoryControl.swift" "$@"
}

apply_and_check() {
  git -C "$scratch/source" apply --index "$scratch/$1.patch"
  test "$(git -C "$scratch/source" write-tree)" = "$2"
  printf '%s tree %s\n' "$1" "$2"
}

/usr/bin/swiftc --version
apply_and_check rollback-floor b81afd281ab00dbd1dc06d7ce0605b7f360aada6
build floor
apply_and_check optional-successor eed0ea9f778a0b570c7abd1effe94aec7aa11fbb
build successor -DOPTIONAL_SUCCESSOR
"$scratch/successor/control" set-optional "$scratch/workspace"
mkdir "$scratch/pre-edit"
cp "$scratch/workspace/workspace.json" "$scratch/pre-edit/"
cp -R "$scratch/workspace/photos" "$scratch/pre-edit/"
"$scratch/floor/control" rollback-edit "$scratch/workspace"
"$scratch/successor/control" reopen "$scratch/workspace"
python3 -B - "$here" "$scratch" <<'PY'
from pathlib import Path
import sys
from uuid import UUID

sys.path.insert(0, sys.argv[1])
from verify import compare_action, require, snapshot

root = Path(sys.argv[2])
first = UUID("F989403F-D7FA-4836-881C-B7F60C82E387")
second = UUID("5F0897D2-1775-4DE5-AD1B-308F230022B3")
before = snapshot(root / "pre-edit", first, second)
after = snapshot(root / "workspace", first, second)
compare_action("offline-edit", first, before, after, "Updated in the ordinary editor’s save path")
require(before.jpeg_digest == after.jpeg_digest, "Host floor edit changed JPEG bytes")
print("PASS verifier on snapshots from exact public repository")
PY
used_kib=$(du -sk "$scratch" | cut -f1)
printf 'Owned scratch: %s KiB before cleanup\n' "$used_kib"
