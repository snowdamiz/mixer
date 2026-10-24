#!/bin/sh
set -eu
PATH=/usr/local/bin:/usr/bin:/bin
LC_ALL=C
export PATH LC_ALL
unset HOME
out=/tmp/compiler-metadata
# Finite negative controls use only disposable copies of public metadata.
sed 's/^Origin: Ubuntu$/Origin: MixerTampered/' /inputs/noble.InRelease > "$out/tampered.InRelease"
if /usr/bin/gpgv --homedir "$out/gpg-home" --status-fd 1 --keyring "$out/base-keyring.gpg" \
    --output "$out/tampered.Release" "$out/tampered.InRelease" > "$out/negative-signature.status" 2> "$out/negative-signature.stderr"; then
    exit 78
fi
grep -q '^\[GNUPG:\] BADSIG ' "$out/negative-signature.status" || exit 78
cat "$out/negative-signature.status"
printf 'MIXER_TAMPERED_SIGNATURE_REJECTED=1\n'
cp /inputs/noble.Packages.xz "$out/tampered.Packages.xz"
chmod 600 "$out/tampered.Packages.xz"
printf '\000' | dd of="$out/tampered.Packages.xz" bs=1 seek=0 conv=notrunc 2>/dev/null
expected_noble=$(sha256sum /inputs/noble.Packages.xz | cut -d ' ' -f 1)
if printf '%s  %s\n' "$expected_noble" "$out/tampered.Packages.xz" | sha256sum -c -; then
    exit 78
fi
printf 'MIXER_TAMPERED_INDEX_REJECTED=1\n'
expanded=0
for suite in noble noble-updates noble-security; do
    /usr/lib/apt/apt-helper cat-file "/inputs/$suite.Packages.xz" > "$out/$suite.Packages"
    bytes=$(wc -c < "$out/$suite.Packages" | tr -d ' ')
    expanded=$((expanded + bytes))
    [ "$expanded" -le 268435456 ] || exit 78
    cp "$out/$suite.Packages" "$out/lists/ports.ubuntu.com_ubuntu-ports_dists_${suite}_main_binary-arm64_Packages"
    cp "/inputs/$suite.InRelease" "$out/lists/ports.ubuntu.com_ubuntu-ports_dists_${suite}_InRelease"
done
printf 'MIXER_METADATA_EXPANDED_BYTES=%s\n' "$expanded"
for suite in noble noble-updates noble-security; do
    printf 'deb [arch=arm64 signed-by=/tmp/compiler-metadata/base-keyring.gpg] https://ports.ubuntu.com/ubuntu-ports %s main\n' "$suite"
done > "$out/sources.list"
if APT_CONFIG=/inputs/offline.conf /usr/bin/apt-get --simulate --no-install-recommends \
    -o APT::Install-Suggests=false --no-remove install gcc:arm64 libc6-dev:arm64 binutils:arm64 \
    > "$out/solver.stdout" 2> "$out/solver.stderr"; then
    code=0
else
    code=$?
fi
cat "$out/solver.stdout"
cat "$out/solver.stderr" >&2
printf 'MIXER_SOLVER_EXIT=%s\n' "$code"
[ "$code" -eq 0 ] || exit 78
printf 'MIXER_METADATA_C3_COMPLETED=1\n'
