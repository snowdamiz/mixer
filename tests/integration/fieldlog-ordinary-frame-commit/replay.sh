#!/usr/bin/env bash
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
repo="$(git -C "$here" rev-parse --show-toplevel)"
jdk="${MIXER_JDK:-/opt/homebrew/opt/openjdk@25}"
sdk="${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}"
jar="$sdk/platforms/android-36/android.jar"
test -f "$jar"
"$jdk/bin/javac" -version

public=73717993d6eea1d968b51f86f701e02406436d41
recipe_ref=2fbba61cb168a9d9a5a7a99e3ffbf43fd9533f4f
sdk_revision=857e4b4aa7a32cda368257b2be1a63e77106bed8
base=9c2d665c31a6f3f2bfabc42bdfffaf72c6661731
successor=807c198cfe800e1b3be7c94795240b29bdd9e3d5
before=15fc9d70092411954f98c69a670f7c6aa7c88b2e5feb0e58eb08b546a18713ad
after=0df1d83604d8738749e7aae93e469446ad2985dd644094771dcdeed6ef396ef1
recipe=tests/integration/fieldlog-pair25-android/rust-runtime-notices
scratch="$(mktemp -d "${TMPDIR:-/tmp}/fieldlog-frame-replay.XXXXXXXX")"
trap 'rm -rf -- "$scratch"' EXIT
patch="$scratch/fieldlog-ordinary-frame-commit.patch"
python3 -B -c 'import base64, pathlib, sys; sys.stdout.buffer.write(base64.b64decode(pathlib.Path(sys.argv[1]).read_bytes()))'     "$here/fieldlog-ordinary-frame-commit.patch.b64" > "$patch"

digest() {
    shasum -a 256 "$1" | cut -d ' ' -f 1
}
test "$(digest "$patch")" = 75f5559e1ad1b91dc669860fb1edc21a8e24bd430d3f1e1ce119f8b246a62161
git -C "$repo" archive "$recipe_ref" "$recipe" | tar -x -C "$scratch"
test "$(digest "$scratch/$recipe/prepare-successor.py")" = 99a8b563f84f345a0d2d6c63b5f11ad6d98434df2b517de34199845a2bf8580f
python3 -B "$scratch/$recipe/prepare-successor.py" --mixer "$repo" "$scratch/work"

app="$scratch/work/fieldlog"
mixer="$scratch/work/mixer"
android="$app/Integrations/GeneratedReport/Platforms/Android/Java/dev/fieldlog/generatedr90/androidhost"
activity="$android/PublicActivity.java"
test "$(git -C "$app" write-tree)" = 34810962320bdfb7877b8bbdd065495e9ec1e2bb
test "$(git -C "$mixer" rev-parse HEAD)" = "$sdk_revision"

apply_settings() {
    local name="$1" expected="$2"
    git -C "$repo" show "$public:verification/receipts/$name" > "$scratch/settings.patch"
    test "$(digest "$scratch/settings.patch")" = "$expected"
    git -C "$app" apply --index --unidiff-zero --whitespace=error "$scratch/settings.patch"
}
apply_settings fieldlog-ios-settings-bounded-7b2b98f0.patch \
    2639352790e03eadd4fc0ae1cb81fe2fbdcfd4d1c7f7d3f872dc405869fa7418
# The public canonical zero-context patch yields the same complete installed
# tree as the context-bearing Settings delta named in the build receipt.
apply_settings fieldlog-android-settings-elapsed-7b2b98f0.patch \
    b1c53a93f02fbbf057fc7e77244ad471b1f4c58a14268ae19c3bc038d9d1abb9
test "$(git -C "$app" write-tree)" = "$base"
test "$(digest "$activity")" = "$before"
printf 'Installed tree %s\n' "$base"
python3 -B "$here/run-host.py" --baseline --jdk "$jdk" "$activity"

git -C "$app" apply --index --whitespace=error "$patch"
test "$(git -C "$app" write-tree)" = "$successor"
test "$(digest "$activity")" = "$after"
printf 'Successor tree %s\n' "$successor"
python3 -B "$here/run-host.py" --jdk "$jdk" "$activity"

adapter_sources=()
for source in "$mixer/native/android/app/src/dev/mixer/android/"*.java; do
    case "${source##*/}" in
        MixerActivity.java|AdapterInstrumentation.java|AppearanceDescriptorV1.java|AppearanceResolutionV1.java) continue ;;
    esac
    adapter_sources+=("$source")
done
"$jdk/bin/javac" --release 17 -Xlint:all,-options -Werror -classpath "$jar" \
    -h "$scratch/headers" -d "$scratch/classes" "${adapter_sources[@]}" "$android/"*.java
printf 'Compiled production FieldLog and Pair25 adapter against API 36 (%s)\n' "$(digest "$jar")"

git -C "$app" apply --index --reverse --whitespace=error "$patch"
test "$(git -C "$app" write-tree)" = "$base"
test "$(digest "$activity")" = "$before"
git -C "$app" diff --exit-code
printf 'Reverse replay restored the exact installed tree\n'
