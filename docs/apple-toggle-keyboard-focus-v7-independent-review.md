# V7 Settings keyboard preparation: independent review

The sealed V7 preparation is **not accepted for native selection**. Three fresh
synthetic host probes reproduce persistence/acknowledgement failures in its actual
Bridge/Session path. Root has confirmed these as blockers and will select a fresh
repair packet. V7 remains immutable. This review did not execute native code,
query an instance, capture a screen, change Settings, or run an application case.

The exact producer seal is
`1332308b51182f2ead68a774f135bc3121e00b7385cbd0337395a90d53175579` (90 files), selected
by root's
`a56b15d641c3dd71fcb7e3472b19c5b8156736091c9fea905c07f6ba1ea8b6da` receipt.
`review-inputs.json` binds 782 deduplicated source, packet, historical, installed
header and canonical tool files. The official `swiftc` symlink is separately
bound to its exact `swift-frontend` target. The producer seal and every input
were checked again before sealing this review.

1. **P1 — A rejected action remains an accepted replay record.** The actual
   `diagnostic_bridge.persist` calls `Bridge.save`, which creates and fsyncs the
   final journal name, before fsyncing its directory
   (`settings_telemetry.py:401-407`). A one-shot injected failure of that actual
   directory `os.fsync` occurs after the probe verifies the switch-action record
   already exists with the exact request bytes. The request raises `OSError`;
   the Session cursor stays at 19, but the journal contains sequence 20. Actual
   offline replay advances to sequence 20 and credits `switchAction="tap"`.
   Retrying sequence 20 raises `Evidence file already exists`. The draft copy
   rolls back memory, but it cannot undo this committed filename. Persist and
   replay need one unambiguous protocol commit boundary, including the failure
   after file creation/directory fsync. Do not let replay credit a request the
   protocol rejected without an explicit recovery/commit decision.
2. **P2 — A rejected final upload leaves a file that prevents completion.**
   `Session._request` persists the assembled payload before its chunk journal
   (`settings_telemetry.py:240`, then the common request journal). When that
   journal save fails before writing, cursor 17, pending upload state, and journal
   prefix remain unchanged and replay agrees. The completed AX file nevertheless
   survives. The same chunk's retry raises `Fixed fresh telemetry artifact` at
   line 391. Coordinate payload publication with request persistence, or support
   an exact, verified orphan recovery rule; do not treat an orphan as an accepted
   upload. The probe retains the payload bytes and hashes.
3. **P2 — Ancillary summary failure turns a committed request into HTTP 400.**
   The inherited `Bridge.request` calls `persist_summary` after
   `Session.request` has committed (`bridge.py:118-120`). The independent real
   loopback HTTP probe injects that summary failure and receives HTTP 400 with
   `OSError: independent postcommit summary failure`, while cursor/action and the
   protocol journal have advanced from 19 to 20. Replay also returns sequence 20.
   This is distinct from finding 1: the protocol record committed successfully
   and replay agrees; an ancillary summary error replaces the success ACK. Define
   and preserve the committed protocol outcome when reporting summary failures,
   so the client does not see a rejection after its action mark was accepted.

The three probes are in `persistence-probes.json`, with before/after cursors,
journal hashes, exact exception/HTTP outcomes, replay summaries, and retry results.
They use the actual sealed Session, actual inherited Bridge and actual replay;
their requests cross a JSON ownership boundary. They are synthetic host
evidence. The partial flows do not produce a setup pass, and no false native or
GA qualification is claimed.

The bounded target repair otherwise matches root selection. The adapter publicly
queries the exact identified/labeled parent, counts it before resolving an index,
queries the unique immediate switch child, rejects nested switches, snapshots
both handles, and validates the exact before/action binding. Its sole conditional
switch input is
`actionTarget.leaf.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()`.
The unchanged initial-on branch performs no input. Host count fields reject
Booleans, metadata/value/flags and geometry fail closed, and fresh action snapshots
follow before-capture completion. Every subsequent bound switch capture follows
the same action completion. The initial-off anchor is that completion; initial-on
uses the original observation. A second marker cannot extend the three seconds.

The V6 failure was a composite-center tap at `(201,160.3333282470703)` outside the
leaf. V7's synthetic observed-layout control keeps the leaf's two-point extension
beyond its parent and selects `(336.5,160.3333282470703)`, strictly inside parent,
leaf and screen. Installed official declarations confirm the query/coordinate
APIs; `debugDescription` is uploaded only as evidence. Public coordinates are
dynamic, so only a future selected official event export can establish where a
real tap landed. Host providers do not execute XCUI dispatch.

Fresh corrected controls pass 13 actual Bridge/Session/replay methods and 61
independent controls compiled with the exact native Swift resolver. They cover
closed integer counts, ambiguous/missing/nonleaf query handles, identity/state/raw
values, strict geometry and neighboring floating-point boundaries, fresh binding,
initial states, single-action enforcement, the original deadline, actual HTTP
rejections, prewrite journal failure rollback and replay. The compiled independent
Swift witness is decoded by the real Python validator. The unchanged transport
binaries pass 16 and 35 existing checks. These counts exclude the three reproduced
defects and all review-policy models.

An independent byte inventory verifies all 69 runner product entries against the
retained archive and product-tree manifest, as well as six tool files and six
installed official headers. The recorded official `build-for-testing` command
succeeded with a generic iOS Simulator destination, arm64 and signing disabled;
its log compiles the actual adapter and resolver. Fresh `vtool` and `lipo` commands
confirm simulator/arm64 binaries. Runner source context remains
`c628863f7dc3dc3b694d2949be6176a311cce04c`, source digest
`e0fbb631305e7ec73c52c1d40a950e8b5392da78e53edc046c6459a2e646eaa7`, product-tree digest
`004235a284df48a38a7d0a074237a44c603f4eb32bfc0bb063fb94b6e2385835`, and archive digest
`d576682db91277803aa1728c0a8b13e6e66a5a5e278b46ee24e7be8abc60333b`.
Compilation is not simulator-runtime proof.

All 37 immutable app/oracle/transport copy bindings match. App source closure
`f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46` and archive
`b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393` are unchanged.
The independent frozen V6 replay reconstructs all 275 records and exactly matches
its failed runtime summary. Replacing only the route predicate in memory credits
routes `[0,1,2]`; enabled/setup remain false. Its saved files remain byte-exact.

The 29-second diagnostic, two-second requests, 600-second session, 2,500 requests,
100 events, 32 uploads, 7,000,000 decoded bytes, 3,072-byte chunks, 40 polls, route
attempts and per-payload bounds remain unchanged in the reviewed source. The
first setup error is rethrown after best-effort terminal evidence, transport latches
its first failure, and inherited all-outcome cleanup attempts independent server,
thread, ephemeral workspace and owned-instance reconciliation. This review audited
that cleanup source; it did not claim a new native cleanup receipt.

Failed review attempts are retained. Attempt 1's independent emitter timestamped
the destination after capture completion; attempt 2 used an unaccepted synthetic
Accessibility container identifier. Correcting those fixtures produced attempt 3's
passing controls without changing producer code. A later inventory attempt rejected
the official compiler symlink under an overly strict regular-file-only rule;
the final pass separately binds the link and canonical tool. `attempt-notes.json`
also records the initial shell-glob lookup error. No failed check is counted as a
pass. All synthetic journal/payload bytes, including these failed attempts, are
retained in `host-evidence.tar.gz` and its per-file manifest. Only exact owned host
compiler scratch and the verified archived synthetic working tree were removed;
no other project data/process was touched.

All six application keyboard cases remain unrun. Physical phones remain
disconnected and deferred. Native keyboard qualification, carrier acceptance and
GA remain false. Root must select and independently review a fresh persistence
repair before any setup-only runtime selection.

Read-only review seal verification:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v7-independent-review/seal_review.py check
```
