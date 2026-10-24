# Authored Android toggle: independent host review

Candidate 3 passes independent source, policy, compositional build and APK
review. Native runtime acceptance is pending the separately reviewed runner and
new emulator observations. Live Android sources remain unchanged.

The three changed Java sources use one geometry for drawing and touch, retain
the ordinary checked listener as the proposal path, and fence touch completion
against the current binding and original input authority. Cancellation clears
local ownership before calling the acquired parent. A rebind or retirement
during a callback is rechecked before proceeding. Post-click reconciliation
uses the latest binding under the existing changing guard. Candidate 2's
unconditional keyboard pressed-state clearing is absent from candidate 3.

Root independently recompiles the three changed production families and four
unchanged fixture classes against verified baseline classes, then rebuilds DEX
from the complete 163-class inventory. Every resulting class and DEX byte matches
the candidate. Unchanged classes were read from the previously qualified archive;
this is a compositional rebuild. The original 20-action fixture is byte-identical,
all eighteen native libraries are unchanged, and APK changes are limited to DEX
and the three private debug signature entries. Official signature and alignment
checks pass.

The actual production policy passes its 33 host cases and 3,556 independently
authored assertions spanning seven densities, both layout directions, both
starting states, endpoint and corridor boundaries, cancellation and binding
identity. These host checks do not establish native event dispatch or authoritative
engine commits. The separate supplement likewise requires its own exact-source
review and native run; its component proposal counts cannot substitute for the
ordinary coordinator fixture.

The [baseline-2 receipt](../verification/android-authored-toggle-input-review/baseline-2/receipt.json)
binds the 106 source inputs, compiler/tools, outputs, retained classes and cleanup.
All command groups and 878,770 bytes of owned scratch were removed. Baseline-1
retains a root helper-hash transcription failure before compilation or native
dispatch; no product defect was inferred from it.

Candidate source closure:
`509ef6a00bbaf034ebbe9dd6d8d3b8716fe96d9600e7fe8fa92fac41ebca3f99`.
APK SHA-256:
`24d75ecc19d08f44adc95e2db123936687929ca5a9fcd71f19189865240f6d18`.
The old P03 native drag failure remains a failure. Full appearance parity,
renderer transaction/lifecycle cases beyond the fixture, physical phones,
public/signed transport, FieldLog and GA remain pending.
