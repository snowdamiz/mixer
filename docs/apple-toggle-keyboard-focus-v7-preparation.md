# V7 public Settings switch leaf preparation

Root selection `verification/apple-toggle-keyboard-focus-v6-root-review/v7-preparation-selection.json`
(SHA-256 `a56b15d641c3dd71fcb7e3472b19c5b8156736091c9fea905c07f6ba1ea8b6da`)
selects this implementation and official compilation. Native execution is not
selected. The selected analysis's 17 sealed files and 660 exact inputs are
rechecked, with 679 deduplicated historical bindings retained in
`immutable-reuse.json`. Earlier preparation, review and failed runtime packets
remain unchanged.

The native helper resolves exactly one public `settings.switches` query matching
both identifier `FKAEnabledSwitch` and label `Full Keyboard Access`. It requires
exactly one immediate `children(matching: .switch)` handle, zero switch children
and zero switch descendants under that leaf. It reads public parent/leaf
identity, type, foreground/app state, existence, enabled/hittable flags, raw string
value, frame and observation time. Parent and leaf must agree on `"0"` or `"1"`;
the leaf is exactly unlabeled/unidentified under its bound parent. Missing,
ambiguous, nested, stale or invalid targets fail before switch input.

Positive parent/leaf overlap and a leaf center strictly inside both frames and
the actual Settings application frame are required. There is no edge tolerance.
The synthetic observed-layout fixture deliberately retains the leaf's two-point
right extension beyond the parent; its center remains strictly inside both.
The action is the public
`resolved.leaf.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()`.
`official/manifest.json` binds installed XCUIAutomation declarations, including
`XCUICoordinate.h`. `debugDescription` remains an AX evidence upload and never
selects or authorizes input. A future official event export must still confirm
that the actual tap falls inside the bound leaf.

Every switch observation binds the public relation, integer parent/leaf/nested
query counts, fresh leaf snapshot, screen frame and chosen center alongside the
parent snapshot. The host rejects Boolean counts. Before the conditional action,
the native resolver re-queries and snapshots both handles, then validates their
identity/state/geometry against the exact before capture. The action mark carries
that before sequence, fresh snapshots/witness and start/completion timestamps.
The actual Session independently requires capture completion <= fresh parent <=
fresh leaf <= action start <= completion <= marker time, exact metadata binding,
and subsequent capture start >= that same action completion. Validation and
selected persistence failures retain the prior accepted cursor, clocks, counters,
bindings and durable journal. Offline replay uses the same verifier.

Initial off performs one conditional coordinate tap and anchors the unchanged
three-second window at completion. Initial on performs no tap and retains the
initial parent observation as its anchor; its no-action start/completion must be
equal. No marker can reset or extend that window. Query resolution does not add
a retry, route or observation budget. Route 2 additionally accepts only the exact
descendant container labels `Full Keyboard Access, Off` and
`Full Keyboard Access, On`, with identifier `FULL_KEYBOARD_ACCESS`. Existing
route target, descendant geometry, search/tap metadata, same-route sequence and
completion-to-capture checks are retained.

Fresh host evidence runs 21 methods through the actual V7 Session, real Bridge
and offline replay, plus 71 controls compiled from the exact native resolver with
a recording query provider. The controls cover parent/leaf absence and ambiguity,
integer-vs-Boolean counts, wrong metadata/state/raw values, nested nonleaves,
zero/disjoint/edge/screen geometry, fresh/stale binding, equal and adjacent timing
boundaries, initial off/on, single-action enforcement, strict window boundaries,
actual HTTP rejection, transactional rollback, selected journal persistence
failure, malformed replay and exact route suffix restrictions. The compiled
Swift witness is also decoded and accepted by the actual Python validator.
The unchanged transport binaries pass their existing 16 and 35 checks. The
analysis's 37 review-policy controls are not counted as implementation tests.
All host AX/PNG/input fixtures remain synthetic.

The frozen V6 journal replays all 275 exact records and exactly matches its failed
runtime summary. Applying only the corrected route predicate credits all three
routes, while enabled evidence and setup remain false. That in-memory historical
control does not mutate the saved V6 packet. `attempt-notes.json` discloses the
unpromoted fixture and default compiler-target attempts.

The official new generic iOS Simulator `build-for-testing` succeeded with Xcode
26.6 / Swift 6.3.3, SDK 26.5, arm64, and signing disabled. It compiled the real
XCUI adapter and public query/coordinate APIs. The fresh build's source revision
context is `c628863f7dc3dc3b694d2949be6176a311cce04c`; the exact harness source digest is
`e0fbb631305e7ec73c52c1d40a950e8b5392da78e53edc046c6459a2e646eaa7`, product tree
`004235a284df48a38a7d0a074237a44c603f4eb32bfc0bb063fb94b6e2385835`, and runner archive
`d576682db91277803aa1728c0a8b13e6e66a5a5e278b46ee24e7be8abc60333b`.
The command log and `vtool`/`lipo` binary receipts bind sources, official tools,
architecture, simulator platform, product tree and archive. This is compilation
and host execution, not an XCUI or simulator-runtime result.

App source closure remains
`f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46`;
app archive remains
`b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393`.
The app, strict oracle and shared Swift transport are byte-exact copies. The
request/event/upload/payload bounds, 29-second diagnostic, two-second request,
600-second session, 2,500 requests, 100 events, 32 upload slots, 7,000,000 decoded
bytes, 3,072-byte chunks, 40 polls, route attempts and per-payload limits remain
unchanged. No app case was added or executed.

Only exact owned build/host scratch paths were removed after evidence collection;
`cleanup.json` records 73322860 bytes removed and proves retained
runner products unchanged. No native instance was created or queried. No UI,
screen capture, simulator runtime, physical phone, setting change, publication,
product tracker or Git mutation occurred in this lane. Physical phones remain
disconnected and deferred; other projects' processes/data were untouched.

This packet stops sealed for independent/root review. All six application
keyboard cases remain unrun. Native keyboard qualification, carrier acceptance
and GA remain false. A separately selected setup-only runtime must verify the
actual event and enabled parent metadata within the unchanged window, then
complete all-outcome owned-instance cleanup before any broader claim.

Read-only sealed verification:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v7-preparation/run.py verify
```
