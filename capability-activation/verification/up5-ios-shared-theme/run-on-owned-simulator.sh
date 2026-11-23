#!/bin/sh
set -eu
: "${OWNED_SIMULATOR_UDID:?requires root ownership and Accessibility preflight}"
: "${UP5_ROOT_EVIDENCE:?requires a fresh root-owned results directory}"
test_run=$1
test -f "$test_run"
test_name=testProductThemeOnBundledAndSignedGuest
mkdir "$UP5_ROOT_EVIDENCE/tmp"
test ! -e "$UP5_ROOT_EVIDENCE/$test_name.xcresult"
test ! -e "$UP5_ROOT_EVIDENCE/$test_name.log"
export TMPDIR="$UP5_ROOT_EVIDENCE/tmp/"
exec /usr/bin/xcodebuild test-without-building -xctestrun "$test_run" \
  -destination "platform=iOS Simulator,id=$OWNED_SIMULATOR_UDID" \
  -parallel-testing-enabled NO -test-timeouts-enabled YES -maximum-test-execution-time-allowance 240 \
  -resultBundlePath "$UP5_ROOT_EVIDENCE/$test_name.xcresult" \
  "-only-testing:UP5ThemeUITests/UP5ThemeUITests/$test_name" \
  > "$UP5_ROOT_EVIDENCE/$test_name.log" 2>&1
