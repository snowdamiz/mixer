# Android toggle native scroll failure: isolated diagnostic contract

The repaired supplement's frozen `runtime/runtime-1` completed 17 component cases,
then failed `actual native ScrollView interception and CANCEL`. Its assertion
counter is 85 including the failing assertion, with 64 reported events. The
failure is retained with its original main-thread stack and instrumentation-bound
JSON. The full 45-case suite remains failed. The separate original 20-action
baseline pass with 429 assertions does not establish supplement acceptance.

The failing expression combines `scrollY > 0`, `proposals == 0`, and
`!toggle.isPressed()`. The existing export records none of these three values at
that assertion. Its final cleanup observation reports pressed false and zero
parent acquire/release counts after explicit cancellation; that cleanup state
cannot identify the failed conjunct or prove that native CANCEL was delivered.
There is no per-event hierarchy trace for the nine injected scroll events.
The earlier `runtime-3` process crash remains undiagnosed and is not attributed
to the same cause.

The source installs content with requested height 6000 and a toggle at left 60,
top 400, width 1000, height 132. It resets scroll to zero and waits for native
idle, resolves screen coordinates, then calls worker `sendPointerSync` nine times
with DOWN, seven MOVE events, and UP. Coordinates move upwards by 35 pixels per
event; diagonal mode also moves right by 10 pixels. Event timestamps use
`base + i * 25`, without a deliberate sleep. These are source observations,
not proof of the measured extent, hit geometry, actual delivery time, or failure
cause. Android documents that injection waits for handling but does not guarantee
all subsequent UI reactions have completed; it specifies uptime as the timebase.
See [Instrumentation](https://developer.android.com/reference/android/app/Instrumentation#sendPointerSync(android.view.MotionEvent)).

Root approved the following observation contract before fixture editing. The
private package is `dev.mixer.android.authoredtogglescrolldiagnostic`. Every
original case body, assertion, event count, coordinate, timestamp schedule,
native budget, screenshot count, and production byte stays unchanged. No paced
gesture mode exists in this candidate. Native execution is root-only and has
**NOT RUN** in this lane.

- The private Activity records public dispatch before/after its unchanged
  superclass call. The fixture ScrollView records dispatch, interception,
  onTouchEvent, and disallow-intercept calls around unchanged superclass calls.
  Content dispatch records the child boundary.
- A public `View.OnTouchListener` records child delivery, including CANCEL, then
  always returns false. Source inspection of the exact frozen candidate's native
  Java inputs and repair fixture establishes that no listener was already
  installed. No reflection or private introspection is used. Android documents
  this callback as preceding the View's handling; false leaves it unconsumed.
  See [OnTouchListener](https://developer.android.com/reference/android/view/View.OnTouchListener).
- Native hooks record action, pointer, local/raw coordinates, down/event/current
  uptime, return value, scrollY, proposal count, pressed state, each assertion
  conjunct independently, input gate, checked/bound state and parent ownership.
  Worker injection records before/after uptime and timestamp lead without reading
  View state off the main thread.
- Pre/post geometry records requested and measured content/viewport extent,
  `canScrollVertically` in both directions, native computed scroll range/extent,
  screen/window/global visible bounds, window visible frame, insets, focus,
  attachment and density. Positive scroll extent is observed independently.
- The trace is separate from the original oracle: at most 2048 entries and
  512 KiB, with SHA256 declared by instrumentation. Saturation does not interrupt
  delivery, but the exported dropped count or any observer failure makes trace
  validation fail. Root's finite export is hash-checked and rejects truncation.
  The added host capture budget is 532480 bytes, separate from the inherited
  33554432-byte log budget and repaired diagnostic budget.

Native interception returning true normally cancels the existing target and
routes later events to the parent. The diagnostic observes those boundaries
rather than assuming the original assertion's label proves the path. See
[ViewGroup interception](https://developer.android.com/reference/android/view/ViewGroup#onInterceptTouchEvent(android.view.MotionEvent)).
Observer Map allocation and public state queries add time during delivery. This
candidate can establish an observed route under instrumentation; it cannot prove
timing equivalence with an unobserved run. A paced or actual-uptime experiment
requires a separate root decision informed by this trace and retention of the
original protocol as a comparison. Neither future timestamp offsets alone nor a
source-only hypothesis authorizes a fixture semantic or product change.

Host verification builds a new private APK using the unchanged 159 production
classes and 18 native libraries, then freshly recompiles the diagnostic fixture,
compares exact class bytes, reproduces exact DEX, and inspects signature,
manifest, resources, descriptor and 16 KiB packaging with official tools. Java
host controls exercise trace saturation, immutable snapshots, concurrent recording
and existing failure forwarding; Python controls check the exact original case
block, dispatch schedule, cleanup tail, listener precondition, serial-specific
capture, identity refusal, correct/wrong hashes, truncation and overflow.
These checks establish host composition and diagnostic plumbing, not native
scroll behavior. No dependencies are added; `THIRD_PARTY.yml` stays hash-bound.

The runner derives from the frozen repaired runner with four finite source
replacements: new package, new closure, extra private trace capture, and trace
validity requirement on a successful run. Its emulator/extraction cleanup tail
is byte-identical. It retains the original owned API37 AVD, port/process identity
checks and all-outcomes cleanup. Extra capture rechecks exact owned process
identity immediately before export; it runs in finally before cleanup and cannot
turn a failed original suite into a pass. The original sealed packets and runtime
evidence remain immutable.

Prepared host commands and exact outcomes are recorded under
`verification/android-toggle-scroll-failure-analysis`. Root must review the
frozen packet and select any native dispatch. Physical phones remain disconnected
and deferred. TalkBack service workflows, full renderer authority, Apple parity,
immutable separate-repository FieldLog packages, stores, operational/customer
evidence and accountable GA acceptance remain pending.

The prepared `supplement-1` APK SHA256 is
`b272894251149cb62ebb95989756d21ad7532bc6a1d6b79d00be77af879ed441`.
Its source closure is
`e878461ca7f47ca76e90b757fba6dcafabcb2f87e4c32430bd3cfc2fd4b68cf8`.
This canonical content closure is not a Git tree. `host-1` reproduces all seven
fixture classes and exact DEX. The failure helper passes 12 checks; trace storage
passes 106; source/runner/export controls pass 21; the separate synthetic trace
summary passes 9. The build removes 189 owned scratch files / 345970216 bytes;
the host replay removes 196 / 173408441 bytes. Every owned command group is empty.
No Git, emulator, simulator, physical-target or CUA command ran in this lane.

Rebuild and host replay commands used:

```sh
python3 -B verification/android-toggle-scroll-failure-analysis/capture_analysis.py
python3 -B verification/android-toggle-scroll-failure-analysis/build.py --attempt supplement-1 --production candidate-3
python3 -B verification/android-toggle-scroll-failure-analysis/freeze.py
python3 -B verification/android-toggle-scroll-failure-analysis/verify.py --attempt host-1
python3 -B verification/android-toggle-scroll-failure-analysis/test_review_trace.py
```

The attempts above already exist and cannot be reused. Read-only packet replay:

```sh
python3 -B verification/android-toggle-scroll-failure-analysis/check.py
```

Root-only dispatch, after exact packet review and selection:

```sh
JAVA_HOME=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home \
  python3 -B verification/android-toggle-scroll-failure-analysis/run.py \
    --build candidate-3 --attempt runtime-1 --execute-native
```

No native dispatch is implied by host preparation. The runtime subtree is excluded
from the packet seal, each attempt must be fresh, and only the instance created by
that invocation may be stopped. An already-exported trace can be summarized with
`review_trace.py --trace <scroll-private-trace.log> --instrumentation
<actual-native-component.log>`; this checks instrumentation binding and presents
delivery/conjunct/timing evidence without inferring a cause or suite acceptance.
