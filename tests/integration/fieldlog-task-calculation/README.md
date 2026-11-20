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
run. The installed Android calculation replay has separate evidence. Installed
iOS calculation remains pending.
[Android calculation receipt](../../../verification/receipts/fieldlog-android-calculation-correction-20261120.json)

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

## Reconstruct the source of the Android calculation replay

Use a fresh disposable FieldLog checkout. The checker stages the patches and
leaves the traced tree in the checkout. Both source overlays and the delivered
byte pins are tracked in Mixer.

```sh
git clone https://github.com/snowdamiz/fieldlog.git "$FIELDLOG"
git -C "$FIELDLOG" checkout --detach 552559d2d3278abb9b1aa7dcf0288102c09a202b
python3 -B tests/integration/fieldlog-task-calculation/android-source-check.py "$FIELDLOG"
```

The checker applies the three selected-draft patches, then the calculation
overlay. It verifies pre-trace tree `5c36b0c71f00727bfd75418feae668bf8d527835` and
25 file hashes. It applies the trace overlay and verifies tree
`7753563b91fe162cfb058cb175ccde979b430033` and 29 file hashes. A fresh checkout
is required after a successful or interrupted run.
[Source receipt](../../../verification/receipts/fieldlog-android-calculation-source-review-20261120.json)

## Rebuild the Android APK and replay it on the host

Use arm64 macOS with Xcode 26.6 at `/Applications/Xcode_26.6.app` and
Xcode 27.2 at `/Applications/Xcode.app`. Install the Swift 6.3.3 release
toolchain and its Android SDK bundle in the standard per-user locations.
Install Rust 1.99.0 with the `aarch64-linux-android` target and `llvm-tools`.
The recipe uses Homebrew OpenJDK 25.0.4.1, Android SDK Platform 36,
Build Tools 36.0.0, and NDK 27.1.12297006. It uses the pinned Swift Crypto
and Swift ASN.1 revisions from the standard SwiftPM repository cache.
The toolchain lock lists the exact compiler, resource, DEX, and signing
inputs that the preflight verifies. [Toolchain pins](android-packaging/toolchain-pins.json)

Use a Mixer checkout containing the recipe, the pinned Mixer commit
`5dea19db36610e312b51918b384364ba590b6ef8`, and its source objects.
The recipe fetches the pinned public FieldLog commit from GitHub.
It uses only local inputs after that fetch.

```sh
run=$(mktemp -d /tmp/fieldlog-calculation.XXXXXXXX)
run=$(cd "$run" && pwd -P)
tests/integration/fieldlog-task-calculation/android-packaging/rebuild.sh "$run/work" "$run/handoff"
(cd "$run/handoff" && shasum -a 256 -c SHA256SUMS)
```

The command needs free loopback port 41897 and up to 6 GiB of local space.
It writes the APK, signed delivery, origin script, checksums, and receipts
to `handoff`. The build uses the tracked 3,530-byte fixture seed and publishes
its hash in both the APK and the host receipt. The witness runs baseline,
correction, rollback, and a cold offline reopen against the same fixture.
[Recipe inputs](android-packaging/recipe.sha256)

Each rebuild creates its own development certificate and OTA root. Signing
time, launch identifiers, and the signed APK and OTA bytes vary. The build
receipt records the freshly linked JNI hash and the exact pinned DEX hash.
The JNI library embeds build paths from Swift Crypto's BoringSSL sources,
so its digest can vary with the scratch directory. The APK and its signed
delivery share the runtime fingerprint recorded for that build.

After success, remove the owned `work` directory and keep `handoff` for
device qualification. If the command fails, use `work/logs` to check stage
exit and custody. Preserve a stage with an `UNKNOWN` result or an
interruption inside the VM builder until its nested commands are accounted for.
