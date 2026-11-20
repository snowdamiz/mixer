# Replay the FieldLog task completion fix

This macOS integration covers the host portion of product-plan §22.2.1. It
compiles the public FieldLog model and storage into the test host. The
developer v3 release service delivers a faulty calculation, its fix, and a
signed rollback to the same host executable. The owned Mixer VM renders the
guest document, and a test presentation witness confirms the first frame.

Use an Apple Silicon Mac with Xcode, Python 3.12 or later, Rust and Cargo, Go
1.26, and the Swift 6.3.3 release toolchain with Embedded Swift and `wasm-ld`.
Set `FIELDLOG_GUEST_BIN` or `FIELDLOG_RUST_BIN` if either toolchain is outside
the default location in `replay.py`. Use a Mixer checkout that contains the
commit in `inputs.json`. The runner fetches FieldLog and the locked SwiftPM
dependencies from their public Git URLs. Go can read dependencies from its
public module proxy. The replay uses disposable signing keys created in
memory and a loopback developer origin.

From the Mixer checkout, pass a fresh run name.

```sh
python3 -B tests/integration/fieldlog-task-calculation/replay.py my-replay
```

The saved projects contain one of three tasks complete, two of two complete,
and zero tasks. The native `Workspace.progress(for:)` oracle yields 33%,
100%, and 0%. The baseline guest yields 0%, 100%, and 0%. The corrected
payload scales the count before dividing and matches the native oracle.
Signed sequence 3 returns to the baseline payload.

The runner checks the hash of the host executable, and the test compares the
saved workspace bytes after each activation. A second process reopens the
repository with the origin stopped, launches the committed rollback, and
rejects the older signed assignment. It checks the workspace again after
closing the cold repository.

The runner writes command logs and `receipt.json` under
`verification/local/fieldlog-task-calculation-my-replay/`. It removes the
disposable checkouts, builds, caches, payloads, and stores after custody
closes. If custody remains unresolved, the receipt identifies the retained
run. iOS Simulator and Android emulator remain pending for this scenario.

The recovered source matches the closed host run's SHA-256 pins. The patch
files omit single-space markers on blank context lines and produce the same
Swift files as the originals. The replay shares the C imports with the
saved-draft integration and uses the v3 loopback client and runtime fixtures
from the pinned Mixer tree. [Source pins](inputs.json)

## Check an installed Android launch and retirement

For each signed phase, capture the recovery state while the checklist is
open. Keep the installed APK, assignment, and workspace checks from the
packet replay. Use the expected runtime, sequence, artifact hash, and payload
hash from its verified assignment and manifest. Use the installation ID
recorded at the first checkpoint.

```sh
readback=tests/integration/fieldlog-task-calculation/android-readback.py
python3 -B "$readback" "$live_state" \
    --runtime "$runtime" --installation "$installation" --sequence "$sequence" \
    --artifact "$artifact_sha256" --payload "$payload_sha256"
```

Once the live readback succeeds, tap **Done** and capture the state again.
Pass both snapshots to check that the same healthy launch survived
retirement and its attempt cleared.

```sh
python3 -B "$readback" "$live_state" --retired "$retired_state" \
    --runtime "$runtime" --installation "$installation" --sequence "$sequence" \
    --artifact "$artifact_sha256" --payload "$payload_sha256"
```

Repeat for the corrected assignment, the rollback assignment, and the cold
offline reopen. Compare the candidate and launch identifiers across phases.
The offline reopen keeps the rollback candidate and earns health for a new
launch. Compare the workspace bytes at every checkpoint.
