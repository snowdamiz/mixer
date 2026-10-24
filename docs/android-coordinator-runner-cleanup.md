# Separately bound Android coordinator runtime runner

The [corrected runner](../verification/android-coordinator-runner-cleanup/run.py)
adds owned extraction cleanup to the prepared Android coordinator runtime attempt.
It is derived from the original frozen runner with SHA-256
`8f4caee8c90fb2ab7348403576e56783e7e9ffd0d13a80850398ca4e34ea78d3`.
The original `android-coordinator-join` packet and all 105 candidate2 inputs remain
unchanged. The [source diff](../verification/android-coordinator-runner-cleanup/host-review-1/runner.diff)
and [host receipt](../verification/android-coordinator-runner-cleanup/host-review-1/receipt.json)
bind this correction independently of that frozen build.

The corrected runner reads builds only from `verification/android-coordinator-join`
and writes attempts only under `verification/android-coordinator-runner-cleanup`.
It accepts `candidate-2` only, pins its receipt, source lock, artifact manifest and
archive, checks all 105 retained source files, and preserves the original APK
SHA-256 `396466de00b4b905c664632e711a5dcda151f85af1a4f9e47c6ff1b68e5c276c`.
Its frozen source closure remains
`ec2acb7c78862d899a4722d8f2c11d90d47c2cc4726af00976d392536fb85b30`, and its
archive remains
`642962760271300298db98efd9f2018c159a2e9767843e4ef2bad84d9f824459`.
The separate runner source closure and exact tool/output hashes are recorded in
the host receipt. It uses an unchanged copy of the original owned process helper.

The runner records the device/inode identity of the fresh `.build` directory.
Its `finally` first performs the unchanged owned emulator/process-group cleanup,
then separately attempts extraction cleanup on success or failure. Only the
exact owned directory may be removed. A substituted directory, symlink, extra
file/directory, special file, unexpected path, open holder or unavailable `lsof`
check preserves the extraction and fails the attempt. The directory identity and
membership are checked again immediately before removal. Each holder-check log
gets a fresh name so a later recovery cannot replace the refusal evidence.
Evidence, packet exports, command logs and receipts remain outside `.build`.
Emulator cleanup and extraction cleanup have independent receipt fields; neither
failure becomes a runtime pass.

This implements the tested checker cleanup semantics from checker SHA-256
`20f00f2fe8c0d1936c7ec2aec771970fed28e1657d8085cc12eae1ced624f679`, adding
creation identity, allowed directory membership and a second pre-removal check.
It is intended for the cooperating local verification process; it does not claim
protection against an adversarial concurrent filesystem attacker.

The host verification command is:

```sh
python3 -B verification/android-coordinator-runner-cleanup/collect_host.py host-review-1 host-tests-2
```

The 20 controlled extraction/runner tests cover successful removal, operation
failure, a real open holder, nested/root/parent symlinks, directory replacement,
wrong paths, unknown ownership, extra files/directories, a FIFO, unavailable
holder checks, partial extraction, repeat cleanup, substitution after the holder
check, dispatch/candidate/path CLI guards, and the actual main `finally` with
cleanup success and failure. The main fixtures use a tiny synthetic archive,
stop before every native command, and install barriers against native SDK
execution and process start. Four preserved guards check exact owned identity,
archive safety, exact environment rejection and controlled host process-group
timeout cleanup. These are host tests, not Android runtime evidence.

The initial [host attempt](../verification/android-coordinator-runner-cleanup/host-tests-1.log)
failed a test assertion that assumed an open holder would make macOS `lsof` exit
zero. `lsof` returned one with the actual holder in its output, and the runner
correctly refused removal because the output was nonempty. The assertion now
checks the holder evidence. The failed attempt's extraction was removed only
after the holder closed, with its own retained recovery receipt. The final host
run is recorded separately; this history is not relabeled as a pass.

After root accepts the sealed correction, root may explicitly dispatch:

```sh
python3 -B verification/android-coordinator-runner-cleanup/run.py --build candidate-2 --attempt runtime-1 --execute-native
```

This headless runner uses targeted ADB and one `-no-window` emulator; desktop
unlock is not required for this bounded subset. Root's
[headless runtime direction](../verification/android-coordinator-join-root-review/headless-runtime-direction.json)
supersedes the earlier unlock assumption for this runner only. `--execute-native`
still requires explicit root dispatch. Use a fresh runtime attempt name if one
already exists. The original reserved-port, exact PID/port/AVD, read-only,
no-snapshot, process-group, environment, APK and native-result checks are retained.

This lane did not run ADB, an emulator, simulator, physical-device query, UI
automation or capture. Android execution and runtime acceptance remain pending
root dispatch/review. Physical phones remain deferred. The full native matrix,
public V2/signed authority, immutable published external FieldLog qualification,
store, customer, operational and GA gates remain pending.
