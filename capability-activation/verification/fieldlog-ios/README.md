# FieldLog signed OTA on iOS Simulator

The R5 target is FieldLog `dev.mixer.fieldlog` 0.1.0 (1) for arm64 iOS Simulator, with a minimum of iOS 26.0. R5 used Xcode 27.2 (27B52). The app opens its usual workspace when launched without the harness argument. [R5 build receipt](../../../verification/receipts/fieldlog-ios-signed-retirement-41a05264.json)

## Prepare a fresh build

Run from the Mixer checkout on arm64 macOS. Use Python 3.11 or later, Xcode 27.2, Go 1.26, and Rust with the `aarch64-apple-ios-sim` target and `llvm-tools-preview`. Make sure the checkout has Mixer revision `79233ba123a394459b792beac648138808cd0930`. Use a new build directory.

```sh
fieldlog_ota_tools="$PWD/capability-activation/verification/fieldlog-ios"
fieldlog_ota_mixer=79233ba123a394459b792beac648138808cd0930
fieldlog_ota_rev=552559d2d3278abb9b1aa7dcf0288102c09a202b
fieldlog_ota_build="$PWD/verification/local/fieldlog-ios-ota-fresh"
mkdir -p "$PWD/verification/local"
mkdir "$fieldlog_ota_build"
mkdir "$fieldlog_ota_build/logs" "$fieldlog_ota_build/tmp" "$fieldlog_ota_build/service-source"

curl --fail --location "https://codeload.github.com/snowdamiz/fieldlog/tar.gz/$fieldlog_ota_rev" \
  -o "$fieldlog_ota_build/fieldlog.tar.gz"
printf '%s  %s\n' 75d2ce2663ade805ca40831b17a460c248e88c62a7689d5a671182bbf0ed7840 \
  "$fieldlog_ota_build/fieldlog.tar.gz" | shasum -a 256 -c
python3 -B experimental-capability-runtime/build-vm.py \
  --revision "$fieldlog_ota_mixer" --target ios-simulator --output "$fieldlog_ota_build/engine"
git archive "$fieldlog_ota_mixer" services | tar -xf - -C "$fieldlog_ota_build/service-source"
(cd "$fieldlog_ota_build/service-source/services" && \
  go build -mod=readonly -o "$fieldlog_ota_build/mixer-service" ./cmd/mixer-service)
```

### Build and verify a fresh Wasm pair

Install the Swift 6.3.3 Embedded Swift toolchain and Wasm SDK from the compact guest experiment. Run its host probe before preparing an iOS build. The probe checks the ABI, exercises both exact modules against the owned macOS VM, and compares the results with the pinned FieldLog workspace. Keep both Wasm files and the passing `receipt.json` together. [Compact guest setup and checks](../../../compiler/experiments/fieldlog-installed-guest/README.md)

```sh
fieldlog_ota_guest="$PWD/verification/local/fieldlog-ios-guest-fresh"
tar -xOzf "$fieldlog_ota_build/fieldlog.tar.gz" \
  "fieldlog-$fieldlog_ota_rev/Sources/FieldLogModels/Workspace.swift" > "$fieldlog_ota_build/Workspace.swift"
python3 -B compiler/experiments/fieldlog-installed-guest/run.py fieldlog-ios-guest-fresh \
  --workspace "$fieldlog_ota_build/Workspace.swift"

fieldlog_ota_manifest="$fieldlog_ota_guest/receipt.json"
fieldlog_ota_manifest_sha=$(shasum -a 256 "$fieldlog_ota_manifest" | cut -d ' ' -f 1)
python3 -B "$fieldlog_ota_tools/prepare.py" "$fieldlog_ota_build" --fresh-candidate \
  --baseline "$fieldlog_ota_guest/baseline.wasm" --reviewed "$fieldlog_ota_guest/reviewed.wasm" \
  --pair-manifest "$fieldlog_ota_manifest" --pair-manifest-sha256 "$fieldlog_ota_manifest_sha"
```

If you receive a fresh pair from another operator, obtain the digest of their passing host replay receipt with the handoff. A fresh compile can produce different bytes with the same behavior. The signer records fresh provenance, and the build receipt records both payload digests and the source receipt digest.

### Use the original R5 Wasm bytes

Obtain the original `baseline.wasm` and `reviewed.wasm` from the R5 artifact owner. The R5 build's `signed/` directory contains the exact two files for that handoff. Place them in any input directory. Prepare checks each file against the original receipt and its pinned digest and length. [Original compact pair receipt](../../../verification/receipts/fieldlog-compact-abi2-41a05264.json)

```sh
python3 -B "$fieldlog_ota_tools/prepare.py" "$fieldlog_ota_build" \
  --baseline "$FIELDLOG_ORIGINAL_PAIR/baseline.wasm" --reviewed "$FIELDLOG_ORIGINAL_PAIR/reviewed.wasm" \
  --pair-manifest verification/receipts/fieldlog-compact-abi2-41a05264.json \
  --pair-manifest-sha256 c0cf700bfae231ba0145a0b0fcbca156235321873529b7600a86da7023098922
```

Prepare creates a fresh development root in memory and embeds its public key in the app bundle. It signs the chosen Wasm pair for the actual bundle identifier, simulator platform, and linked VM archive. The app and test runner use ad hoc signing.

### Replay delivery on the host

Use a fresh output directory. This exercises publication, rollback, exact offer and payload bytes, and XCTest selection generation.

```sh
python3 -B "$fieldlog_ota_tools/run.py" "$fieldlog_ota_build" "$fieldlog_ota_build/check-service" --check
```

## Root runtime

After the fresh Accessibility and owned-device preflight, root runs the selected test on an already booted, disposable arm64 iOS Simulator. Use the new build above or an explicitly retained, digest-verified R5 build. Root owns the device and runs final acceptance after cleanup.

```sh
python3 -B "$fieldlog_ota_tools/run.py" \
  "$fieldlog_ota_build" "$FIELDLOG_ROOT_EVIDENCE/live" --device "$OWNED_SIMULATOR_UDID"
```

The runtime wrapper opens an isolated loopback service and starts a single, nonparallel `test-without-building` execution from the exact build products. The selector is `FieldLogUITests/FieldLogSignedOTATests/testSignedBaselineReviewRollbackAndOfflineReopen`. The service credential is ephemeral and scoped to the test runner. The app fetches delivery responses without publisher access.

The test publishes baseline (sequence 1), review (2), and rollback (3). Each phase launches the same app against the same private repository. The app downloads through the real service and submits the signed wire data to `CapabilityGuestUIRuntime`. It mounts `MixerGuestScreen`, waits for committed native first-screen health, and interacts through XCTest taps. The final launch omits the delivery endpoint and selects the retained rollback from the app-private store. The test service stays running during that final launch. The app has no delivery URL in that phase.

The signed modules still start each process with an open task in guest memory. The embedding matches the rendered `Inspect pump` task to a fixed fixture in FieldLog’s real `WorkspaceRepository`. It records changes only after observing the matching delivered native event and validated guest frame. A host action explicitly reopens the saved task after relaunch so that the fresh guest and the durable task begin from the same logical state before accepting new guest input. The review frame must leave the workspace revision and outbox count unchanged until confirmation. This covers local task and outbox persistence for the isolated task. Arbitrary FieldLog tasks, guest state hydration and migration, general OTA adoption, sync, physical devices, and release gates are outside this slice.

## Evidence

Keep the result bundle, `xctest.log`, test command, service launch and result records, and exported attachments. Export the workspace ID before device cleanup.

```sh
xcrun xcresulttool get test-results summary --path "$FIELDLOG_ROOT_EVIDENCE/live/signed-ota.xcresult"
xcrun xcresulttool export attachments --path "$FIELDLOG_ROOT_EVIDENCE/live/signed-ota.xcresult" \
  --output-path "$FIELDLOG_ROOT_EVIDENCE/attachments"
```

Use the `workspace-id` attachment to copy only `Library/Application Support/FieldLogSignedOTA-<workspace-id>` from the exact owned app container. Keep the same directory name under `$FIELDLOG_ROOT_EVIDENCE`. Record the JSON from `readback.py BUILD COPIED_DIRECTORY` in `run.json` as `diskEvidence`.

Use the R5 root evidence format for a new run. In `run.json`, record the upper-case device UUID as `owned`, the Accessibility result as `publicAXTrusted`, the XCResult summary as `summary`, and the array of command records as `commands`. Each command record has `args`, `exit`, and the local filename `log`. Record the harness command with absolute script, build, and output paths. Use `python3 -B` for the harness invocation.

Record the raw `xcrun simctl list devices -j` output before creating the device, after observing it in `Shutdown` and before deleting it, and after deletion. The initial and final inventory reads are the first and last command records. Record the initial inventory as `baseline`, keyed by UUID with `[runtime, name, state]` values. Set `ownedRemoved` and `externalExact` from the final inventory. Record a caught error as `failure`.

After cleanup, root uses the verifier's exit status for acceptance.

```sh
python3 -B "$fieldlog_ota_tools/accept_runtime.py" "$fieldlog_ota_build" "$FIELDLOG_ROOT_EVIDENCE"
```

The verifier requires both the harness and XCTest to exit zero, exactly one test and one pass with zero failures or skips, and clean service exit with a closed listener and reusable port. It reads the result bundle to match the offline and reviewed candidate and launch IDs to the copied disk state. Disk readback checks the signed envelopes, payload digests, native health, accepted sequence 3, workspace revision 6, and all seven outbox entries. Cleanup requires the owned device's observed shutdown and deletion and matching external device identities and states. The verifier reads the recorded device evidence. Root performs every device operation.
