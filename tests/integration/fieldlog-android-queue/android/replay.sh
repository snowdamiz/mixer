#!/bin/bash
set -euo pipefail
umask 077
if [[ $# != 2 ]]; then
    printf 'Usage: %s SOURCES PREPARED_SOURCE_DIRECTORY\n' "$0" >&2
    exit 2
fi
handoff="$(cd "$(dirname "$0")" && pwd -P)"
sources="$(cd "$1" && pwd -P)"
prepared="$(cd "$2" && pwd -P)"
pair=735ecec14e10e2dfed1e58a122c3fab08e569bef
sdk="$sources/mixer"
test "$(git -C "$sdk" rev-parse HEAD)" = "$pair"
test -z "$(git -C "$sdk" status --porcelain)"
test -d "$prepared/app/Integrations/GeneratedReport"
test -f "$prepared/pair23/sdk/Package.swift"
CROSS="$prepared/android-run"
mkdir "$CROSS"
source "$handoff/environment.sh"
source "$handoff/../git-offline.sh"
mkdir -p "$TMPDIR" "$CLANG_MODULE_CACHE_PATH" "$XDG_CACHE_HOME" "$CROSS/work/"{pair23,cli-cache,cli-config,cli-security}
cp -R "$prepared/pair23/." "$CROSS/work/pair23/"
git -C "$CROSS/work/pair23" init -q --template=
git -C "$CROSS/work/pair23" apply "$handoff/pair23-system-libz.patch"
"$HOST_SWIFT" build --package-path "$CROSS/work/pair23/cli" --scratch-path "$CROSS/work/cli-build" \
    --cache-path "$CROSS/work/cli-cache" --config-path "$CROSS/work/cli-config" --security-path "$CROSS/work/cli-security" \
    --manifest-cache local --disable-dependency-cache --force-resolved-versions --jobs "${FIELDLOG_SWIFT_JOBS:-8}" --product mixer \
    > "$CROSS/cli.log" 2>&1

app="$prepared/app/Integrations/GeneratedReport"
project="$CROSS/FieldLogGenerated"
cli="$CROSS/work/cli-build/debug/mixer"
python3 -B "$app/scripts/build-android.py" --mixer "$cli" --sdk-checkout "$sdk" \
    --android-adapter-path "$CROSS/work/pair23/native/android" --output "$project" \
    > "$CROSS/recipe.log" 2>&1
python3 -B "$handoff/inspect.py" "$CROSS" "$prepared" "$handoff/pair23-system-libz.patch"
