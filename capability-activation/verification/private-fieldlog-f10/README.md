# Signed FieldLog F10 smoke on macOS

The trusted test embedding opens the normal installed attempt with a headless
presenter and the selected FieldLog repository. The private debug build admits
a development macOS identity with UI schema 3, the exact wire and header
dependencies in this directory, and the two existing startup milestones.
The development signer pins the actual capability VM archive in the identity
and binds the signed manifests and assignments to that runtime fingerprint.

The attempt stages and consumes the signed Wasm through the existing durable
store. The capability VM validates exact start, event, and ready exports and
admits only storage get and poll imports. A single V3 exchange binds that VM to
the presenter. It completes the inert loading document before recording durable
effects intent. After native enable, the first ready turn requests only
`material_test/queue-0`. Mailbox completion drives the next ready turn. The
guest then decodes the real `workspace.queue` event and renders page one with
the same queue projection used in the causal headless proof.

Use Python 3.12+, Xcode, the Swift 6.3.3 Wasm toolchain, and Cargo with the local
locked dependencies. Run this from a checkout of the draft revision.

```sh
python3 -B capability-activation/verification/private-fieldlog-f10/replay.py \
  --revision "$(git rev-parse HEAD)" \
  --cargo /absolute/path/to/cargo \
  --guest-tools /absolute/path/to/swift-6.3.3.xctoolchain/usr/bin
```

The runner compiles the checked-in `Guest.swift` with the pinned Mixer queue
projection and C import shim. It compiles the exact two FieldLog source blobs
from the pinned repository in an isolated source projection. The smoke asserts
the three revisions, generation and delivery, the historical navigation, list
and sections, the first 20 IDs and exact UTF-8 labels, one scoped read, zero
writes, byte-exact workspace reopen, stale input, and completion of installed
attempt retirement. A signed schema-1 document with a valid MUI3 header stops
before effects. The replay also checks mixed identity refusal and runs the
existing signed V1 and W09 regressions with the private profile enabled and
disabled.

The scope is a local headless smoke for the opening action and first page.
The fixture uses an in-memory development signing key and a temporary disk
workspace. The runner removes its scratch after terminal process-group
observations and records the exact path if custody is unresolved.
