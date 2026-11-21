# Replay signed Commit in the FieldLog Apple editor

Use an arm64 Mac with Xcode 27.2 (27B52), Rust 1.99.0, and Embedded Swift
6.3.3. Set `MIXER` to the checkout containing this guide and `WORK` to a fresh
workspace. Use the same Mixer revision for the runtime, bridge, SDK, and
replay sources.

## Reconstruct FieldLog

Check out FieldLog `552559d2d3278abb9b1aa7dcf0288102c09a202b` in
`$WORK/fieldlog`. Verify its tree is `1b62520f35c7e57a01b568291078686574f627c4`.
Apply the first four patches with `git -C "$WORK/fieldlog" apply --index` in
this order. The paths are relative to the Mixer checkout.

1. `tests/integration/fieldlog-saved-draft/android/audited-patches/rollback-floor.patch`
2. `tests/integration/fieldlog-saved-draft/android/audited-patches/optional-successor.patch`
3. `tests/integration/fieldlog-saved-draft/android/android-app-composition.patch`
4. `tests/integration/fieldlog-entry-save/entry-save-decision.patch`

Copy `tests/integration/fieldlog-entry-save/EntrySaveDecision.swift` into
FieldLog's `Integrations/GeneratedReport/Sources/FieldLogFeatures/` and add it
to the FieldLog index. Apply the next three patches with the same command.
Check each result with `git -C "$WORK/fieldlog" write-tree`.

1. `tests/integration/fieldlog-entry-save/android-editor/fieldlog-editor.patch`
   yields `e518fa0702a90ee5bd9e9f067de9fd9b0f09cc64`.
2. [`fieldlog-apple-editor.patch`](fieldlog-apple-editor.patch) yields
   `1534ac8af1bda5a76a81a7fc3c70cef26ae5e606`.
3. [`fieldlog-apple-editor-correction.patch`](fieldlog-apple-editor-correction.patch)
   yields the baseline tree `12986b06d22c8480cf0406c36698ae3ccb6c624f`.

Create `$WORK/baseline/` and export the baseline with
`git -C "$WORK/fieldlog" checkout-index --prefix="$WORK/baseline/" -a`.
Apply [`fieldlog-apple-editor-dismissal.patch`](fieldlog-apple-editor-dismissal.patch)
in FieldLog. Verify the candidate tree is
`515684732fb55e9e48e15e55651f7931fd72b8e6`.

## Build the replay

1. Export the Mixer packages beside FieldLog.

   ```sh
   revision=$(git -C "$MIXER" rev-parse HEAD)
   mkdir "$WORK/mixer" "$WORK/lib"
   git -C "$MIXER" archive "$revision" sdk updates runtime-identity \
     capability-activation experimental-capability-runtime vm |
     tar -xf - -C "$WORK/mixer"
   ```

2. Place swift-crypto `c2cbadd7263439d8015189668f96ff5b5be565ce` and
   swift-asn1 `3b6410f7dee09eb33cdd26260c5fd47fda19b0e2` in
   `$WORK/swift-crypto` and `$WORK/swift-asn1`. In the exported SDK and
   updates manifests, change the swift-crypto dependency to
   `.package(path: "../../swift-crypto")`. Set `SWIFTCI_USE_LOCAL_DEPS=1`.

3. Build the VM and link its archive under the bridge's expected name.

   ```sh
   cargo build --manifest-path "$WORK/mixer/vm/Cargo.toml" --offline --locked \
     --release --features experimental-capability-native --lib --target-dir "$WORK/cargo-host"
   ln -s "$WORK/cargo-host/release/libmixer_vm.a" "$WORK/lib/libmixer_vm_capability_experimental.a"
   ```

4. Set `FIELDLOG_SWIFT_BIN` to the Embedded Swift toolchain's `usr/bin`.
   Run `build-guests.sh` from the replay directory with `$WORK/guests` as
   its fresh output directory. The guest inputs are in the same Mixer checkout.

5. Copy `ReplayPackage.swift` to `$WORK/host-package/Package.swift`.
   Link `Replay.swift`, `Sign.swift`, and `main.swift` into
   `$WORK/host-package/Sources/Replay/`. Link `FieldLogDraftStorage.swift` from
   `$WORK/fieldlog/Integrations/InstalledGuest/`. Link `WorkspaceModel.swift`,
   `SelectedDraftGuestBinding.swift`, and `InstalledDraftGuest.swift` from
   `$WORK/baseline/ios/FieldLog/` into the same target.

6. Run the following build with `-Xswiftc -DFIELDLOG_DISMISSAL_BASELINE`.
   Copy the resulting `$WORK/swift-host/debug/Replay` to `$WORK/Replay-baseline`.
   Switch the three baseline source links to `$WORK/fieldlog/ios/FieldLog/`
   and run the build without that define.

   ```sh
   swift build --package-path "$WORK/host-package" --scratch-path "$WORK/swift-host" \
     -Xswiftc -enable-testing -Xcc "-I$WORK/mixer/vm/include" -Xlinker "-L$WORK/lib"
   ```

## Sign and run the controls

Compute the VM and linked source digests in the same shell. Use the file
rosters from Git so the digest covers the intended inputs even when the
exported packages use local dependency paths.

```sh
fieldlog="$WORK/fieldlog"
fieldlog_tree=$(git -C "$fieldlog" write-tree)
engine=$(shasum -a 256 "$WORK/lib/libmixer_vm_capability_experimental.a" | cut -d ' ' -f 1)
source=$(git -C "$MIXER" ls-tree -r "$revision" vm | shasum -a 256 | cut -d ' ' -f 1)
link=$(
  {
    git -C "$fieldlog" ls-tree -r "$fieldlog_tree" Package.swift Sources ios \
      Integrations/InstalledGuest Integrations/GeneratedReport/Sources/FieldLogFeatures
    git -C "$MIXER" ls-tree -r "$revision" sdk updates runtime-identity \
      capability-activation experimental-capability-runtime vm
  } | shasum -a 256 | cut -d ' ' -f 1
)
```

Use the same freshly signed material for both host executables. The signer uses
an ephemeral fixture key and the [host fixture metadata](host-signing-metadata.json).
Run these commands in Bash.

```bash
baseline="$WORK/Replay-baseline"
candidate="$WORK/swift-host/debug/Replay"
spec="$WORK/mixer/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures"
metadata="$MIXER/tests/integration/fieldlog-entry-save/apple-editor/host-signing-metadata.json"
sign_args=("$engine" "$source" "$link" "$revision" "$metadata")
commit="$WORK/material/InstalledEntryCommit"
tools="$WORK/material/InstalledDraft"
multiple="$WORK/material/authorityReplay"
no_poll="$WORK/material/authorityNoPoll"

mkdir -p "$commit" "$tools" "$multiple" "$no_poll"
"$baseline" sign "$spec" "$WORK/guests/entry-commit.wasm" "$commit" "${sign_args[@]}"
"$baseline" sign-tools "$spec" "$WORK/guests" "$tools" "${sign_args[@]}"
"$baseline" sign-authority "$spec" "$WORK/guests/entry-commit-multiple.wasm" "$multiple" "${sign_args[@]}"
"$baseline" sign-authority "$spec" "$WORK/guests/entry-commit-unconsumed.wasm" "$no_poll" "${sign_args[@]}"

"$candidate" run "$commit" "$WORK/candidate-all" all "$tools"
"$candidate" run "$multiple" "$WORK/candidate-multiple" authorityReplay
"$candidate" run "$no_poll" "$WORK/candidate-no-poll" authorityNoPoll
```

Run the baseline cases separately against fresh disk roots. The matching
`legacyRetry` and `legacyExplicitRetry` cases should fail on an extra
dismissal write. The changed `legacyOptionalConflict` and
`legacyBooleanConflict` cases should fail when the baseline presents success.

```sh
"$baseline" run "$commit" "$WORK/baseline-legacyRetry" legacyRetry "$tools"
"$baseline" run "$commit" "$WORK/baseline-legacyExplicitRetry" legacyExplicitRetry "$tools"
"$baseline" run "$commit" "$WORK/baseline-legacyOptionalConflict" legacyOptionalConflict "$tools"
"$baseline" run "$commit" "$WORK/baseline-legacyBooleanConflict" legacyBooleanConflict "$tools"
```

The candidate host replay calls the production dismissal method and the
ordinary editor's binding setter. A matching legacy retry leaves the workspace
bytes unchanged. A changed follow-up leaves the editor selected. A new Commit
adds one entry and one outbox event. The cancellation cases cover a held write
and selection changes before and after guest retirement. The checks use the
signed guest and a disk repository on macOS.

## Compile the generic iPhoneOS target

Build the same VM with `SDKROOT=$(xcrun --sdk iphoneos --show-sdk-path)`,
`IPHONEOS_DEPLOYMENT_TARGET=26.0`, and `--target aarch64-apple-ios`. Link its
archive as `libmixer_vm_capability_experimental.a` in `$WORK/ios-lib`.

Copy the candidate to `$WORK/ios-src/fieldlog` without its two
`Package.resolved` files. Link the exported `mixer`, `swift-crypto`, and
`swift-asn1` directories alongside it. Build the same source with signing
disabled.

```sh
xcodebuild -project "$WORK/ios-src/fieldlog/ios/FieldLog.xcodeproj" -scheme FieldLog \
  -configuration Debug -sdk iphoneos -destination 'generic/platform=iOS' \
  -derivedDataPath "$WORK/ios-derived" -clonedSourcePackagesDirPath "$WORK/ios-packages" \
  -disableAutomaticPackageResolution -skipPackageUpdates -disablePackageRepositoryCache \
  'CODE_SIGNING_ALLOWED=NO' 'ARCHS=arm64' 'ONLY_ACTIVE_ARCH=NO' 'ENABLE_DEBUG_DYLIB=NO' \
  "HEADER_SEARCH_PATHS=\$(inherited) $WORK/mixer/vm/include" \
  "LIBRARY_SEARCH_PATHS=$WORK/ios-lib" build
```

The generic build compiles both SwiftUI sheets. The replay exercises the
ordinary editor callbacks through their model and binding. Installed UI
execution requires its own evidence.

For the tested source trees, commands, and observed results, see the
[v80 composition receipt](../../../../verification/receipts/fieldlog-v80-signed-commit-59144ad9.json).
