#!/bin/sh
# Selected offline authentication and APT simulation only. No update/install.
set -eu
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
unset HOME
out=/tmp/compiler-metadata
mkdir -m 700 "$out"
mkdir -m 700 "$out/gpg-home" "$out/lists" "$out/archives"
mkdir -m 700 "$out/lists/partial" "$out/archives/partial"
cp -L /var/lib/dpkg/status "$out/base-status"
cp -L /usr/share/keyrings/ubuntu-archive-keyring.gpg "$out/base-keyring.gpg"
sha256sum -c /inputs/expected-tools.sha256
signer=F6ECB3762474EDA9D21B7022871920D1991BC93C
now=$(date -u +%s)
field() { sed -n "s/^$1: //p" "$2"; }
for suite in noble noble-updates noble-security; do
    release="$out/$suite.Release"
    if ! /usr/bin/gpgv --homedir "$out/gpg-home" --status-fd 1 --keyring "$out/base-keyring.gpg" \
        --output "$release" "/inputs/$suite.InRelease" > "$out/$suite.gpg.status" 2> "$out/$suite.gpg.stderr"; then
        cat "$out/$suite.gpg.status"
        cat "$out/$suite.gpg.stderr" >&2
        printf 'MIXER_SIGNATURE_FAILED=%s\n' "$suite"
        exit 78
    fi
    cat "$out/$suite.gpg.status"
    cat "$out/$suite.gpg.stderr" >&2
    observed=$(awk '$1 == "[GNUPG:]" && $2 == "VALIDSIG" {print $3}' "$out/$suite.gpg.status")
    [ "$observed" = "$signer" ] || exit 78
    [ "$(field Origin "$release")" = Ubuntu ] || exit 78
    [ "$(field Suite "$release")" = "$suite" ] || exit 78
    [ "$(field Codename "$release")" = noble ] || exit 78
    case " $(field Architectures "$release") " in *' arm64 '*) ;; *) exit 78 ;; esac
    case " $(field Components "$release") " in *' main '*) ;; *) exit 78 ;; esac
    issued=$(date -u -d "$(field Date "$release")" +%s)
    [ "$issued" -le "$((now + 10))" ] || exit 78
    validity=$(field Valid-Until "$release")
    if [ -n "$validity" ]; then
        valid_until=$(date -u -d "$validity" +%s)
        [ "$valid_until" -ge "$now" ] || exit 78
        printf 'MIXER_VALID_UNTIL=%s:%s\n' "$suite" "$valid_until"
    else
        printf 'MIXER_VALID_UNTIL=%s:absent\n' "$suite"
    fi
    row=$(awk 'BEGIN {active=0} /^SHA512:$/ {active=1;next} /^[^ ]/ {active=0} active && $3 == "main/binary-arm64/Packages.xz" {print $1 " " $2}' "$release")
    algorithm=SHA512
    if [ -z "$row" ]; then
        row=$(awk 'BEGIN {active=0} /^SHA256:$/ {active=1;next} /^[^ ]/ {active=0} active && $3 == "main/binary-arm64/Packages.xz" {print $1 " " $2}' "$release")
        algorithm=SHA256
    fi
    set -- $row
    [ "$#" -eq 2 ] || exit 78
    expected=$1
    size=$2
    [ "$(wc -c < "/inputs/$suite.Packages.xz" | tr -d ' ')" = "$size" ] || exit 78
    if [ "$algorithm" = SHA512 ]; then
        [ "${#expected}" -eq 128 ] || exit 78
        printf '%s  %s\n' "$expected" "/inputs/$suite.Packages.xz" | sha512sum -c -
    else
        [ "${#expected}" -eq 64 ] || exit 78
        printf '%s  %s\n' "$expected" "/inputs/$suite.Packages.xz" | sha256sum -c -
    fi
    printf 'MIXER_SIGNER_VERIFIED=%s:%s\n' "$suite" "$observed"
    printf 'MIXER_INDEX_VERIFIED=%s:%s:%s:%s\n' "$suite" "$algorithm" "$expected" "$size"
    printf 'MIXER_RELEASE_ISSUED=%s:%s\n' "$suite" "$issued"
    sha256sum "$release"
done
printf 'MIXER_ALL_METADATA_AUTHENTICATED=1\n'
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
if APT_CONFIG=/inputs/offline.conf /usr/bin/apt-get --simulate --no-download --no-install-recommends \
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
printf 'MIXER_METADATA_C2_COMPLETED=1\n'
