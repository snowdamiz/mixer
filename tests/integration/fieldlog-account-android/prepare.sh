#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 2 && ( $# != 3 || "$3" != --baseline ) ]]; then
    printf 'Usage: %s MIXER_CHECKOUT NEW_WORK_PATH [--baseline]\n' "$0" >&2
    exit 2
fi

handoff="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$1" && pwd)"
work="$2"
base=820ae2102905e76df153f4c0b7ac1b727d9fe751
recipe_ref=2fbba61cb168a9d9a5a7a99e3ffbf43fd9533f4f
recipe=tests/integration/fieldlog-pair25-android/rust-runtime-notices
sdk=857e4b4aa7a32cda368257b2be1a63e77106bed8
installed=9c2d665c31a6f3f2bfabc42bdfffaf72c6661731
corrected=807c198cfe800e1b3be7c94795240b29bdd9e3d5

digest() {
    shasum -a 256 "$1" | cut -d ' ' -f 1
}

git -C "$repo" cat-file -e "$base^{commit}"
recipe_work="$(mktemp -d "$(dirname "$work")/.fieldlog-frame-recipe.XXXXXXXX")"
trap 'rm -rf -- "$recipe_work"' EXIT

decode() {
    local source="$1" target="$2" sha="$3"
    python3 -B -c 'import base64, pathlib, sys; sys.stdout.buffer.write(base64.b64decode(pathlib.Path(sys.argv[1]).read_bytes()))' "$source" > "$target"
    test "$(digest "$target")" = "$sha"
}
decode "$handoff/../fieldlog-ordinary-frame-commit/fieldlog-ordinary-frame-commit.patch.b64" "$recipe_work/frame.patch" \
    75f5559e1ad1b91dc669860fb1edc21a8e24bd430d3f1e1ce119f8b246a62161
decode "$handoff/fieldlog-android-account-shell.patch.b64" "$recipe_work/account.patch" \
    a477754bc34745f2fb3e581503057d3065da92dc38ac3dab481789de59ed88c3

git -C "$repo" archive "$recipe_ref" "$recipe" | tar -x -C "$recipe_work"
test "$(digest "$recipe_work/$recipe/prepare-successor.py")" = 99a8b563f84f345a0d2d6c63b5f11ad6d98434df2b517de34199845a2bf8580f
python3 -B "$recipe_work/$recipe/prepare-successor.py" --mixer "$repo" "$work"

app="$work/fieldlog"
test "$(git -C "$work/mixer" rev-parse HEAD)" = "$sdk"
test "$(git -C "$app" write-tree)" = 34810962320bdfb7877b8bbdd065495e9ec1e2bb

apply_settings() {
    local name="$1" expected="$2"
    git -C "$repo" show "$base:verification/receipts/$name" > "$recipe_work/settings.patch"
    test "$(digest "$recipe_work/settings.patch")" = "$expected"
    git -C "$app" apply --index --unidiff-zero --whitespace=error-all "$recipe_work/settings.patch"
}

apply_settings fieldlog-ios-settings-bounded-7b2b98f0.patch \
    2639352790e03eadd4fc0ae1cb81fe2fbdcfd4d1c7f7d3f872dc405869fa7418
apply_settings fieldlog-android-settings-elapsed-7b2b98f0.patch \
    b1c53a93f02fbbf057fc7e77244ad471b1f4c58a14268ae19c3bc038d9d1abb9

test "$(git -C "$app" write-tree)" = "$installed"
git -C "$app" apply --index --whitespace=error-all "$recipe_work/frame.patch"
test "$(git -C "$app" write-tree)" = "$corrected"
git -C "$app" diff --exit-code
printf 'Verified corrected FieldLog tree %s and pinned Mixer SDK %s\n' "$corrected" "$sdk"

git -C "$app" apply --index --whitespace=error-all "$recipe_work/account.patch"
test "$(git -C "$app" write-tree)" = 08b6b6ed6ab977cfaff767b6e6953a0ea5d7fb2c

paired="$recipe_work/confirmed-owner"
mkdir "$paired"
bash "$repo/tests/integration/fieldlog-account-ios/prepare.sh" "$paired"
owner="$paired/source/fieldlog/Sources/FieldLogModels/FieldLogAccount.swift"
test "$(digest "$owner")" = e0511a3d374ccbd27d1ea38beb9e55d437e730513c9902f1289c04a25d23eacc
test "$(git hash-object "$owner")" = d6e383eeca9756d249c692cd01173951b8b9a419
relative=Integrations/GeneratedReport/Sources/FieldLogModels/FieldLogAccount.swift
test ! -e "$app/$relative"
cp "$owner" "$app/$relative"
git -C "$app" add -- "$relative"
test "$(git -C "$app" write-tree)" = 11d989672893be5e5cdb2488901469d57fae71f9
git -C "$app" diff --exit-code
printf 'Verified confirmed FieldLog Android composition %s\n' "$(git -C "$app" write-tree)"

if [[ ${3:-} != --baseline ]]; then
    decode "$handoff/fieldlog-android-account-mount.patch.b64" "$recipe_work/mount.patch" \
        548fe6eb410ff5d4ced63254755c67b63455d5392d4e9bffbc986060ddeb18ce
    git -C "$app" apply --index --whitespace=error-all "$recipe_work/mount.patch"
    test "$(git -C "$app" write-tree)" = 3e87547ef0a2e39e52142a9c85ec0a64014cbca2
    git -C "$app" diff --exit-code
    decode "$handoff/fieldlog-android-account-cold.patch.b64" "$recipe_work/cold.patch" \
        66c1da18f0dcb203a6e5adb88c5183783703d5d6289359d16b29afafe338f6a3
    git -C "$app" apply --index --whitespace=error-all "$recipe_work/cold.patch"
    test "$(git -C "$app" write-tree)" = 066e503849ee4561a8839e487b72d8724b51ed3c
    git -C "$app" diff --exit-code
    printf 'Verified corrected account mount and cold-start tree %s\n' "$(git -C "$app" write-tree)"
    decode "$handoff/fieldlog-android-account-warm-expiry.patch.b64" "$recipe_work/warm.patch" \
        5a1b24756ab7e460f45a6c7c1031acdf4155bd56fc693f67ff06261e6a438e0d
    git -C "$app" apply --index --whitespace=error-all "$recipe_work/warm.patch"
    test "$(git -C "$app" write-tree)" = 000c3321f7c1d63160b31fbedb3f1f14554e658b
    git -C "$app" diff --exit-code
    printf 'Verified active account expiry tree %s\n' "$(git -C "$app" write-tree)"
fi
