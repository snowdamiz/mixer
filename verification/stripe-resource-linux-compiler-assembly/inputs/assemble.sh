#!/bin/sh
# Owned assembly script. Package maintainer scripts and payload tools never run.
set -eu
PATH=/usr/bin:/bin
LC_ALL=C
export PATH LC_ALL
unset HOME
umask 077
ulimit -c 0
out=/tmp/compiler-payload
tree=$out/tree
mkdir -m 700 "$out" "$tree"
printf '{"schema":1,"status":"native-assembly-pending"}\n' > "$out/payload-manifest.json"
cp /inputs/notice-inventory.json "$out/notice-inventory.json"
cp /inputs/control-inventory.json "$out/control-inventory.json"
for tool in /usr/bin/dpkg-deb /usr/bin/tar /usr/bin/find /usr/bin/sort /usr/bin/sha256sum /usr/bin/awk; do
    [ -x "$tool" ] || { printf 'MIXER_MISSING_TOOL=%s\n' "$tool"; exit 78; }
    printf 'MIXER_TOOL=%s\n' "$tool"
    sha256sum "$tool"
done
/usr/bin/dpkg-deb --version
/usr/bin/tar --version
# dpkg-deb consumes zstd/xz/gzip through existing image libraries. These are
# observed as bytes only; no unselected package decompressor is installed.
for library in /lib/aarch64-linux-gnu/libzstd.so.1 /lib/aarch64-linux-gnu/liblzma.so.5 /lib/aarch64-linux-gnu/libz.so.1; do
    [ -f "$library" ] || { printf 'MIXER_MISSING_DECOMPRESSOR_LIBRARY=%s\n' "$library"; exit 78; }
    sha256sum "$library"
done
sha256sum -c /inputs/packages.sha256
# Every input archive and the complete cross-package data/link graph were
# validated before this single native attempt. dpkg-deb -x only extracts data.
while IFS=' ' read -r expected archive; do
    archive=${archive# }
    /usr/bin/dpkg-deb --extract "$archive" "$tree"
done < /inputs/packages.sha256
printf 'MIXER_DATA_EXTRACTION_COMPLETED=1\n'
/usr/bin/find "$tree" -type f -exec /usr/bin/sha256sum '{}' + > "$out/hashes.txt"
/usr/bin/find "$tree" -mindepth 1 -printf '%P\t%y\t%m\t%s\t%l\t%i\t%n\t%U\t%G\n' | /usr/bin/sort > "$out/entries.tsv"
# Host path controls reject quote/backslash/control characters, making these
# finite JSON string fields unambiguous; actual file hashes remain independent.
/usr/bin/awk -F '\t' '
FILENAME == ARGV[1] { path=substr($0,67); sub("^/tmp/compiler-payload/tree/", "", path); hash[path]=substr($0,1,64); next }
BEGIN { printf "{\"schema\":1,\"files\":["; first=1; expanded=0 }
{
 if (!first) printf ","; first=0;
 printf "{\"path\":\"%s\",\"nativeType\":\"%s\",\"modeOctal\":\"%s\",\"bytes\":%s,\"target\":\"%s\",\"inode\":%s,\"links\":%s,\"uid\":%s,\"gid\":%s", $1,$2,$3,$4,$5,$6,$7,$8,$9;
 if ($2 == "f") { printf ",\"sha256\":\"%s\"", hash[$1]; expanded += $4 }
 printf "}";
}
END { printf "],\"expandedRegularBytes\":%.0f,\"compilerExecuted\":false,\"scriptsExecuted\":false}\n", expanded }
' "$out/hashes.txt" "$out/entries.tsv" > "$out/payload-manifest.json"
/usr/bin/tar --sort=name --format=gnu \
    --mtime=@0 --owner=0 --group=0 --numeric-owner -cf "$out/compiler-payload.tar" -C "$tree" .
bytes=$(wc -c < "$out/compiler-payload.tar")
[ "$bytes" -le 268435456 ] || exit 78
sha256sum "$out/payload-manifest.json" "$out/notice-inventory.json" "$out/control-inventory.json" "$out/compiler-payload.tar"
printf 'MIXER_COMPILER_PAYLOAD_TAR_BYTES=%s\n' "$bytes"
if [ -e "$tree/usr/bin/cc" ] || [ -L "$tree/usr/bin/cc" ]; then
    printf 'MIXER_ARCHIVED_CC_PRESENT=1\n'
else
    printf 'MIXER_ARCHIVED_CC_PRESENT=0\n'
fi
printf 'MIXER_STATIC_ASSEMBLY_COMPLETED=1\n'
