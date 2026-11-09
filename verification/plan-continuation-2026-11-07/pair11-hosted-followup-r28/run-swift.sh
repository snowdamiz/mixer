#!/bin/bash
set -euo pipefail
cd /Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4
D=verification/plan-continuation-2026-11-07/pair11-hosted-followup-r28
export DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer
export SDKROOT=/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk
export TOOLCHAINS=com.apple.dt.toolchain.XcodeDefault
unset MIXER_SWIFT JAVA_TOOL_OPTIONS
python3 -I -B -S scripts/ci/prepare-cli-host-tests.py --toolchain-receipt "$D/apple-toolchain.json" --output "$PWD/$D/host" > "$D/host-selection.stdout"
source "$D/host/environment.sh"
swift build --package-path cli --scratch-path "$PWD/$D/build" --product mixer -j 2 > "$D/swift-build.log" 2>&1
export MIXER_STORE_TEST_CLI="$PWD/$D/build/arm64-apple-macosx/debug/mixer"
test -x "$MIXER_STORE_TEST_CLI"
swift test --package-path cli --scratch-path "$PWD/$D/build" -j 2 > "$D/swift-tests.log" 2>&1
