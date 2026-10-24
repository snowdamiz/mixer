# Private native keyboard and focus qualification preparation

This packet reuses the exact private app at source closure
`f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46`
and app archive
`b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393`.
The app/carrier was not changed or recompiled. The prerequisite pan-commit v2
root acceptance and complete cleanup are explicitly bound before runtime.
Every previous packet and native observation remains immutable.

The new public XCTest runner contains seven methods. The first uses public
Settings UI to traverse Accessibility, Keyboards & Typing, and Full Keyboard
Access, then observes/enables its native switch. Each screen/search attempt,
transition and final switch state is captured as AX text and screenshot
attachments. Traversal is capped at five swipes per named row with bounded waits.
A setup failure leaves the six dependent app methods explicitly skipped/unrun.
No host Mac settings, private preference keys or deep links are used.

The installed official SDK headers declare `typeKey(_:modifierFlags:)` for iOS
and `hasFocus`; their exact bytes are snapshotted and verified. The official
[iOS 26 guide](https://support.apple.com/en-lamr/guide/iphone/ipha4375873f/26/ios/26)
provides the Settings route and default Tab, Shift-Tab and Space commands.
The runner cross-build verifies these public APIs against the pinned SDK;
compilation does not qualify native keyboard delivery.

Each mode runs from both initial values and resets the fixture anew:

| Mode | Required actual public inputs and observations |
| --- | --- |
| Enabled | At most 12 Tab inputs must reach the authored toggle; Space toggles exactly once, second Space reverses once; forward navigation reaches the plain reference then next target, reverse navigation returns through those actual neighbors. |
| Stale gate | Reach native toggle focus, close the existing gate, observe silent Space without binding loss, reopen, and require one accepted Space transition. |
| Disabled | Reach focus, disable, record actual immediate focus; if focus remains, record silent Space there; Tab must reach an enabled neighbor, Space must activate that actual neighbor while authored values stay silent, and reverse navigation must exclude the disabled toggle. |

Each key has a raw app baseline/after capture plus a closed native AX witness
from the three fixed element identifiers. The witness binds case, bridge
generation and action index, records monotonic times around public `typeKey`,
and contains before/after `hasFocus`, enabled/selected metadata and geometry.
Native AX focus and the app's `isFocused` observation are reported separately;
this packet does not qualify focus paint/compositor parity. The plain reference
is a native neighbor; no reference value-change event is assumed.

The same `evaluate` endpoint accepts the selected keyboard witness. It is
validated and durably saved before the inherited native observation/evaluation.
Only its in-memory baseline is annotated for the oracle; raw app captures remain
unaltered. Verdicts include the exact witness and host binding for replay. Missing,
duplicate, reordered, stale, wrong-case/action/generation or malformed evidence
fails. A `typeKey` return requires the corresponding actual native focus
traversal or exact application transition; direct primary callbacks never count
as keyboard delivery. The existing resume/reset/set-on/stale/disable commands
are allowed only at fixed per-case phases. No endpoint, arbitrary command,
path, process, device or input authority is added to the bridge.

The reviewed stable observation reader and its absolute-deadline adapter are
reused unchanged. The original root-owned simulator lifecycle, instance bounds,
baseline preservation and independent cleanup remain inherited. A narrow fixed
artifact adapter exports official xcresult attachments before ephemeral bundle
cleanup after test return, failure or timeout when the owned bundle exists.
It checks the canonical owned workspace identity and uses only the fixed
`xcresulttool export attachments` command, a 30-second timeout and fixed packet
output directory. The export is inventoried with size/count bounds and digests.
Export failure is recorded and never suppresses cleanup; missing required
Settings/export evidence leaves qualification false.

Twenty host test methods cover synthetic phase/route outcomes, negative
focus/value/event/type/counter/order/identity mutations, fixed command cursors,
witness persistence/replay, absent keyboard delivery, and export success,
timeout, failure, unsafe-path and missing-setup behavior. These are host controls,
not native keyboard or Settings receipts.

Preparation commands from the repository root:

```sh
python3 -B verification/apple-toggle-keyboard-focus/prepare_runner.py
python3 -B verification/apple-toggle-keyboard-focus/record_provenance.py
python3 -B verification/apple-toggle-keyboard-focus/host_controls.py
python3 -B verification/apple-toggle-keyboard-focus/seal_packet.py
python3 -B verification/apple-toggle-keyboard-focus/run.py verify
```

After root independently reviews the actual seal, root owns this native command:

```sh
python3 -B verification/apple-toggle-keyboard-focus/run.py run --scope interaction --reviewed-seal ACTUAL_REVIEWED_SHA256
```

Recovery uses this packet's `run.py cleanup --scope interaction`. Before editing
a rejected sealed attempt, preserve its exact named bytes with
`reject_preparation.py 'Concrete rejection reason'`. Phones remain disconnected.
Physical keyboard/VoiceOver, compositor parity, live Apple integration, FieldLog,
store, customer, operational and GA gates remain pending.
