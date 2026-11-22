# Private Android F05 editor witness

The private development witness uses Mixer
`7fa6b6ea813f73055c38e7d2bf8e607c75c9c384`, the historical 102,293-byte
F05 Wasm, and the ordinary Pair25 V4 renderer. The default launch leaves
the fixture off. The opt-in journey creates a synthetic workspace and
opens the signed new-task editor. It needs an offline, disposable ARM64
API 36 emulator and local development signing.

The four encoded patches retain the exact source used for the witness.
Decode them before applying and compare their SHA-256 values with the
[installed receipt](../../../verification/receipts/fieldlog-f05-android-paced-editor-api36-7fa6b6ea.json).

1. Apply the private Android overlay to the pinned Mixer source projection.
2. Apply the cross-link correction to the original witness package and its
   projected Mixer input. The macOS build uses Xcode 26.6 and SDK 26.5.
3. Apply the platform correction in the projected Mixer input. The private
   verifier still requires the exact editor development scope for the host
   and roots. It applies the macOS platform rule only to macOS development
   scopes.
4. Apply the window-readiness correction to the witness Java source. Build
   the Android owner with Swift 6.3.3 RELEASE and the pinned historical VM
   archive. Bind the rebuilt JNI and generated Java to the development
   packet before sealing it.

The host test uses the actual Swift verifier and the public materials from
the exact synthetic development packet. In a disposable host projection,
select the Android constants in `FieldLogEditorDevelopment.swift` and build
with `MIXER_PRIVATE_FIELDLOG_EDITOR`. Put `F05PlatformTests.swift` in the
updates package test target and set `F05_FIXTURE_PACKET` to the local public
packet. The test checks signed artifact, assignment, offer, and retained
verification, plus refusal of field substitutions in the host and roots.
Native signing keys are unnecessary for that replay.

The installed test made one launch for Cancel and another for Save. Cancel
preserved the workspace bytes and closed the owner. The second process
recovered the candidate and wrote one task and one matching outbox event.
Each character waited for its frame commitment. A separate run sending the
title as a burst lost the editor before Save. Both results are retained.
F06, general Android IME behavior, and iOS remain open.
