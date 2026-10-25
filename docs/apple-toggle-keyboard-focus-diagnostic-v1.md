# Apple keyboard focus diagnostic V1: source preparation only

This derivative prepares observation code for the unresolved V3 first-Tab
failure. It makes no focus repair and grants no native acceptance. The sealed
toggle-to-null witness still has exactly one false predicate,
`actualNativeFocusTraversal`. The destination remains unknown until a later
reviewed native run observes it.

The deliverable is a 19,426-byte unified patch, a deterministic preparation
generator, and 17 passing host controls. It references eleven existing files by
SHA-256 and adds only one small Python support module to the proposed source
overlay. It copies no build products, runtime tree, prior evidence directory,
or package. The six prepared source files exist only as patch text and in-memory
test values. The original V3 sources and evidence are read only.

## Prepared observations

The controller and carrier call `super.didUpdateFocus` and record the public
`UIFocusUpdateContext` previous/next endpoints, focus heading, and process uptime.
Each non-null endpoint records its class, object identity, public accessibility
identifier, frame, and, for a `UIView`, window attachment and frame in window.
An explicit null endpoint has `state: "null"` and null metadata. An item with no
identifier has `state: "item"`; an outside-ID destination remains distinguishable
from an absent destination. Non-view attachment metadata is explicitly null.

These records use a separate 128-entry trace with its own revision and dropped
count. They never consume or renumber the original `diagnosticTrace`. The existing
app persistence timer also notices that new trace's revision and retains
`focusContexts`, `focusContextDropped`, and `focusContextRevision` in
`observations.json`, already captured through the bridge side channel. The hooks
make no focus requests, redirects, vetoes, or input substitutions.

XCTest keeps the canonical three-ID witness shape. It records each full AX row's
start/end interval separately, including that row's existing wait and sequential
property reads. The collection is explicitly non-atomic; its original end
timestamp is retained as `witnessUptime`. Up to four collection timing records per
action are retained, followed by an exact dropped count. No per-row timing is
inserted into the closed oracle payload.

After the original witness is fixed, XCTest makes at most one additional pass
over the same three IDs, reading only `hasFocus`. It waits and retries zero times.
Its deadline is the earlier of 250 ms after the pass starts or the original
witness's 12-second window end. A synchronous public XCUI read cannot be
preempted: if one returns after that deadline, the result is explicitly
`incomplete-budget` and no further row is queried. This is a bounded call count
and admission deadline, not a proven hard wall-clock ceiling. The existing
action, method, bridge, and command timeouts are not increased.

The test sends timing and follow-up data alongside the original witness in the
existing `/evaluate` request. Its diagnostic part is capped at 4,096 bytes; an
oversize record becomes a small incomplete marker. The existing 8,192-byte
request-body limit remains unchanged. The prepared bridge saves this record as
`focus-diagnostic-<actionIndex>`, strips it, and enters the byte-identical original
`keyboardWitness` branch with the same witness object. Invalid diagnostic
envelopes produce incomplete receipts. A storage failure propagates; it cannot
manufacture a passing result. Both app context records and XCTest diagnostics
therefore survive through the existing host side channel independently of
xcresult attachment export.

The original first acquisition Tab, strict fixed membership, key API calls,
semantic phases, failed-cursor branch, and completion guard remain unchanged.
The diagnostic sample cannot replace `after`, choose a favorable sample, advance
the cursor, or grant any acceptance. Additional observation can affect runtime
timing; this lane establishes source isolation and host behavior, not native
noninterference.

## Reproduce the preparation and controls

From the repository root:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-toggle-keyboard-focus-diagnostic-v1/run_host_controls.py
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-toggle-keyboard-focus-diagnostic-v1/prepare.py --check
```

The first command writes only this verification directory. It regenerates
`source.patch` and `prepared.json`, runs local controls, and records the command,
Python version, source digests, individual tests, stdout/stderr, and explicit
limitations in `receipt.json`. The second command checks retained generated
artifacts against the current digest-bound inputs without rewriting them.

Observed result: **17 tests passed, zero failures/errors/skips**, under Python
3.14.8. Controls cover the retained failed JSON decision, the independent limited
three-ID traversal predicate, a pre-focused launch's unchanged first Tab,
favorable diagnostic data that cannot alter the opaque retained failed decision,
no cursor advancement and next-begin refusal, explicit null/outside-ID/anonymous
endpoints, 128-entry truncation with eleven dropped records, sequential row
intervals, one follow-up pass, expired and overrun budgets, invalid/oversize
diagnostics, persistence failure, and exact in-memory application of every
generated patch hunk.

The cursor/decision control is a local test double fed the retained failed
verdict as data. It does **not** reexecute the original keyboard oracle, bridge,
authority driver, composition, or selected runtime. The independent predicate
model covers only fixed-ID traversal. Source restoration controls additionally
prove that removing the two observational bridge insertions recovers its bound
original bytes, and that the original `acquire()`/semantic methods remain
byte-identical. These are host preparation controls, not compiler or platform
receipts.

## Source binding

The original execution seal remains
`7baff6c525359b0647caa2808d0fa73b7d1e8cc54146408d904570eabd80e3b7`.
`prepared.json` and `receipt.json` retain all eleven exact input paths, hashes,
and byte counts, including both unchanged oracle sources, the failed witness,
its retained after/verdict packet, and the accepted failure analysis/review.
The review revision `ba9ad4372f94463ba4d363cdfd76dd565c96413f` is an inherited
label; no Git command was run in this lane.

| Prepared source path in overlay | SHA-256 |
| --- | --- |
| `source/Prototype/DiagnosticTrace.swift` | `9dbd3eff88f0df0ecb34c2024f005b6be27568cbc75b8ee00c8202870937d4fa` |
| `source/Prototype/main.swift` | `a47094a2ce18806ca27cc3a3ea4964bfb5ba2fc00ddd70516bcf8923bcbd965f` |
| `source/Prototype/AuthoredToggleCarrier.swift` | `b688ba48eb6aaf19e7b72b2bc1f46ef802883a05ee378b4cb54b52c79656b0ef` |
| `harness/UITests/ToggleUITests.swift` | `2e5bd5d9c22ab9d1b074898444635bf43ef046b23d8a156e9352faf3ffb9d9c6` |
| `runtime/verification/apple-toggle-keyboard-focus/keyboard_bridge.py` | `d7316ed9e904d2cf8ec142bccab5ede06c495f8a0cb9817b358d29deb3d62a68` |
| `runtime/verification/apple-toggle-keyboard-focus/focus_diagnostic.py` | `370c6437b410a356364035ce0a0147a6e044587d39c61246b62f6d6e0a0e75fd` |

The input tree digest is
`a1b254cd94628cc63fcf086dcb80310bf166877c46f39c2af1cefa9c75577fb2`.
The prepared source tree digest is
`91e86b048aa920917e1882f062ef32cea278e23a4529b973e75179c27e819969`.
The patch digest is
`5d86c026f5356491a0e759552144f8e50304bece3eb17a266837b37022216adb`.
Tree digests use SHA-256 over sorted, indented JSON descriptors with a trailing
newline, as implemented in `prepare.py`. They do not seal an executable packet.

## Pending work and limits

Command-runner finalization is intentionally a separate pending slice. It still
needs incremental output timestamps, owned process/pipe-EOF state, and one
bounded post-suite diagnostic capture while preserving the existing 600-second
ceiling and cleanup. No command-runner file is patched here, and no mocked
finalization claim is attached to these 17 controls.

No compiler, build, native runtime, simulator/emulator, process/device query,
network/server, UI, capture, signing, store, or physical-phone operation was run.
Swift type checking and public API behavior remain unverified. Phones remain
disconnected and deferred. Carrier, OTA, immutable published-package dogfood,
store, operational, and GA gates remain pending.

Root independently reviews this source preparation before selecting any later
integration/build/native work. Existing user authorization for simulator
development remains valid; this internal review is not a new permission request.
The later minimal native selection remains one owned simulator lifecycle with
`test000PublicSettingsFullKeyboardAccess` and `test010EnabledFromOff`, preserving
first-Tab behavior and stopping at that first case's failure. No selected runtime
or execution packet is created by this preparation.
