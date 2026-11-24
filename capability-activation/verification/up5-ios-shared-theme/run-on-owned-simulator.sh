#!/bin/sh
set -eu
: "${OWNED_SIMULATOR_UDID:?requires root ownership and Accessibility preflight}"
: "${UP5_ROOT_EVIDENCE:?requires a fresh root-owned results directory}"
test_run=$1
test -f "$test_run"
test_name=${2:-testProductThemeOnBundledAndSignedGuest}
case "$test_name" in
  testIncreasedContrastOnBundledAndSignedGuest) requested=enabled ;;
  testProductThemeOnBundledAndSignedGuest|testHeldPressRendersPressedFillAndRoutesOnRelease|testBoldTextTraitLoanRendersHeavierGlyphs|testSettingsBoldTextRendersHeavierGlyphs)
    requested=disabled ;;
  *) printf 'Unknown UP5 selector: %s\n' "$test_name" >&2; exit 2 ;;
esac
if ! printf '%s\n' "$OWNED_SIMULATOR_UDID" | /usr/bin/grep -Eq '^[[:xdigit:]]{8}(-[[:xdigit:]]{4}){3}-[[:xdigit:]]{12}$'; then
  printf 'An exact owned Simulator UUID is required.\n' >&2
  exit 2
fi
run="$UP5_ROOT_EVIDENCE/$test_name"
mkdir "$run" "$run/tmp"
export TMPDIR="$run/tmp/"
setting_log="$run/contrast-setting.log"
contrast() {
  printf 'xcrun simctl ui %s increase_contrast%s\n' "$OWNED_SIMULATOR_UDID" "${1:+ $1}" >> "$setting_log"
  xcrun simctl ui "$OWNED_SIMULATOR_UDID" increase_contrast "$@" 2>> "$setting_log"
}
read_contrast() {
  value=$(contrast) || return 1
  printf 'observed=%s\n' "$value" >> "$setting_log"
  case "$value" in enabled|disabled) printf '%s\n' "$value" ;; *) return 1 ;; esac
}
previous=$(read_contrast)
restore_contrast() {
  if contrast "$previous" >> "$setting_log" && test "$(read_contrast)" = "$previous"; then
    return 0
  fi
  printf 'Failed to restore Increase Contrast on %s. See %s\n' "$OWNED_SIMULATOR_UDID" "$setting_log" >&2
  return 1
}
trap 'status=$?; restore_contrast || status=1; exit "$status"' EXIT
contrast "$requested" >> "$setting_log"
test "$(read_contrast)" = "$requested"

test_status=0
/usr/bin/xcodebuild test-without-building -xctestrun "$test_run" \
  -destination "platform=iOS Simulator,id=$OWNED_SIMULATOR_UDID" \
  -parallel-testing-enabled NO -test-timeouts-enabled YES -maximum-test-execution-time-allowance 240 \
  -resultBundlePath "$run/$test_name.xcresult" \
  "-only-testing:UP5ThemeUITests/UP5ThemeUITests/$test_name" \
  > "$run/$test_name.log" 2>&1 || test_status=$?

if [ "$test_name" = testHeldPressRendersPressedFillAndRoutesOnRelease ]; then
  container=$(xcrun simctl get_app_container "$OWNED_SIMULATOR_UDID" dev.mixer.fixture.up5theme data)
  capture="$container/Library/Caches/UP5-held-press.png"
  if [ -f "$capture" ]; then
    cp "$capture" "$run/held-window.png"
  elif [ "$test_status" = 0 ]; then
    printf 'Missing native held-window capture.\n' >&2
    test_status=1
  fi
fi
exit "$test_status"
