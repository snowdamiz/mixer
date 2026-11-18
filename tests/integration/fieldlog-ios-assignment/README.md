# Open a saved FieldLog task from an iOS notification

The ordinary Debug app can post a local assignment for a task with a responsible person. This XCTest creates a project and assigned task, grants notification permission, taps the SpringBoard notification, checks the task title and open status, and returns to the checklist. The app uses the local workspace and Apple's notification center.

## Prepare the app

Run from the Mixer repository root on macOS with Xcode. Set `FIELDLOG_CHECKOUT` to a FieldLog checkout containing the revision below. The commands create a private copy of each source tree and resolve the SDK locally.

```sh
fixture="$PWD/tests/integration/fieldlog-ios-assignment"
run=$(mktemp -d "$PWD/verification/local/fieldlog-assignment.XXXXXXXX")
mkdir "$run/fieldlog" "$run/mixer"
git -C "$FIELDLOG_CHECKOUT" archive 552559d2d3278abb9b1aa7dcf0288102c09a202b Package.swift Sources Tests ios | tar -xf - -C "$run/fieldlog"
git archive 56ff14c925168284761c5aca4f0bd4129cf3c995 Package.swift sdk/Sources sdk/Tests | tar -xf - -C "$run/mixer"
cd "$run/fieldlog"
git init -q
git apply "$fixture/fieldlog-ios-assignment.patch"
cat "$fixture/AssignmentUITest.swift" >> ios/FieldLogUITests/FieldLogUITests.swift
sed -i '' 's|.package(url: "https://github.com/snowdamiz/mixer.git", revision: "56ff14c925168284761c5aca4f0bd4129cf3c995")|.package(path: "../mixer")|' Package.swift
rm ios/FieldLog.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved
```

## Exercise the notification

Use a fresh owned Simulator with notifications at their default permission state. Set `FIELDLOG_SIMULATOR_UDID` to that device's UUID. Start with the workspace empty.

```sh
xcodebuild test -project ios/FieldLog.xcodeproj -scheme FieldLog -configuration Debug \
  -destination "platform=iOS Simulator,id=$FIELDLOG_SIMULATOR_UDID" \
  -derivedDataPath "$run/derived" -resultBundlePath "$run/result.xcresult" \
  -disableAutomaticPackageResolution -skipPackageUpdates -parallel-testing-enabled NO \
  -only-testing:FieldLogUITests/FieldLogUITests/testAssignmentNotificationOpensOrdinaryTask
```

The expected workspace contains one project, one open task assigned to Rae, and the two outbox events created when saving them. Remote push delivery requires separate verification.
