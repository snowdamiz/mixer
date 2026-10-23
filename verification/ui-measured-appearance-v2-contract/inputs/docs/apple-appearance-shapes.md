# Grouped-list and switch shape evidence

This bounded supplement retains the native Apple reference and proposes concrete
shared geometry for root/design review. The [receipt](../verification/apple-appearance-shape-measurement/receipt.json),
[analysis](../verification/apple-appearance-shape-measurement/analysis.json),
[gallery](../verification/apple-appearance-shape-measurement/gallery.html) and
[machine-readable candidate](../verification/apple-appearance-shape-measurement/proposed-shared-recipe.json)
separate public UIKit properties, exact screenshot samples, and authored shapes.
The proposed curves remain measurably different from the native raster. They are
not accepted shared defaults or a completed §8.3 parity result.

The source is an isolated derivative of the immutable measurement harness and
frozen SDK. It adds public visible-cell observations and renders public shape
candidates offscreen. It adds no visible modifiers. All 12 native captures have
exactly equal decoded pixels and node records to their parent measurement case.
The eight historical cases also have exactly equal decoded pixels to the original
uninstrumented reference: zero differing pixels in each 1,206×2,622 image. A
single additional Controls capture validates the later cell-height path export.
This proves integrity in these retained simulator cases; it does not prove native
behavior, Android parity, physical appearance, publication, or qualification.

The dedicated simulator is `MixerAppearanceShapes`; it is separate from the
reference and font-profile simulators. It uses iPhone 18 Pro, iOS 27.0 `24A434`,
402×874 logical points and 3× scale, built with Xcode 27.1 `27A9275`, SDK 27.1 and
Apple Swift 6.4. Capture commands, versions, source stages, digests, logs and
output manifests are retained. Only this dedicated simulator was booted/changed;
it was shut down after both runs. No physical-device inventory or run occurred.

## What public native objects expose

Across the retained large and accessibility-medium controls, typography, layout,
and Arabic RTL cases, public `UICollectionView.visibleCells` contains
`UICollectionViewListCell` values. Every observed cell has `layer.cornerRadius=0`,
`layer.cornerCurve=continuous`, `backgroundConfiguration.cornerRadius=0`,
`backgroundView=nil`, and `selectedBackgroundView=nil`. Content-view corner radii
are also zero. Background configuration insets and stroke width are zero. The
visible outline plainly remains rounded, so these zero/nil properties do not
identify a native corner radius or hidden path. They are retained unmodified.

Public `maskedCorners` values distinguish observed row positions: 3 for first,
0 for middle, 12 for last, and 15 for a single-cell section. These flags do not
expose the drawn curve. No private class, reflection, KVC, selector, sublayer
inspection, or private ancestry-to-node mapping is used.

Public [separatorLayoutGuide](https://developer.apple.com/documentation/uikit/uicollectionviewlistcell/separatorlayoutguide)
rectangles on interior rows are 338×⅓ pt, at x=32 inside 370 pt cells at x=16.
Final-row guides can be 370 pt wide even when no separator is painted. Public
guide existence is therefore not a visibility rule. Raw boundary scanlines show
two painted pixel rows at 3× (⅔ pt of raster occupancy), with exact colors
`#E8E8E8` light / `#38383B` dark. The painted spans are x=96…1109 inclusive in
pixels: 1,014 pixels, or 338 pt, inset 16 pt from each cell edge. These facts hold
for the measured role rows, wrapping rows, controls, accessibility, and RTL; the
raw per-row samples remain in the analysis. Raster occupancy is not an assertion
that UIKit declares a ⅔ pt separator property.

## Explicit grouped-list recipe proposal

Use separate fields for outer group inset 16 pt, row content inset 16 pt, row
height policy, header placement, interior separator, and closed group outline.
At this width the resulting group edges are x=16/386, with ordinary content
leading x=32 in LTR and trailing x=370 in RTL. Symmetric separator insets remain
16 pt in RTL.

First header tops are 10 pt below the measured native List top. Header-to-first
cell gaps measure 9⅔–10 pt; previous group bottom to next header top measures
27⅓–27⅔ pt. Thus a concrete candidate uses 10 pt after each header and 27⅔ pt
before subsequent headers, with explicit pixel rounding. The resulting total
intergroup space includes the header's own 20⅓ pt large / 33⅔ pt accessibility
height: observed group-to-group gaps are 57⅔–58 and 71–71⅓ pt respectively. A
single fixed 16 pt groupGap cannot describe these named contexts. Headers remain
separate structural content with their measured typography; native offsets
depend on navigation/List layout and should not be imposed from window y=0.

Large rows match `max(52, topLevelContentHeight + 30)` in these fixtures, with
content vertically centered and at least 15 pt above/below. This includes title,
wrapping/max-lines, explicit stacks, fields and button roles. Accessibility body
and button rows are 63⅔ pt, wrapping and stack rows grow further. The caption
row is 59 pt although its measured caption height plus 30 is 56⅓ pt; the public
environment minimum remains 52. A candidate profile floor of 59 reproduces this
case, but is an authored bounded rule, not a measured universal native minimum.
The accessibility filled-field cell is 65⅔ pt, ⅓ pt above its measured content
height plus 30. Preserve that rounding residual instead of claiming an exact
general row-height formula.

Toggle node geometry follows the label: 20⅓ / 33⅔ pt. Its public UISwitch is 28 pt
high even when the label node is shorter. Center the visual track in the resolved
row independently. Applying 30 pt padding to an HStack whose content height is
the larger of track and label would incorrectly make ordinary rows 58 pt here.

For the outline, the concrete candidate is a shared continuous 26 pt closed
cubic curve. The retained public `RoundedRectangle.path(in:).cgPath` outputs
include a 370×208 group and 370×52, 370×63⅔ and 370×101 cell cases. They prove a
public closed-path representation can be generated and translated to both native
toolkits without private access. Their literal move/line/cubic/close coordinates
are in the candidate JSON; adapters can consume the same vector commands rather
than selecting unrelated platform rounding defaults.

This candidate does not identify the native group curve. Native top-left
frontiers vary with first-cell height near the vertical tangent. Comparing the
same 100 scanlines with explicit 0.5 encoded-RGB coverage gives 60–79 exact
frontier rows out of 100 for the full-group candidate; bounded cell-height
candidates improve some cases to 86–88 rows. Maximum difference is 9–10 pixels
at the first scanline, with later differences usually one pixel. The coverage
threshold is an analysis convention, not physical alpha. The native group/cell
clipping relationship and antialiasing remain unresolved. Root must explicitly
accept an authored shared outline or continue that curve work before calling
this an exact preservation of the Apple shape.

## Explicit switch recipe proposal

Public UISwitch outer frames are 63×28 pt in all measured profiles, while the
intrinsic size remains 61×28 pt. No non-nil `onTintColor` or `thumbTintColor`
identifies a shape or paint. Static raw scanlines support the candidate below:

| Quantity | Concrete candidate | Evidence boundary |
| --- | --- | --- |
| Track | 63×28, continuous closed curve requested radius 14 | Public outer bounds plus raster contour; authored path |
| Thumb | 37×24, continuous closed curve requested radius 12 | Interior raster spans plus authored path; not a 27 pt circle |
| Thumb inset | 2 pt vertically and at the selected end | Center scanlines show 109 fully flat pixels plus two edge pixels across a 111 px candidate footprint |
| Thumb x | 24 when `isOn != isRTL`, otherwise 2 | Raw RTL checked thumb is physically left, checked LTR right |
| Thumb y | 2 | Bounded scanlines and candidate rectangle |

Normal and disabled checked LTR switches and checked RTL switches are measured;
accessibility-medium retains the same outer/control size. The label/control
layout places the public control at x=309 in LTR and x=32 in RTL. Mirror both
control placement and the selected thumb end.

| Static interior paint | Light | Dark |
| --- | --- | --- |
| Checked track | `#34C759` | `#30D158` |
| Unchecked track | `#C5C5C7` | `#5A5A5E` |
| Disabled checked track | `#99E3AC` | `#26773B` |
| Normal thumb | `#FFFFFF` | `#FFFFFF` |
| Disabled checked thumb | `#FFFFFF` | `#8E8E8F` |

Use these as distinct per-state shared paint candidates. Applying one global
disabled opacity or keeping the dark disabled thumb white changes measured
pixels. Disabled-off is not present in the immutable fixture and is unresolved.

The public track/thumb cubic paths are feasible shared static shapes but are not
exact native paths. In ten fully visible measured switches, the track-side
half-coverage frontier differs by at most 1–2 pixels, and the thumb frontier by
at most two pixels at 3×. Track sampling uses the side opposite the thumb; thumb
sampling explicitly excludes the outer-track neighborhood because light canvas
and thumb can have identical RGB. Raw scanlines are the primary evidence; the
thresholded comparison cannot identify native alpha, shadows or compositing.
Pressed, dragged, intermediate animation, focus, disabled-off, lighting/shadow,
other scales and other OS versions remain unmeasured.

## Verification and remaining boundaries

Run `python3 verification/apple-appearance-shape-measurement/scripts/test-analysis.py`
for decoder, projection, exact-difference, closed-path and retained-evidence
checks; `scripts/verify-seal.py` validates retained bytes, both source stages,
parent inputs, and this document. `scripts/analyze.py` regenerates exact pixel
and public geometry comparisons from retained artifacts. Capture scripts create
or use only their own named simulator, never phones; the supplement records its
separate source stage and commands.

The current product renderer and shared resolver are not linked into this app.
No product code, tracker, dependency, font asset, commit or push was changed by
this lane. No physical iOS/Android check, VoiceOver/TalkBack workflow, signed
release, immutable published FieldLog package, store/customer/operational receipt
or GA gate is accepted by these measurements. Accountable design review and all
specified physical/release/GA evidence remain pending. Phones stay disconnected.
