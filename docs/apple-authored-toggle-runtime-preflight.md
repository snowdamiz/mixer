# Frozen Apple toggle runtime handoff

This handoff qualifies only the retained `candidate-2-directional-pan` prototype.
It changes no product source, fixture, producer script, or frozen proof. The root
lane owns all native execution, CUA input, AX inspection, and compositor capture.
Physical phones remain disconnected and unqueried. Every actual gesture, native
scroll/key/AX behavior, and paint result is pending at handoff.

The read-only verifier revalidates the producer's 43 sealed files, 26-file source
closure, retained output of all 19 host policy cases, 11 successful build commands,
five-file exact app archive, Info.plist identity, and arm64 iOS Simulator Mach-O
bindings. No build or policy producer script is rerun. The accepted build used
Xcode 27.1 (27A9275), the iPhoneSimulator27.1 SDK path, Swift 6.4, and an iOS26.0
simulator deployment target. The retained binaries themselves report SDK27.0
and minimum OS26.0 in `LC_BUILD_VERSION`; this distinction is recorded rather
than normalized. Root must observe whether that exact binary runs on iOS26.5.

The runner pins `DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer`.
Host inspection confirms its Info.plist says Xcode26.6 (bundle build24959), and
fingerprints its simctl and Simulator executables without running them. Existing
`verification/apple-native-resume-2026-10-24/commands.json` and
`simulator-lifecycle.json` retain availability evidence for arm64 iOS26.5 (23F77),
including iPhone17Pro support. That is historical evidence. Before creating any
instance, the root runner records live Xcode version, simctl help, tool hashes,
devices, and available runtimes, and requires that exact runtime/build/device.

## Root command contract

Run from `/Users/andreyyurlov/Documents/dev/mixer`. The following commands never
change the frozen producer packet. `verify.py` is read-only. Host tests mock every
native/process operation and use disposable owned scratch only.

```sh
python3 -B verification/apple-authored-toggle-runtime-preflight/verify.py
python3 -B verification/apple-authored-toggle-runtime-preflight/test_guards.py
python3 -B verification/apple-authored-toggle-runtime-preflight/runtime.py restore
python3 -B verification/apple-authored-toggle-runtime-preflight/runtime.py install
python3 -B verification/apple-authored-toggle-runtime-preflight/runtime.py command self-tests
python3 -B verification/apple-authored-toggle-runtime-preflight/runtime.py collect self-tests
```

`restore` rejects archive traversal, duplicate or extra files, links, special
files, wrong modes, wrong hashes, and a partially populated destination. It writes
only `runtime/restored-app/MixerAuthoredToggle.app`, and rechecks the exact
manifest on reuse. Installation rechecks both the restored and installed bundle.
No trusted app content is sourced from the ignored producer `build/` directory.

Install creates exactly one recorded `MixerAuthoredToggleCandidate2Runtime`,
iPhone17Pro/iOS26.5 instance. It refuses a second live record, an unrecorded
instance with that name, or any missing/active protected iOS27 instance. The four
protected IDs are `24DD0059-D1DD-456D-ADF9-0946595DDE66`,
`1A7E942B-CF97-4DBB-8786-1D982744EBE4`,
`D55AD884-6D5A-4403-9D16-A0FEE48A29C5`, and
`328CA6E8-BA26-4404-8D47-63EF761B0F91`. The runner never boots, shuts down,
deletes, or alters any of those devices. It snapshots all existing device states
for comparison after cleanup. Every failure after creation invokes owned cleanup.

The runner launches the app through public simctl and never starts a Simulator
frontend. Root should select/open the pinned Xcode26.6 Simulator through its
authorized UI workflow and select only the recorded owned UDID. Before input,
root must record frontend ownership:

```sh
# Root started this exact new pinned Simulator process; substitute its actual PID.
python3 -B verification/apple-authored-toggle-runtime-preflight/runtime.py frontend --pid 12345 --started-by-root
# Or root reused a pre-existing frontend, which cleanup must preserve.
python3 -B verification/apple-authored-toggle-runtime-preflight/runtime.py frontend reuse
```

Registration rejects baseline PIDs and checks the exact pinned executable plus
process start time. Cleanup may terminate only that registered unchanged process.
Root must register a newly started frontend immediately; an unregistered frontend
is preserved and cannot be counted as verified frontend cleanup. Frontend reuse
must be an actual observed choice, not a substitute for registering a new process.

## Actual input and observation protocol

Only CUA supplies tap, timed hold, drag, keyboard focus/Space, and native AX/UI
activation. Public simctl is restricted to simulator inventory/lifecycle,
app installation/launch/container lookup, and status-bar setup. This wrapper has
no touch/key/accessibility injection, `performPrimaryAction` shortcut, simctl
screenshot, AX automation, recognizer synthesis, or native UI automation. The
frozen app's `self-tests` are explicit programmatic harness tests; they must not
be labeled actual user input.

The root must use a fresh CUA UI state to locate the toggle and map its observed
`frameInWindow` into current frontend screen coordinates. The input rectangle is
63×44 points. With the scroll at top it starts at the row's x=`scroll.width−83`,
y=30. Do not reuse stale absolute screen coordinates. Every case records exact
CUA tool, command/arguments, result, screenshot and observation filenames.

`command` permits only `self-tests`, `reset`, `set-on`, `disable`, `stale`,
`resume`, `rtl`, `dark`, `cancel`, `focus`, `authored-value`, and
`clear-authored-value`. These write the frozen app's explicit command channel.
Each acknowledgement is checked against both app stage and observations. Repeated
commands use an acknowledged unique harmless barrier, because the frozen app
ignores a command equal to its current stage. `reset` restores off/enabled/LTR/light
and scroll-top, but it does not reset cumulative counters. Assert counter deltas.

```sh
python3 -B verification/apple-authored-toggle-runtime-preflight/runtime.py command reset
# Root supplies a real CUA timed native hold while this watcher is running.
python3 -B verification/apple-authored-toggle-runtime-preflight/runtime.py held cancel-case --after-held-command cancel
python3 -B verification/apple-authored-toggle-runtime-preflight/runtime.py held disable-case --after-held-command disable
python3 -B verification/apple-authored-toggle-runtime-preflight/runtime.py held stale-case --after-held-command stale
# A CUA horizontal drag can be watched after UIPan has cancelled UIButton tracking.
python3 -B verification/apple-authored-toggle-runtime-preflight/runtime.py held pan-case --when pan --after-held-command disable
python3 -B verification/apple-authored-toggle-runtime-preflight/runtime.py capture after-release-unique-label
python3 -B verification/apple-authored-toggle-runtime-preflight/runtime.py collect final-unique-label
```

`held` waits at most18 seconds. Touch mode requires actual native `highlighted`
and `tracking`; pan mode requires actual `panActive`. The watcher stores the app
observation and can then issue a cancellation/state command. The root must capture
the actual compositor during the held interval using CUA. Capturing only the app
state does not prove pressed paint. `capture`/`collect` create non-overwritable
timestamped JSON observations; they never create screenshots.

Root can record CUA evidence with a JSON file containing `tool`, `command`,
`result`, and `scope`, plus optional absolute `screenshotPath`. The note API
records the exact note and hashes an existing screenshot; it performs no input.
Put those note files and CUA screenshots beneath this packet's mutable `runtime/`.

```sh
python3 -B verification/apple-authored-toggle-runtime-preflight/runtime.py note /absolute/path/to/cua-note.json
```

| Case | Harness preparation, then exact native input intent | Required observed result |
| --- | --- | --- |
| Tap/reverse | `reset`; CUA tap center; capture; second CUA tap; capture | Each actual tap adds one primary acceptance and one value event, selected state reverses. |
| Held/cancel/disable/stale | `reset` before each; CUA timed center hold; root watcher issues one named command; CUA release; capture | Held paint/tracking captured; cancellation clears pressed state; release adds no event or accepted primary. Also reject a fresh tap while disabled/stale. |
| LTR forward/reverse | `reset`; CUA drag off-thumb right through >6pt; reverse from `set-on` left; capture an intermediate held pan | Thumb follows actual translation; one changed-side value event; no duplicate primary. |
| RTL forward/reverse | `reset`, `rtl`; CUA off-thumb left, then on-thumb right | Logical endpoint reverses; same event constraints. |
| Return/same side | `reset`; CUA horizontal move >6pt then return to original side and release | Preview ends at retained side, zero value events. |
| Horizontal outside | `reset`; CUA horizontal drag/release beyond x bounds while y remains in corridor | Clamped endpoint commits once. |
| Vertical outside | `reset`; CUA admit horizontal pan, then release above y=−22 or below y=66 relative to toggle | Preview clears; retained state and event count preserved. |
| Mid-pan invalidation | `reset`; CUA held horizontal pan; watcher issues `disable`, `stale`, `set-on`, or `rtl` in separate cases | Active preview cancels; no delayed event on CUA release; binding/direction command retained. |
| Scroll arbitration | `reset`; CUA primarily vertical drag starting inside toggle | Native scroll offset changes; no toggle value event; tracking/pressed clears. |
| Keyboard/focus | Root enables/observes actual Simulator keyboard focus; CUA focus movement, Space, then next-control movement | Native focus reaches toggle in order; Space emits once; next target becomes focused. `command focus` alone does not prove this. |
| Simulator AX | Root CUA AX inspection in off/on/disabled/authored-value states and actual native UI activation | Native toggle/button role and selected/disabled state, metadata, ordered native focus and once-only activation. Programmatic self-test activation is separately scoped. |
| Paint | Root CUA captures off/on, pressed, disabled, dark and RTL | Exact canonical track/thumb paint and bounds; no default glass escape. State JSON alone is insufficient. |

Parent-scroll rebinding and full production reconciliation/retirement cannot be
triggered through this frozen prototype's command set. Their actual native
behavior remains pending product integration evidence. The prototype provides no
physical VoiceOver, complete Apple adapter, separate-repository FieldLog release,
store/signing, customer operation, or GA qualification.

## Cleanup and evidence boundary

Always run the following, including after failed input/AX/paint cases:

```sh
python3 -B verification/apple-authored-toggle-runtime-preflight/runtime.py cleanup
python3 -B verification/apple-authored-toggle-runtime-preflight/verify.py
```

Cleanup revalidates ownership against UUID/name/runtime/device type, saves final
observations, shuts down and deletes only the recorded instance, and checks its
absence and preservation of every baseline device state. It stops only a
registered unchanged root-started frontend. Device/frontend removal failures stay
unpassed and retryable. This is one evidence run: after successful cleanup a new
installation requires a new reviewed packet, preserving this run's receipts.

Every subprocess gets an independent event JSON containing argv, working directory,
explicit developer directory, timestamps, duration, exit status and stdout/stderr.
Separate event files prevent the CUA hold watcher from overwriting a parallel
root command's log. The lifecycle retains source closure, runner/tool fingerprints,
exact restored/installed app hashes, available runtime, before/after states, and
cleanup. The immutable handoff seal includes the runner, verifier, tests, host
receipt and this document; only `runtime/` is explicitly excluded. Runtime evidence
must receive its own root-reviewed final receipt/seal when actual execution ends.
