# Replay the matched TaskCompletion host benchmark

The [original receipt](../../../verification/receipts/l03-d3-taskcompletion-matched-macos-4bf1078d.json)
records five interleaved pairs of macOS processes. Each process times three
prepared events through frame materialization and checks all four frame bytes
against the historical D3 digests. A separate control checks refusals and the
Swift trap location. Peak RSS covers the whole process. The timings describe
this host workload, including the guest's synchronous VM call.

The original raw unsigned Wasm module was 5,266 bytes. Its SHA-256,
`b21b28e540a35ce0b9244e489940b3b6c1390c948ba7cfdde3cb87d79f88eb59`,
identifies only that build. Two independent scratch builds produced the same
byte count and different hashes. Review found differences in the debug line
and data sections. The data-section difference remains unexplained. Compare
frame digests and the diagnostic source location
when replaying. The function index and byte offset describe the current
artifact. The receipt covers host observations only.

## Set up and run the pinned replay

Use arm64 macOS with the native Swift compiler selected by `xcode-select`,
the Swift 6.3.3 release toolchain under `~/Library/Developer/Toolchains`, and
Rust 1.99.0 under `~/.rustup/toolchains`. The receipt lists the tool versions
used in the measurement. Start in a Mixer checkout containing both commits
below. The replay uses local Git objects and builds Cargo offline.

Create a new scratch directory and keep its path for cleanup.

```sh
replay_root=$(mktemp -d /tmp/mixer-taskcompletion.XXXXXXXX) &&
  export replay_root
```

Run the following block. The 1,900 MiB sparse disk image bounds the replay's
checkout, build outputs, and logs. The detached checkout shares the source
repository's objects through a read-only alternate. The two verified harness
files are the only overlays.

```sh
(
  set -eu
  adoption=00aa86d374ada80f64a25255c1adaac427db2d13
  pin=4bf1078d46ad80912151b789c27485ff41578d1e
  tree=a7d7189dd9ee0233d00dff9fba056e55e6595284
  harness=compiler/experiments/fieldlog-guest-benchmark
  receipts=verification/receipts
  source_repo=$(git rev-parse --show-toplevel)
  objects=$(git rev-parse --path-format=absolute --git-path objects)
  git cat-file -e "$adoption^{commit}"
  test "$(git rev-parse "$pin^{tree}")" = "$tree"

  mkdir "$replay_root/volume"
  hdiutil create -quiet -size 1900m -type SPARSE -fs HFS+ \
    -volname MixerTaskReplay "$replay_root/replay.sparseimage"
  hdiutil attach -quiet -nobrowse -noautoopen -mountpoint "$replay_root/volume" \
    "$replay_root/replay.sparseimage"
  checkout="$replay_root/volume/checkout"
  git init -q --template= "$checkout"
  printf '%s\n' "$objects" > "$checkout/.git/objects/info/alternates"
  git -C "$checkout" sparse-checkout set --no-cone --stdin <<EOF
/$harness/
/compiler/experiments/fieldlog-installed-guest/
/compiler/experiments/fieldlog-reactor/support.py
/compiler/experiments/profile-budget/analyze.py
/compiler/qualification_support.py
/experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/
/vm/
/$receipts/l03-d3-task-review-event-trap-7b61fe1c.json
/$receipts/l03-d3-task-completion-android-7b61fe1c.json
/$receipts/l03-d3-task-completion-host-benchmark-7b61fe1c.json
EOF
  git -C "$checkout" switch -q --detach "$pin"
  cd -P "$checkout"
  git -C "$source_repo" cat-file blob "$adoption:$harness/MatchedTask.swift" \
    > "$harness/MatchedTask.swift"
  git -C "$source_repo" cat-file blob "$adoption:$harness/matched_task.py" \
    > "$harness/matched_task.py"
  shasum -a 256 -c <<EOF
887fe08b21caca8b0d6eb70ee2d85be51d61c2e7bb152c92c6b43693ecd7e2b4  $harness/MatchedTask.swift
2d8137f209570e64e30d417f2d832680eccb541a96c4749cdcfb0b32e2bfe365  $harness/matched_task.py
EOF
  git diff --exit-code --quiet "$pin" --
  python3 -B "$harness/matched_task.py" > "$replay_root/volume/receipt.json"
  git diff --exit-code --quiet "$pin" --
)
```

The harness has a 240-second campaign deadline and shorter per-command
deadlines. Inspect `"$replay_root/volume/receipt.json"` after a successful
run. Confirm `custody.unknown` is zero and `custody.scratchRemoved` is true.
Record the receipt before detaching the volume. If the harness reports unknown
custody, preserve the scratch volume and the reported process identity.

After confirming cleanup is safe, detach the volume and remove this run's image
and empty directories. A successful detach confirms the volume is no longer
mounted.

```sh
hdiutil detach "$replay_root/volume" &&
  rm "$replay_root/replay.sparseimage" &&
  rmdir "$replay_root/volume" "$replay_root"
```

The [adoption replay receipt](../../../verification/receipts/l03-d3-taskcompletion-pinned-replay-00aa86d3.json)
records a fresh session with this setup and its cleanup.
