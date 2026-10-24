# V4 Settings diagnostic: retained runtime analysis

Status: failed diagnostic, preserved unchanged. Offline replay exits zero and
matches the runtime's diagnostic summary exactly; that is replay agreement, not
setup acceptance. Root's review is
`verification/apple-toggle-keyboard-focus-v4-root-review/runtime-review.json`,
SHA-256 `8eb08e6e2e3767eeba2cf3191c75385db49813d25615f0ff77c5488323ee5f1b`.
The separate analysis directory binds every inspected runtime file and source.
No V5 implementation, build, native launch, UI action, bound change or
qualification change occurred.

## Observed sequence

The journal contains 22 records, sequences 0–21, two complete AX files totaling
47,626 bytes and no PNG. It records Settings launch, the first route search,
Accessibility tap and its post-navigation observation. There is no switch action,
three-second anchor, subsequent route tap, terminal capture or completion marker.
All six application cases are unrun.

The initial search snapshot at sequence 2 reports a foreground, enabled,
hittable Cell with positive frame `{{16,432.333…},{370,52}}` but empty identifier
and label. The raw AX tree, `settings-0002-ax.txt:62`, shows that anonymous Cell
contains a Button identified `com.apple.settings.accessibility`, labelled
Accessibility, and a StaticText labelled Accessibility. The existing expected-row
predicate therefore correctly marks the captured container unmatched. Its native
child label was not part of the structured route witness.

After the actual tap, sequence 10 still finds the old Cell present at
`{{-105,432.333…},{370,52}}`, unhittable and anonymous. It is neither the expected
named row nor the explicit absent-selector exception. The corresponding AX tree
contains an Accessibility navigation bar at line 13 and the new page content.
Thus the route-opened witness sampled the retained old selector rather than
structured destination-page evidence.

On that page, `settings-0010-ax.txt:267` places the Keyboards & Typing Cell at
`{{20,1057},{362,53}}`; its Button and StaticText descendants at lines 272–273 have
zero frames. The XCTest log next queries that StaticText, then captures a tree.
There is no swipe or Keyboards tap before the host records
`ValueError: Attached Settings geometry`.

Frozen Swift source lines 127–134 select a cell or text, call `capture`, and only
then test exists/hittable or perform the bounded swipe. The host's snapshot
validator requires positive dimensions for every existing element, including a
nonactionable search result. This explains how an offscreen search observation
can abort the search before its swipe. The rejected request body was not retained;
its exact attributes cannot be asserted. A host-only candidate reconstructed
from the retained zero-frame StaticText reproduces that same validator error and
is explicitly labelled reconstructed in `analysis.json`.

## Failure classification and exports

The first durable host failure is geometry validation. The last accepted receipt
is only 6.244 seconds after start, with 22 accepted requests against limits of
29 seconds and 2500 requests. The official XCTest case lasts 8.911633 seconds.
There is no evidence that either total budget was exhausted.

Swift `post` line 19 maps a broken transport latch, request cap and elapsed
deadline to the same `budget` error. Lines 36–38 latch transport failure; later
terminal/termination/completion attempts report `budget`. The runner does not
retain the HTTP rejection status/reason as a causal witness. Its final reported
`budget` therefore cannot identify the initial cause. Preserve the native result
as reported; do not relabel it a successful or expected qualification boundary.

xcodebuild terminates with exit 65 after 33.254 seconds. Official summary/tests
report one failure, zero passes, zero skips, with `caught error: "budget"`.
Attachment export succeeds, unlike V2: it contains a 6,198,404-byte MP4 recording
and two binary-plist activity archives (UI snapshot and synthesized event), not
the three requested durable AX/PNG pairs. Their manifest, sizes, hashes and
archive class inventory are retained in the analysis. No recording-frame content
is inferred here. No 600-second post-test hang recurred.

The outer strict assertion is consequent on this real failed XCTest/bridge run,
not the expected exit-zero diagnostic-only boundary. All five cleanup operations
passed; owned simulator `56B1AE34-A005-4D55-BC9D-C022C6EBD269` and the ephemeral
workspace are absent. Native keyboard, carrier and GA qualification remain false.

## Minimal next-source proposal, awaiting root selection

1. Preserve raw anonymous container metadata and add one fixed named-descendant
   witness for each public route. Bind the actual tap target to its queried
   StaticText/Button descendant with the exact route label, native type and
   positive actionable geometry. The first observed descendant Button identifier
   is `com.apple.settings.accessibility`; other route identities remain validation
   expectations until observed. Do not rewrite the Cell's empty fields into the
   child's label. For post-navigation evidence, sample the fixed destination
   navigation bar/page context and retain the old selector separately; a retained
   offscreen old Cell must not be described as absent or as destination evidence.
2. Separate nonactionable route-search shape from actionable geometry. Permit a
   finite zero-frame, explicitly unhittable search observation as diagnostic
   evidence so the existing bounded swipe can execute. It cannot bind a successful
   route tap. Keep positive geometry and expected native metadata mandatory for
   actionable targets and every actual switch/window sample. Keep the tap policy,
   all attempt/time/payload bounds and anchored three seconds unchanged.
3. Preserve the first named error before secondary capture/teardown, distinguish
   broken transport from genuine budget exhaustion, and retain bounded HTTP
   rejection status/reason. A selected host correction could quarantine only a
   well-framed, closed Settings metadata record rejected by semantic validation,
   under a fixed failure filename without advancing accepted cursors. Do not
   retain arbitrary framing bodies or resume an unusable cursor. This is a
   proposed explicit evidence extension requiring root selection, not implemented
   behavior. Preserve terminal screenshot/AX through the existing finite paths
   where possible; missing image evidence must remain incomplete.

Required new negative controls: the captured anonymous Cell alone must fail route
identity; a correct named descendant must remain bound to its actual target;
wrong-label/unrelated-child/frame-mismatch proofs must fail; a retained negative-x
old selector cannot establish destination success; zero-frame/unhittable searches
must remain raw and unable to authorize a tap; zero-frame hittable targets and
all invalid switch states must still fail. Exercise HTTP 400 with geometry reason
versus genuine elapsed/request budgets, first-error preservation through secondary
capture failure, quarantined-record bounds and nonadvancement of time/sequence,
and successful export versus unavailable export. Replay the actual V4 failure
unchanged and retain all earlier controls/findings.

Reproduction from the repository root:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v4/replay.py
python3 -B verification/apple-toggle-keyboard-focus-v4-runtime-analysis/analyze.py
```
