# Source-only Slice B proposal packet

This is preparation for root selection. It contains 25 bounded source/read-input
snapshots, their identities, the proposed contract identity and supplemental
custody/coverage results. It does not contain an implemented effect runner,
product-test results, native execution or source-profile selection.

`receipt.json` binds the exact core and frozen Slice A candidate inputs, tool
identities, source revision, selected-input projection digest, retained patch
failure and limitations. The projection is not a complete repository tree digest.
`freeze.stdout` is the capture result; `check.stdout` and `source-only-result.json`
are supplemental source-only results. All captured command stderr is retained.

Run the bounded read-only handoff verification from the repository root:

```sh
python3 -B verification/android-private-owner-effect-integration-proposal/seal.py verify
```

`manifest.json` seals the proposal and every packet member except the manifest
itself and its `handoff.sha256` binding. `check.py` can recheck current exact seam
identities and coverage, but rewrites its own result; use it only before a new
freeze/seal. Do not rerun `freeze.py` over this receipt. Historical snapshots are
evidence and must never become a second canonical implementation.

Root owns implementation selection, profile identities, metadata, independent
acceptance and delivery. Native runtime/capture and physical devices remain
pending under the active restrictions. No general-purpose dependencies were
added.
