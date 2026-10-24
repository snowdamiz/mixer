# Private keyboard V3: independent source and host review

Status: **CHANGES_REQUIRED_DIAGNOSTIC_CONTRACT**. The selected preparation is not
ready for this reviewer to recommend the next native diagnostic. Three executable
adversarial cases expose misleading setup/route/timing evidence. They do not
escape the diagnostic boundary: native keyboard qualification, carrier acceptance,
`runPassed`, and GA remain false throughout.

The review covers only preparation seal
`85534f657be3e1a0bda34fe830dc29636065eb602401b4386b3076c35a108c21`
and root selection
`703d2c5db1e79b8eaf4b17fba95bd660de598cf575ed861b08b6c70115bdeb28`.
It reads the repository instructions and selected source. It changes only this
document and `verification/apple-toggle-keyboard-focus-v3-independent-review/`.
There were no Git operations, compiler invocations, UI/computer-use operations,
screen captures, native commands, simulator/emulator queries or runs, physical
device queries, live integration, or tracker edits. No native or GA authorization
is issued here.

## Findings requiring a new preparation

1. **V3-IR-01, P2 — validate switch metadata for every enabled-window sample.**
   At `settings_telemetry.py:201`, `enabled_samples` accepts a timely String `1`
   without checking the observed target's identifier, label, type, existence,
   foreground or enabled state. Lines 257–261 check expected metadata only for
   before/after/terminal. The real adapter therefore accepts an after-switch `0`,
   an in-window `1` from `OtherSwitch`, then the expected switch's terminal `1`
   after the deadline as `setupObservationSatisfied: true`. Wrong element type and
   background/nonforeground state also reproduce this. Preserve invalid samples
   as diagnostic evidence, but require the expected stable foreground switch
   metadata before a sample can satisfy the three-second window.

2. **V3-IR-02, P2 — bind selected route success to the row observed before tap.**
   At `settings_telemetry.py:179` and `:222`, route indices, attempts and marker
   order are checked, but the tappable route-search witness is not bound to the
   selected public row. Replacing all three search identifiers and labels with
   `Unselected public row` still yields a successful setup observation. The
   frozen Swift caller itself uses the intended labels; the host verifier does
   not establish that route from the journal. Validate the successful
   route-search/tap witness against the fixed row contract. Keep absent/failed
   searches as failure evidence. A `route-opened` snapshot may legitimately show
   the old selector absent after navigation; this finding does not require the
   old row to remain present on the new page.

3. **V3-IR-03, P2 — reject regressing persisted host receipt times.**
   At `settings_telemetry.py:132`, `host - start_host <= 29` permits negative
   elapsed time and there is no last-host-receipt check. `replay.py:27` uses each
   saved receipt time as that clock. Changing a complete synthetic journal's
   sequence-one receipt from `100.001` to `99`, after start at `100`, is accepted
   by actual replay and returns successful setup evidence. Track the accepted
   host cursor transactionally and reject first/later regressions. The running
   host uses `time.monotonic`; this is a persisted-evidence validation defect,
   not an observed reversal of the real clock.

The structured findings are in `findings.json`. `finding-witnesses.json` retains
bounded synthetic summaries, relevant AX metadata, sample times and the replay
mutation. They are explicitly host-generated inputs, never native Settings
evidence. No producer packet was repaired or rewritten.

## Verified boundaries

All 92 preparation seal entries remain byte-exact before and after the review.
The original 81-entry keyboard packet and 70-entry V2 packet also verify. The
frozen application source map hashes to
`f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46`;
its archive remains
`b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393`.
The app archive/source-lock and V2 strict oracle are byte-identical to the V2
copies. The strict oracle hash remains
`feefd59c5796966f68fd9b342f9eae396779cccea4ee74031f6623f203318582`.

Runner sources match the recorded build source closure
`67d819e7e479c026aae99be598647603691fbdb4716e2f396c4c6ebf0268668e`.
All 69 runner archive entries match their types, modes, sizes and hashes; the
archive is
`2bd1c1f9fed7b6248242c3e312a516d02f763c0b02dfb1008ef3c4be318aef1b`,
and product tree is
`e267bb779734cf11c49bd29abbe4f57cb4506db95217c7c1e024d7ad9fb29597`.
Independent Python Mach-O parsing confirms both binaries target platform 7
(iOS Simulator), arm64. The official launcher records minimum 14.0/SDK 26.4;
the compiled XCTest bundle records minimum 26.0/SDK 26.5. Those distinct values
agree with the retained official provenance; no rebuild was performed here.
Read-only producer preflight also verifies installed pinned tool/header hashes.

The Swift runner contains only `test000PublicSettingsFullKeyboardAccess`; scope
selection also lists only that method. The host adapter rejects all app `begin`
requests. All six application cases remain explicitly unrun. The action branch
contains one conditional switch tap for initial String `0`, or no tap for initial
String `1`. The anchor is read immediately after the tap returns, or uses the
initial enabled raw observation. No hardware-keyboard or private-preference
operation is added.

The Swift `snapshot` reads target value before recording `observedUptime`
(`ToggleUITests.swift:110–111`). Its caller checks that time against the existing
absolute deadline after post-action captures and each poll. A slow value query
therefore cannot give a late return an earlier timestamp. Screenshot/AX/upload
latency occurs after the raw observation and cannot reset that deadline. AX
queries, app-state queries and the PNG are not atomic; capture start/end times
preserve that limit. The wrong-target poll finding above concerns metadata,
not a discovered deadline reset in the Swift caller.

The actual capability-authenticated loopback HTTP adapter rejects bodies above
8192 bytes, duplicate JSON keys and an incorrect capability. The closed
`settingsDiagnostic` union is allowed on `/evaluate` before app generation zero
can begin; app begin is rejected outright. Request/chunk/event/upload/total-byte
limits, exact canonical chunk order, digest/length checks, fixed derived slots,
PNG framing checks and session/operation budgets remain present. No supplied
path, selector, target, command or callback obtains authority. Existing 44
producer controls cover malformed counters/times, wrong generation, caps,
duplicate/reordered chunks and stages, bad payloads and persistence failures.

Independent tests use the actual inherited `Bridge.request`, persistence, HTTP
framing and `replay.replay` implementations. Successful ACK preparation observes
file/directory fsync first; capability text does not appear in the durable
captures. Persistence failure does not advance the setup cursor. A complete
failing setup retains all three PNG/AX pairs and replays as diagnostic failure;
a partial upload stays incomplete. Missing chunk records or changed PNG bytes
are rejected. Termination/suite markers alone cannot complete the diagnostic.

The inherited strict XCTest qualification assertion and the full independent
cleanup function remain selected from the frozen original harness. V3 summary
always keeps strict/native/carrier/GA fields false, including with synthetic
complete successful Settings evidence. `diagnosticCompleted` and
`setupEvidenceComplete` describe diagnostic evidence only. The expected inherited
assertion boundary remains distinct from real XCTest failure/timeout. The
producer's export-exception control and independent cleanup test show that
failures do not suppress later independent cleanup attempts. This source/host
review does not establish that future native resource cleanup succeeds.

## Reproduction and results

`receipt.json` contains exact argv/cwd, Python/host versions, complete stdout and
stderr, durations, input digests, source revision context and result counts. The
revision context is the selected `9a9c0e000234b07a92c4484979d3587f7f24df48`,
not a new Git query. Review execution used Python 3.14.8 on arm64 macOS 27.0.1.
The retained build receipt records Xcode 26.6 (17F113) and Swift 6.3.3; these are
provenance inputs, not new compiler invocations.

| Check | Observed result |
| --- | --- |
| Read-only V3 preflight and exact seal/archive checks | Passed |
| Exact sealed producer controls | 44 methods passed |
| Unchanged V2 oracle/adapter controls | 29 methods passed |
| Independent real-adapter controls | 17 methods: 14 passed, 3 contract-finding methods failed |
| Independent failure records | 5, because the poll finding has 3 failing subcases |
| Native, compilation, devices, screen capture | Unperformed |
| Host scratch cleanup | Temporary host fixtures removed; no native resources created |

The producer suite is loaded unmodified by `execute_producer_controls.py`.
Only its mocked exporter's in-memory `BASE` is redirected into review-owned
scratch, so its exception test cannot create or overwrite a producer runtime
receipt. Native command/export execution remains mocked in that test. The V2
suite runs directly and unchanged in a separate Python process.

From the repository root, the direct independent suite intentionally exits 1
while these three contract defects remain:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v3-independent-review/test_independent.py
```

The sealed review can be verified and the exact expected findings reproduced
without changing its receipts:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v3-independent-review/run_review.py --check
```

That orchestrator exits zero only when the producer controls still pass and the
three recorded contract-finding methods still fail as documented. Its status
remains `CHANGES_REQUIRED_DIAGNOSTIC_CONTRACT`; it is not a clean implementation
test pass. A repaired producer needs a separately sealed preparation and fresh
review. Physical phones, actual runtime/cleanup behavior, full keyboard/carrier
qualification, published-package dogfood and GA remain outside this review.
