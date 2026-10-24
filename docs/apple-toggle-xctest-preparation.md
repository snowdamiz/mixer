# Apple toggle XCUITest simulator preparation

This is a separately authored verification harness for the two immutable SDK26.5
apps. Preparation has not launched, installed, booted, or tested an app on a
simulator. It has not used CUA, queried a physical phone, changed product code,
changed an app assertion, or accepted the carrier. Root must independently review
the source, host controls, receipt, and sealed artifact before native execution.

The frozen root review remains authoritative: the diagnostic completed 19 strict
checks with 11 true and 8 false; the source-identical comparator completed 12 with
10 true and 2 false. Direct primary-action and accessibility-selection expectations
also failed the plain UIButton reference. Actual exposed-element CUA clicks did
toggle. CUA drag attempts delivered only submillisecond begin/end pairs, including
the standalone pan positive control, and the scroll attempt added no events or
offset. Those attempts did not qualify native movement or identify a carrier bug.

## Official contracts and predicate choice

Apple documents native button selection when
[`changesSelectionAsPrimaryAction`](https://developer.apple.com/documentation/uikit/uibutton/changesselectionasprimaryaction)
is enabled with no menu. Its
[`performPrimaryAction()`](https://developer.apple.com/documentation/uikit/uicontrol/performprimaryaction())
documentation describes primary-action invocation. These contracts do not turn the
observed unchanged selection into success. The original checks, names, order,
counts, return observations, and failed results are retained; this harness does
not repair their invocation expectations or manually toggle selection.

Apple describes
[`accessibilityActivate()`](https://developer.apple.com/documentation/objectivec/nsobject-swift.class/accessibilityactivate())
as an element activation method reporting success, called by the accessibility
system for a VoiceOver double tap. A direct method call, a system-mediated tap,
and physical VoiceOver remain separate evidence. XCTest
[`tap()`](https://developer.apple.com/documentation/xcuiautomation/xcuielement/tap())
sends an event to a system-computed hittable point; these tests qualify only that
simulator tap path if their strict native state/event checks pass.

The driver uses public
[`press(forDuration:thenDragTo:withVelocity:thenHoldForDuration:)`](https://developer.apple.com/documentation/xcuiautomation/xcuicoordinate/press(forduration:thendragto:withvelocity:thenholdforduration:)):
initial hold 0.15 s, velocity 120 in the API's documented units, final hold 0.15 s.
It does not synthesize UIKit touches, call private APIs, set recognizer state, or
alter fixture gesture policy. Native geometry, requested coordinates, parameters,
full before/after observations, and actual trace are retained for every action.
The authored target frame must match the native fixture's window frame within
one point before input. Standalone/list geometry is derived from the current
native exposed label/toggle geometry and the frozen fixture layout.

Apple's
[`cancelsTouchesInView`](https://developer.apple.com/documentation/uikit/uigesturerecognizer/cancelstouchesinview)
contract permits pending view touches to be suppressed and delivered touches to
be cancelled after recognition. The ordinary pan default and authored pan both
enable this behavior. Consequently, view `touchesMoved` is preserved as an
observation; its absence alone is not a movement or carrier failure.

The strict movement predicate instead requires one native recognizer identity,
ordered began → changed → ended callbacks, at least 150 ms between its earliest
and latest callbacks, progressing native time, native translation progression of
at least 12 points, and final translation in the requested direction. Missing,
stationary, wrong-direction, mixed-identity, cancelled, partial, or submillisecond
callback sequences fail. Requested API parameters alone never establish delivery.
All six official Markdown pages, URLs, hashes, and retrieval time are retained in
`verification/apple-toggle-xctest-preparation/official/`.

## Closed test scope

The independently authored external-app UI-testing target contains 12 methods and
15 required action evaluations. Each method terminates its candidate, begins a
new observation generation, launches the exact bundle, and awaits fixed setup
commands. Tests run serially on one explicitly selected simulator; no worker
cloning or parallel test destinations are requested.

| Methods | Strict evidence |
| --- | --- |
| Standalone native pan | Actual native recognition/time/translation; authored state and events unchanged. This surface remains outside all scroll ancestors. |
| Upward blank-list scroll | Native scroll-pan recognition/translation and positive offset of at least 20 points; authored state unchanged. |
| LTR off→on, LTR on→off, RTL off→on, RTL on→off pans | Correct independent initial value/layout direction; native admission and timed movement; intermediate preview without state/event commit; exactly one pan/value transition; zero primary activation; cleared preview and stationary list after release. |
| Upward drag starting on carrier | Native scroll recognition/translation and positive offset; horizontal authored admission rejects; no authored pan/value transition. |
| Diagnostic authored, plain UIButton, and comparator authored tap pairs | Independent native off→on→off transitions, same identities, exactly one primary per tap, exactly one correct authored value event, zero authored pan acceptance. Plain UIButton value-change count is observed separately; no undocumented zero-event contract is imposed. |
| Diagnostic and comparator direct API suites | Original exact 19/12 check names and order, all results retained, every original strict check must be true, and diagnostic explicit completion required. Existing failures remain XCTest failures. |

The complete XCTest command is expected to remain nonzero if the original direct
API failures reproduce, even when independent user-input cases pass. The runner
preserves that exit code and both groups of verdicts. Collection success never
means test success. A test that fails before evaluation makes the closed 15-action
set incomplete and cannot yield an accepted run.

## Telemetry bridge and immutable inputs

The loopback server binds `127.0.0.1` on an ephemeral port and requires a random
per-run capability. Only five fixed POST routes exist. Request schemas, candidate
IDs, case IDs, command order, actions, geometry, body/response sizes, socket waits,
observation size, and session lifetime are bounded. Requests cannot supply a
path, device, PID, shell command, or input event. Duplicate JSON/security framing,
nonfinite geometry, redirected files, and hard links fail closed.

Root's runner alone selects the exact owned simulator and its two installed data
containers. The bridge only reads existing `observations.json` and writes existing
fixture commands (`reset`, `resume`, `rtl`, `set-on`, `self-tests`) in a fixed case
sequence. A prelaunch reset command prevents a prior failed case from replaying
its final command; the caller terminates the candidate before this step. No native
state, event, trace, selected value, or verdict is fabricated or rewritten.

A new launch must write a fresh observation after the generation begins. Every
command must acknowledge its stage with a newer file signature and event count
under the same native identity. Direct diagnostics additionally await explicit
suite completion. Baselines, acknowledged command generations, post-input captures,
trace overflow, and failures are durable. No fixed sleep substitutes for command
acknowledgement; post-input settling is bounded to 350 ms and cannot create a pass.

The exact comparator archive remains
`1c55dab124608b019ab4a1b6e0a9a2355e5f72287602b890a0a3f78aa6b30fa9`,
source closure
`04f91d8abf20e3401a916b8ab03c6d638eefd53f2e8aa8fcded31ef9706e5b9d`.
The exact standalone diagnostic archive remains
`0742f08641fdfa4fdf84dc4f69b0938fff79966348810758161d4c1be8582253`,
source closure
`0ddb00a4ecbe73012bd4cef167696bdbbd9827f3edb99677a9a7b04f07a8de3f`.
The reviewed retry packet validates exact content/inventory and its existing
finite installed-mode normalization. Installed inventory is recorded before an
assertion. Restored archive permissions remain exact. Authored drawing, path
consumer, selection behavior, and pan policy are preserved byte-for-byte.

Capabilities exist only in process memory and a mode-0600 temporary xctestrun
configuration inside an owned mode-0700 workspace. Retained command output is
redacted. Because xcresult may retain the runner environment, only redacted
official summary/test JSON and the independent full native observations are
retained; the ephemeral raw xcresult/configuration is removed. This makes no
screenshot or compositor parity claim. Apple-managed global diagnostic caches
are not independently inspected by this preparation.

## Reproducible build and root execution

`preparation-commands.json` contains the exact successful generic-simulator
`build-for-testing` command and complete output. The build uses Xcode 26.6
(17F113), Swift 6.3.3, arm64 iPhoneSimulator26.5 SDK, and minimum iOS 26.0.
`build-products-manifest.json` binds source files/tree digest, tool/SDK-setting
hashes, all 69 compiled product entries, and an exact compressed runner archive.
This is a compiler receipt, not a simulator or physical-device receipt. Only the
Python standard library and installed Apple platform tools are used.

Root first runs the read-only verifier and host controls from the repository root:

```sh
python3 -B verification/apple-toggle-xctest-preparation/harness.py verify
python3 -B -m unittest discover -s verification/apple-toggle-xctest-preparation -p 'test_*.py' -v
```

If the prepared Products directory is absent in a restored checkout, restore the
sealed runner archive first. This validates all archive paths/types/modes/bytes
before writing only the absent canonical Products directory:

```sh
python3 -B verification/apple-toggle-xctest-preparation/harness.py restore-products
```

Do not rebuild or edit a sealed producer. The retained generic build command is
reproducible preparation input for a separately reviewed attempt; different source
paths/tool revisions may produce different runner bytes and need their own seal.

After independent source/host-control review and root selection, root supplies the
actual SHA-256 of `packet-seal.json` as `REVIEWED_SEAL_SHA256` below and runs once
in a supervised execution cell. This lane has not dispatched this command:

```sh
python3 -B verification/apple-toggle-xctest-preparation/harness.py run --reviewed-seal REVIEWED_SEAL_SHA256
```

The run creates exactly one fresh uniquely named iPhone 17 Pro instance on available
iOS 26.5 (23F77), installs the two exact archived apps, and invokes official
`test-without-building` for its explicit UDID. It records the baseline and owned
identities before mutation. A creation intent is durable before `simctl create`;
if creation succeeds but its response is lost, cleanup reconciles only one fresh
exact unique name/type/runtime outside the baseline. Ambiguity preserves devices
and fails cleanup.

The XCTest process has a 600-second bound; individual cases have 30/45-second
allowances and bridge waits have finite bounds. The runner retains original
interrupted command output and stops only its own subprocess group. Every outcome
independently attempts server shutdown/close, thread completion, identity-checked
ephemeral-workspace removal, and owned-simulator cleanup. One cleanup failure
cannot skip later resources. Cleanup deletes only the owned device, verifies all
baseline device identities/states and pinned frontend identities, and preserves
unknown processes/instances. No Simulator frontend is launched or signalled by
this runner. Failures remain failures until root reconciles them.

After a hard process kill or host interruption, root uses the recorded recovery
command, which also attempts all recorded cleanup resources independently:

```sh
python3 -B verification/apple-toggle-xctest-preparation/harness.py cleanup
```

Runtime results belong only under this packet's mutable `runtime/` subtree.
Keep `lifecycle.json`, `commands.json`, complete `captures/`, official exported
XCTest results, cleanup outcomes, and the strict runtime verdict. Do not mutate
the prior diagnostic or retry packets.

## Current evidence and limits

All 70 host controls pass. They cover oracle rejection of stationary/partial/
wrong-direction movement, cancelled view delivery with real recognizer movement,
stale generations, missing command acknowledgement, partial direct suites,
incorrect check names, duplicate events, trace overflow, HTTP/path/command bounds,
exact runner archives, lost-create-response recovery, and independent cleanup.
They are host fixtures/mocks and do not qualify UIKit or actual simulator cleanup.
Earlier host/preparation attempts are retained. The first host attempt failed
because its task-owned temporary path used macOS's `/var` alias; the test fixture
was canonicalized and the production path guard was unchanged.

Native execution, native tool-delivery qualification, direct API diagnosis, full
carrier acceptance, keyboard/focus, native no-change/cancellation/disable/stale
matrix, compositor paint comparison, physical phones/VoiceOver, product adapter
integration, immutable external FieldLog release consumption, public release,
store, operational, accountable-reviewer, and GA gates remain pending.
