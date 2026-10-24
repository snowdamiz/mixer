# Android authored toggle input repair contract — draft for root selection

Repair the reproducible visible-geometry interaction by giving the existing native
`Switch` subclass one small authored gesture adapter. Drawing and touch must use
the same authored endpoints. Keep the real `Switch` checked state, ordinary
checked listener, native accessibility node and native keyboard activation.
This is a proposed production contract, not an implementation selection or a
native acceptance receipt. Only this document and its owned proof directory were
written. No production adapter, fixture, tracker, Git state or native instance
was changed by this lane.

The [sealed diagnosis](android-pointer-native-diagnosis.md) verifies the complete
P03 sequence reached the Activity, including all eight MOVE events and UP. P01
tap and P02 held-tap pass; P03 leaves revision 3 and checked=false. The mismatch
between authored 66 px travel and a conditional platform 111 px carrier is
source-supported, but actual private `Switch` touch state and the exact child
route remain unobserved. This repair targets the demonstrated public behavior;
it does not claim the conditional internal cause is established or require
hidden-platform reflection before implementation.

The input capture verifies the exact 20-file diagnosis seal SHA-256
`802e1939b44e43237471732c89bfd6132f4678622d5899ad759be35219e93e44`.
The current source snapshot closure is recorded in
`verification/android-authored-toggle-input-contract/capture-receipt.json`.
The current source is identified by copied bytes and their closure, not by an
unverified current Git revision. The prior candidate remains revision
`d4909e275df7e757a5218cc0a88112f4fc3f088b`, tree
`5344a10fa8641d537c2e4699811262d162c6ff2f`, input closure
`9082e2de1327bd0784d752db5dfbe4484751d565b3410e01e78664321467f5ce`,
APK `57e82e4e98cdc61581c0639603ec6efa500a66d8d2754f6b47ece89c8165d714`.
Its runner identity remains separately recorded in the root receipt.

## Ownership and public platform basis

Plan sections 8.3/8.4 require shared component appearance with native input,
accessibility and keyboard services, and coarse feature-state transitions.
No Patch/Skip code, generated source, test, fixture or dependency may supply the
repair. This lane's Python model is independently authored specification
arithmetic; it is neither a replacement native engine nor product source.

Android documents that parent interception cancels the child and transfers
handling to the parent, while `requestDisallowInterceptTouchEvent` controls
interception by the parent and its ancestors. Retain that dispatch ownership;
do not manually forward, retarget, replay or synthesize MotionEvents.
[Android ViewGroup gesture guide](https://developer.android.com/develop/ui/views/touch-and-input/gestures/viewgroup).
Use the actual context's scaled touch slop, expressed in pixels.
[ViewConfiguration](https://developer.android.com/reference/android/view/ViewConfiguration#getScaledTouchSlop()).
Use the superclass click path for native click behavior and notification, with
the existing checked listener as the ordinary value-change route.
[CompoundButton.performClick](https://developer.android.com/reference/android/widget/CompoundButton#performClick()).
Official specifications and their raw fetched bytes are retained in the proof
directory; no Android framework implementation is copied into product code.

`NativeRenderer.Input.open(record)` is already the admission authority. It checks
the current committed presentation, the exact record in the live map, enabled,
attached, shown and window-focus state. `Input.event` repeats that gate, records
an interaction epoch, and sends the ordinary envelope. `NativeCoordinatorV2`
owns prepare/attach/commit/rollback/retirement. The adapter must reuse these
owners. It must not cache an independent session, generation, environment permit,
packet, JNI callback or reducer closure. A captured **binding object identity**
is only a local gesture fence, in addition to the existing gate.

## Shared geometry and declared platform differences

Use one native helper, consumed by both `onDraw` and touch policy, to derive the
track origin, authored 63×28 logical track, authored 37×24 thumb, 2/24 logical
thumb origins, centered 63×44 logical carrier input rectangle, and off/on centers
from the bound descriptor, density, direction and current native frame. Preserve
the existing paths, rounding/conversion, label placement, paints, row frame and
drawable metrics. The drawing and input helper must agree with the existing
fixture's original geometry at its unchanged tuple. Native `Switch` measurement
and empty drawable dimensions must not be tuned to change its hidden touch range.

Logical travel is 22 units, currently 66 px at density 3. Let `a` and `b` be the
actual authored off/on centers in the view's local pixel coordinates. They are
reversed in RTL. For initial checked value `c`, DOWN x coordinate `d` and current
x coordinate `x`, the logical on fraction is:

```text
q = clamp((c ? 1 : 0) + (x - d) / (b - a), 0, 1)
```

Reject unavailable/nonfinite geometry or zero/invalid travel. The helper must not
substitute a minimum travel, widen coordinates, move fixture points, or use an
invisible platform thumb range. The same endpoint-center drag works in either
physical direction and LTR/RTL, independent of speed.

The [Apple candidate-2 contract](apple-authored-toggle-contract.md) supplies the
same 22-unit travel, clamping, midpoint tie-to-initial, horizontal outside release
and final vertical corridor. Its UIKit directional pan currently requires native
recognition plus ≥6 points and >1.2× vertical dominance. Android instead uses
actual `ViewConfiguration` slop and strict horizontal dominance after parent
dispatch. These admission thresholds are intentionally platform-native and are
not claimed identical. Once admitted, endpoint selection and release semantics
are shared. Neither candidate's native input behavior is accepted yet.

The baseline carrier hit rectangle is 63×44 logical units centered on the track.
Its ongoing-drag release corridor expands **only vertically** by 22 logical units
at each edge: relative y −22 through 66 inclusive. For the retained Android
tuple it is local y −66 through 198 px. A taller label/row does not silently
widen this carrier corridor. This is ongoing-gesture policy, not an expanded
initial hit target or invisible carrier workaround. Initial DOWN must be inside
the existing permitted visible row bounds. Drag eligibility additionally requires
DOWN inside the authored 63×44 carrier rectangle. Label taps/holds use the normal
row click path; horizontal label drift beyond slop cancels that tap.

## Native gesture state machine

`NativeSwitch.onTouchEvent` owns supported single-contact touch delivery. Never
send this stream to `Switch.onTouchEvent`; doing so would retain two competing
drag machines. Do not invoke app/guest logic, JNI, or reducers on DOWN/MOVE.
Keep constant-sized local state: pending/drag/draining/idle, stable pointer ID,
DOWN coordinates, original checked value, binding identity, geometry, preview
fraction and interception ownership. Native draw invalidation and the renderer's
local interaction epoch are permitted; no feature-state envelope is sent.

| State/event | Required action |
| --- | --- |
| Fresh DOWN | Cancel prior local tracking first. Require `!record.changing`, matching record/view and toggle recipe, existing `Input.open`, coherent native/bound checked state, valid geometry, one contact, finite coordinates and permitted row bounds. Snapshot the binding/geometry and stable pointer ID. Set pending/pressed and record a local interaction. No timeout changes state or commits. |
| Pending MOVE | Recheck the existing gate, binding identity, pointer and coherent checked state. Process delivered historical positions chronologically before the current sample using constant memory. If `abs(dy)>slop && abs(dy)>=abs(dx)`, clear pending/pressed and surrender to normal parent handling. Do not disallow interception while pending. |
| Horizontal admission | When `abs(dx)>slop && abs(dx)>abs(dy)` and DOWN was carrier-eligible, lock this attempt to horizontal drag and request parent interception disallow. Compute preview using the full DOWN-to-current displacement, including the slop-crossing MOVE; do not reset the displacement origin or discard the crossing distance. Ineligible label movement cancels its tap. |
| Drag MOVE | Recheck admission/fence and update clamped `q` natively. Keep checked/accessibility state committed. Once horizontal ownership begins, subsequent vertical movement does not switch to scrolling; native CANCEL always wins. Parent vertical arbitration before admission remains native. |
| Pending UP | Process its coordinates as a final sample, including any slop crossing. If still pending, current position must be inside the row. A stationary tap or arbitrarily held tap toggles once on UP; there is no toggle long-press action or long-press commit. |
| Drag UP | Process final coordinates. If final y is outside the authored release corridor, cancel. Otherwise `q>0.5` selects on, `q<0.5` selects off, and exact `q==0.5` retains the DOWN value. An x outside the row remains a valid clamped horizontal side release. A side equal to the retained state emits no ordinary value change. |
| CANCEL / ACTION_OUTSIDE | End tracking, clear pressed/preview, release owned interception and emit nothing. `ACTION_OUTSIDE` is an actual event, distinct from a drag coordinate whose x is outside the row. No synthetic UP follows a CANCEL. |
| Extra pointer / active pointer lost | Cancel the whole attempt; never transfer to a different pointer or reinterpret the remaining contact as a fresh DOWN. Require a new admitted DOWN. |
| Unexpected or invalid input | No native-carrier fallback. Drain the owned remainder without activation, or reject an unowned event. A malformed action/index, nonfinite sample or incoherent native state cannot commit. Tool-specific mouse/stylus behavior is not newly qualified by the finger fixture. |

Touch slop provides admission hysteresis; the midpoint tie rule avoids inventing
an additional release dead band. Selection does not use velocity or a fling
override. A fast release below the midpoint retains the original side; a full
endpoint drag selects its endpoint, including after the existing 150 ms pause.
There is no new spring, inertia, long-press action or velocity tracker.

Pressed feedback begins on admitted DOWN and ends on every cancellation or
terminal completion. Pending movement outside the row clears pressed paint;
returning inside before slop/cancellation can restore it. An active drag remains
pressed while tracked, including a temporary vertical excursion; final corridor
validation controls release. The thumb follows `q` continuously in native
`onDraw`. Visual on/off palette selection follows the preview side, with a tie
using the initial side, as in the Apple draft. Only drawing/paint changes;
`isChecked`, native accessibility selected/checked state and packet values retain
the committed value until successful activation. Cancel/failure immediately
snaps drawing back to the latest bound value. Every endpoint, light/dark,
pressed, disabled and focus paint remains the existing shared-theme paint.

## Completion, activation and cancellation fences

Before calling any superclass activation, save the desired result and binding
identity; clear local tracking/pressed/preview and release interception. Then
recheck the same binding identity and `Input.open`. If the desired side differs
from coherent native/bound state, invoke the gated ordinary `performClick` once.
Its superclass toggles the native checked value; the existing ordinary checked
listener remains the **only** `valueChange`/JNI/reducer proposal path. A return
value of false from `performClick` is not a reducer failure oracle: native click
return values describe click-listener handling, not authoritative commit success.

Override `performClick` as the shared activation fence: cancel any in-flight
touch **before** attempting activation, reject closed/changing/incoherent input,
then delegate to `super.performClick`. This applies equally to direct native
click, keyboard and accessibility activation. A subsequent UP from the cancelled
touch cannot toggle again. Do not call both `setChecked` and `performClick` for
one proposed change. Do not synthesize click/accessibility events or implement
alternate keyboard mappings. Gate native key dispatch and accessibility action
entry using the same `Input.open`, then delegate to their superclass; preserve
focus navigation, native enabled state, role, checked state, labels/hints/value
overrides and native action delivery. Key repeat/cancel, accessibility click and
interleaving with a held touch require actual native tests.

Wrap superclass activation in a `finally` reconciliation: if native checked state
differs from the **latest** `record.binding.nativeToggleValue`, restore that value
under `Record.changing`, preserving/restoring any preexisting changing guard.
Never restore a saved DOWN value over a synchronous newer binding. Restoration
must work after coordinator retirement and must not reopen the owner or emit
another ordinary event. If a new binding removes/replaces this record, cleanup
of the old view cannot affect the replacement view. Retain coordinator failure
containment and all native/engine rollback authority.

The precise promise is **at most one ordinary valueChange/JNI/reducer proposal
per successful terminal activation**, zero proposals for locally rejected,
cancelled, unchanged-side or stale input, and no authoritative commit for an
engine-rejected proposal. A rejected admitted proposal may cause a second raw
Java checked-listener callback while restoring state under `changing`; that
callback emits no ordinary event. Raw callback count, ordinary proposal count
and committed revision count are separate observations. Existing P03 export
observes revisions, not raw listener multiplicity.

Cancellation is idempotent. Track the exact parent on which this adapter acquired
interception disallow. Clear its ownership flag before requesting `false`, and
release that acquired request exactly once on **every** cleanup path: UP,
CANCEL, rejection, pointer loss, binding replacement, parent move, disabled,
visibility loss, detach, focus/window-focus loss, environment invalidation and
retirement. Do not issue a parent request if this adapter never acquired one;
do not release against a newly rebound parent or after a new gesture has started.
Release before invoking an arbitrary callback. Handling a parent-delivered CANCEL
only clears owned state and returns normally; it must not synthesize another
CANCEL, re-enter parent dispatch, consume later parent movement, or prevent the
parent from completing its interception.

`Record.bind` cancels before assigning **any** new binding, even if values compare
equal. Native layout/frame changes, parent rebinding and lifecycle callbacks
cancel immediately. Renderer environment invalidation and retirement must cancel
live toggle tracking synchronously because a closed `Gate` can consume later
events before the child sees CANCEL. Close gates first, then cancel. Attachment
and rollback must not resurrect a cancelled preview or pressed gesture from a
journal snapshot. In particular, current `restoreV2` restores `state.pressed`;
the minimal integration must explicitly clear toggle transient state after that
restoration. No cancellation adds a guest event. Renderer local interaction epoch
changes for admitted input/preview mutations prevent an earlier prepared candidate
from ignoring transient interaction; after any local epoch call, recheck that
retirement did not cancel the gesture before writing preview state.

## Minimal production change surface for root selection

| File | Bounded change |
| --- | --- |
| `native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java` | Shared authored toggle-geometry helper; small local gesture state; `onTouchEvent`; gated superclass `performClick` with latest-binding restoration; native key/accessibility fences; lifecycle/parent/frame cancellation; preview origin/palette; `Record.bind` cancellation helper. Keep checked listener and wire envelope schema. |
| `native/android/app/src/dev/mixer/android/NativeRenderer.java` | Call record cancellation on gate closure for environment invalidation/retirement and attachment/rollback boundaries. Ensure rollback cannot restore cancelled pressed tracking. Reuse `Input.open` and `Input.interaction`; no additional JNI or admission authority. |
| New narrowly owned Android policy/native test files | Pure production-policy tests and real native carrier/coordinator supplemental cases. Product file ownership and exact paths require root assignment before edits. |

`NativeCoordinatorV2`, `NativeEnvironmentV2`, `NativeBridge`, engine/reducer,
descriptors, appearance geometry, packet format, Swift/iOS product adapter and
the frozen 20-action fixture need no behavior change for this repair. Any
discovered necessary exception must return to root for a new bounded contract.

## Executable verification and acceptance boundaries

The retained host command is:

```sh
python3 -B verification/android-authored-toggle-input-contract/test_contract.py
```

It currently passes 16 finite tests, including endpoint matrices at five
densities, LTR/RTL, exact sealed P03 coordinates/schedule, slop-crossing arithmetic,
midpoint tie, held-tap policy, clamping, vertical corridor, cancellation,
pointer loss, binding replacement, nonpointer interleaving, rejection restoration
and parent-release idempotence. This models the **proposed** contract only.
It imports no production adapter, runs no Android View, uses no native dispatch,
and proves no accessibility, scroll, keyboard, JNI or device behavior.

After root selects and implements the contract, use these finite gates:

1. Pure tests execute the actual extracted production policy, not a second test
   implementation. Check endpoints both ways/RTL at all supported densities;
   full crossing MOVE; strict slop/tie boundaries; midpoint ±epsilon and tie;
   clamp/return; final corridor inclusive edges ±epsilon; no velocity override;
   historical-sample ordering; pointer IDs/multi-touch/nonfinite input; local
   interaction overflow; replacement binding and latest-value restoration.
2. Crosscompile changed production Java with official Java 17 target/SDK37 stubs
   and D8; compile the private harness against those exact class bytes. Bind
   compiler/tool versions, source closure, class/dex/library/APK hashes and byte
   inventories. Retain existing ABI/library bytes unless separately justified.
   No byte/syntax check qualifies native behavior. Keep one constant-size gesture
   state per toggle, O(1) extra storage per event/history sample, no guest/JNI
   call or feature message on MOVE, and unchanged packet/resource bounds.
3. Keep the **exact existing 20-action fixture** byte-identical: P01–P05 three
   cycles, P06, G01, G02a, G02b, G03, with unchanged event coordinates, geometry
   derivation, event offsets, pressure/source/history metadata, settle/failure
   oracle, action order, and existing budgets (≤16 events/action, ≤320 injected
   events, ≤2048 observation rows, ≤180 s native duration). New APK/source hashes
   identify the repair, not a fixture rewrite. The old candidate/run remains
   failed evidence. This fixture's LTR/light baseline cannot qualify RTL.
4. Add a separate finite native supplement, without changing that baseline:
   reverse/RTL endpoint drags; intermediate thumb screenshots while committed
   state is unchanged; crossing slop and return-side; horizontal outside release;
   exact corridor boundaries and outside cancellation; thumb/track-start vertical
   and diagonal parent arbitration; mid-drag disable/stale/bind/frame/parent/
   environment/detach/window-focus changes; pointer loss/extra pointer; native
   accessibility click, disabled/stale rejection and native role/checked metadata;
   actual keyboard activation/repeat/cancel/focus order; keyboard/accessibility
   activation during a held touch followed by old UP. Observe ordinary event
   proposals in a native test `Input`/existing EventSink boundary separately from
   authoritative coordinator commits. Never derive callback counts from revisions.
5. Use one owned emulator for Android native testing, preserve other projects'
   instances/data, and clean it up even after failure. Record actual environment,
   commands, tools, source/tree closure, raw export/output, all attempted packets
   and cleanup; seal nested receipts. Final physical phones, TalkBack service
   workflows, Apple parity, public/signed transport, separate-repository FieldLog,
   store, operational and GA acceptance remain independently pending.

The tradeoff is deliberate: a small explicit adapter removes dependence on an
unobserved private drag range while retaining native state and activation.
It takes ownership of touch classification and therefore requires native
arbitration/lifecycle evidence. The alternative carrier-geometry tuning retains
the hidden range coupling; a whole custom accessibility/keyboard control would
expand scope. Neither is selected by this draft. Root must freeze this contract
and assign product ownership before implementation begins.
