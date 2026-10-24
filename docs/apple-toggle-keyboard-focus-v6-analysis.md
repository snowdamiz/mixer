# V6 failed Settings setup: offline analysis and V7 proposal

V6 completed its setup diagnostic and failed the actual public Settings enable
assertion. The single XCTest method failed, `xcodebuild` exited 65, and the outer
runtime exited 1. This is an observed setup failure, not the expected inherited
diagnostic qualification boundary. No application case ran.

This analysis binds root selection
`37fad53c29f09de16730107e9d8d80cd78ab111a34bbecf2b6a517fa17b1b681`,
the 184-file preparation seal
`5b2743fd61dbabc95abc6e50468347efe406953fb1314785b17013922b6438fd`,
and the 158-file independent review seal
`24dfa4e5b4b354447fc03686d8b8732c3387ff019f6305f0dd6fc52fb9bcd1c0`.
All sealed input hashes were independently checked before and after replay.
`review-inputs.json` inventories 660 exact input paths, including actual runtime
files, public SDK declarations, root review, sources and earlier sealed evidence.
The root selection's source revision context is
`06147f0ef6c704a08b6fac7561ad98bcc5165d46`; the unchanged runner's historical
source revision context remains `9a9c0e000234b07a92c4484979d3587f7f24df48`.
No new Git revision, compilation or native execution is asserted by this analysis.

The actual environment was iPhone 17 Pro, arm64, iOS Simulator 26.5 build 23F77,
owned instance `A44DD179-A70C-4154-99D9-C0CB86FE8360`. The recorded command used
Xcode 26.6 `test-without-building` with exactly
`-only-testing:MixerToggleUITests/ToggleUITests/test000PublicSettingsFullKeyboardAccess`,
parallel testing disabled, and maximum simulator destinations 1.
`actual-native-command.json` retains the full original argv, stdout and stderr.
It is read historical evidence; this analysis did not execute it.

The real V6 replay reconstructed all 275 durable records, 275 requests and final
sequence 274, and exactly matched `runtime-verdict.json.settingsDiagnostic`.
There are no bridge failures, pending uploads or missing completion markers.
All three destination captures follow their own accepted tap completion and
preceding tap sequence. That V6 ordering repair behaved as specified. Reached
destinations do not erase a false row binding or a switch that remained off.

The final official synthesized event attachment,
`A6931A16-533A-45C4-AFBD-F0C3555C24F7`, contains a tap down/up at
`(201.0, 160.3333282470703)`. Both points equal the center of the structured
outer switch frame `(36, 146.3333282470703, 330, 28)` selected by
`settings.switches["Full Keyboard Access"].firstMatch`. The public test log
identifies this call as `Tap "FKAEnabledSwitch" Switch`. The AX diagnostic shows
that composite contains a labeled button and an unlabeled switch leaf, with
rounded leaf frame `(305, 146.3, 63, 28)`. The actual point lies outside that
leaf and just to the right of the label's rounded right edge 198.7. It hit the
composite center gap; a label hit is not established. `decoded-official-events.json`
retains all five decoded synthesized events, including three route taps, one
scroll and this one conditional switch tap. Decoding uses `plistlib` data only;
no archived Objective-C class is instantiated.

The before, after and terminal PNGs are byte-identical, SHA-256
`92f094dd856480874c8d3db60b5b30f5dd7c1af9bb679a2c1322385d2543f669`.
The before PNG was visually inspected and shows the switch off. All twelve
structured before/after/poll/terminal samples also report string value `"0"`.
The anchor is 914614.2180647084, the deadline is 914617.2180647084, and no enabled
sample occurred within that exact three-second interval. The final poll began
before the deadline but its observation completed afterward; it is off and gives
no enabled credit. No additional timeout or retry is justified by this evidence.
Whether an actual leaf tap enables Settings still requires a selected native run.

Route 2 has a separate evidence mismatch. Its actual container is the identified
`FULL_KEYBOARD_ACCESS` cell labeled `"Full Keyboard Access, Off"`, with the
exact labeled descendant text and contained geometry. The tap's public target
metadata matches that search, and the destination navigation bar matches after
the completed tap. V6 `route_target` permits only empty or exact route-name
container labels, so this bounded status suffix makes `rowMatched` false.
Thus `routeTaps` remains `[0,1]`, although claimed route indices are `[0,1,2]`.
Even a future enabled switch sample cannot satisfy the complete setup contract
until that row witness is represented correctly. This is an overly narrow
container-label predicate, not evidence that the observed navigation failed.

The proposed V7 repair has two bounded changes:

1. Resolve exactly one public switch composite with identifier
   `FKAEnabledSwitch` and label `Full Keyboard Access`. Obtain its immediate
   `children(matching: .switch)` through public XCTest APIs, require exactly one
   leaf and no switch children beneath that leaf, and reject ambiguity or missing
   targets. Bind both snapshots, exact public-query relation and counts, bundle,
   foreground state, enabled/hittable flags, raw string values and geometry.
   Require parent and leaf values to agree in `{"0","1"}`. The unlabeled leaf
   remains actionable only through this exact identified parent relation.
   Require positive intersecting frames and a selected leaf center strictly
   inside parent, leaf and actual screen bounds. The observed leaf extends two
   points past the parent's right edge, so full rectangular containment would
   reject this observed layout. No arbitrary edge tolerance is proposed. Use the
   resolved public leaf for the existing single conditional tap, retaining the
   identified parent as the state oracle. Serialize target/binding metadata and
   tap start/completion into the existing bounded observation/mark flow, require
   action binding to the preceding observation, and preserve completion-to-capture
   ordering. A subsequent official event export must confirm the chosen action
   point was inside the bound leaf. Do not send an input command from the host.
2. For route 2's descendant relation only, additionally admit the exact container
   labels `Full Keyboard Access, Off` and `Full Keyboard Access, On` when its
   identifier is exactly `FULL_KEYBOARD_ACCESS`. Preserve all existing descendant
   identity, label, state, geometry, tap/search identity and same-route temporal
   checks. Reject arbitrary prefixes, extra suffixes and wrong identifiers. The
   `On` fixture is a synthetic bounded alternative, not an observed V6 row.

The 37 executable host controls cover actual V6 rejection, the bounded proposal's
Off/On alternatives, extra labels, wrong ID/type/state, mismatched or disjoint
descendants, wrong route/relation, composite-as-leaf, absent/ambiguous query counts,
nested nonleaf targets, wrong leaf identity/value/state, zero/disjoint/edge geometry
and wrong parent. These are review models in `analyze.py`, not V7 runtime code.
The actual leaf was never queried for hittability or captured as structured
metadata in V6; proposed leaf flags are explicitly synthetic. Public
`XCUIElement.h` defines `tap` as using a computed hittable point and provides
immediate-child queries. It also declares `debugDescription` unsuitable as a test
dependency. The retained AX text is observational only; it cannot select or
authorize the future action. Installed official declarations are copied and hashed
in this lane. The video is inventoried but was not watched or decoded.

V7 must retain the anchored three-second window, 29-second diagnostic, two-second
request maximum, 600-second session, 2,500 requests, 100 events, 32 upload slots,
7,000,000 decoded bytes, 3,072-byte chunks, existing per-payload limits, 40 polls,
route attempts and all first-error/transactional rejection behavior. No budget,
time, route-order, strict-oracle, app or transport expansion is proposed. A fresh
runner build is required because the native target selection changes. Root must
select implementation, independent host review and official compiler evidence
before selecting another one-instance setup-only diagnostic. Fresh controls must
exercise the actual new Session and native selection helper, including stale
bindings, rejection rollback and persistence, initial-off single-tap and initial-on
zero-tap behavior, exact before/equal/after deadline boundaries, and V6's frozen
failed journal. Host contract models cannot stand in for that verification.

The recorded lifecycle shows all five cleanup steps passed, the owned simulator
and ephemeral workspace removed, and baseline states preserved. Analysis did no
live instance query or cleanup; root's independent runtime review binds that
historical cleanup evidence. No instance was created by this lane.

All six application keyboard cases remain unrun. Native keyboard qualification,
carrier acceptance and GA remain false; physical phones remain disconnected and
deferred. The prior V3/V5 failures remain unchanged in their sealed packets. This
lane writes only its new verification directory and this document; root retains
runtime acceptance, tracking and Git ownership. Exploration read/decoder errors
are disclosed in `exploration-notes.json`. No existing audit script was rerun.

Recheck without changing any packet:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v6-analysis/analyze.py --check
```
