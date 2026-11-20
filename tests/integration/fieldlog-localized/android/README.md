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

1. Export both guests and verify both Wasm hashes and the localized source
   digest from `binding.json`. In a fresh native campaign, use the
   [engine-pair preparation](../../fieldlog-android-engine-pair/replay/prepare.sh)
   and [toolchain preflight](../../fieldlog-android-engine-pair/replay/toolchain.py).
   Recompute the 918-file consumer digest after generating `manifest-base.xml`.
   Use the maintained overlays in their original order for FieldLog and Mixer.
   Run the `tools` phase of the maintained [build driver](../../fieldlog-android-engine-pair/replay/build.sh)
   through the preflight to obtain `mixer-identity`, `mixer-update` and the
   release service from `9495996b00b5185c3d7fbf310615f69eadec9624`.
2. Build just `scratch/pair-new/vm` for `aarch64-linux-android` using the
   maintained offline, locked release build with
   `experimental-capability-native`. Enforce the `new` archive and source pins
   in [engines.json](../../fieldlog-android-engine-pair/inputs/engines.json).
   Run [android-jni.sh](../../fieldlog-android-engine-pair/replay/android-jni.sh)
   with `APP old NEW_ENGINE_ARCHIVE` under the preflight environment. Its
   `old` argument selects the branch that compiles the shared C objects. The
   linked engine comes from the explicit new archive. Run the maintained
   [manifest/Dex step](../../fieldlog-android-engine-pair/replay/manifests.sh)
   and use only the `old` version 24101 manifest for this APK.
3. Generate a fresh development Ed25519 root with artifact and assignment
   authority for the maintenance manifest's Android FieldLog scope, and choose
   one owned loopback port. Assemble a single `Installed/` bundle using the
   [packager's binding inputs](../../fieldlog-android-engine-pair/replay/package-pair.py).
   Bind the actual new-engine archive, linker inputs/JNI, DEX, manifest,
   settings, fallback sources and trust roots into the identity descriptor.
   Derive the one host identity with `mixer-identity`. Package and development
   sign one APK using the maintained FieldLog
   `build-signed-checklist-android.py` source and installed asset SHA-256 list.
   Verify the APK certificate, package/version, 16 KiB alignment, arm64 JNI and
   identity asset against the resulting descriptor and link evidence.
4. Use the [manifest template](../../fieldlog-android-engine-pair/inputs/manifest.json)
   and the maintained [protocol signing calls](../../fieldlog-android-engine-pair/replay/sign.go).
   Issue distinct releases `fieldlog-localized-baseline` and
   `fieldlog-localized-reviewed` for the **same** derived runtime, scope, root
   and `beta` channel, with sequences **1** and **2**. Use the exported Wasm
   hashes and byte lengths, the localized recipe commit as `source_commit`,
   and the localized guest inventory in `provenance_id`. Use the unchanged
   capability grants, limits and empty asset map. Verify each exact signed
   set with `mixer-update` against the embedded identity and root, sequence 1
   at cursor 0 and sequence 2 at cursor 1. Record both digests and remove the
   signing material once the packet is sealed.
5. Run the pinned local release service with just that one host and development
   root. Follow the [maintained origin request shapes](../../fieldlog-android-engine-pair/replay/origin.py).
   Upload each signed manifest and base64 Wasm via the project artifact route,
   validate each digest via `/releases/validate`, then publish only sequence 1
   via `/channels/beta/publish`. Publish sequence 2 after observing healthy
   sequence 1. Use the localized payloads and the one-runtime registration
   described here when adapting the two-cohort tooling.

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
