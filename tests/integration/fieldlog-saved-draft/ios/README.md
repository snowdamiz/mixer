# iOS saved-draft rollback readback

This verifier checks copied FieldLog workspace and recovery snapshots for L08 §22.2.4. The existing bound product identifies the native entry point as `FieldLogUITests/FieldLogSignedDraftTests/testSignedOptionalFieldSurvivesRollbackAndOrdinarySave`, targeting `dev.mixer.fieldlog` 0.1.0 (1). Use the exact arm64 Simulator archive and signed assignments documented in the receipt. The receipt records the private binding patch and build packet by digest. It establishes build provenance. The device pause still applies. [Bound iOS app receipt](../../../../verification/receipts/fieldlog-ios-selected-draft-bound-app-20261119.json)

## Run the host controls

From the Mixer checkout, run these commands with public Mixer `9c14c70b5a2b8bd8b99b2b632fd5e67a590375e5` available as a local Git object.

```sh
python3 -B tests/integration/fieldlog-saved-draft/ios/test_verify.py -v
tests/integration/fieldlog-saved-draft/ios/test_public_repository.sh
```

The Python controls exercise the CLI with authored captures. The macOS control downloads the digest-pinned public FieldLog `552559d2d3278abb9b1aa7dcf0288102c09a202b` source and reads the two reviewed repository overlays from the pinned Mixer object. It verifies both patched Git trees and compiles their `FieldLogModels` and `FieldLogStorage` directly with `swiftc`. The successor sets the flag and refuses an unsaved UUID. A fresh floor process reads the same draft and saves an ordinary note with a stale optional field. A third process reopens the successor and checks both draft identities, the flag, the outbox and the JPEG. The Python verifier also compares the actual before and after snapshots for that edit. The host test uses no app or update service.

## Capture contract for an authorized installed run

Use the exact bound product above. The maintained signed fixture shows how to wait for a native first screen, drive a hittable button, attach labels and health launch identities, and confirm termination. Its rotation test shows the public `--fieldlog-ui-workspace` launch argument and attached `FieldLogUITest-<uuid>` workspace folder. Those checklist harness arguments are specific to that fixture. Use the bound draft test’s own launch setup. The ordinary upgrade fixture shows exact workspace and photo copies using `Library/Application Support/FieldLog` for the ordinary app; use the directory identified by the bound test for an isolated workspace. [Signed XCTest](../../../../capability-activation/verification/fieldlog-ios/FieldLogSignedOTATests.swift), [Isolated checklist XCTest](../../../../capability-activation/verification/fieldlog-ios/rotation/ChecklistJourney.swift), [Ordinary workspace readback](../../fieldlog-ios-installed-upgrade/upgrade_journey.py)

Prepare two saved drafts in the same project, with distinct valid titles. Give A one JPEG and B no attachments. Leave both follow-up flags unset. For every checkpoint, copy the raw `workspace.json` and the `photos/` directory into `CHECKPOINT/before/` and `CHECKPOINT/after/`. Capture after queued saves settle, with navigation outside the before/after window. The verifier permits an open-draft pointer and revision change between checkpoints. The offline note may take multiple ordinary editor saves to settle. The optional flag write must advance the revision once. A read-only action must preserve the full workspace bytes. All checkpoints must preserve the JPEG bytes.

| Checkpoint | iOS assignment | Native action and observation |
| --- | --- | --- |
| `baseline` | 1, baseline | Check A. Confirm `Ready to save entry` and `JPEG linked`. |
| `corrected` | 2, corrected | Repeat the read of A under the corrected release. |
| `optional` | 3, optional | Observe `Follow-up unset`. Mark follow-up required once on A and observe `Follow-up required`. |
| `rollback` | 4, corrected | Check A under the read-only rollback. The result and JPEG remain visible and the follow-up control is absent. |
| `offline-edit` | Origin unavailable | Edit A’s note in the ordinary editor and wait for its local save. Record the app PID and visible note. |
| `cold-reopen` | Retained 4, origin unavailable | Terminate and relaunch FieldLog. Open A and observe the edited note, the same JPEG, and the retained read-only result. Record the new app PID. |
| `reupgrade` | 5, optional | Reopen A and read the retained flag and JPEG without a write. |
| `unsaved` | No attachment admitted | Attempt the signed action on a draft UUID absent from disk. Observe refusal or a disabled action and verify both saved drafts are untouched. |
| `second` | 5, optional | Open B with a fresh panel. Observe `Follow-up unset` and `No photo shown`. |
| `reselect-first` | 5, optional | Return to A with a fresh panel. Observe `Follow-up required` and `JPEG linked` again. |

The public ordinary iOS `WorkspaceModel.newDraft` saves before opening the editor. A blank new draft shown by that flow is already saved. The unsaved checkpoint needs an observed unavailable selection from the bound harness or a separately instrumented native control. Likewise, use the existing selector for the behavior it actually covers and capture further checkpoints separately if needed. The public receipt identifies the entry point and build inputs, but does not describe its assertions or exported files. The verifier’s filenames are capture destinations.

Copy the raw capability recovery `state.json` into `CHECKPOINT/recovery/state.json` for each checkpoint with a numbered assignment, including the retained offline launch. Use the recovery directory for the bound draft runtime. The maintained signed readback helpers demonstrate the persisted candidate and health format and reconcile it to XCTest attachments. [Signed readback](../../../../capability-activation/verification/fieldlog-ios/readback.py), [Rotation readback](../../../../capability-activation/verification/fieldlog-ios/rotation/verify-readback.py)

Create `journey.json` from the native observations. Its keys are `bundleID`, `appSHA256` for the measured installed executable, `firstDraftID`, `secondDraftID`, `unsavedDraftID`, `offlineNote` for the exact intended edit, and `phases` keyed by the checkpoint names above. Each phase records the observed `selectedDraftID`. Signed phases also record `guestLaunchID`, `validation`, `photo`, `followUpBefore`, and `followUpAfter`. Use JSON `null` for an absent follow-up control. For the offline edit and cold reopen, include `originUnavailable`, `appPID`, and `visibleNote` from the origin and app observations. For the unsaved case include `refused` from the selection observation. Keep the underlying XCTest attachments, origin outage evidence, and app executable measurements with the original run.

```sh
python3 -B tests/integration/fieldlog-saved-draft/ios/verify.py \
  "$EVIDENCE" "$PINNED_BOUND_BUILD_RECEIPT"
```

Supply the unmodified receipt from the pinned Mixer revision, using `git show` to copy it to an owned input file if needed. The verifier compares native observations to the copied workspace and to release identity and health in the copied recovery state. It checks JPEG markers, length, linkage and byte continuity. Native evidence collection, image decoding, signed-envelope verification, origin custody, and test dispatch remain part of the installed run. The Android isolation receipt provides a separate precedent for these checkpoints. [Android acceptance](../../../../verification/receipts/fieldlog-android-saved-draft-isolation-20261120.json)
