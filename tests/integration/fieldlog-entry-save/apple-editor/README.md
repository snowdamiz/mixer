# FieldLog signed entry Commit and editor dismissal

The baseline is FieldLog `874cc93a4dd5ee5533c66539bde944e7f0396615` with
tree `12986b06d22c8480cf0406c36698ae3ccb6c624f`. Apply
`fieldlog-apple-editor-dismissal.patch` to get tree
`515684732fb55e9e48e15e55651f7931fd72b8e6`. Mixer
`d6ce0ccd0f7275e568f11e95eac1ecd0ef346413` is the parent of this fixture
change. Build the runtime from Mixer
`9c356cc25aa94b046bae01c6255bdf14de8bf4ab` with tree
`d1487ee854b58069855a8fa4cbb21a5721d3a822`.

## Reconstruct the FieldLog baseline

In a fresh workspace, check out FieldLog
`552559d2d3278abb9b1aa7dcf0288102c09a202b` in `fieldlog/`. Set
`MIXER` to a Mixer checkout and use the following paths from the
fixture revision. Apply these patches with `git -C fieldlog apply --index`
in order.

1. `tests/integration/fieldlog-saved-draft/android/audited-patches/rollback-floor.patch`
2. `tests/integration/fieldlog-saved-draft/android/audited-patches/optional-successor.patch`
3. `tests/integration/fieldlog-saved-draft/android/android-app-composition.patch`
4. `tests/integration/fieldlog-entry-save/entry-save-decision.patch`

Copy `$MIXER/tests/integration/fieldlog-entry-save/EntrySaveDecision.swift`
to `fieldlog/Integrations/GeneratedReport/Sources/FieldLogFeatures/`
and add it to the FieldLog index. Continue applying the patches.

5. `tests/integration/fieldlog-entry-save/android-editor/fieldlog-editor.patch`
   yields tree `e518fa0702a90ee5bd9e9f067de9fd9b0f09cc64`.
6. `tests/integration/fieldlog-entry-save/apple-editor/fieldlog-apple-editor.patch`
   yields tree `1534ac8af1bda5a76a81a7fc3c70cef26ae5e606`.
7. `tests/integration/fieldlog-entry-save/apple-editor/fieldlog-apple-editor-correction.patch`
   yields baseline tree `12986b06d22c8480cf0406c36698ae3ccb6c624f`.

Use `git -C fieldlog write-tree` to verify the exact baseline. Export it
with `git checkout-index --prefix=/absolute/path/to/baseline-files/ -a`.
Apply the dismissal patch in `fieldlog/` and verify the candidate tree.

## Run the macOS controls

Use Xcode 27.2 (27B52), Rust 1.99.0 and Embedded Swift 6.3.3. The compact
receipt includes argv, outputs, tool versions, source and artifact hashes,
and observations of process termination.
[Dismissal receipt](../../../../verification/receipts/fieldlog-ios-editor-dismissal-20261121.json)

1. Export `sdk`, `updates`, `runtime-identity`, `capability-activation`,
   `experimental-capability-runtime` and `vm` from the runtime revision into
   `mixer/` alongside `fieldlog/`. Place `swift-crypto` at
   `c2cbadd7263439d8015189668f96ff5b5be565ce` and `swift-asn1` at
   `3b6410f7dee09eb33cdd26260c5fd47fda19b0e2` alongside `mixer/`.
   Point the SDK and updates manifests at
   `.package(path: "../../swift-crypto")` and set `SWIFTCI_USE_LOCAL_DEPS=1`.
2. Copy `mixer/vm/include/mixer_vm*.h` to
   `mixer/experimental-capability-runtime/Sources/CMixerVMCapability/include/`.
   Run `cargo build --offline --locked --release --features experimental-capability-native --lib`
   in `mixer/vm`. Link the archive as `libmixer_vm_capability_experimental.a`
   under a fresh library directory.
3. Put the `fieldlog-entry-save` and `fieldlog-saved-draft/guest` inputs
   in their repository-relative locations.
   Use the pinned runtime revision for `fieldlog-saved-draft/guest`. Set
   `FIELDLOG_SWIFT_BIN` to the Embedded Swift toolchain's `usr/bin`.
   Run `build-guests.sh` with a fresh output directory.
4. Copy `ReplayPackage.swift` to `host-package/Package.swift`. Link
   `Replay.swift`, `Sign.swift`, and `main.swift` into
   `host-package/Sources/Replay/`, plus
   `Integrations/InstalledGuest/FieldLogDraftStorage.swift` from FieldLog.
   Link the baseline copies of `WorkspaceModel.swift`,
   `SelectedDraftGuestBinding.swift`, and `InstalledDraftGuest.swift`.
   Build using `swift build --package-path host-package -Xswiftc -enable-testing`
   with `-Xswiftc -DFIELDLOG_DISMISSAL_BASELINE` and
   `-Xlinker -L/absolute/path/to/lib`. Copy the resulting `Replay` executable
   to `Replay-baseline`. Switch the three source links to the candidate in
   `fieldlog/ios/FieldLog/`. Build again without the baseline define.
5. Sign once and use those same files in both replays. Create empty outputs
   named `InstalledEntryCommit`, `InstalledDraft`, `authorityReplay`, and
   `authorityNoPoll`. Use the template directory
   `mixer/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures/`.
   Hash the macOS VM archive for `ENGINE_SHA256`. The receipt contains the
   verified `SOURCE_SHA256` and `LINK_SHA256` roster digests. Extract
   `.toolchain.hostSigningMetadata` from the
   [author receipt](../../../../verification/receipts/fieldlog-ios-ordinary-entry-commit-20261121.json)
   for `METADATA_JSON`.

   ```sh
   Replay-baseline sign FIXTURES GUESTS/entry-commit.wasm InstalledEntryCommit ENGINE_SHA256 SOURCE_SHA256 LINK_SHA256 METADATA_JSON
   Replay-baseline sign-tools FIXTURES GUESTS InstalledDraft ENGINE_SHA256 SOURCE_SHA256 LINK_SHA256 METADATA_JSON
   Replay-baseline sign-authority FIXTURES GUESTS/entry-commit-multiple.wasm authorityReplay ENGINE_SHA256 SOURCE_SHA256 LINK_SHA256 METADATA_JSON
   Replay-baseline sign-authority FIXTURES GUESTS/entry-commit-unconsumed.wasm authorityNoPoll ENGINE_SHA256 SOURCE_SHA256 LINK_SHA256 METADATA_JSON
   ```

6. Use a fresh repository path for every invocation. Run the baseline cases
   individually because a failed assertion exits the command.

   ```sh
   Replay-baseline run InstalledEntryCommit FRESH_ROOT legacyRetry
   Replay-baseline run InstalledEntryCommit FRESH_ROOT legacyOptionalConflict
   Replay-baseline run InstalledEntryCommit FRESH_ROOT bothProvisioned InstalledDraft
   Replay run InstalledEntryCommit FRESH_ROOT all InstalledDraft
   Replay run authorityReplay FRESH_ROOT authorityReplay
   Replay run authorityNoPoll FRESH_ROOT authorityNoPoll
   ```

The baseline host control runs the same model calls as the pinned SwiftUI
callbacks. The candidate host control calls the production dismissal method
and invokes the ordinary editor's production binding setter. It checks the
snapshot after the signed guest retires, then after the outer callback and a
cold repository reopen. The baseline writes a second revision on a matching
retry and reports success for a changed follow-up. The candidate dismisses a
matching retry while preserving every workspace byte. A conflicting replay
leaves the editor selected. A new commit preserves the edited title and note
and the tool's follow-up value, removes the draft, and adds one entry and one
outbox event. The cancellation controls hold the repository write across Done
and exercise selection changes both before and after guest retirement.

## Compile the ordinary Apple app

Build the pinned VM with the same Cargo options plus
`--target aarch64-apple-ios`. Name the resulting archive
`libmixer_vm_capability_experimental.a`. In a fresh copy of the candidate,
remove its two remote package locks and expose the same local dependencies.
Build `ios/FieldLog.xcodeproj`, scheme `FieldLog`, with `-sdk iphoneos`,
`-destination 'generic/platform=iOS'`, `ARCHS=arm64`,
`CODE_SIGNING_ALLOWED=NO`, a fresh DerivedData path, and
`LIBRARY_SEARCH_PATHS` pointing to the iPhoneOS archive. The compile covers
both SwiftUI sheets. The macOS replays exercise the signed guest and disk
repository. Installed UI and device behavior remain outside this receipt.
