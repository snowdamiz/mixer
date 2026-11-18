# Resolve competing offline FieldLog task edits

Run from the Mixer root on macOS with Swift 6, Python 3 and a local FieldLog checkout. The replay saves edits in two independent workspaces while the backend is offline, reconnects to a local SQLite service, and resolves the title conflict while retaining the peer's assignee. It also retries after a lost acknowledgement and checks that a later edit and unrelated outbox events survive.

```sh
mixer=$PWD
fixture="$mixer/tests/integration/fieldlog-task-sync"
run=$(mktemp -d "$mixer/verification/local/fieldlog-task-sync.XXXXXXXX")
mkdir "$run/source"
git -C "$FIELDLOG_CHECKOUT" archive 552559d2d3278abb9b1aa7dcf0288102c09a202b | tar -xf - -C "$run/source"
cd "$run/source"
git init -q
git apply "$fixture/fieldlog-task-conflict.patch"
git apply "$mixer/verification/fieldlog-entry-sync/fieldlog-552559d2-local-backend.patch"
git apply "$fixture/fieldlog-saved-task-sync.patch"
python3 -B verification/host/replay-saved-task-sync.py "$run/replay"
```

This exercises the ordinary editor model, the on-disk repository, and authenticated loopback HTTP with synthetic tokens. Mobile screens and automatic background sync need their own checks.

## Ordinary iOS task editor

On an arm64 Mac with Xcode 27.2, build the FieldLog app, its XCTest runner and the host-side SQLite fixture from the pinned Git objects. Use a Mixer checkout containing its SDK history and set `FIELDLOG_CHECKOUT` to a checkout containing FieldLog revision `552559d2`.

```sh
run=$(mktemp -d "$PWD/verification/local/fieldlog-ios-conflict.XXXXXXXX")
tests/integration/fieldlog-task-sync/ios/prepare.sh "$PWD" "$FIELDLOG_CHECKOUT" "$run/build"
```

The build runs the model replay and checks both app signatures. For the native replay, use a fresh, booted iOS 27 Simulator owned by this test. Complete the repository Accessibility preflight before boot and set `OWNED_SIMULATOR_UDID` to that device. Install the app before running the two XCTest phases.

```sh
xcrun simctl install "$OWNED_SIMULATOR_UDID" "$run/build/ios/Debug-iphonesimulator/FieldLog.app"
python3 -B "$run/build/journey.py" --simulator "$OWNED_SIMULATOR_UDID" --scratch "$run/native"
```

The first phase saves a title through the ordinary task editor while the service is offline. The second submits a competing saved edit from a separate replica, reopens the conflict on iOS and selects the local title with the peer’s assignee. The driver checks the persisted task after relaunch, the earlier outbox rows and the two events in SQLite. Read `native/receipt.json` alongside the two XCTest results. The driver removes its seeded workspace after known closure. The owner handles Simulator shutdown and removal, and preserves the referenced resources if the driver writes `HOLD.json`.
