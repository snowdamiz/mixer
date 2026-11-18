# Resume a FieldLog photo from the On device queue

The opt-in FieldLogLocalSync configuration shows confirmed JPEG bytes in the ordinary SwiftUI queue. **Cancel send** leaves the selected event queued. **Resume send** checks the backend's saved prefix before sending the remaining bytes. A late duplicate chunk must return its original receipt and leave SQLite unchanged.

## Run the local tests

Use a macOS host with Xcode, Python 3.12 or later, Git, and a FieldLog checkout containing commit `552559d2d3278abb9b1aa7dcf0288102c09a202b`. The replay reads the committed patch and SDK revisions listed in [the input manifest](input-manifest.json) from the current Mixer repository. Run from the Mixer repository root. Each command takes a new scratch directory.

```sh
mkdir -p verification/local
fixture="$PWD/tests/integration/fieldlog-ios-queue"
run=$(mktemp -d "$PWD/verification/local/fieldlog-queue.XXXXXXXX")
"$fixture/replay.sh" host "$PWD" "$FIELDLOG_CHECKOUT" "$run/host"
"$fixture/replay.sh" public "$PWD" "$FIELDLOG_CHECKOUT" "$run/http"
"$fixture/replay.sh" prepare-native "$PWD" "$FIELDLOG_CHECKOUT" "$run/prepared"
```

The host replay invokes the SwiftUI row actions and reads the real loopback backend's SQLite database. It checks both a chunk already committed when the user cancels and one that commits after the user resumes. The public HTTP replay also checks duplicate chunks after finalization. Prepare-native builds the app and XCTest bundle with the pinned SDK.

## Run the iOS test

Use a booted, owned Simulator with a clean FieldLog container and a compatible runtime. The inspection command resolves the XCTest selector and paths without launching the app.

```sh
python3 -B "$fixture/journey.py" "$run/prepared" --inspect-native
xcrun simctl install "$OWNED_SIMULATOR_UDID" "$run/prepared/derived/Build/Products/FieldLogLocalSync-iphonesimulator/FieldLog.app"
python3 -B "$fixture/journey.py" "$run/prepared" --simulator "$OWNED_SIMULATOR_UDID"
```

The native test seeds its workspace, runs the Cancel and Resume actions on the selected queue row, then compares the outbox, entry and JPEG bytes. The recorded host run covers both cancellation timings. On iOS 27.0 Simulator the test passed with one matching JPEG on the server and seven unrelated events preserved on disk. XCTest can move the app data container during installation. The driver resolves its new path and verifies the run marker before reading the saved workspace. [Host receipt](../../../verification/receipts/fieldlog-ios-current-resume-41a05264.json) · [Simulator receipt](../../../verification/receipts/fieldlog-ios-queue-native-41a05264.json)
