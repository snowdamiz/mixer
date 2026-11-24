#!/usr/bin/env bash
set -euo pipefail

fixture=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$fixture/../../../.." && pwd)
replay=$(cd "${1:?Supply a fresh directory under verification/local}" && pwd)
case "$replay/" in
  "$repo/verification/local/"*/) ;;
  *) echo "Replay directory must be under verification/local" >&2; exit 2 ;;
esac

mkdir "$replay/source" "$replay/tmp" "$replay/cache" "$replay/config" "$replay/security"
export TMPDIR="$replay/tmp/" CLANG_MODULE_CACHE_PATH="$replay/cache/clang"
cd "$repo"

swift --version
git rev-parse HEAD 'HEAD^{tree}'
shasum -a 256 sdk/Sources/{MixerCore,MixerUI,MixerSwiftUI,MixerApple}/*.swift \
  sdk/Tests/MixerAppleTests/SynchronousTextHostTests.swift "$fixture"/{StarterFeature.swift,BundledMountTests.swift,host-replay.sh} \
  > "$replay/input-sha256.txt"
shasum -a 256 "$replay/input-sha256.txt"

for module in MixerCore MixerUI MixerSwiftUI MixerApple; do
  mkdir "$replay/source/$module"
  cp "sdk/Sources/$module/"*.swift "$replay/source/$module/"
done
mkdir "$replay/source/Starter" "$replay/source/Tests"
cp "$fixture/StarterFeature.swift" "$replay/source/Starter/"
cp "$fixture/BundledMountTests.swift" sdk/Tests/MixerAppleTests/SynchronousTextHostTests.swift "$replay/source/Tests/"

cat > "$replay/source/Package.swift" <<'SWIFT'
// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Mixer",
    platforms: [.macOS(.v14)],
    targets: [
        .target(name: "MixerCore", path: "MixerCore"),
        .target(name: "MixerUI", dependencies: ["MixerCore"], path: "MixerUI"),
        .target(name: "MixerSwiftUI", dependencies: ["MixerUI"], path: "MixerSwiftUI"),
        .target(name: "MixerApple", dependencies: ["MixerCore", "MixerUI", "MixerSwiftUI"], path: "MixerApple",
                swiftSettings: [.define("MIXER_BUNDLED_MOUNT_REPLAY")]),
        .target(name: "UP5StarterFeature", dependencies: ["MixerSwiftUI"], path: "Starter",
                swiftSettings: [.unsafeFlags(["-module-alias", "SwiftUI=MixerSwiftUI"])]),
        .testTarget(name: "ReplayTests", dependencies: ["MixerApple", "MixerUI", "UP5StarterFeature"], path: "Tests")
    ]
)
SWIFT

run_tests() {
  swift test --package-path "$replay/source" --scratch-path "$replay/build" \
    --cache-path "$replay/cache" --config-path "$replay/config" --security-path "$replay/security" "$@"
}

run_tests > "$replay/baseline.log" 2>&1
grep -E 'Executed [0-9]+ tests?, with 0 failures|Test run with [0-9]+ tests? .* passed' "$replay/baseline.log"

mount="$replay/source/MixerApple/MixerBundledFeatureMount.swift"
cp "$mount" "$replay/baseline-mount.swift"
run_mutant() {
  local mutant=$1 test=$2 match=$3 replacement=${4-}
  python3 - "$replay/baseline-mount.swift" "$mount" "$match" "$replacement" <<'PY'
from pathlib import Path
import sys

source, output = map(Path, sys.argv[1:3])
match, replacement = sys.argv[3:]
text = source.read_text()
if text.count(match) != 1:
    raise SystemExit(f"Expected a unique mutation site: {match!r}")
output.write_text(text.replace(match, replacement, 1))
PY
  if run_tests --filter "BundledMountTests/$test" > "$replay/$mutant.log" 2>&1; then
    echo "Surviving mutant: $mutant" >&2
    return 1
  fi
  # A compiler, runner or test discovery error is not a killed mutant.
  grep -F "Test Case '-[ReplayTests.BundledMountTests $test]' failed" "$replay/$mutant.log" >/dev/null
  echo "Refused mutant: $mutant ($test)"
}

run_mutant promotion testExactReceiptBeforeForeignUpdateCannotPromote ' host.isCurrent(receipt.snapshot),'
run_mutant admission testForeignUpdateAfterPromotionRevokesOldCallback $',\n              host.isCurrent(displayed.snapshot)'
run_mutant terminal testCancelFromReadyObserverStaysTerminal '        if let terminalStatus { status = terminalStatus }'
run_mutant dropped-edit testHeldTextBindingContinuesAcrossItsOwnReceipts \
  '        if !latest.utf8.elementsEqual(installed.utf8) {' '        if latest.utf8.elementsEqual(installed.utf8) {'
run_mutant stale-cursor testHeldTextBindingContinuesAcrossItsOwnReceipts '        edit.snapshot = snapshot'
