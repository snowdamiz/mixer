# FieldLog title and cancel in Embedded Swift

This host replay advances L03 and the F05/F06 editor slice. It runs one unsigned
Embedded Swift guest through the existing Mixer table-memory-v3 session API from
public commit `2acaac67605c369ff1667e3ccc3eb56d376e536e`. The replay passes the
VM's default limits and the module declares a maximum of 64 memory pages.

The host compiles the original F05 and F06 `TaskEditor` and
`TaskEditorPresentation` with each release's pinned MixerCore and MixerUI.
It takes the title and Cancel node generations from the original presentations.
The Foundation-free editor compiles the historical title reducer case extracted
from the verified Git blob. Extraction changes the state receiver to `self` and
the empty-effect return to a void return. The same extracted code and boundary
run in native Swift and as the guest. The boundary projects historical revision,
generation and event checks, publication and cancellation onto just the title
and Cancel controls.

For every turn, the harness compares the reply, revision, outcome, route count
and title UTF-8 against the untouched historical presentation. It compares the
published snapshot title with the document value on each turn. Cancel
verifies the latest reducer spelling. The harness verifies that rejected
actions leave the original serialized document
and projected state unchanged. The F06 oracle confirms the historical title
has the vertical axis and delivers the multiline edit through its shared
presentation.

## Observed results

The 86,887-byte guest declares zero imports, two initial memory pages and a
64-page maximum. All 12 turns matched in each historical version. The peak
invocation cost for those turns was 23,467 fuel. The Unicode edit includes
a newline, a combining accent and an emoji sequence. A canonically equivalent
follow-up leaves the document and revision unchanged. Cancel clears the route
and publishes the latest reducer spelling, including its exact UTF-8 bytes.
The injected save closure traps if called. Both sessions closed and their old
handles were refused.

The untouched editor fails Embedded Swift compilation at `import Foundation`.
The isolated 12,288-byte decomposed edit passed and used 595,832 fuel to send.
Submitting its 8,192-byte canonically equivalent spelling succeeded in both
historical host editors. The guest hit `fuel_exhausted` at 1,000,000 and the VM
refused subsequent access to that session. This bounds the projection's
coverage even for input below the SDK's 16,384-byte limit.

The evidence covers local reducer state and the title event path. Full
document exchange, Save, signed installation, and F06's platform renderer
remain unqualified. L03 and L08 remain open.

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
