#!/bin/sh
# Selected package-tool metadata only. No update/install/network/BEAM/compiler.
set -eu
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
unset HOME
out=/tmp/compiler-metadata
mkdir -m 700 "$out"
id
uname -a
printf 'MIXER_CORE_LIMIT='
ulimit -c
for tool in /usr/bin/apt-get /usr/bin/apt-cache /usr/bin/dpkg /usr/bin/dpkg-query \
    /usr/lib/apt/apt-helper /usr/bin/gpgv /usr/bin/sha256sum /usr/bin/sha512sum \
    /usr/bin/sed /usr/bin/awk /usr/bin/date; do
    if [ ! -x "$tool" ]; then printf 'MIXER_MISSING_TOOL=%s\n' "$tool"; exit 78; fi
    printf 'MIXER_TOOL=%s\n' "$tool"
    sha256sum "$(readlink -f "$tool")"
done
/usr/bin/apt-get --version
/usr/bin/apt-cache --version
/usr/bin/dpkg --version
/usr/bin/gpgv --version
cp -L /var/lib/dpkg/status "$out/base-status"
cp -L /usr/share/keyrings/ubuntu-archive-keyring.gpg "$out/base-keyring.gpg"
chmod 444 "$out/base-status" "$out/base-keyring.gpg"
sha256sum "$out/base-status" "$out/base-keyring.gpg"
wc -c "$out/base-status" "$out/base-keyring.gpg"
/usr/bin/dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n'
printf 'MIXER_METADATA_C1_COMPLETED=1\n'
