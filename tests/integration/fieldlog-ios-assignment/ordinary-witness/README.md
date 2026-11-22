# FieldLog ordinary iOS workspace acceptance witness

Source reconstruction follows the current-owner assignment replay recorded in
`fieldlog-ios-assignment-recovery-73e9f093.json` at public Mixer
`d203a1c27027e2ae10bc46deb911cc94b8c28cbb`. The FieldLog tree must resolve to
`73e9f093470ef9173a8e6a21da56f8537622212f`. The local SDK checkout is stock
Pair25 at `857e4b4aa7a32cda368257b2be1a63e77106bed8`.

The one XCTest creates and then opens the saved **Pump station witness** project.
It saves an unfinished **Pressure reading** draft, reopens it, edits its note and
selects the sole synthetic image using **Choose photo**. It uses **Done** to keep
the draft. It then sets the manual pin to **37.42, −122.08** in **Site map** and
changes **Settings → Appearance** from **System** to **Dark**. After terminating
the process, it checks that the saved project restored, the pin and appearance
can be read through their ordinary controls, and the draft has the expected title,
note and one photo.

The pre- and post-termination checkpoints run from the ordinary **On device**
tab. The test requires one offline project-created outbox event bound to the
correct project and matches the draft's attachment UUID to a decodable on-disk
JPEG. The Debug observer compares the disk snapshot to the workspace opened by
the app. The test attaches and compares SHA-256 digests of the exact workspace,
JPEG and Settings files before reopening the draft on the cold app. The observer
requires both the existing isolated workspace argument and this witness's
readback argument. It performs only reads. Settings use their normal on-disk
path, so run on a fresh disposable app install. Apple camera capture and location
permission, assignment notifications, and signed OTA refusal have separate
acceptance. This path uses the library and a manual pin.

## Rebuild and verify on the host

From the Mixer repository root, use Xcode 27.2, Rust 1.99.0 with the
`aarch64-apple-ios-sim` target, and local Git stores for the pinned Swift Crypto
and Swift ASN.1 dependencies. Set `SWIFT_CRYPTO_GIT_STORE` and
`SWIFT_ASN1_GIT_STORE` when the default SwiftPM cache paths in `build.sh` differ.
Set `FIELDLOG_RUST_BIN` if needed. Preparation fetches the exact public FieldLog
base and uses Mixer Git objects already available locally. Only the two test
sources and the stock resolution lock are overlaid in the disposable build copy.

```bash
fixture="$PWD/tests/integration/fieldlog-ios-assignment/ordinary-witness"
mkdir -p verification/local
run=$(mktemp -d "$PWD/verification/local/ordinary-ios-witness.XXXXXXXX")
"$fixture/prepare.sh" "$PWD" "$run"
"$fixture/build.sh" "$run"
products="$run/derived/Build/Products"
python3 -B "$fixture/verify-build.py" "$products"
python3 -B "$fixture/make-photo.py" "$run/fieldlog-witness.png"
```

## Run on a root-owned Simulator after separate admission

Use a fresh, dedicated English iPhone Simulator with an empty Photo Library,
and perform the project's Accessibility preflight before boot. Import exactly
`fieldlog-witness.png` once into that device's library using its exact owned UUID.
Start with a fresh app install so Settings report **System**. The test selects
one English Photo Library asset and fails if more than one matching selectable
asset is visible. Preserve the plan beside the **Debug-iphonesimulator**
directory when transferring the build.

```bash
xcodebuild test-without-building \
  -xctestrun "$products/FieldLog_iphonesimulator27.2-arm64.xctestrun" \
  -destination "platform=iOS Simulator,id=$FIELDLOG_SIMULATOR_UDID" \
  -parallel-testing-enabled NO \
  -only-testing:FieldLogUITests/FieldLogUITests/testOrdinarySavedDraftPinAndSettingsSurviveColdLaunch \
  -resultBundlePath "$run/ordinary-fieldlog.xcresult"
```

Accept the witness only if the named test passes and the result has the equal
warm and cold digest attachment. Retire only the owned test instance after
collection. This handoff contains host build evidence. Runtime confirmation
depends on the installed app, including the system photo picker and SwiftUI
accessibility values.
