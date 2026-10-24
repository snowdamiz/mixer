# Private native keyboard and focus qualification

This follows the private pan-commit carrier at source closure
`f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46`.
The full pan-commit rerun must pass before its carrier is accepted. Preparing a
separate keyboard harness may proceed concurrently; it does not qualify input.
Keep every earlier source, runner, seal and failed observation immutable.

Prefer the exact existing app archive, which already exposes the toggle, a
plain UIKit reference button, and the next native focus target. Reuse their
compiled bytes with explicit provenance. A new XCTest runner may add public
keyboard events and accessibility observations. Do not change the carrier,
shared appearance, binding semantics or product adapters in this preparation.
Report any missing fixture instrumentation before expanding the app delta.

Use public native event delivery. The installed iOS simulator SDK declares
`XCUIElement.typeKey(_:modifierFlags:)` for iOS and exposes `hasFocus`.
Dispatching the primary target directly is not keyboard evidence. Establish
focus using actual keyboard navigation and observe the focused native element;
do not assign focus flags or replace the native focus engine. If Full Keyboard
Access requires enabling, use the disposable simulator's public Settings UI.
Do not change the host Mac's accessibility settings or private preference keys.
Preserve the settings UI observations and distinguish environmental setup from
the application checks. A setup failure leaves the dependent cases unrun.

Cover both initial values with an enabled, current input gate. Tab must reach
the authored toggle in a recorded native traversal, Space must produce exactly
one accepted primary transition and one matching value event, a second Space
must reverse it once, and subsequent forward/reverse navigation must reach the
actual neighboring controls in their observed order. Preserve the toggle's
native identity and selected/disabled accessibility metadata. Capture the
focused state and event history before and after each input. The plain UIKit
reference is a focus neighbor, not an assumed source of value-change events.

While focused, closing the fixture's existing input gate must make Space silent
without losing the current binding; reopening it must restore one-event input.
Disabling the toggle must prevent a value change or event and allow native focus
navigation to another enabled control. Record whether UIKit removes focus and
how traversal behaves; do not infer it from `isEnabled`. Reset fixture state and
establish a new baseline for every case. Keep unsuccessful key delivery,
unexpected traversal, and incomplete observations as failures or pending checks.

Use closed case/action tables, bounded polling and the reviewed stable
observation reader. Keep the existing bridge endpoints, command grammar,
instance ownership and independent cleanup. Add only explicit keyboard case
requests needed by the new public XCTest methods. Bind source, runner, tool
versions, app provenance, raw native observations and strict verdicts; include
host controls that reject stale focus, duplicate/missing events, wrong values,
identity changes and absent native keyboard delivery. Never label a direct
semantic callback as a real keyboard action.

The existing `evaluate` endpoint may accept one closed keyboard witness for a
selected keyboard case. Bind its exact case, action index and bridge generation;
permit only fixed native element identifiers, Tab/Shift-Tab/Space, before/after
AX snapshots and monotonic times around the public `typeKey` call. Validate and
persist it before evaluation, and include it in the replayed verdict. Missing,
duplicate, reordered, stale or mismatched witnesses fail the case. A successful
`typeKey` return alone is insufficient: require the corresponding native focus
or application transition and exact current capture. Keep ordinary inherited
empty-body evaluation unchanged. Existing fixture commands may occur between
keyboard actions only through a fixed per-case sequence. This adds no endpoint,
arbitrary path, command, device, process or input authority.

Root reviews the prepared packet and owns execution. Use at most one owned
simulator, after the current pan-commit instance has finished and been cleaned.
Cleanup is required on all outcomes, including Settings or focus setup failure.
Preserve other projects' devices, data and frontend processes. Physical phones
remain disconnected. These checks can accept a development slice; they do not
close compositor parity, live Apple integration, physical VoiceOver, FieldLog,
store, operational or GA gates.
