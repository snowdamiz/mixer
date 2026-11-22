# FieldLog history corpus for L08, G27 and G33

The corpus is anchored to `snowdamiz/fieldlog` commit `552559d2d3278abb9b1aa7dcf0288102c09a202b`, tree `1b62520f35c7e57a01b568291078686574f627c4`. I reviewed the production deltas across its 31-commit ancestry. Six commits provide the 20 behaviors. Fourteen behaviors arrived together in the additive `c6562ba` Android integration. This is a 20-behavior corpus and the history does not contain 20 corresponding product commits or release cycles.

The existing Mixer `compiler/Fixtures/FieldLogCorpus/main.swift` exercises one FieldLog model snapshot. The tracked D8 record calls for a 20-change report. I found no existing historical before/after manifest in the tracked dogfood, gate or compact receipt indexes.

Each manifest row pins an introducing commit and its first parent, paired blob IDs and the exact after-side line range and SHA-256. An absent before blob means that path did not exist in the parent. In the integration import, ordinary iOS already had drafts, checklists and report export. The rows cover Android delivery and changes that have distinct outcomes such as browse history without writes, retain a valid edited date across reopen, or refuse a projected save before disk mutation. The queue, checklist, and entry-history pages represent separate user workflows. Source and existing tests establish those distinctions. I omitted the baseline root snapshot, CI/build and documentation changes, test-only rows, and cosmetic subdivisions. The corpus does not claim to sample independent releases or the broader history of private Mixer afterimages.

## Coverage

| Measure | Result |
| --- | ---: |
| Source-anchored product behaviors | 20 |
| Practical OTA denominator | 17 |
| Rows with selected passing macOS host controls | 18 |
| Eligible rows with selected passing macOS host controls | 15 of 17 |
| Proven signed OTA on both targets | 0 of 17 eligible and 0 of 20 overall |

The native exclusions are **F07** for shipping the Android launcher, manifest and native bridge, **F17** for adding the Android system document picker and native content-URI bridge, and **F19** for installing the native report provider, URI grant and OS chooser. **F18** stays eligible because the persisted draft and attachment-reference change can be evaluated with an already installed picker. **F01–F03** stay eligible despite originating in SwiftUI. The current route can be missing a UI operation without the requested behavior inherently requiring a new platform permission or capability.

The 0/17 and 0/20 figures report achieved evidence. The pass/fail capability of unexecuted rows remains open. The receipts below cover selected native behavior. Corpus-wide patch size, the full Section 22 recovery matrix, and the two-target 80% threshold remain open. L08, G27 and G33 remain open.

## F02 checklist row moves

The separate F02 replay runs the historical Move down and Move up callback
bodies through FieldLog's original `WorkspaceModel` and disk-backed
`WorkspaceRepository`. Each action adds one project-scoped
`taskOrderChanged` record. A fresh process reads the saved order after each
move. An out-of-bounds move preserves the workspace file byte for byte.

From the Mixer checkout root, run the fixture with a FieldLog checkout that
contains the two F02 commits in the corpus.

```sh
python3 -B compiler/experiments/fieldlog-change-corpus/f02/replay.py \
  --mixer . --fieldlog /absolute/path/to/fieldlog
```

FieldLog's historical Debug Simulator receipt reports a Move down tap and
visible row-order check. The recorded source-tree digest remains
unreproduced. Native Move up, gestures, accessibility, and signed OTA
remain open.
[Host replay receipt](../../../verification/receipts/fieldlog-f02-ordinary-ios-host-2acaac67.json) ·
[Runner custody checks](../../../verification/receipts/fieldlog-f02-runner-custody-2acaac67.json)

## F10 signed Pending Changes

The macOS fixture uses the same bounded Swift queue projection in the native
control and the Embedded Swift guest. It seeds the real FieldLog repository
with 26 unsent records. The signed guest shows pages of 20 and 6 and preserves
page 2 after returning from Tasks. Six host actions are delivered. The
Entries action reaches the destination handoff marker. The fixture records
four storage reads, zero write attempts, and identical bytes and revision
after reopening the repository.

Run the replay from a Mixer checkout containing public v80. Supply a separate
FieldLog checkout containing the corpus history. The toolchain paths appear
in `--help`.

```sh
python3 -B compiler/experiments/fieldlog-change-corpus/pending-queue/replay.py \
  f10-pending-queue --fieldlog /absolute/path/to/fieldlog
```

The second signed fixture hydrates the historical navigation layout and
routes the queue-open action. V1 refuses the returned `navigation` root at
`event/document` before it presents the queue. Both owners retire. Rebuilt Wasm hashes can vary with the scratch path.
[Signed F10 receipt](../../../verification/receipts/fieldlog-f10-signed-pending-queue-v80.json)

The private `FeatureUIV3` exchange replays the historical hierarchy in the
headless render model. The decoded action and the current scoped page drive
the transition. The v81 replay delivers six actions across nine frames and
reopens the exact workspace bytes after three reads and zero writes. The
headless V1 control refuses the navigation document and clears its frame.

```sh
python3 -B compiler/experiments/fieldlog-change-corpus/pending-queue/replay-headless-v81.py
```

The runner uses the pinned v81 Mixer and FieldLog source. Use `--fieldlog`
to supply a local Git checkout containing the pinned FieldLog history.
[Headless V3 replay](../../../verification/receipts/fieldlog-f10-historical-queue-v81-feature-ui-v3-review-fix.json)

The private signed V3 replay on `dda816101e` builds a development guest
against the exact installed VM and runs it on macOS. It hydrates the first
page through one scoped read, delivers the queue action, and displays the
historical navigation and list with 20 pending rows. Durable health requires
the observed actionable frame. The replay leaves the workspace bytes
unchanged.
[Private replay recipe](../../../capability-activation/verification/private-fieldlog-f10/README.md) ·
[Signed V3 receipt](../../../verification/receipts/fieldlog-f10-v3-root-dda81610.json)

The private Android witness on tree `6c5bc8ca` ran the six actions
from the Pending Changes opening tap through Entries. API 36 readback
matched the historical workspace bytes and all 26 rows across both
pages. The observed first-page frame earned durable health after the
opening tap, and the owner retired. A successor with all 12 required
notices passed the same journey. Both APKs loaded a locally staged
signed development packet.
[Android navigation](../../../verification/receipts/fieldlog-f10-signed-android-navigation-api36-6c5bc8ca.json) ·
[APK notice successor](../../../verification/receipts/fieldlog-f10-signed-android-notices-api36-6c5bc8ca.json)

The private iOS owner passed the signed six-action route on macOS with
synthetic pages and a host-supplied display acknowledgement. Its
arm64 Simulator test bundle linked. The historical workspace is pinned
for the native follow-up. Installed iOS verification and service
delivery across both targets remain open.
[iOS consumer and build](../../../verification/receipts/fieldlog-f10-ios-simulator-signed-consumer-ecba9fa.json)

## First unsupported case

- **F01 is the earliest source-only gap.** The historical change applies `.scrollDismissesKeyboard(.interactively)` at `ios/FieldLog/EntryEditor.swift:68`. The signed Guest UI V1 route has no corresponding guest operation. No device or signed payload was run for it.
- **F05 is the first executable guest-profile rejection.** The probe encodes the real `70f3aa1` FieldLog task presentation, rooted at `task.screen` / `navigation`. The Guest UI V1 exchange in the later pinned SDK rejects the startup frame as `startup/document` before effects intent, with no admitted revision. That route accepts a supported stack/text control. This is a host protocol test of the real frame, with signing, installation and VM execution outside its scope.
- **F06** independently shows the actual `task.title` field rejected by the ordinary public validator as `UIValidationError.unsupportedTextFieldAxis(.vertical)`. The explicitly vertical-enabled host test preserves multiline Unicode input. The V1 startup route also rejects the full F06 frame.
- **F13** runs the exact 100,000-byte submission through the pinned V4 Android application on macOS. The same integration explicitly refuses V3 app admission with `PublicHostError.profile`, before activation or a workspace write.

Existing signed FieldLog proof uses separately prepared compact task variants. It cannot be mapped to a historical before/after pair in this corpus. R6060 recorded artifact size and owner mismatches for a different full guest pair. This replay does not reuse either pair or touch the L04 inspector or L08 draft-schema lane.

## Private signed F05 host

The [signed editor replay](signed-editor/replay.py) starts from the exact historical F05 capture. It verifies an ephemeral Ed25519 release manifest and assignment with Mixer’s v3 verifier, then opens the authenticated guest in the owned ABI2 VM. The editor profile uses the existing FeatureDocumentV3 and text event codecs within the ABI2 control header and bounds. Its opt-in exchange is patched into a private SDK projection. The profile fingerprint binds that projection and host code to the local trust root.

The editor fixture is written in C and embeds the historical Swift UI frame. The guest handles text changes, cancel, and Save. Save sends one scoped capability request to the historical FieldLog WorkspaceRepository. The host selects the project and validates the submitted fields. The guest leaves the editor after the repository acknowledges the commit. The multiline control adds the later vertical axis property to the historical title field and exercises a Unicode newline round trip through that same repository.

The host opens the verified payload directly. Selecting this profile from the installed signed recovery store and mounting it through the FieldLog UI remain unverified. The host receipts do not change the two-target OTA counts or qualify F06’s Apple field renderer.

A separate unsigned Embedded Swift replay compiles the historical F05 and F06
title reduction and compares Edit, Cancel, and one short-title Save in the
owned VM. The host commits the title emitted by the guest and checks the
task and its linked outbox entry on disk after reopening the repository.
Signed installation of that Swift guest remains open.
[Compact Swift editor replay](../fieldlog-embedded-editor/README.md)

```sh
python3 compiler/experiments/fieldlog-change-corpus/signed-editor/replay.py \
  --output /path/to/fresh-private-output \
  --fieldlog /path/to/local/fieldlog \
  --frame /path/to/corpus-output/f05-frame.json
```

Use the existing Swift 6.3.3 guest toolchain, macOS Swift, Rust, and local SwiftPM repositories for the SDK's pinned Swift Crypto and Swift ASN.1 revisions. The replay reads the frame and Git objects locally, uses file-scoped source projections, and writes the command and source digests to its private receipt.

## Executed scope

The replay runs the original FieldLog tests for the initial shared task reducer (`d51adf5`), shared presentation (`70f3aa1`), ordinary pinned app, and pinned GeneratedReport integration. It uses the exact public SDK revision declared by each package. The private ordinary snapshots change the SwiftPM dependency locator and append the probe target after the normal tests. All production sources and original test sources come from Git archives. GeneratedReport uses the documented `FIELDLOG_MIXER_SDK` input. Its Android tests execute actual Swift presentation and local disk behavior on macOS, sometimes through an app-owned C entry with a test surface. Java tests use FieldLog's exact nested Java helper extraction and the real JVM. They do not invoke Android's provider, Activity, launcher, picker or chooser.

The broad `70f3aa1` suite fails one original repository assertion. It expects `"Rae"` but disk preserves `"  Rae  "`. The two designated F05 controls pass. The pinned ordinary suite passes with the updated expectation. Preserve the earlier failure in the receipt.

## Replay

Use a fresh private output directory, the FieldLog repository with the pinned ancestry, a local Mixer repository with the SDK objects in the manifest, Swift 6.4.2 on macOS, Python 3.12+ and a JDK. FieldLog can be fetched read-only with a no-checkout clone. The runner needs no live service, payment credentials, device or remote write.

```sh
python3 replay.py \
  --fieldlog /path/to/fieldlog \
  --mixer /path/to/mixer \
  --jdk /path/to/jdk/Contents/Home \
  --output /path/to/new-private-output
```

The output contains the verified source excerpts, exact test commands, tool versions, observed scratch sizes, Swift and JVM logs, the captured F05 frame and a structured receipt. Exit 1 preserves and surfaces the historical whole-suite failure even when every selected control passes. Review the named controls, the first guest-profile refusal and the receipt scope before using the evidence for a gate.
