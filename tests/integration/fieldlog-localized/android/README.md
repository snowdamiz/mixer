# FieldLog Android localized checklist

This is the L02 / L08 §22.2.5 fixture for one ordinary saved task titled
`فحص المضخة 07`. Both guests contain that static title. Install the assignments
only in the disposable development fixture and select that saved task.
The selected-task wire still carries the committed workspace revision and the
completion bit. The guest receives neither the task title nor its ID through
the wire.

## Run the host fixture

Use arm64 macOS, Python 3.11+, the Swift 6.3.3 release toolchain, Rust 1.99.0
and the macOS 26.5 SDK from Xcode 26.6. [Pins](pins.json) lists the exact tool
digests and payload bytes. The runner uses the maintained engine-pair source
preparation and process supervisor. Its public source inputs may need network
access on the first run. It uses an ignored disposable campaign, keeps the
maintained free-space reserve and checks its own allocated file bytes after
each phase against the 600 MiB budget.

```sh
python3 -B tests/integration/fieldlog-localized/android/replay.py
```

For a root-owned handoff, add `--export-dir` with an unused output directory
whose parent already exists. It receives only `baseline.wasm`, `reviewed.wasm`
and `binding.json`. The command emits JSON evidence to stdout and reaps its
owned groups before removing scratch.

If the replay fails after attempting the compiler build, it retains scratch
and records the wrapper observations in `HOLD.json` when it can write the
file. The wrapper exit and process group do not establish descendant closure.

The probe runs each compiled Wasm through the pinned Mixer VM with the deferred
start and bounded mailbox limits. Capability responses come from the ordinary
FieldLog `FieldLogTaskStorage` over a fresh `WorkspaceRepository`. It checks
the three Arabic row nodes, exact renderer action, duplicate/stale events,
review without a write, canonical reads after complete and reopen, one outbox
append per accepted change, and persistence after closing and reopening the
repository. It services the mailbox in process. This is fixture evidence for
the guest and saved-task contract.

### Source binding

| Input | Revision or digest |
| --- | --- |
| Mixer checkout base | `9bdd8958da5612cfb015cd6d5de62c4d245dba0b` |
| Public FieldLog | `552559d2d3278abb9b1aa7dcf0288102c09a202b` |
| Mixer Android host | `c392e762d6bb24562647fe22a2de738250ba3e7f` |
| Prepared Android consumer, 918 files | `e619e155178db0433d6ef554fb8729d73609e7b0ebd648183b9b6bf7c4b8099a` |
| Guest base | `3184c398ba5e5dcded110a65772d793ba9caf9f6` |
| Guest after maintained `selected-task.patch` | `92797cc9e62b0a64f199d81c6ade62e6960393c61faf7c05ebf0b4115a1ace80` |
| Guest after `localized-guest.patch` | `180f21811c230bc633982527cd09a45de14101f661e50bf95c72863904681939` |
| Single engine source | `9fd7e7f6ebd9cadfd96d71a6c71225e6b11e33b9` |

Source inventories hash the concatenated lines `<file SHA-256>  <relative path>\n`
sorted by path components. The guest inventory includes the applied patches.
The receipt's recipe hash uses this same format over the five local recipe
files. The maintained pair tree ID is bound in [pins.json](pins.json).

## Root-owned APK and assignments

The single-APK packager admits the exact sealed current-engine APK and the
localized guest export from `c5634293217517ee66ecd4dd154f1823de9834ed`.
[Input pins](package-pins.json) cover the APK, original descriptor and link
evidence, sealed verification tools, and source binding. Use the maintained
[toolchain preflight](../../fieldlog-android-engine-pair/replay/toolchain.py)
and put Go 1.27.1 ahead of other Go installations on `PATH`.

```sh
base=/path/to/sealed/engine-pair/handoff
guests=/path/to/verified/guests
python3 -B tests/integration/fieldlog-localized/android/package.py \
  --check-inputs --base "$base" --guests "$guests"
python3 -B tests/integration/fieldlog-localized/android/package.py \
  --base "$base" --guests "$guests"
```

The first command checks the exact inputs, manifests, and routing without
allocating a campaign. The second compiles only the small Go fixture signer
against the pinned protocol. It preserves the original Android manifest, DEX,
JNI, and all other APK payload members except the installed roots, identity,
and loopback port. It aligns and development-signs the APK with a fresh
certificate, then verifies both assignments against the identity and root
extracted from that APK. Scratch is removed after checksum verification. If
the command fails or is interrupted, preserve the printed campaign and any
custody markers for root review.

From the printed `handoff/` directory run `shasum -a 256 -c SHA256SUMS`.
From the Mixer checkout, run the loopback origin against that same handoff.

```sh
python3 -B tests/integration/fieldlog-localized/android/origin.py "$handoff"
```

For the installed replay, add `--control "$control"`, where `$control` is
a fresh directory path. The service uploads and validates both releases,
publishes sequence 1, and writes `baseline.ready.json` after verifying its
offer. Use the port in that record for the exact ADB reverse. Once sequence 1
is healthy on the installed device, create `"$control/publish-reviewed"`.
Wait for `reviewed.ready.json` before pressing **Check for update**. To
stop the origin, create `"$control/stop"` and wait for its terminal receipt.

If either retained input is unavailable, reproduce the original guest export
at its pinned recipe commit and rebuild the
[maintained engine pair](../../fieldlog-android-engine-pair/README.md) after
storage permits. A rebuilt APK has fresh keys and a different digest, so
review and pin the new sealed handoff before reuse.

## Root-owned device comparison

Install once in a fresh owned Android emulator with the exact loopback reverse.
Create and save the sole task `فحص المضخة 07` under an ordinary project. Record
its task and project IDs, committed revision, outbox, APK hash, installation
ID and runtime. Open the signed checklist for that task and confirm sequence 1
is healthy with both `first_screen` and `feature_started`. Save the journal
and untouched workspace before publishing sequence 2.

For each sequence, capture the same untouched task at **1× LTR**, **1× RTL**
and **2× RTL**. Record the actual locale, direction and effective font scale
alongside the screenshot and accessibility bounds or layout readback. Check
logical leading-edge alignment, row order, wrapping without clipping,
visibility and clickability of the button, and the visual order of `07`.
Check for a size response between the RTL measurements. After switching to
sequence 2 through **Check for update**, verify the updated status and button,
stable APK/runtime/installation, both durable launch milestones and unchanged
workspace before interaction.

Tap the reviewed button once and observe the confirmation frame with identical
workspace revision and outbox. Tap confirmation once and verify the canonical
completed frame, the same task ID at revision +1, and exactly one new
`taskSaved` row for that task. Stop the origin and remove the exact reverse.
Force-stop, relaunch and reopen the checklist offline. Confirm sequence 2 and
the completed state from disk. Tap reopen once, verify the canonical open
frame, revision +1 and one further outbox append. Relaunch offline again to
verify the reopened state. Save the paired screenshots, journals, delivery
logs and workspace readbacks, then close and clean up the owned emulator,
origin and scratch. Record a visible failure and its matching durable
readback separately if either disagrees with the screen.

Save the workspace snapshots as `workspace-<checkpoint>.json`. Use
`baseline-ltr`, `baseline-rtl`, and `baseline-large` for the three
scale and direction captures, and the matching `reviewed-` labels for
sequence 2. Run `verify-workspace.py --help` for the full checkpoint list.
After the replay, pass the capture directory to `verify-workspace.py`.
