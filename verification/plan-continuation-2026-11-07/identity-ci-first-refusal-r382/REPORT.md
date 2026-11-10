# R382: exact identity CI first refusal

Run [42898333587, job 130117303812](https://github.com/snowdamiz/mixer/actions/runs/42898333587/job/130117303812) at `12a57c991cc5e51d5f2ad898a522355deed481a9` refused the delivered source manifest before any Docker operation. The artifact records `CollectorError: frozen product digest mismatch`; this is a source-authority refusal, not an observed identity runtime failure.

## Verified counterexample

- The downloaded ZIP SHA256 is `d2cc884bd384ed8c63ff1558ece70d955c191905d94dc579d2fa72073eb39658`, matching GitHub artifact 13801596659. Its manifest tree and every member's length/hash validate.
- Top-level `state.json`, `artifact-manifest.json`, and `finalizer.json` were read before command payloads. State records zero containers, zero unresolved creates, zero cleanup errors, two commands, and a frozen primary failure. No UNKNOWN resource was discovered in this attempt. This does not release any other run or hold.
- Both commands were complete, successful Git reads: exact HEAD, then `cat-file --batch`. Their raw payload is retained in `artifact.zip`. No Docker command or network method was reached.
- The actual second-command stdout contains all 178 selected blobs. Exactly one differs: `hosted/test/mixer_hosted/builds/coordinator_test.exs`, selected 21,500 bytes / `af70ef055e97ff1ba16b546297f802a7b7dc339fcf7e9c5bc45c5af2b70bfdb6`, delivered 25,019 bytes / `39d0cc1695723998e68e636e22d425e56c4e9f5ffb3d7e8d718670f12e43579b`.
- The complete selected digest is `8d0139c8c64e02f29f42a96384661f60dd7b724fa5fb4d5f54f6e7c1b7b78cd3`; the delivered digest is `219b37e01c8170a8ca9d434ed9160235d1f97737ad831683a8e700e025b59044`. The other 177 selected rows, including the lock and selected identity sources, match exactly. This comparison covers the finite selected inventory, not an independently enumerated full repository.
- The exact source diff adds the test `completion already in flight cannot commit after lease replacement or escape its tenant` at the existing coordinator-test location. `coordinator-only.diff` retains it. The historical selected test was fetched from `9e860ea12074ca31bef4087ce34177a03f295dd8` and verified against the selected row.

## Owning authority and minimum blocker

`hosted/scripts/test-identity-network.py:1478-1481` validates its compiled `FROZEN_MANIFEST`, reads those same paths from the delivered SHA, and validates the observed digest. `validate_source_manifest` at lines 382-384 explicitly rejects a caller-selected digest. `_validate_source_manifest` at line 378 raises the observed refusal. `Collector.run` at lines 1441-1469 retains the exception in state and returns 1, explaining the silent command step.

The current authority is `verification/identity-network-fixture-amendment-v2/metadata/selected-source-manifest.json`, owned by that namespace's `source-amendment.json` (SHA256 `45f0c33f8f521ff43ed58b13c34466dea593ecd1c9e8aab166b1e075da07ef84`). It selects the old coordinator-test row. Its only authorized delta is whitespace in `identity/tls_fixture_lifecycle_control_test.exs`; the collector checks that exact boundary at lines 473-493. The fresh GitHub SHA identifies delivered bytes but does not authorize replacement of this selected contract.

The minimum blocker is current execution-source authority for the single coordinator-test replacement. A separately owned successor source selection must explicitly admit that exact delta and preserve the existing identity methods, lock, image/execution/resource/custody policy, and bindings through archive, preparation, restore, compile, and final comparison. The old v2 format-only packet cannot supply that authority. No narrow implementation defect was proved: the current validator does exactly what its accepted contract requires. A blind digest refresh, ignored test row, replacement with old source under a current-SHA claim, or skipped workflow would change the qualification contract or conceal the failure. No canonical patch is supplied.

## Executable inert verification

`diagnose.py` reproduces the actual refusal from the downloaded command bytes, with process/shell/socket creation denied during collector import and validation. Both commands passed on Python 3.14.8 / Darwin 27 arm64:

```text
python3 -B verification/plan-continuation-2026-11-07/identity-ci-first-refusal-r382/diagnose.py
python3 -O -B verification/plan-continuation-2026-11-07/identity-ci-first-refusal-r382/diagnose.py
```

Seven controls pass in each mode: historical selected input accepted; actual delivered input refused; restoring only the coordinator manifest row accepted; caller-recomputed digest refused; changed lock refused; missing selected file refused; artifact hashes and both Git command completion records verified. The row-restoration control changes only an in-memory diagnostic manifest; no repository source is restored. Results are in `inert-normal.json`, `inert-optimized.json`, and `source-counterexample.json`.

The actual job log confirms 141 pure controls passed before the collector step. Those fixture-based controls do not establish that current delivered product blobs satisfy a frozen source selection. The collector step lasted about 0.123 seconds and exited 1. No failed workflow was rerun, no network collector was launched, and no Docker, namespace, device, historical held resource, credential, root Git, or remote mutation operation was performed. All writes are confined to this R382 output directory. Application/floor work remains independent. Current network/runtime qualification remains unrun for this delivery.

Two initial local diagnostic helpers failed harmlessly: `ast.literal_eval` could not resolve the manifest's dictionary expansion; a platform-formatting helper attempted a subprocess and was blocked by the inert guard. The final replay imports the side-effect-free collector under guards and reads `os.uname()` directly. Neither helper launched product work or created unknown custody.
