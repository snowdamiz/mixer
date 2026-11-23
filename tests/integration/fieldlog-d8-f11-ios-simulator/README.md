# F11 signed iOS Simulator note witness

The disposable export uses Stage `2843fdb54c` and enables the historical note
profile only for arm64 iOS Simulator with `MIXER_F11_IOS_FIXTURE`. The macOS
private constructor keeps its original gate. The arm64 device SDK rejects
the note constructor even when passed the Simulator define.

The witness stages the historical Wasm with short-lived development trust and
a 50 ms VM turn. A UIKit Paste control appends `Edited` in one edit. The
shipped UIKit display probe must acknowledge revision 2 before Save or Commit.
Save reopens the Pair25 repository under the live owner. Commit writes one
linked `entrySaved`. A separate app process checks the committed entry and
workspace hash.

[Build and exclusion controls](../../../verification/receipts/l08-d8-f11-ios-simulator-2843.json)

## Rebuild

Use fresh scratch under `verification/local/`. Create the `$work/export`
directory. The pinned Stage must have the retained F11 seed recipe. Supply a
FieldLog Git object store with Pair25 base `552559d2d3` and F11 anchor
`c6562ba80b`. Use the preinstalled SwiftPM caches and Rust Simulator target.

```sh
python3 -B "$fixture/prepare.py" "$stage" "$fieldlog_git" "$work/export"
python3 -B "$fixture/overlay.py" "$work/export/source"
IPHONEOS_DEPLOYMENT_TARGET=26.0 CARGO_INCREMENTAL=0 CARGO_PROFILE_RELEASE_DEBUG=0 \
  cargo +1.99.0-aarch64-apple-darwin build --offline --locked --release --lib \
  --target aarch64-apple-ios-sim --features experimental-capability-native \
  --manifest-path "$work/export/source/vm/Cargo.toml" --target-dir "$work/rust"
python3 -B "$fixture/issue.py" "$work" \
  "$work/export/source/capability-activation/verification/f11-native/Witness/SealedInput" \
  /opt/homebrew/opt/openssl@3/bin/openssl
python3 -B "$fixture/build.py" "$work" --seconds 120
python3 -B "$fixture/controls.py" "$work"
python3 -B "$fixture/package-kit.py" "$work" "$kit"
```

The kit includes the relative-path `.xctestrun` and a SHA-256 member manifest.
The root-owned selector is
`F11NativeWitnessUITests/F11WitnessUITests/testPasteSaveAndCommitRestoredNote`.
The development packet expires two hours after issue. Reissue and rebuild in
fresh scratch to renew. The issuer discards the ephemeral private key.
