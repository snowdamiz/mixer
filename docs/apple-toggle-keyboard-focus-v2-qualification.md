# Private keyboard and focus v2 preparation

This is a separate oracle/cursor wrapper selected by root in
`verification/apple-toggle-keyboard-focus-root-review/v2-repair-selection.json`.
All 81 named bytes of the original keyboard seal remain unchanged. The app
source/archive, public seven-method XCTest runner source/product tree/archive,
and all runtime authority/lifecycle code are reused identically. Nothing is
recompiled and preparation performs no native instance discovery or execution.

The original oracle accepted synthetic observations with application focus false
while authored AX focus was true, and accepted a changed AX toggle label. Those
are oracle findings, not native observations. V2 requires each paired app
`focused` state to equal the authored element's native AX `hasFocus`, before and
after every input. Disagreement is failing evidence pending native analysis.
No equivalence between the platform focus mechanisms is assumed or waived.

The authored AX label must equal its corresponding application label. Every one
of the three fixed native identifiers and labels must remain stable before/after
each key and across successive keys and fixture commands. The existing app
already records `stateChanged("focus")` from `didUpdateFocus`, and samples
`toggle.isFocused`. When app focus changes, v2 requires a fresh captured focus
event whose state matches final app focus. Missing or inconsistent signals fail;
this packet does not add app instrumentation or infer successful focus delivery.

Acquisition deliberately has a strict three-element scope: every Tab must change
to an observed fixed native element, with at most 12 acquisition steps. An
outside-fixture or unchanged result fails. The packet does not qualify general
system navigation or traversals through unobserved focus groups. Fixed neighbor
order, real Space transitions, stale/disabled behavior and all prior checks remain
unchanged.

Twenty-nine host methods pass: the 20 previous runtime/oracle controls with
synthetic app focus aligned to their paired AX observations, plus nine new v2
methods. Explicit negative controls cover four before/after focus disagreements
in both directions, three authored-label/current-app mismatches, six fixed-ID
substitutions, six label changes, three between-key metadata changes, two
missing/incorrect focus signals, two nonfixed/unchanged acquisition results, and
the two root synthetic regressions. These are host controls, not keyboard evidence.

The unchanged public Settings method still gates all six application methods.
Its failure leaves those cases skipped/unrun. The reviewed same-endpoint
witness/command adaptation, stable reader/deadlines, fixed owned xcresult
attachment exporter (including failure/timeout attempts), one-instance lifecycle,
baseline preservation and independent cleanup remain unchanged. Root alone may
select and run the new seal after independent review.

Prepare and review from the repository root:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v2/prepare_reuse.py
python3 -B verification/apple-toggle-keyboard-focus-v2/host_controls.py
python3 -B verification/apple-toggle-keyboard-focus-v2/seal_packet.py
python3 -B verification/apple-toggle-keyboard-focus-v2/run.py verify
```

Root-owned native entry point after selection:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v2/run.py run --scope interaction --reviewed-seal ACTUAL_REVIEWED_SHA256
```

Recovery uses this packet's `run.py cleanup --scope interaction`. Before editing a
rejected sealed v2 preparation, preserve it using this packet's
`reject_preparation.py 'Concrete rejection reason'`. Do not edit the original
81-file packet. Phones stay disconnected; physical keyboard/VoiceOver, compositor
parity, live Apple integration, FieldLog, store, operational and GA gates remain
pending.
