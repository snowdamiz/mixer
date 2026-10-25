# Apple focus diagnostic v1: retained evidence analysis

The selected run still fails the first acquisition Tab. The new diagnostic establishes that the app's native carrier focus clears during the public key call and that all three fixed AX targets report false afterward. It identifies no replacement focus item. It does not justify a product fix or an oracle exception.

This is offline analysis of packet `d7c4c0f146434eeb7323036809acb5b4a80d41ff10f596eed8c25bdaa314e783`, with inherited source label `ba9ad4372f94463ba4d363cdfd76dd565c96413f`. No Git query, service, native run, simulator/device query, UI operation, or capture was performed in this lane. Physical phones remain disconnected and deferred.

## Exact endpoints and timing

The app trace is nested under `observation.focusContexts` in `runtime/captures/0001-after-1.json`. Its eight ordered entries preserve the two-entry baseline prefix, with zero dropped entries. The sole concrete endpoint has:

| Field | Observed value |
| --- | --- |
| Class | `AuthoredToggleCarrier` |
| Identity | `ObjectIdentifier(0x00000001035a8600)`; equals the before/after app carrier state identity |
| Endpoint identifier | Explicit `null` |
| Local frame | `(287, 30, 63, 44)` |
| Window frame | `(303, 244, 63, 44)`; agrees with authored AX geometry |
| Attached to window | `true` at each concrete endpoint observation |

Every other endpoint is explicit `state: "null"`, with null class, identifier, identity, frame and attachment fields. No `UIButton`, foreign item, or concrete off-scope destination appears. The identifier observer uses a `UIAccessibilityIdentification` cast; the carrier source separately overrides `accessibilityIdentifier`, and AX consistently returns `authored-toggle`. The null trace identifier must be preserved as observed; it does not establish that the actual carrier lacks its authored identifier.

The `XCUIElement.typeKey(_:modifierFlags:)` Tab call spans uptime `929382.6786694584`–`929383.0009764167` (322.307 ms). All six new context entries occur inside it; all eight entries have raw heading `0`.

| Context sequence | Observer | Milliseconds after key start | Previous → next |
| --- | --- | ---: | --- |
| 3 | carrier | 102.613 | same attached carrier → null |
| 4 | controller | 109.454 | same attached carrier → null |
| 5 | carrier | 313.368 | null → same attached carrier |
| 6 | controller | 315.248 | null → same attached carrier |
| 7 | carrier | 317.535 | same attached carrier → null |
| 8 | controller | 319.897 | same attached carrier → null |

App focus events independently record false at +107.640 ms, true at +313.458 ms, then false at +317.639 ms. These are carrier/controller observations of the recorded transitions, not six distinct user actions. Attachment is established at the observed contexts; continuous attachment and root cause are not established.

## AX timing and unchanged strict result

The authoritative before AX sample reports only `authored-toggle` focused. The authoritative after sample reports all three fixed IDs false; each remains present, enabled and hittable with stable identifier, label, selection and frame. App carrier `isFocused` agrees before and after. There is no paired-focus disagreement or missing app focus-update signal, and no semantic activation or value change.

The added timing record explicitly marks its reads sequential and non-authoritative. The full before observation spans 3334.061 ms and the after-primary observation 3226.884 ms. Each includes three per-row existence/property reads, so neither is an atomic observation. The single focus-only follow-up completes in 16.070 ms, within its 250 ms allowance, and reads all three IDs false. It supports the retained final state at three later observation points; it does not prove continuous absence of focus, alter the authoritative sample, or identify a destination outside those IDs. No polling observation was retained for this acquisition action.

The unchanged v2 oracle and its exact pure dependency closure were replayed against the retained before/after app observations and actual witness. The full oracle result matches the recorded result after removing only runtime reporting fields `ownedSimulatorIdentity`, `generation`, and `actionIndex`; the latter two were checked against the witness binding. The sole false predicate remains `actualNativeFocusTraversal`. The failed bridge branch sets `failed = true` without advancing acquisition count, phase, native metadata or last-after time. No fallback sample or native retry was used.

Reproduce the host analysis from the repository root:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -I -B verification/apple-focus-diagnostic-v1-analysis/reanalyze.py
```

The final run passes 39 executable checks. [receipt.json](../verification/apple-focus-diagnostic-v1-analysis/receipt.json) records the command, Python version, inherited revision label, selected source-tree digest, script hash, input hashes and nine unchanged oracle/case member hashes. [summary.json](../verification/apple-focus-diagnostic-v1-analysis/summary.json) retains the compact observations and replay outcome. [source-excerpts.json](../verification/apple-focus-diagnostic-v1-analysis/source-excerpts.json) preserves four source excerpts and their full-file hashes, checked against the packet-bound accepted-source manifest. Extraction is temporary and removed; no hosted authority/catalog or native orchestration module was imported.

## Outcome, limits and smallest useful next diagnostic

Existing official xcresult JSON reports two methods: public Settings setup passed; `test010EnabledFromOff` failed. The observed command exited 65 in 58.214 seconds, both streams reached EOF and the owned process group was absent. The earlier 600-second finalization stall was not reproduced in this one run. Existing lifecycle evidence reports all five cleanup resources passed, the owned UUID `0C8B440A-4FBD-4AAE-A672-DCDE2D3ED120` absent, baseline states preserved and ephemeral capability configuration removed. These statements read existing receipts; root owns final aggregate sealing and independent cleanup verification.

The evidence narrows the failure to a native focus transition away from the sole concrete carrier, followed by final app/AX agreement on loss. It does not establish whether the carrier, layout, native keyboard environment, or input delivery causes it. Comparator behavior was not observed, the other five keyboard cases remain unrun, and carrier, physical-device, signing, store, FieldLog, operational and GA gates remain pending.

The smallest useful next selected diagnostic is one first Tab starting from the **existing plain UIButton reference**, under the same Settings setup, layout, public key API, bounded observers and unchanged strict predicates. Make only the diagnostic initial-focus preference select `referenceButton`, require that fixed reference to be observed focused before the key, then retain its single first-Tab result. This can test whether the same loss occurs from an ordinary native neighbor without adding a new fixture or changing authored carrier behavior. A successful reference transition would narrow the failure; it would not prove a carrier cause or qualify the full case. A failed transition remains failure. No such run is selected or performed here, and no automatic retry or broad AX inventory is justified.
