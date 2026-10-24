#!/bin/sh
# Selected offline authentication and APT simulation only. No update/install.
set -eu
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
LC_ALL=C
export LC_ALL
umask 077
ulimit -c 0
unset HOME
out=/tmp/compiler-metadata
mkdir -m 700 "$out"
mkdir -m 700 "$out/gpg-home" "$out/lists" "$out/archives"
mkdir -m 700 "$out/lists/partial" "$out/archives/partial"
cp -L /var/lib/dpkg/status "$out/base-status"
cp -L /usr/share/keyrings/ubuntu-archive-keyring.gpg "$out/base-keyring.gpg"
sha256sum -c /inputs/expected-tools.sha256
: > "$out/solver.stdout"
: > "$out/solver.stderr"
printf "MIXER_BASE_PREPARED=1\n"
