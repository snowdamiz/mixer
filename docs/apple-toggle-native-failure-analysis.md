# Apple toggle: bounded native failure analysis and diagnostic handoff

The frozen candidate is **not accepted**. On the root-owned iOS 26.5 (23F77)
simulator, its 12 programmatic checks contain two failures and one vacuous pass.
Actual coordinate taps and simulator accessibility-element activation changed
native selection once per activation. Directional pan, positive scroll
arbitration, keyboard focus, and pressed compositor pixels remain unqualified.
The evidence supports investigating separate invocation and input-delivery paths;
it does not establish a UIKit bug, a recognizer-policy bug, or a CUA limitation.

This lane changed only this document and
`verification/apple-toggle-native-failure-analysis/`. No product adapter,
original producer, frozen archive, original runner, original runtime evidence,
simulator, physical device, or CUA surface was changed. No Git command ran. The root's
94-file review receipt and exact CUA commands are retained and digest-checked by
the read-only `analyze.py` in this packet. Original runtime cleanup is verified:
the owned device/frontend are absent and all four baseline device states remain
unchanged. The first cleanup failure remains historical evidence.

## Observations and limits

| Input | Observed native result | Conclusion |
| --- | --- | --- |
| First direct `performPrimaryAction()` from off | Primary target and one value event; selection remained off; emitted value was `false`. | The fixture's required selection transition failed. |
| Second direct `performPrimaryAction()` | Another primary target/value event containing `false`; selection remained off. | The named deselection check passed without a preceding on state. Its premise was invalid. |
| Direct enabled `accessibilityActivate()` | No selected-state transition or value event. | Required direct-call behavior failed. The original fixture did not retain the return Boolean separately, so its value cannot be recovered from the compound failed check. |
| Two CUA coordinate taps | Off→on→off, one primary acceptance and value event each. | Native touch activation was observed in both directions. |
| CUA exposed-element `click(8)` | Off→on; accessibility-activation count 2→3, touch-begin count 2→3; one value event. | Simulator accessibility-element activation was observed. The coexistence of activation and touch tracking is consistent with a system-mediated path; the internal mechanism and physical VoiceOver behavior are not established. |
| CUA horizontal drag intent | One primary toggle; zero pan acceptances, zero tracking continuations, final pan state `.failed`. | This was not a qualified directional pan. Intermediate delivery and recognizer admission were not recorded. |
| CUA downward vertical drag at offset zero | Begin/end; no value event, no continuation, final pan `.failed`, offset stayed zero. | This is not a positive scroll control: a downward drag at the top can remain at offset zero. It does not identify the cause of missing scroll evidence. |
| Timed held click | Separate watcher observed tracking/highlight/authored-pressed true; release emitted once. | Held state and release were observed. CUA screenshot requests serialized until release, so pressed pixels were not captured. |

The root also recorded held cancel/disable/stale restoration, rejection of fresh
disabled/stale taps, and a dark RTL tap retaining authored accessibility value and
native selected state. Tab did not establish native focus. Screenshots were
inspected in the conversation; no local pixel artifact or numerical comparison
exists. These scoped observations do not satisfy the full carrier matrix.

## Public Apple contracts

Apple's [`changesSelectionAsPrimaryAction`](https://developer.apple.com/documentation/uikit/uibutton/changesselectionasprimaryaction)
describes selection toggling for a button's primary action when no primary menu
is provided. [`performPrimaryAction()`](https://developer.apple.com/documentation/uikit/uicontrol/performprimaryaction())
invokes the control's primary action. The installed UIButton/UIControl headers
retain both APIs and distinguish primary invocation from dispatching installed
target/action handlers. The observed direct-call state/event mismatch remains a
failure; these documents do not justify replacing native selection with a manual
toggle or treating unchanged-state dispatch as success.

Apple's [`accessibilityActivate()`](https://developer.apple.com/documentation/objectivec/nsobject-swift.class/accessibilityactivate())
describes the element's activation implementation and a Boolean reporting its
success. The installed UIAccessibility header documents a default unsuccessful
implementation. That does not prove UIButton's subclass behavior or the entire
assistive-technology activation pipeline. Direct invocation, simulator exposed
element activation, and physical VoiceOver need distinct receipts.

Apple's public [pan recognizer](https://developer.apple.com/documentation/uikit/uipangesturerecognizer)
requires native movement before beginning. Both the
[view admission method](https://developer.apple.com/documentation/uikit/uiview/gesturerecognizershouldbegin(_:))
and the [recognizer delegate method](https://developer.apple.com/documentation/uikit/uigesturerecognizerdelegate/gesturerecognizershouldbegin(_:))
can reject recognition. They share the selector used by this candidate, so an
instrumented callback is not proof of which role invoked it. The public
[dynamic failure method](https://developer.apple.com/documentation/uikit/uigesturerecognizerdelegate/gesturerecognizer(_:shouldberequiredtofailby:))
supports the authored-pan/scroll-pan relationship. Native cancellation can also
end UIButton delivery after a pan recognizes; zero `continueTracking` alone is
not a diagnosis. Installed SDK headers and fetched official Markdown documents
are snapshotted with URLs and SHA-256 in `evidence-manifest.json`.

The original runner correctly requires 12 fresh passing checks and raises on the
two false results. The enclosing root shell continued to a later collection
command; this was not a runner pass. Its code and failed observations remain
unchanged. The new handoff likewise distinguishes an observational `probe` from
a strict `command self-tests` and never promotes a failed result to acceptance.

## Isolated candidates

Both new apps crosscompile with Xcode 26.6 (17F113), Swift 6.3.3, the
iPhoneSimulator26.5 SDK, arm64 simulator platform, and minimum OS 26.0. The
original archived candidate was built with Xcode 27.1; its binary declares SDK
27.0. Compilation alone does not establish runtime behavior on iOS 26.5.

| Artifact | Source/app identity | Intended comparison |
| --- | --- | --- |
| Original frozen candidate 2 | Closure `04f91d8abf20e3401a916b8ab03c6d638eefd53f2e8aa8fcded31ef9706e5b9d`; original SDK27.0 archive unchanged. | Historical failed invocation and partial native observations. |
| `sdk26-comparator` | All 26 original source files byte-identical, including Info.plist; same `MixerAuthoredToggle.app` and bundle ID. Distinct artifact packet/archive. | Hold source and app identity fixed while changing compiler/SDK. |
| `diagnostic-candidate-2-standalone-pan` | Distinct `MixerToggleDiagnostics.app`, bundle `dev.mixer.verification.authoredtoggle.diagnostics`; source closure recorded in its lock. | Observe plain UIKit references and invocation/delivery/admission details under the comparator's toolchain. |

The first 110-file handoff is preserved byte-for-byte under `history/attempt-1`,
including its seal `09fc2dd83a20035243b7dc3b512bb6c334291f3863e6bc31fb1eb7b451c1fb42`.
Its pan reference shared a scroll ancestor. Before any native run, root requested
the diagnostic-only correction: the new reference is a direct child of the root
view, outside all scroll ancestors and below the native focus button. Its exact
29-line diff from the first diagnostic source is retained. The comparator,
authored carrier, authored policy, and app identities are unchanged. One new
fixture check asserts root-view attachment; the diagnostic total is now 19.

The diagnostic carrier preserves the exact authored `draw` implementation,
canonical path consumer, native UIButton selection/traits, primary gate, and
`TogglePanPolicy`. It adds public observation callbacks, not new gesture policy,
synthetic input, recognizer state writes, or selection fallback. A plain custom
UIButton is a visible reference. A separate UIView with an unfiltered public pan
is a standalone movement-delivery reference outside the list. Those references are diagnostic fixture UI,
not product appearance or accessibility acceptance.

Each off→on and on→off programmatic case explicitly establishes its own initial
selection. The fixture records before, immediate return/effects, next main-queue
turn, and effects after a bounded 250 ms settle. It records the direct
accessibility return separately. Strict verdicts still require the selected-state
transition, exactly one primary action, the authored carrier's exactly one
correct value event, identity/window attachment, and successful AX return where
applicable. Disabled/stale cases require no value event or state change. A plain
UIButton's own `.valueChanged` behavior is observed separately. All 17 executable
host cases for this shared verdict reject the original vacuous pass and missing
or duplicate transitions. This validates the oracle, not UIKit.

Gesture telemetry records public touch type, phase, timestamp, locations and
coalesced count; receipt/admission decisions; translation/velocity; dynamic
failure decisions; authored-pan callbacks; scroll-pan callbacks and offsets; and
scroll cancellation decisions. Its bounded 8,192-entry in-memory trace reports
overflow, which disqualifies a complete trace. Additional logging can affect
timing, so changed behavior remains evidence for diagnosis, not automatic proof
of repair.

## Root-only bounded native handoff

No new native run occurred in this lane. Do not rerun sealed build/oracle producer
scripts. These read-only checks validate retained evidence and exact app payloads:

```sh
python3 -B verification/apple-toggle-native-failure-analysis/analyze.py
python3 -B verification/apple-toggle-native-failure-analysis/runtime.py verify
python3 -B verification/apple-toggle-native-failure-analysis/test_guards.py
```

After root review, start one supervised session in a background execution cell;
retain its session ID and wait for the printed ready state. The default session
bound is 600 seconds, maximum 900. It restores exact archives, creates one named
iPhone 17 Pro/iOS 26.5 (23F77) instance, installs both distinct bundles on that
instance, and starts the comparator. No iOS 27 runtime is used.

```sh
python3 -B verification/apple-toggle-native-failure-analysis/runtime.py session --seconds 600
```

Root exclusively selects the owned Simulator through CUA. Immediately register a
newly root-started pinned frontend PID, or explicitly record baseline reuse.
Registration refuses baseline PIDs, missing/reused identities, or another
executable. Do this before further UI input; unknown newly appearing frontends
are preserved and prevent a clean receipt until root reconciles ownership.

```sh
python3 -B verification/apple-toggle-native-failure-analysis/runtime.py frontend register --pid ROOT_OBSERVED_PID
# Or, only when reusing a frontend that predates this session:
python3 -B verification/apple-toggle-native-failure-analysis/runtime.py frontend reuse
python3 -B verification/apple-toggle-native-failure-analysis/runtime.py probe self-tests
python3 -B verification/apple-toggle-native-failure-analysis/runtime.py capture comparator-programmatic
python3 -B verification/apple-toggle-native-failure-analysis/runtime.py launch diagnostic
python3 -B verification/apple-toggle-native-failure-analysis/runtime.py probe self-tests
python3 -B verification/apple-toggle-native-failure-analysis/runtime.py capture diagnostic-programmatic
```

`probe` returns the actual check list and `checksPassed`, including false results;
its successful collection exit is not a test pass. Strict `command self-tests`
requires all 12 original or all 19 diagnostic checks and aborts the supervised
session on failure. The diagnostic suite must reach its explicit complete state;
acknowledging the command name is insufficient. Other commands only change the
explicit fixture state. Actual touches, keyboard/AX actions, and compositor
captures come only from CUA, with exact commands and current coordinates retained
through `note` or a root evidence file. Original coordinate values must not be
blindly reused after fixture geometry changes.

Start with independent positive controls: drag the plain pan surface and scroll
upward on noninteractive list content from the top. Compare that recorded input
with the same directional intent starting on the authored carrier. Delivered
movement plus a false admission decision can identify a candidate policy issue;
missing movement in both references cannot establish one. Preserve all failed
attempts. Do not modify thresholds, broaden touch types, or change selection
because an expected callback is absent.

Finish regardless of result, then poll the supervised execution cell to its
terminal cleanup result:

```sh
python3 -B verification/apple-toggle-native-failure-analysis/runtime.py finish
python3 -B verification/apple-toggle-native-failure-analysis/runtime.py status
```

The supervisor runs cleanup on finish, deadline, SIGINT/SIGTERM, install failure,
and command errors. Device and frontend cleanup failures remain failures. After
the supervisor exits, `runtime.py cleanup` safely retries recorded cleanup if
needed. A hard process kill/host failure still requires that explicit recovery;
no runtime tool can guarantee a `finally` block after process destruction.
Cleanup validates the recorded device identity, deletes only that owned instance,
rechecks all baseline IDs/states, and preserves other projects. PID start/command
identity is checked before one SIGTERM. After that, only observation occurs:
transient zombie/command-label states are polled for absence; a reused PID is
preserved; a timeout is not absence. Forty mocked host guard cases cover these
boundaries. They do not qualify actual simulator cleanup until root executes it.

Carrier acceptance still requires the original directional matrix in both layout
directions, intermediate preview and release boundaries, positive scroll
arbitration, actual keyboard focus/activation, disabled/stale/cancellation gates,
and compositor paint evidence. No programmatic fixture correction replaces those
requirements. Physical phones/VoiceOver remain deferred to final acceptance;
production integration/reconciliation, immutable external FieldLog consumption,
store, operational, and GA gates remain pending.
