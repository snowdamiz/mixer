#!/bin/sh
set -eu

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    printf 'Usage: %s XCTESTRUN [controls|healthy-callback]\n' "$0" >&2
    exit 2
fi
: "${OWNED_SIMULATOR_UDID:?supply the already booted, root-owned iOS 26.5 Simulator UUID}"
printf '%s\n' "$OWNED_SIMULATOR_UDID" |
    grep -Eq '^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$'
case "${2:-controls}" in
    controls)
        set -- "$1" testInvalidFirstFrameBoundary \
            testSignedNativeFrameFailureStaleDeliveryAndOfflineRelaunch \
            testSharedThemeRendersInBundledAndSignedGuest \
            testNativeTapBeforeAndAfterDisplayAcknowledgment
        ;;
    healthy-callback)
        set -- "$1" testDelayedHealthyRendererCallbackAcrossOwnerReplacement
        ;;
    *)
        printf 'Expected controls or healthy-callback\n' >&2
        exit 2
        ;;
esac

fixture=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
repo=$(CDPATH= cd -- "$fixture/../../.." && pwd -P)
products=$(CDPATH= cd -- "$(dirname -- "$1")" && pwd -P)
plan="$products/$(basename -- "$1")"
build=$(dirname "$(dirname "$(dirname "$products")")")
case "$build" in
    "$repo"/verification/local/s4-ios-native-replay.*) ;;
    *)
        printf 'Expected the test plan produced by build.sh in this worktree\n' >&2
        exit 2
        ;;
esac
test "$products" = "$build/derived-data/Build/Products"
test -f "$plan"
shift
run=$(mktemp -d "$build/tests.XXXXXX")
mkdir "$run/tmp"
export TMPDIR="$run/tmp/"
printf 'S4 test directory: %s\n' "$run"
printf '%s\n' "$OWNED_SIMULATOR_UDID" > "$run/device-uuid.txt"

status=0
for test_name do
    budget=300
    case "$test_name" in
        testInvalidFirstFrameBoundary|testSharedThemeRendersInBundledAndSignedGuest) budget=120 ;;
    esac
    result="$run/$test_name.xcresult"
    /usr/bin/xcodebuild test-without-building -xctestrun "$plan" \
        -destination "platform=iOS Simulator,id=$OWNED_SIMULATOR_UDID" -destination-timeout 30 \
        -resultBundlePath "$result" -parallel-testing-enabled NO -test-timeouts-enabled YES \
        -maximum-test-execution-time-allowance "$budget" \
        "-only-testing:S4NativeUITests/S4NativeUITests/$test_name" \
        > "$run/$test_name.log" 2>&1 || status=$?
    xcrun xcresulttool get test-results summary --path "$result" > "$run/$test_name.json"
    xcrun xcresulttool export attachments --path "$result" \
        --output-path "$run/$test_name-attachments" > "$run/$test_name-attachments.log"
done
exit "$status"
