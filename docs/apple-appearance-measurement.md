# Preserving the existing Apple design in the shared native contract

The existing Apple renderer has now been measured without applying a shared theme.
The [measurement receipt](../verification/apple-appearance-measurement/receipt.json),
[gallery](../verification/apple-appearance-measurement/gallery.html) and
[raw analysis](../verification/apple-appearance-measurement/analysis.json) extend the
immutable reference from `958998d92f1c2ba205de09a83d957d738b619572`. Every original
fixture, in both Debug and Release, has exactly the same decoded pixels as its
historical PNG: 16 comparisons, zero differing pixels per 3,162,132-pixel image.
All 12 Debug/Release profile pairs also have equal decoded pixels and equal node
geometry/font records. This establishes that these probes did not perturb the
recorded output in these cases. It is simulator integrity evidence, not a physical
parity pass, accepted shared design, or renderer integration.

The source is an isolated derivative of the exact reference harness and frozen SDK.
Only a clear SwiftUI background geometry probe, explicit section header probe, and
native measurement export were added. Structural Sections remain structural.
No font, tint, color, padding, control style, or List style is installed. The original
reference seal passed before and after capture and remains unchanged. The new
project adds a real optimized Release configuration. Neither the current product
renderer nor the concurrently developed shared resolver is linked by this app.
The provisional theme/resolver comparison inputs are separately frozen and hashed.

The dedicated iPhone 18 Pro simulator runs iOS 27.0 `24A434`, with a 402×874 pt window,
3× scale and 1206×2622 PNGs. Its observed safe area is 62 pt top / 34 pt bottom.
Xcode 27.1 `27A9275`, iOS Simulator SDK 27.1 and Apple Swift 6.4 built both variants.
`commands.json` records exact commands, times, exit codes and log paths. Debug and
Release each cover the eight historical cases plus LTR accessibility-medium
Typography and Controls in light/dark. RTL uses Arabic and accessibility-medium.
No physical device was discovered, used, or requested.

## What was actually observed

Each capture's `measurements.json` separates SwiftUI geometry, explicit semantic
Font resolution, actual public UIKit objects, and reference-only semantic UIColor
and preferred UIFont tables. Geometry is view layout bounds in global points; it
is not a glyph-ink rectangle, hit target, or a promise that every child fits inside
that bound. UIKit observations use public type casts and properties. Subview paths
are evidence identifiers only; no private class name or internal ancestry is mapped
to a supported node contract.

The probe uses public `Font.resolve(in: fontResolutionContext)` on iOS 26+. The
explicit body/headline/title/caption values are the fonts selected by the frozen
renderer, resolved in their actual environment. CoreText ascent/descent/leading,
cap/x height, names and numeric traits accompany the point sizes. These public
font objects do not establish which fallback face shaped each Arabic glyph. A
nil environmental Font is recorded as unresolved. The exact section/header and
button/toggle label fonts are consequently not asserted from a private view.

| Observed role/property | Large | Accessibility-medium | Evidence and limit |
| --- | ---: | ---: | --- |
| Explicit body | 17 pt regular | 28 pt regular | Resolved semantic Font; single-line bounds 20⅓ / 33⅔ pt |
| Explicit headline | 17 pt semibold | 28 pt semibold | Resolved `.SFUI-Semibold`; CoreText weight trait 0.3 |
| Explicit title | 28 pt regular | 38 pt regular | Resolved semantic Font; ordinary single-line bounds 33⅔ pt |
| Explicit caption | 12 pt regular | 22 pt regular | Resolved semantic Font; single-line bounds 14⅓ / 26⅓ pt |
| Expanded navigation title | 34 pt bold | 44 pt bold | Public UILabel with exact title text; `.SFUI-Bold`, weight trait 0.4; visible in PNG |
| Navigation bar height | 106 pt | 112 pt LTR / 119 pt Arabic | Public UINavigationBar / list top boundary; title and native shaping change geometry |
| Section header Text bounds | 20⅓ pt high | 33⅔ pt high | Explicit header GeometryReader; actual header Font remains unresolved |
| Default minimum List row environment | 52 pt | 52 pt | Public SwiftUI environment floor; actual accessibility rows grow |
| Ordinary control List cell | 370×52 pt, x=16 | Rows grow with content | Actual UICollectionView cell bounds; not a universal fixed-height rule |
| Ordinary field view | 338×22 pt, x=32 | 338×34 / 35⅓ pt | Public UITextField and SwiftUI bounds; field fonts 17 / 28 pt |
| Native switch outer frame | 63×28 pt | 63×28 pt | Public UISwitch; intrinsic size 61×28, track/thumb dimensions remain unresolved |

Ordinary first-group content uses outer cell edges x=16 and x=386; text/field content
starts at x=32. The first title row is 63⅔ pt high, then ordinary headline/body/caption
rows are 52 pt. The explicit VStack has measured 8 pt content gaps and the explicit
HStack has measured 16 pt gaps. The absent-spacing VStack's body/caption gap measures
2 pt, with the caption centered under its wider sibling. This last value belongs to
the specific semantic-font pair and environment; it is not a measured universal
native stack default. The baseline-aligned HStack's child frames and ZStack child frames are retained as data.

In RTL, content and headers end at x=370; the public UISwitch moves to x=32 from x=309
in LTR. The Arabic navigation title uses a taller laid-out label despite the same
44 pt base font. These are bounds and environment observations, not a completed
RTL shaping, focus-order, back-navigation, or accessibility workflow test.

The native PNGs declare sRGB. Exact flat interior color counts, excluding no pixels
by heuristic, are retained for every measured node rectangle and selected public
UIKit rectangles. The following values occur as repeated interior pixels in those
named regions, with antialiasing and background pixels separately counted. Values
are observations of these screenshots, not claims that SwiftUI exposes these paints
as a public API or that an arbitrary OS version has the same palette.

| Region | Light RGB | Dark RGB |
| --- | --- | --- |
| List canvas | `#F2F2F7` | `#000000` |
| Group row interior | `#FFFFFF` | `#1C1C1E` |
| Body and disabled body ink | `#000000` | `#FFFFFF` |
| Section header ink | `#85858B` | `#8D8D93` |
| Normal button ink | `#0088FF` | `#0091FF` |
| Destructive button ink | `#FF383C` | `#FF4245` |
| Disabled button ink | `#BFBFBF` | `#555556` |
| Checked switch interior | `#34C759` | `#30D158` |
| Unchecked switch interior | `#C5C5C7` | `#5A5A5E` |
| Disabled checked switch interior | `#99E3AC` | `#26773B` |

The public collection background and nav/field text properties independently confirm
relevant canvas and text values. UISwitch onTintColor/thumbTintColor are nil;
their screenshot colors are measured pixels, not non-nil UIKit property values.
Disabled body ink remains unchanged while disabled buttons and toggles visibly
change. A universal disabled-foreground substitution cannot preserve this baseline.

## Concrete shared-contract delta recommendation

The binding §8.3 goal is the same app design through both native toolkits. Preserve
this Apple reference when refining the shared contract. These are proposed field
and recipe changes for accountable root/design review, not approved defaults:

1. Add separate `navigationExpandedTitle` and `sectionHeader` typography/paint
   roles. Expanded navigation needs the observed 34 pt bold profile, distinct from
   the document's 28 pt regular title. Section headers must not resolve as the
   12 pt caption or primary body paint; preserve their measured bounds and gray
   ink while their exact contextual font is resolved through further evidence.
   Represent expanded/collapsed navigation state explicitly before implementing
   scroll transitions; the compact title objects present in UIKit are not a
   tested collapsed-navigation receipt.
2. Define bounded per-role accessibility profiles or curves. Body/headline scale
   by 28/17 here, title by 38/28, caption by 22/12 and navigation by 44/34. One shared
   `textScale1024` multiplier over all four roles cannot reproduce those values.
   Specify the shared normalized profile mapping on both platforms and test it
   rather than importing an iOS category name as an Android implementation rule.
3. Extend the palette/state recipe with `sectionHeaderText`, `toggleOn` and
   per-component disabled paints/opacity. Review the measured light canvas/surface
   ordering and accent/destructive values. Keep ordinary disabled Text's appearance
   distinct from disabled interactive controls. The current resolver substitutes
   disabledText globally and uses accent for checked switches; neither preserves
   the reference. Checked green must be a shared explicit token, not an Apple-only
   exception or a native toolkit default selected independently per platform.
4. Add a grouped-list recipe with separate outer group insets, row content insets,
   row-height floor, separator insets, header spacing and group shape. Measured
   ordinary outer/content leading positions are 16/32 pt and the row floor is
   52 pt. The current single List inset set, 44 pt floor, 16 pt groupGap and lack
   of group shape cannot fully describe the reference. Do not infer a corner
   radius, border, separator thickness or universal group gap from these bounds;
   the native rounded outline still needs an explicit accepted shared recipe.
   Treat absent stack spacing as a role/context rule or require an explicit
   app gap; replacing its observed 2 pt with an unconditional 8 pt changes design.
5. Separate switch outer-control/label layout from track/thumb metrics. The public
   native outer frame is 63×28 pt, while the provisional recipe's track is 51×31
   and thumb 27. Those quantities are not interchangeable. Capture or author an
   accepted shared switch shape/state recipe before both adapters implement it;
   the public outer frame and exact pixel colors do not identify track geometry,
   thumb corner model, shadow or pressed animation.

The comparison inputs retain the provisional `sharedCandidate1` descriptor and
resolver. Its body/headline/title/caption base sizes already match the explicit
ordinary semantic-font sizes, but this does not validate its line boxes, font
fallback, shared systemSans choice, section/nav mappings, list/control geometry,
state rules or accessibility scaling. Native widget consumption remains separate.
No production theme or renderer change was made by this measurement slice.

## Remaining evidence

The producing agent visually inspected all 12 Debug PNGs; Release has equal decoded
pixels. All original fixtures remain readable and complete. The added accessibility
LTR views retain large text with later rows below the initial viewport. These are
agent observations, not accountable reviewer acceptance.

The existing eight historical cases are pixel-protected against probe perturbation.
The four additional LTR accessibility profiles have no historical uninstrumented
PNG; their Debug/Release equality alone does not independently prove a lack of
probe perturbation. Their initial viewport intentionally leaves later rows below
the visible area. Offscreen/lazily absent nodes are not reported as visually checked;
clipped rectangle samples are bounded to PNG pixels and can include other visible
content outside the List viewport, so use visible baseline rows for paint decisions.

Still unresolved: exact contextual header/control-label font and glyph fallback;
group corner model and separator geometry; switch track/thumb/shadow internals;
placeholder alpha/compositing recipe; pressed/focused/input/keyboard states;
expanded-to-collapsed navigation; full scrolling/accessibility focus/selection;
other sizes/locales/contrast/device widths/OS releases and environment transitions.
No test here exercises VoiceOver, TalkBack, physical iOS/Android design parity,
native behavior, signed terminal/display/health, immutable published FieldLog,
signing/store/customer/operational qualification or any GA gate. Phones remain
disconnected and those checks remain explicitly pending.
