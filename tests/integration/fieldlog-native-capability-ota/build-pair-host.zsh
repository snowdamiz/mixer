#!/bin/zsh
set -eu
work=${1:A}
calc=${2:A}
recipe=${0:A:h}
package="$work/host-package"
source "$calc/offline-swiftpm.zsh"
export TMPDIR="$work/tmp" CLANG_MODULE_CACHE_PATH="$work/host-clang" SWIFTPM_MODULECACHE_OVERRIDE="$work/host-modules"
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
cp "$work/host-build/debug/Probe" "$work/storage-only-probe"
cp "$recipe/SealPair.swift" "$package/Sources/Seal/Seal.swift"
python3 -B - "$package/Sources/Probe/Probe.swift" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
text = source.read_text()
old = 'percentages == (sequence == 2 ? ["33%", "100%", "0%"] : ["0%", "100%", "0%"])'
if text.count(old) != 1:
    raise SystemExit("Unexpected calculation presentation probe")
source.write_text(text.replace(old, 'percentages == ["33%", "100%", "0%"]'))
PY
/usr/bin/swift build --package-path "$package" --scratch-path "$work/host-build" \
    --cache-path "$work/host-cache" --config-path "$work/host-config" --security-path "$work/host-security" \
    --disable-dependency-cache --disable-prefetching --skip-update --force-resolved-versions \
    --jobs 8 --disable-index-store -Xswiftc -DFIELDLOG_CALCULATION_FIXTURE -Xswiftc -gnone \
    -Xcc "-I$work/host-engine/include" -Xlinker "-L$work/host-engine/lib"
