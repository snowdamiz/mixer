# Private keyboard setup: v3 diagnostic preparation

Root selected this evidence repair in
`verification/apple-toggle-keyboard-focus-v3-root-review/selection.json`, SHA-256
`703d2c5db1e79b8eaf4b17fba95bd660de598cf575ed861b08b6c70115bdeb28`.
The separate runner has been cross-built and host-tested. No native execution or
acceptance occurred in preparation. Every native outcome remains
`DIAGNOSTIC_ONLY`, even if Settings succeeds. The failed v2 result and all earlier
seals are preserved. App, carrier, hardware keyboard configuration, private
preferences, host settings and the strict v2 focus oracle are unchanged.

The bound inputs and extracted timeline are in
`verification/apple-toggle-keyboard-focus-v3-preparation/diagnosis.json`.
The retained command output is copied byte-for-byte into that new directory for
inspection; the original packet is unchanged. Offline verification found all 81
original keyboard seal entries and all 70 v2 seal entries byte-exact. Root's failed
runtime review has SHA-256
`0a90b63443e1ecf5ccf61f1c05ca150382ae753c98cc718489331c6265695ed8`.

## What the retained evidence establishes

The XCTest stdout records the public Accessibility, Keyboards & Typing, and Full
Keyboard Access route taps. At test time 13.50s it records a tap on the
`FKAEnabledSwitch` switch. The frozen runner taps only if the initial String value
is `"0"`, so initial zero is an inference from the source and trace, not a retained
raw AX value. It then fails its final `value == "1"` guard after the fixed three
second poll. The actual poll values, Settings hierarchy and screenshots are
unavailable: their only sink was XCTest attachments.

The failure attachment is logged at 17.37s. `settings.terminate()` starts at 17.47s
and returns before the test fails at 18.804s. All six application methods then
report skipped; their guard precedes app launch and bridge `begin`. The Selected
tests suite finishes failed at local time `2026-10-24 15:17:13.588 -0400`, after
19.113s, with one failure and six skips. There are zero application input actions.

The xcodebuild command remains outstanding until its 600s deadline, then its owned
process group is interrupted. This locates the stall after reported test and
teardown completion. It does not identify an XCTest, testmanager, runner-exit,
attachment, or result-writer stack. The official attachment, summary and tests
exports subsequently return exit 64 because `session.xcresult/Info.plist` is absent.
That observation occurs after forced interruption; it cannot establish that a
previously finalized bundle was corrupt or explain the switch outcome.

The late root screenshot shows Home, after Settings had already been terminated.
It does not recover the switch-page state. The duplicate accessibility class
warning and a possible simulator hardware-keyboard dependency remain unproven
hypotheses. No source/product bug is inferred. All five independent cleanup
operations passed; the owned simulator and ephemeral workspace are absent.

Relevant frozen source locations:

- `verification/apple-toggle-keyboard-focus/harness/UITests/ToggleUITests.swift:50`:
  Settings AX/PNG evidence exists only as XCTest attachments.
- The same file at lines 70, 74, 81, 85, 86, 88 and 97: public setup method,
  deferred Settings termination, switch lookup, single conditional tap, three
  second deadline, enabled-value guard and six-method dependent gate.
- `verification/apple-toggle-pan-origin-correction/harness.py:119`: command waits
  with `communicate(timeout=...)`; output is persisted on completion/interruption.
- The same file at lines 350, 365 and 373: per-test 30/45s allowances, command
  timeout 600s, official export and independent cleanup after failure.
- `verification/apple-toggle-keyboard-focus/run.py:107`: owned attachment export
  already runs in `finally`, including command timeouts. Its placement is correct;
  finalized xcresult availability is the missing durability dependency.

## Selected fixed Settings witness

Use the existing capability-authenticated loopback `/evaluate` route. Add a
setup-only body union in a new dedicated-process bridge adapter, accepted before
the first app `begin` and never interpreted as an application verdict. Do not add
an endpoint or change the inherited 8192-byte framing limit, command grammar,
container paths, observation reader, ordinary empty-body evaluation or cleanup.

The first fixed `setup-start` request returns a host-issued setup generation token.
Subsequent records must bind that token, the one fixed setup case, strictly
increasing sequence, ordered runner monotonic times, host receipt monotonic times,
the fixed Settings bundle and route, and an enumerated stage/action. Persist and
fsync each accepted record before acknowledging it. Do not persist the bridge
capability. Host-side setup state is separate from app launch generations.

The closed progression records Settings foreground, each existing row search and
route tap, before-switch, after-tap, poll samples, terminal success/failure, and
before/after Settings termination. Existing search attempts remain bounded at
six per row and five swipes per row. Record actual target identifier, label,
element type, exists, hittable, enabled, raw String value or an explicit absent /
unsupported-type outcome, frame, app state and times. Preserve failure reasons
without coercing a missing/non-String value into zero or success. Fixed row labels
and observed identifiers are schema-constrained; no client-supplied selectors,
actions, arbitrary strings as filenames, shell commands, paths or devices.

Retain complete public `debugDescription` AX text for route observations and raw
`XCUIScreenshot.pngRepresentation` at three fixed slots: before-switch,
immediately-after-tap, and terminal. For an already-enabled initial switch, the
middle slot is explicitly after-no-tap; never invent an actual tap. Include a
fresh AX tree with each screenshot, observed alert/prompt structure, and capture
start/end times, so a screenshot and AX query are not falsely described as atomic.

Preserve the 8192-byte request bound with an explicitly typed chunk record on
that same route. Permit only the current fixed evidence slot and strictly ordered
3072-byte decoded chunks, binding record sequence, chunk index/count, total byte
count and full-payload SHA-256. Each PNG is at most 2,000,000 bytes, each AX tree at
most 200,000 bytes, and the aggregate decoded setup payload at most 7,000,000 bytes.
Host paths are derived solely from its fixed slot/sequence table. Verify exact
reassembled size/digest and PNG framing before completing a slot; preserve
incomplete parts and mark them incomplete. No placeholder image or truncated AX
tree qualifies as a complete observation. Bounded upload failures remain visible
and cannot enable Settings or the dependent gate.

Take before/after evidence around the same single conditional tap. Establish the
existing three second absolute poll deadline immediately after that tap, before
post-tap capture; capture/upload must not extend that deadline. Record samples
available within it and the final guard value. Keep the 600s session cap and
existing per-test allowances. Uploads use the remaining finite budget, never a
fresh deadline per retry; each chunk is sent at most once. A timeout or incomplete
image means incomplete diagnostic evidence, not a setup pass. Do not add taps,
switch policies, Settings routes, simulator keyboard preconfiguration or private
preferences to this attempt.

Host runtime summary distinguishes `settingsReportedEnabled`,
`settingsEvidenceComplete`, `settingsDiagnosticOnly`, app cases unrun, command
terminal state, official result availability and cleanup. A durable success can
describe observed Settings value one; it cannot turn this diagnostic attempt into
keyboard qualification. Keep official attachment export attempts as independent
extra evidence, including timeout/exception handling.

Root selected the fixed setup-only diagnostic scope containing test000. Its
six dependent app cases remain explicitly unrun even if setup succeeds. A later
full seven-method attempt requires review of this diagnostic evidence.

## Narrow post-test visibility

Durable before/after Settings termination markers distinguish a future termination
stall from the already observed post-suite stall. The installed official SDK
declares `XCTestObservation` test-case, suite and bundle completion callbacks and
`XCTestObservationCenter` registration. If root selects runner completion
instrumentation, use only fixed test000/suite/bundle stages, with a single bounded
telemetry attempt per stage. Observer delivery may differ between observers; do
not infer unobserved internal ordering or actual process exit from a callback.
An observer callback itself must not wait indefinitely or extend the session.

The current output already supports the post-test boundary. It does not justify
an exact hang cause or a new broad process-inspection authority. Do not add a new
post-suite kill policy or longer timeout before evidence shows a reason. The
existing owned-command interruption and independent cleanup remain authoritative.

## Host controls and official cross-build

Test the setup/chunk state machine independently with strict types and negative
mutations: missing/duplicate/reordered stage and chunk; wrong generation/case /
bundle/route/identifier; stale/nonfinite/bool times and counters; no tap falsely
labelled as a tap; zero/absent/non-String switch values claiming success; value one
without required observations; digest/length/PNG mismatch; oversized AX, image,
aggregate and HTTP body; partial upload; supplied path/selector/command; expired
session and operation budgets; save/ACK failure; failure during termination; and
official export failure. Verify records survive a simulated command exception and
all independent cleanup attempts still run. Replay the frozen v2 oracle and
existing controls unchanged; no app-focus or metadata relaxation is proposed.

The selected implementation is `settings_telemetry.py`, the one-method public
runner under `harness/`, and a new dedicated-process `run.py` adapter. The runner
shares one 29s diagnostic deadline, clamps each single-attempt upload to at most
two seconds, caps requests at 2500, events at 100, uploads at 32 and poll samples
at 40. The inherited 600s command/session cap and per-test allowances are retained.
If a public UI call outlasts the diagnostic budget, the next telemetry request is
rejected; XCTest's existing timeout and independent cleanup are the outer bounds.
PNG framing, chunk CRCs and dimensions are validated, with maximum width/height
4096; complete raw PNG bytes remain available for root's visual review.

All 44 new host methods pass, including complete failing Settings evidence,
multi-chunk/replay mutations, late enabled values, initial-enabled anchoring,
session clamp, filesystem persistence failure and descriptor closure. The first
38-method control attempt exposed a termination marker condition that incorrectly
required a terminal capture after capture failure; its failed receipt is retained
and the condition was corrected. The unchanged v2 suite separately passes all 29
methods. No host synthetic record is native Settings evidence.

The official `build-for-testing` command targets `generic/platform=iOS Simulator`
with arm64 and signing disabled. It does not boot or discover any simulator. The
new runner product tree is
`e267bb779734cf11c49bd29abbe4f57cb4506db95217c7c1e024d7ad9fb29597`,
archive `2bd1c1f9fed7b6248242c3e312a516d02f763c0b02dfb1008ef3c4be318aef1b`.
Tool versions, official header snapshots and both launcher/XCTest binary load
commands are bound in the packet. The supplied launcher reports its own SDK and
minimum separately from the newly compiled XCTest bundle.

`run.py` keeps the inherited qualification assertion and cleanup byte-for-byte.
It records `diagnosticCompleted` and `setupEvidenceComplete` separately; strict
native keyboard qualification, carrier acceptance and GA remain false. An exit-zero
XCTest command followed by the inherited strict-qualification assertion is named
`expected-diagnostic-only-inherited-qualification-boundary`. It is not a Settings
or XCTest failure and is not hidden to force a zero diagnostic process exit.
An actual test failure or xcodebuild timeout remains an observed failure.

Offline commands from the repository root are:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v3-preparation/host_controls.py
python3 -B verification/apple-toggle-keyboard-focus-v3-preparation/build_runner.py
python3 -B verification/apple-toggle-keyboard-focus-v3-preparation/record_provenance.py
python3 -B verification/apple-toggle-keyboard-focus-v3-preparation/seal_packet.py
python3 -B verification/apple-toggle-keyboard-focus-v3-preparation/run.py verify
```

Preparation commands must not overwrite a sealed packet. Root reviews the seal
before its new owned native diagnostic. Root-only execution uses `run.py run
--scope interaction --reviewed-seal <selected-seal>`; only test000 is selected.
After a root run, replay the fixed durable journal with:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v3-preparation/replay.py
```

An incomplete journal remains incomplete; replay cannot retroactively pass v2.
The frozen app closure remains
`f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46`,
archive `b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393`.
The strict v2 focus oracle, all prior packets and the actual failed runtime remain
unchanged. Physical phones and wider product/GA acceptance remain pending.
