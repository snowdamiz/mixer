# FieldLog D2 signed checklist on macOS

Run the replay from the Mixer worktree on an arm64 Mac with Xcode 26.6, the Swift 6.3.3 Embedded Wasm toolchain, Rust 1.99.0, and the pinned Swift Crypto and Swift ASN.1 objects in the local SwiftPM cache.

```sh
python3 -B tests/integration/fieldlog-d2-signed-owner/replay.py \
  --stage "$pinned_mixer_checkout" --assembly "$composite_delivery/stage.sh" \
  --receipt verification/local/fieldlog-d2-host-new-run.json
```

Use the retained composite delivery's `stage.sh` and the original D2 composition,
iOS route, and task-editor patch deliveries. The replay verifies the assembly
script digest before invoking it. The script verifies the patch digests and
reconstructs FieldLog tree `74cdeca2ed0d4b0eb6b1bc1a6c5fa278b8ee498a` in a
fresh directory. The replay verifies the Stage input pin `d4c99c2f53`, uses
the `6bc461f4` SDK and VM, and materializes dependencies from local Git objects.

The executable uses the shipping `NativeEntry.swift`, `PublicFactory.swift`, `SignedChecklist.swift`, and `Integrations/InstalledGuest` sources byte for byte. The host SwiftPM manifest selects the existing Android owner branch with `FIELDLOG_ENTRY_COMMIT_HOST_TEST`. The entry-commit fixture flag is disabled. The host renderer supplies synthetic draw and tap witnesses through Mixer's transport. The production owner performs signed release verification, Wasm execution, and selected-draft storage dispatch. The identity has the Android platform field required by that owner and binds the local Mach-O and VM archive hashes. It is development material for this host replay. The manifest points to a disposable commit of the reconstructed tree.

The signer generates an Ed25519 key in memory and the origin binds a disposable loopback port. A mounted guest may use only the existing nine-byte selected-draft storage ABI. The replay checks that a current input changes only the selected draft's follow-up, that invalid authority cannot write, and that reselection revokes the old lease. It closes delivery before starting a fresh process and checks the retained signed release, the workspace and linked JPEG bytes, inodes, and modification times. The receipt records only digests and observations. Android ELF/JNI execution and native mobile UI are outside this replay's scope.

The supervisor caps the run at 11 minutes and samples a 1.5 GiB scratch budget. It removes temporary binaries, material, and workspace data after the direct child is reaped and its process group is absent. A missing terminal observation preserves the exact owned scratch for custody.
