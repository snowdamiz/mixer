#!/bin/bash
set -euo pipefail
umask 077
journey=$(cd "$(dirname "$0")" && pwd)
if [[ $# != 3 ]]; then
    printf 'Usage: %s SOURCES PREPARED EXISTING_RECEIPT_DIRECTORY\n' "$0" >&2
    exit 2
fi
sources="$(cd "$1" && pwd -P)"
lane="$2"
receipt="$3"
test -d "$receipt"
lane="$(cd "$lane" && pwd -P)"
receipt="$(cd "$receipt" && pwd -P)"
sdk="$lane/pair23/sdk"
candidate="$lane/app/Integrations/GeneratedReport"
work=$(mktemp -d "$lane/host-run.XXXXXXXX")

# Add a host ABI driver in an isolated copy of the accepted Swift package.
mkdir -p "$work/source/Sources/QueueJourney" "$work/cache" "$work/tmp"
cp "$candidate/Package.swift" "$work/source/"
cp "$work/source/Package.swift" "$work/candidate-manifest.swift"
cp -R "$candidate/Sources/." "$work/source/Sources/"
cp -R "$candidate/Tests" "$work/source/"
cp "$journey/QueueJourney.swift" "$work/source/Sources/QueueJourney/"
cp "$sdk/Package.resolved" "$work/source/"
mkdir -p "$work/source/Sources/QueueABI/include"
cat > "$work/source/Sources/QueueABI/include/QueueABI.h" <<'C'
#include <stdint.h>

typedef int32_t (*QueueSurface)(int64_t, int32_t, const uint8_t *, intptr_t,
                               const uint8_t *, intptr_t, const uint8_t *, intptr_t);
int32_t mixer_public_android_submit(int64_t, int32_t, const uint8_t *, intptr_t,
                                   const uint8_t *, intptr_t, const uint8_t *, intptr_t,
                                   const uint8_t *, intptr_t, QueueSurface);
int32_t mixer_public_android_poll(int64_t);
C
touch "$work/source/Sources/QueueABI/QueueABI.c"
python3 - "$work/source/Package.swift" <<'PY'
from pathlib import Path
import sys
manifest = Path(sys.argv[1])
source = manifest.read_text()
marker = "    targets: [\n"
addition = '''        .target(name: "QueueABI"),
        .executableTarget(name: "QueueJourney", dependencies: ["QueueABI", "FieldLogAndroid", "FieldLogModels", "FieldLogStorage", .product(name: "MixerAndroid", package: "mixer"), .product(name: "MixerUI", package: "mixer")]),
'''
assert source.count(marker) == 1
manifest.write_text(source.replace(marker, marker + addition))
PY
export FIELDLOG_MIXER_SDK="$sdk"
export TMPDIR="$work/tmp/"
export CLANG_MODULE_CACHE_PATH="$work/module-cache"
source "$journey/../git-offline.sh"
swift_build=(swift build --disable-sandbox --disable-netrc --disable-dependency-cache --force-resolved-versions --jobs "${FIELDLOG_SWIFT_JOBS:-8}" --package-path "$work/source"
    --scratch-path "$work/swift-build" --cache-path "$work/cache" --config-path "$work/config"
    --security-path "$work/security" --product QueueJourney)
if ! /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' "${swift_build[@]}" >"$work/build.log" 2>&1; then
    cat "$work/build.log" >&2
    exit 1
fi
tail -4 "$work/build.log"
binary=$(/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' "${swift_build[@]}" --show-bin-path)/QueueJourney
for interruption in cancel close; do
    python3 -B "$journey/journey.py" "$binary" "$lane/app/Backend/local_entry_sync.py" \
        "$work/runtime-$interruption" "$receipt/host-$interruption.json" "$work/source" "$sdk" "$work/source/Package.resolved" "$interruption"
done

mkdir "$work/regression-workspaces"
export FIELDLOG_WORKSPACE="$work/regression-workspaces"
swift_tests=("${swift_build[@]}")
swift_tests[1]=test
if ! /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
    "${swift_tests[@]:0:${#swift_tests[@]}-2}" \
    --filter 'EntryPresentationTests|FieldLogGeneratedHostTests|PaginationContractTests' > "$work/tests.log" 2>&1; then
    tail -80 "$work/tests.log" >&2
    exit 1
fi
grep -E 'Executed [0-9]+ tests?, with|✔ Test run with' "$work/tests.log" > "$receipt/host-regression.txt"
rm -rf -- "$work"
