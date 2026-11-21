# Replay FieldLog Edit, Cancel, and Save in Embedded Swift

This host replay advances L03 and the F05/F06 editor slice. It runs one unsigned
Embedded Swift guest through the existing Mixer table-memory-v3 session API from
public commit `2acaac67605c369ff1667e3ccc3eb56d376e536e`. The replay passes the
VM's default limits and the module declares a maximum of 64 memory pages.

The host compiles the original F05 and F06 `TaskEditor` and
`TaskEditorPresentation` with each release's pinned MixerCore and MixerUI.
It takes the Title, Cancel, and Save node generations from the historical
presentations. The guest compiles the title reducer and the successful Save
state transitions extracted from the pinned editor. The Save projection
admits an unpadded printable ASCII title up to 240 bytes with an empty
responsibility label. The original editor keeps its full validation.

For every turn, the harness compares the reply, revision, outcome, route count
and title UTF-8 against the untouched historical presentation. It compares the
published snapshot title with the document value on each turn. Cancel
verifies the latest reducer spelling. The harness verifies that rejected
actions leave the original serialized document
and projected state unchanged. The F06 oracle confirms the historical title
has the vertical axis and delivers the multiline edit through its shared
presentation.

## Observed results

The 92,501-byte guest declares zero imports, two initial memory pages and a
64-page maximum. The 12 Edit and Cancel turns matched the prior trace in
both releases. The peak invocation cost for those turns was 23,478 fuel.
The Unicode edit includes a newline, a combining accent and an emoji sequence. A canonically equivalent
follow-up leaves the document and revision unchanged. Cancel clears the route
and publishes the latest reducer spelling, including its exact UTF-8 bytes.
The Edit and Cancel replay uses a save closure that traps if called.

The Save replay submits `Inspect pump P-17` through the historical
presentation's **Add** action and the guest's Save action. Both publish
the saving state at revision 3 and the saved outcome with an empty route
stack at revision 4. The Save action used 13,255 fuel in each guest session.

The owner consumes one typed guest request and calls the pinned
`WorkspaceRepository.transact` with `Workspace.saveTask`. An owner success
completes the guest Save. Each leg closes its repository and opens a fresh
repository on the same directory in the same process. The reopened task and
its linked `taskSaved` outbox record match across legs, with one repository
revision added per Save. The VM refused access through each retired handle.

The untouched editor still fails Embedded Swift compilation at
`import Foundation`. The prior receipt records the separate
`fuel_exhausted` result for the long canonically equivalent edit. The current
replay covers unsigned host sessions and synthetic local data. Full document
exchange, failed Save outcomes, signed installation, and F06's platform
renderer remain unqualified. L03 and L08 remain open.
[Edit and Cancel receipt](../../../verification/receipts/fieldlog-f05-f06-embedded-editor-2acaac67.json) and
[Save and cold readback receipt](../../../verification/receipts/fieldlog-f05-embedded-editor-save-2acaac67.json).

## Replay

Use macOS, Python 3.12 or later, the Swift 6.3.3 guest toolchain and its WASI
SDK, a matching Xcode host Swift compiler and SDK, and Rust. Run from the
Mixer checkout with the pinned Git objects available.

```sh
python3 -B compiler/experiments/fieldlog-embedded-editor/replay.py \
  --swift-toolchain /path/to/swift-6.3.3.xctoolchain/usr \
  --wasm-sdk /path/to/wasm32-unknown-wasip1 \
  --rustc /path/to/rustc \
  --receipt /path/to/new-receipt.json
```

The replay clones public FieldLog into a temporary directory unless
`--fieldlog` points to an existing checkout with the pinned objects. It builds
the VM and both oracles from Git objects, verifies the exact historical
sources, and removes the temporary directory after observing command exit and
process-group absence.
