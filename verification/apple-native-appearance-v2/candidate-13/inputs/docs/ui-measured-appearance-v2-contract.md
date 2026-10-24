# Measured shared native appearance 2 — contract candidate

**Design only, awaiting root freeze.** This closes a proposed typed/data/native
consumer seam for product-plan §8.3. It supplies no engine implementation, installed
resources, renderer support, publication, signed authority, or GA acceptance.
It replaces `sharedCandidate1` only in the **new** proposed format
`mixer.native-appearance.2`; V1 remains a different, unchanged contract.

The executable artifacts are
[the closed JSON schema](../verification/ui-measured-appearance-v2-contract/descriptor-schema.json),
[canonical default proposal](../verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json),
[typed Swift declarations](../verification/ui-measured-appearance-v2-contract/ContractTypes.swift),
[authored curve definitions](../verification/ui-measured-appearance-v2-contract/shape-definitions.json),
and [bounded design checker](../verification/ui-measured-appearance-v2-contract/scripts/check-contract.py).
The schema and semantics below jointly define admission. The declarations show
field ownership and native plan shape, not constructible installed authority.
Their host/iOS/Android typechecking establishes declarations only.

## Accepted inputs and explicit adoption

The inputs are scoped root acceptances for
[Apple appearance measurement](../verification/apple-appearance-measurement-root-review/acceptance.json)
(385 bindings), [font profiles](../verification/apple-appearance-font-profile-root-review/acceptance.json)
(571), [shape evidence](../verification/apple-appearance-shape-root-review/acceptance.json)
(260), and [shared text-profile data](../verification/ui-shared-text-profiles/acceptance.json).
The latter now has 89 SDK tests per Debug/Release plus direct public consumers;
this lane inspected its source/tests and independently compares all 72 role sizes
with the retained native table. No issue was found within that data-only scope.

This candidate explicitly adopts the six-role hierarchy, measured flat paints,
separate grouped-list metrics, a **shared authored full-group** continuous-26
outline, and shared static 63×28 track / rectangular 37×24 thumb outlines. Both
native adapters must consume that same recipe. The root's review of measured
inputs did not accept these new authored renderings as native-exact output.
[Shape findings](apple-appearance-shapes.md) and the original proposal retain the
9–10 px first-scanline group residual and 1–2 px switch residual at 3×. The new
integer curve quantization and radius clamp are additional authored choices;
their actual native pixels have not been measured. No unchanged-Apple-pixel claim
attaches to adopting them. Phones remain disconnected; no device work is requested.

## Version, bounds, and typed ownership

`UIAppearanceConfigurationV2` contains `id`, `mode`, and `resources`. Its wire
object has exactly one of these shapes:

```text
shared:           {format,id,mode:"shared",resources,theme}
platformSpecific: {format,id,mode:"platformSpecific",resources,iOS,android,reason}
format:           "mixer.native-appearance.2"
theme.recipe:     "measuredShared2"
```

There is no automatic or platform-default mode. Platform-specific appearance
requires two complete V2 themes and an explicit, nonblank, reviewable ASCII reason;
no unavailable asset, OS branch, or rendering failure can choose that mode.
All objects reject missing/unknown fields and unknown enum values. No arbitrary
style dictionaries, native names, callbacks, CSS, downloaded descriptors, custom
paths, gradients, executable assets, or per-node theme keys are admitted.

The byte rules are explicit: 1…65,536 bytes; ASCII; one JSON value; canonical
lexicographic ASCII object-key order; preserved array order; no whitespace outside
strings except one terminal LF; unsigned decimal integers without leading zeros;
no fraction, exponent, sign, boolean, null, BOM, duplicate key, or trailing bytes.
Strings use JSON's shortest required escaping for quote/backslash/control values;
field-specific character sets disallow control bytes. At most 20 container levels,
8,192 values, 64 elements in any array. Array order is authored and digest-bound.
The design checker enforces these limits; a product streaming codec must admit
counts/depth **before** retaining children and must not merely copy this checker.

Raw scalar metrics are UInt32 logical 1/64 point/dp values in 0…65,536; font sizes
are 64…16,384. Weights are closed 400/500/600/700. Colors are uppercase
`#RRGGBBAA`, unpremultiplied encoded sRGB. Alpha is applied once. No global opacity
or implicit disabled dimming follows. IDs are 1…128 `[A-Za-z0-9_.-]` ASCII bytes.
Every derived extent, coordinate, sum, and native measured box must remain in
0…2,147,483,647 logical 64ths, admitted using checked UInt64 intermediates;
overflow, nonfinite native measurements, and negative extents are explicit errors.
The V2 error family must distinguish malformed/canonical/bounds/resource/font/
unsupported-profile/unsupported-native-operation/layout/native-attachment failures.
It is never a release-authority classification by itself.

The schema reuses only safe V1 primitive shapes: color representation, insets,
alignment enums, font face/source/fallback, and resource entries. It does not
reuse V1 palettes, typography line boxes, controls, theme, environment, resolver,
recipe enum, or codec. New `UIRecipeV2`, `UIThemeV2`, `UIAppearanceDescriptorCodecV2`,
`UIAppearanceEnvironmentV2`, `UIPreparedAppearanceV2`, and native consumers are
separate types. No V2 enum value is appended to `UIRecipeV1`. Both codecs must
reject the other format; the existing 1,906-byte V1 golden and V1 resolver
semantics remain byte-for-byte unchanged. Callers opt into V2 through a separately
coordinated host bootstrap; no existing call silently switches recipes.

## Complete theme fields

Every theme contains exactly `recipe`, `typography`, `light`, `dark`, `stacks`,
`groupedList`, `button`, `field`, `toggle`, and `navigation`. All fields, nested
paint state matrices, and bounds are enumerated in the closed schema and named
struct fields in `ContractTypes.swift`. The canonical default is the normative
machine-readable proposal; this document explains how a consumer uses it.

### Required invariants versus canonical default values

The numeric geometry and color examples in this document describe the canonical
`mixer.measured-candidate.v2` **default proposal** wherever the schema permits app
customization. A complete app theme may replace those admitted fields explicitly;
consumers must use its captured values, not hardcode the examples. Such a theme
requires its own native/design evidence. Merely sharing a recipe name never makes
it match the retained Apple reference or grants native support.

| Category | Required invariant | Customizable/default distinction |
| --- | --- | --- |
| Wire/admission | Exact format, recipe, closed fields/enums, canonical bytes, byte/count/depth/value limits | ID and explicit platform-specific reason are app values within their bounds |
| Typography | Exactly twelve profiles × six roles with the size/weight family above; selector, range and ties-up policy fixed | Font source and declared defaultProfile may vary; systemSans/l are this default |
| Paint/state | Complete role/value matrices; precedence; no global dim; disabled button background, field caret/selection, and toggle overlay are canonical clear; inactive field outline width zero | All other admitted RGBA8 paints/outlines are explicit app values; the measured RGB examples and authored candidates are this default |
| Stack/list/control metrics | Closed algorithms, growth/overflow rules, explicit spacing precedence, interior separators, row/control/label separation | Gaps, insets, floors, hit metrics, group radius and separator thickness may vary within bounds; 2/8,16/15,52/59,44,26 and43/64 are this default |
| Group floors | Nondecreasing profile floors, every floor at least fixed track height28 | The twelve particular 49…59 floors are this default |
| Shapes/switch | Named curve versions and coefficients; full-group closure/clamp; fixed63×28/r14 track,37×24/r12 thumb,2 inset and logical trailing checked end | Group radius is an admitted app value (26 here); switch geometry is fixed, not customizable under this recipe |
| Navigation | Expanded navigationExpanded/leading, compact headline/center; closed wrap/snap policy; expanded minimum ≥ compact minimum | Insets and bar floors are admitted app values;16,8 and106/44 are this default |
| Resources/native authority | Catalog/font-reference invariants and immutable native capture; required operations fail closed | Resource/font choices need actual installation/coverage evidence; a public descriptor or prepared data plan never supplies it |

The schema permits numeric/color variation, while the additional semantic checks
close the stated cross-field invariants. Neither is optional. The geometry owner
will provide `UINativeShapeV2` once in
`sdk/Sources/MixerUI/AppearanceGeometryV2.swift`; the later value/codec owner
references that enum rather than redeclaring it. The verification declaration
probe sketches its public cases in its own module only.

Typography has `font`, `profiles`, `defaultProfile`, and `preferencePolicy`.
`profiles` has exactly twelve named rows, each exactly six named `{size64,weight}`
metrics. `measuredShared2` freezes this profile family: a changed size/weight is
not admitted under the same recipe. App colors, geometry within bounds and
font source can vary in a complete theme; a different profile family requires a
new explicit recipe contract. `defaultProfile:l` names the authored baseline for
build/reference use; it is not a fallback for an unknown native preference.

| Profile | Body | Headline | Title | Caption | Header | Expanded navigation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| xs | 14 | 14 | 25 | 11 | 14 | 31 |
| s | 15 | 15 | 26 | 11 | 15 | 32 |
| m | 16 | 16 | 27 | 11 | 16 | 33 |
| l | 17 | 17 | 28 | 12 | 17 | 34 |
| xl | 19 | 19 | 30 | 14 | 19 | 36 |
| xxl | 21 | 21 | 32 | 16 | 21 | 38 |
| xxxl | 23 | 23 | 34 | 18 | 23 | 40 |
| a1 | 28 | 28 | 38 | 22 | 28 | 44 |
| a2 | 33 | 33 | 43 | 26 | 33 | 48 |
| a3 | 40 | 40 | 48 | 32 | 40 | 52 |
| a4 | 47 | 47 | 53 | 37 | 47 | 56 |
| a5 | 53 | 53 | 58 | 43 | 53 | 60 |
| Weight | 400 | 600 | 400 | 400 | 600 | 700 |

Numbers in the table are logical units; wire sizes multiply them by 64. Header is
its own semibold role, not caption. Expanded navigation is its own bold role,
not the document's regular title. Button, field, and toggle labels use body.
Compact navigation uses the existing headline role; it is an explicit authored
candidate, not a measured collapsed-navigation result.

The selector accepts a converted preferred **body size in logical 64ths** and
selects the nearest anchor among 896,960,1024,1088,1216,1344,1472,1792,2112,2560,
3008,3392. Compare exact integer distances; an exact tie selects the larger row.
The inclusive supported interval is 896…3392. Outside it returns
`unsupportedBodySize`; no cap, extrapolation, or smaller-font fallback. An
explicit app override may name one of the twelve IDs and is recorded as an
app override. Native iOS categories map directly to these twelve rows, including
all accessibility categories; unknown categories fail. The selected row supplies
all six metrics together. No scalar multiplies the six sizes afterward.

Android's proposed preference boundary uses the **current window** DisplayMetrics:

```text
bodyPx = TypedValue.applyDimension(COMPLEX_UNIT_SP, 17, metrics)
oneDpPx = TypedValue.applyDimension(COMPLEX_UNIT_DIP, 1, metrics)
bodyLogical = Double(bodyPx) / Double(oneDpPx)
check both API results and ratio finite/positive; check unrounded 14…53 support
body64 = floor(bodyLogical * 64 + 0.5), checked UInt32
profile = nearest(preferredBodySize64: body64)
```

This is an app normalization policy awaiting Android platform evidence. The
[official dimension API](https://developer.android.com/reference/android/util/TypedValue#applyDimension(int,%20float,%20android.util.DisplayMetrics))
converts SP/DIP to pixels using current metrics. Android's
[fontScale documentation](https://developer.android.com/reference/android/content/res/Configuration#fontScale)
explicitly says scaling is nonlinear and the field is informational; do not use
`Configuration.fontScale`, `scaledDensity`, or a hand-authored curve as the direct
font equation. After selection apply `size64/64` as an explicit logical size using
PX/DIP conversion **without another SP/semantic multiplier**. Preference conversion,
rounding around anchors, window changes, configuration changes and unsupported
preferences need a real Android receipt. The checker supplies no such receipt.

`systemSans` is the explicit default on each platform, with native script/emoji
fallback. It requires the same hierarchy, numeric sizes and weights; it does not
promise identical installed faces, glyph widths, ink, line breaks or raster.
No Apple font is redistributed. `bundled` preserves V1's explicit face list and
`none|systemSans` fallback option. Referenced native font bytes, PostScript identity,
weight/style and glyph coverage still need native validation; synthetic styling,
missing-weight substitution, and undeclared fallback are not permitted. Required
400/600/700 normal faces must exist; an italic face requires that weight's normal
face. `fallback:none` must reject missing coverage. Neither the font table nor
CoreText line advance is a universal text box: actual native shaping, wrapping,
combining marks, Arabic and emoji can require more height. Grow layout to contain
admitted text; never clip to the retained Latin probe height or shrink to fit.

## Paint/state selection

Each light/dark `UIPaintsV2` contains canvas, surface, separator, six text paints,
three button-role matrices, a field matrix, and on/off toggle matrices. A matrix
contains concrete RGBA8 values; it never derives disabled state by multiplying a
whole subtree's opacity. Native widgets must not add a second tint, ripple,
elevation, border, font padding, capitalization or disabled alpha.

| Measured static region adopted as candidate | Light | Dark |
| --- | --- | --- |
| Canvas / grouped row surface | #F2F2F7 / #FFFFFF | #000000 / #1C1C1E |
| Primary text, including disabled ordinary Text | #000000 | #FFFFFF |
| Header ink | #85858B | #8D8D93 |
| Normal/cancel button | #0088FF | #0091FF |
| Destructive button | #FF383C | #FF4245 |
| Disabled button | #BFBFBF | #555556 |
| Interior separator | #E8E8E8 | #38383B |
| On / off track | #34C759 / #C5C5C7 | #30D158 / #5A5A5E |
| Disabled on track / thumb | #99E3AC / #FFFFFF | #26773B / #8E8E8F |

All colors above are opaque. Text paints for the other static roles explicitly
use primary; disabling an ancestor changes interaction, not those text paints.
The default's interactive disabled label color uses the button disabled paint.
Where exact contextual observation is absent this is an authored shared choice.

Button states are `enabled`, `pressed`, `disabled`, each `{label,background}`;
normal/destructive/cancel have separate complete tables. Pressed background is the
role color with alpha 0x1F, clipped to the explicit button overlay radius 8 and
label visual rect plus label insets. Its minimum hit envelope is separate. The
optional keyboard focus outline uses the role color, width 2/radius 8. Focus and
press may coexist. The disabled table has clear background and clears both states.
Press and focus values are authored candidates; no native pressed evidence exists.

Field states are `enabled`, `focused`, `disabled`, each with text, placeholder,
background, caret, selection and outline. Plain/focused background is clear;
text is primary; placeholder is authored #B3B3B5 light / #5A5A5E dark, **not a claim
about native placeholder compositing**. Caret is accent; selection uses accent
alpha 0x3D. Focus adds width-2/radius-8 accent outline inside the available visual
rect without changing layout. Disabled field uses disabled label/placeholder,
clear caret/selection and zero outline. Press alone adds nothing to a field;
native editor focus selects `focused`. These complete field states are authored
candidates. Native IME composition, selection, editing menus, secure platform
keyboard handling and submit routing remain native.

Toggle `on` and `off` each contain enabled/pressed/disabled `{label,track,thumb,
overlay}` plus keyboard-focus outline. Enabled thumb is white. Disabled-on paints
use the measured track/thumb colors above. **Disabled-off is authored**:
#E5E5E7 track / white thumb in light, #38383B track / #8E8E8F thumb in dark.
Pressed keeps label/track/thumb and adds accent alpha 0x1F over the track beneath
the thumb, clipped to the track path. There is no thumb morph, scale, shadow,
elevation, drag-intermediate paint, or timed animation in this bounded recipe.
These unmeasured states remain candidates. On input capture, the native control
must retain its gesture cancellation/activation semantics and native switch
accessibility; it must not emit an event merely for a repaint.

State precedence is inherited disabled → value/role → pressed → keyboard/editor
focus decoration. Disabled suppresses press/focus and activation. VoiceOver/
TalkBack focus is native accessibility state, not this keyboard-focus outline.
Noninteractive nodes ignore press/focus. State updates cannot change geometry,
identity, revision, text profile, document content or action bindings. An authored
`clear` is an explicit paint, never permission to inherit a native style.

## Layout, rows, grouping, and navigation

All missing stack alignment defaults are center. Explicit UI-v1 spacing,
including zero, wins. Convert admitted explicit 0…256 spacing to logical 64ths
with `floor(value*64+0.5)`. Missing HStack gaps are 8. Missing VStack gaps are 2
only for an adjacent direct text body→caption pair; all other pairs are 8. This
is an explicit authored context policy preserving the measured ordinary pair,
not a universal native spacing observation. A VStack plan carries exactly
`max(0,childCount-1)` gap values so mixed roles are unambiguous. ZStack overlays
children in original order with intrinsic sizing constrained by parent; no
Android-only child fill. First/last baseline alignment requires actual native
baseline support. An adapter that lacks it rejects the whole required candidate.

Grouped-list dimensions distinguish outer group inset 16, row content horizontal
insets 16, semantic content height, row bounds, hit envelopes, switch visual bounds
and label bounds. At the measured 402 width these place group edges at 16/386 and
content at 32/370. Logical leading/trailing mirrors under RTL; IDs and child order
do not reverse. Native safe areas constrain the viewport once, outside app content.
Window y coordinates from reference captures never become app padding.

A list turns each immediate Section into a group; each contiguous run of direct
non-Section children forms one unheaded group. Its rows are the Section's immediate
children or that direct run. The Section retains its own normal identity record;
group metadata creates no new document nodes or event identities. An empty titled
Section displays its header with no group outline and no header-to-row gap; an
empty untitled Section displays nothing. Other groups use these steps in order:

1. Apply topPadding 10 once before the first visible header/group; an ordinary
   header starts there. A later header starts 1771/64 (27.671875) after the preceding
   visible group/header bottom. This quantizes the 27⅔ candidate. An unheaded later
   group uses the same independently named `groupWithoutHeaderGap64`.
2. Lay out header using sectionHeader native shaping, original case and title.
   No automatic uppercase, caption substitution, extra toolkit margins, or fixed
   line box. Header-to-first-row gap is 10. Its own text height contributes to the
   total intergroup distance. There is no single total `groupGap`.
3. For each row compute `max(profileFloor, semanticContentHeight + top15 + bottom15)`.
   Its full native-shaped content is centered vertically in the available row
   interior; if additional native glyph extent is required, the row grows. Floors
   are xs49,s50,m51,l52,xl54,xxl56,xxxl59,a1…a5=59. They are authored shared policy
   informed by profile observations, not universal native minima. The accessibility
   filled-field residual of ⅓ pt remains unresolved; this formula is not an exact
   preservation claim.
4. Semantic content height is actual top-level native text/field/stack content.
   A toggle row uses **label semantic height**, independently centers the fixed
   28-high track in the row, and reserves 63 plus labelGap8 horizontally. It never
   adds 30 to `max(labelHeight,trackHeight)`; that would incorrectly turn an ordinary
   52 row into 58. The profile floor must admit the track. Button 44×44 and field
   44-high hit envelopes do not become padded semantic content. Outside a list,
   reserve each control's own minimum hit envelope and its visual/semantic extent.
5. Draw one row surface and one full-group outline across the sum of row heights.
   Do not round individual first/last cells. Paint an interior separator only
   between two rows in this same group, never after its final row. Separator
   insets are 16 from each group edge, thickness 43/64 (0.671875), centered at the
   shared row boundary and clipped to the full group. This quantizes the observed
   ⅔ raster-occupancy candidate; it is not a UIKit property claim. A public final
   separator guide is not permission to draw a final separator.
6. Add bottomPadding 10 after the last visible group/header.

Native measurements are admitted as finite positive extents and rounded **up** to
logical 64ths to avoid reducing their required bounds. Full-group dimensions come
from final admitted native layout. Header/group aggregation uses checked UInt64,
with the derived extent limit above. Group width below its horizontal insets,
negative available text width, unresolved required shaping, or unsupported nested
scroll layout is an explicit layout failure, never clipping or a fallback widget.

A Section outside a List is explicit vertical content: optional sectionHeader (absent/empty title has none),
header-to-content gap10 only when it has both header and content, then children with gap8 and
logical leading alignment. It receives no grouped outline/row wrappers. A nested
Section used as a List row uses that same semantic content. Nested Lists and
non-root/multiple navigation nodes are unsupported contexts in this bounded native
profile; reject them before mutation even if ordinary UI-v1 validation admits the
tree. This does not narrow the product inventory required for later qualification.

Navigation has one existing root/child and two explicit native presentation states.
Expanded title uses navigationExpanded, leading alignment, insets top0/leading16/
bottom8/trailing16. Compact uses headline, centered, horizontal16, one line with
native tail ellipsis. Both use primary text on canvas. Empty/missing title has no
label. There is no implicit platform icon or back-chevron substitution in the
current root-only appearance recipe. Preserve the existing native navigation and
system back behavior; this adds no route, restoration or full-navigation claim.

For the default, the authored compact bar floor is 44 and expanded total floor
is 106. In general resolve `compactExtent=max(minimumCompactBar,
shapedCompactOneLineHeight + compactInsets.top + compactInsets.bottom)`, then
`expandedExtent=max(minimumExpandedBar, compactExtent + shapedExpandedTitleHeight
+ expandedInsets.top + expandedInsets.bottom)`. Both native title measurements
come from the selected profile before choosing presentation. Missing/empty title
uses compactExtent for both states, with no title gap/expanded reservation.
Capture expanded overflow as `expandedBarExtent - compactBarExtent`, at least zero;
select compact when native content scroll offset is greater than or equal to that
positive overflow, otherwise expanded (zero overflow stays compact). Use the
expanded measurement independent of current presentation to avoid feedback. The
bounded proposal snaps with no intermediate animation; preference change, focus
scrolling and native gestures remain native. This compact-state/threshold/minimum
policy is an explicit unmeasured candidate. The accepted native 106/112/119-point
observations are contextual data, not proof of this general formula. Adapters must
obtain new native validation before calling expanded/compact parity complete.

## Closed authored curves and numeric conversion

There is no native radius lookup. Public `RoundedRectangle.path(in:).cgPath`
outputs supplied **design input**; the new V2 geometry below is owned, closed,
versioned app geometry. Native `cornerCurve`, platform rounded rectangles, dynamic
CGPath export, arbitrary command parsing and hidden cell geometry are not runtime
substitutes. The default uses radius64=1664 (26); shorter/narrower groups clamp
this *authored* parameter. It does not identify Apple's native radius.

The full-group curve uses coefficients with denominator 1,000,000:
`a=1528665,b=1088490,c=868407,d=631494,e=74911,f=169060,g=372824`.
For width `w`, height `h`, requested `r` in logical 64ths, first compute:

```text
r' = min(r, floor(min(w,h)*1000000/(2*a)))
A…G = nearest64(r' * correspondingCoefficient / 1000000), ties upward
nearestRational(n,d) = floor((2*n+d)/(2*d)), checked UInt64
```

The tangent extent is A, not r'. The fixed cubic controls for the upper-left
corner, traversing from left to top, are:

```text
start (0,A)
C (0,B) (0,C) (E,D)
C (F,G) (G,F) (D,E)
C (C,0) (B,0) (A,0)
```

Reflect this corner into all four quadrants, join straight tangent segments,
close exactly once with nonzero fill. Start at `(w,nearestRational(h,2))`, line to
`(w,h-A)`, traverse lower-right, lower-left, upper-left, upper-right and close;
`group_path` in the checker is the literal 18-command normative expansion. Width
or height zero produces an empty path. All points, including controls, must stay
inside the admitted rect. Rounding is performed on nonnegative corner offsets
first; derive opposite coordinates by subtraction to preserve exact symmetry.
This clamp avoids overlapping authored tangent regions. Neither it nor the
quantization claims to reproduce the measured cell-height native clipping.

Track and thumb use exactly the sealed 18-command `fixedPaths` in
`shape-definitions.json`, already quantized once to logical 64ths. They are
63×28 with authoring-radius14 and **37×24** with authoring-radius12. The thumb is
not a 27-point circle. These named variants admit no arbitrary size/radius/path
field. The corresponding descriptor dimensions/radii must equal those constants.
Thumb y=2; x=24 if `checked != rightToLeft`, else 2. Thus checked selects logical
trailing in both directions; control placement itself also mirrors. There is no
runtime public-path generation, shadow, geometry interpolation, or independent
Android outline choice. Zero-area groups are harmless geometry, not display proof.

Density is independent of profile: first reject nonfinite actual density or raw
density outside the inclusive 0.125…16 interval, **before** rounding. Then normalize
`density1024=roundTiesUp(density*1024)`, supported 128…16384, with no clamp.
For a nonnegative logical extent m, final integer pixel edge rounding is
`floor((UInt64(m)*density1024 + 32768)/65536)`. Round shared absolute rectangle
boundaries consistently and derive pixel widths by subtracting edges to avoid
seams. Convert path controls to native floating path coordinates using the exact
rational `coordinate64*density1024/65536`; do not round each cubic control to an
integer pixel or apply density twice. Final antialiasing/text raster remains
native and may differ. The checker tests bounded path closure, control counts,
reflection and point bounds; actual native fill, clipping and animation/state
behavior remain unqualified.

## Immutable resolution and native transaction

The declaration probe proposes internal
`prepareAppearanceV2(snapshot:captured:environment:buildSupport:) throws`.
Inputs are one validated immutable `UIRenderSnapshot`, one internally captured
installed descriptor/resources, one normalized immutable environment, and a
build-owned concrete support value. A caller cannot gain support by conforming to
a protocol. Raw config or public prepared data never proves native capability.

The environment records scheme, direction, selected profile, density, viewport,
safe area, locale, accessibility visual preferences, and a monotonic host environment
generation. It contains no uniform textScale. UIKit/Android preference, locale,
window, density, orientation and accessibility change observations must be captured
coherently on the UI owner. Unknown/unsupported required visual accessibility
contexts, including unqualified Bold Text or increased-contrast transformations,
fail explicitly; they cannot be silently ignored or forged as a supported profile.
Reduce Motion remains native; this bounded recipe has no timed animation. Native
VoiceOver/TalkBack roles, labels, values, actions and focus order remain required.
No setting is qualified by this document alone.

Preparation revalidates the complete descriptor semantics and standard document
bounds; verifies each identity from the same snapshot; checks exact resources,
profile and build support; and admits all derived counts/geometry before retaining
output. It returns exactly one node record per snapshot node in preorder (at most
4,096), each carrying ID+generation, kind, original child IDs, inherited disabled
and a closed resolved recipe. Every group/row reference resolves to those same
records. Native-shaped layout and attachment may still fail after pure preparation;
preparation is not an irreversible reconciler mutation or a display witness.

| Current kind | Required V2 resolved payload/consumer |
| --- | --- |
| text | Exact body/headline/title/caption role, size/weight, maxLines/selectable; actual native wrapping, ellipsis, script/emoji fallback and selection |
| button | Body, exact normal/destructive/cancel role, complete paints, label geometry and independent hit envelope; native activation and action routing |
| textField | Body, native editable control, field metrics/state; native IME, caret, selection, focus, keyboard/submit and accessibility |
| toggle | Body label + value, fixed named track/thumb geometry, placement/end mirroring and complete paints; native switch semantics/action/cancellation |
| vStack | Exact childCount−1 gaps plus logical alignment; original child order |
| hStack | Same gaps plus top/center/bottom/first/last text baseline semantics |
| zStack | Closed overlay alignment, original paint order, intrinsic children constrained by parent |
| list | Ordered groups and row placements, row policy, header metrics, outline/separators/surface; native scrolling and retained scroll identity |
| section | Optional sectionHeader; structural children and explicit list/outside-list context |
| navigation | Optional expanded and compact title metrics, exact chrome policy; native navigation/system back behavior |

Disabled descendants inherit interaction restrictions. Surviving IDs/kinds retain
their generation and native selection, IME composition, focus and scroll state.
Changing a font/theme/environment does not manufacture a node replacement or guest
revision. Removed or replaced IDs retire listeners and native state as required
by the existing identity contract. No native event binding is copied from a style.

An ordinary update stages document validation, reconciler candidate identities,
appearance, resources, native measurements and native hierarchy changes before one
UI-thread commit of snapshot+identity map+style+native view tree. If preparation or
attachment fails, dispose staged listeners/views and preserve the last committed
tree/snapshot/plan as one unit. The producer cannot first commit a new reconciler
snapshot then ask whether its styling is supported. No partial old/new render or
new actions against an old display is allowed.

Environment-only update stages a new plan/layout for the **same** snapshot and
commits only if its captured document/config/environment generations still match;
a stale candidate is discarded and rebuilt. It does not emit a guest event or
increment the guest revision. Press/focus/scroll state is native ephemeral data
keyed by exact identity; it is discarded if stale and cannot overwrite a newer
snapshot or environment plan.

Signed presentation uses its existing terminal lifecycle. It must derive the
capture internally from installed native material and never accept a guest style
ID, public theme setter, app-supplied support proof, or mutable downloaded file.
An unsupported candidate or native attach failure follows existing terminal
presentation failure/retirement, earns no event/input/display/health authority,
and cannot use the retained old tree as a witness for a new candidate. Relevant
environment/style changes invalidate the current signed display observation and
require a fresh **real native** display witness after commit; pure resolution,
layout, old screenshots, timing, or this contract checker are insufficient.

## Resource bootstrap and separately owned signed boundary

Resource entries keep the V1 closed catalog semantics: at most 64 entries,
4 MiB each/16 MiB total; unique IDs and case-insensitive paths; bounded relative
ASCII paths with no empty/dot/dot-dot segment; lowercase SHA-256; nonblank trimmed
provenance; scale1…4; locale and direction variants explicit. At most 16 font
resources, each scale1/locale `und`/neutral. Paths and digests are references only.
Capture native bundle bytes once into owned immutable storage before host setup,
with no alias to a mutable external buffer; reject symlinks/path escape,
wrong sizes/hash/format/identity, missing declared variants and unauthorized
fallback. Immutable captured bytes, never later path rereads, reach consumers.
No new dependencies or redistributed font/icon asset is introduced here.

The ordinary bootstrap owner implements V2 descriptor emission/capture from one
app configuration, copies **the same canonical bytes** into both native bundles,
and supplies the native consumer's internal capture. The pure codec owner cannot
claim installation. Each native adapter owner implements actual toolkit consumption
and required-operation support, including captured font validation and all ten
contexts it advertises. Build tooling and integration must verify consumed bytes
and exact descriptor/code/resource closure; a second maintained Java default table
is forbidden. Stage5 JNI headers/packets are untouched by this design.

Signed installation/identity binding is a separate serial owner and implementation
slice. Existing identity/release/native-closure fields must not be silently
reinterpreted to bind V2 or to authorize V2 rendering. Root must freeze a new
explicit version/binding that includes exact descriptor format+digest, authored
curve implementation, resource bytes/catalog, consumer support and actual native
build closure, then implement and review its private installation edge. If existing
closures cannot faithfully express it, a versioned identity/release contract is
required. Until that happens, **signed V2 is unavailable**, even if ordinary V2
renders. No new `mxis_*` argument, NativePacketV1 field, signed guest header/event,
release domain, or public proof is created by these artifacts.

## Executed scope and implementation acceptance boundary

Run `python3 verification/ui-measured-appearance-v2-contract/scripts/run-checks.py`
to replay retained normal/optimized checker runs and declaration typechecks from
the exact pre-implementation input-lock/snapshot, with command outputs, versions,
revision/tree digests, and artifact seal. It does not discover new SDK sources.
Run `scripts/verify-seal.py --check-live` in that directory for the final retained
artifact and original live-input check; later implementation files are outside
this frozen design input set.
The checker tests closed nested fields, canonical bytes and V1/V2 separation;
all 2,497 admitted body64 inputs and ties/unsupported boundaries; the full six-role
native table; all ten state-role mappings; component-specific disabled paints;
resource catalog/font-reference failures; row/visual separation; shape symmetry,
closure/bounds/overflow; and unsupported-operation rejection. Its synthetic resource
positive case deliberately validates references without claiming a real font.
It is a design checker, not production codec/runtime integration evidence.

After root freeze, product implementation still needs independent Swift/JVM codec
and resolver corpora, native preference conversion, real installed resource
capture, complete native operation support, failure-atomic ordinary and signed
integration, identity/listener/IME/scroll retention, and actual native consumption
of every resolved field. Native reference captures must compare the **new authored
recipe** on both adapters and document residual design changes from Apple; equal
pure tables alone cannot satisfy §8.3. Pressed, disabled-off, focus, compact
navigation and the authored clamp need new native validation. No further measurement
was performed in this lane.

Physical iOS/Android side-by-side review, interaction/VoiceOver/TalkBack/keyboard/
navigation workflows, signed display/health, immutable published FieldLog packages
from its separate repository, store/customer/operational qualification and all GA
gates remain pending. This design receipt cannot mark any of them verified. Root
owns freeze, implementation assignment, integration, trackers, commit and push.
This lane changed only this document and its verification directory.
