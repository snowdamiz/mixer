#!/bin/sh
set -eu
PATH=/usr/local/bin:/usr/bin:/bin
LC_ALL=C
export PATH LC_ALL
unset HOME
out=/tmp/compiler-metadata
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
