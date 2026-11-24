# S5 signed Compose editor

This development fixture combines the pinned API 28 HWUI and Android IME host with the installed release, assignment, recovery, VM, and app-private storage owners. The fixture uses the existing V2 document, event, and native-header codecs. Its identity is `mixer-local/s5/signed-compose-v2/development/android` and its bundle is `dev.mixer.compose.s5.signed.v2`. The two version-2 dependencies distinguish this wire from the legacy V1 wire. The existing V2 document retains its schema-1 envelope.

The build projects the fixture overlay into a disposable checkout and defines `MIXER_S5_SIGNED_COMPOSE` there. The legacy installation entry points retain their original checks. A one-use development key signs the releases and assignments on the build host. The APK embeds the corresponding trust root and signed material. The disposable release trust root expires after 24 hours. The Android app runs offline.

Swift releases the exact prepared snapshot and records the presentation receipt after the matching Compose window-buffer acknowledgment. Each Save admits one title event followed by one activation. The signed guest checks the sequence and current guest revision, writes the title via `storage.keyValue.v1`, and publishes its next revision after storage completes.

Version 1 cancellation retires the exact pending presentation claim. On a healthy owner, the drawn frame keeps its native input authority and the committed write stays in storage. The exchange routes input against that drawn frame first, checks the same node generation and enabled binding against the latest canceled guest snapshot, and encodes the event at the guest's current revision. First-frame cancellation enters recovery without earning health. The rollback first refuses an altered Ed25519 signature, then installs the original artifact under assignment sequence 3.

## Build and replay on macOS

Run these from the Mixer checkout. Use fresh ignored work directories and point `s5_prior` at the approved S5 OS IME delivery. The build uses Xcode 26.6, Swift 6.3.3, the API 28 Swift Android SDK, Rust 1.99.0, NDK r27d, JDK 25, and Gradle 9.8.1. The two Swift dependency revisions are read from the local SwiftPM repository cache and pinned in `link.py`.

```sh
s5_fixture=capability-activation/verification/s5-signed-compose
python3 -B "$s5_fixture/link.py" verification/local/s5-host
python3 -B "$s5_fixture/link.py" verification/local/s5-android --mode android
python3 -B "$s5_fixture/apk.py" verification/local/s5-apks verification/local/s5-android \
  verification/local/s5-host/swift-build/debug/SignFixture "$s5_prior"
```

The macOS executable loads signed WASM through the installed runtime with a synthetic presentation acknowledgment. It checks first-frame failure and exact committed bytes after a canceled draw. It then checks two successive cancellations from the same accepted frame, three accepted saves, and signed rollback. To verify the Android payload on the host, extract `assets/s5-signed` from the final app APK. Pass that directory and a fresh private state directory to `Replay`. The Android build links the signed capability stack for API 28 and builds two APKs from the pinned Compose project. The signed output includes the replay script and API 28 signature checks.

## Root Android replay

Install both APKs on the same isolated, ARM64 API 28 AVD with HWUI. The root-owned wrapper must use the supplied `replay-os-ime.sh` because the signed V2 fixture uses its own package and IME authority. The script verifies the exact AVD and private ADB port and restores the original IME settings. Use a fresh app install so assignment sequence 1 begins with an empty recovery store.

Instrumentation holds the candidate’s exact HWUI receipt, verifies the provisional state and rendered pixels, vetoes the next traversal, and promotes that receipt. It cancels a first post-Save proposal after an offscreen marker and Android pre-draw veto, then cancels a second post-Save proposal after its matching window-buffer receipt. In both cases the Android-managed IME retains composition and selection through the accepted binding. Accessibility Save then drives 15 Unicode readbacks with exact window-marker and glyph comparisons. The replay also checks signature refusal, rollback, input through the retired OS connection, stale receipt and input refusal on detach, and byte-for-byte storage readback. Require the instrumentation pass marker, result code `-1`, restored settings, and root’s terminal device cleanup.
