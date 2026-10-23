# Pure shared appearance resolution v1

This is a data prerequisite for the shared appearance contract. It implements the
provisional `sharedCandidate1` recipe for the ten current UI-v1 kinds without
changing a renderer, host, reconciler, descriptor, packet, signed factory or native
installation contract. Resolving ten kinds does not mean any native adapter
supports those ten appearance recipes. Root integration and independent review
remain separate.

The candidate tokens come only from the existing validated configuration and its
sealed default. The [Apple reference observations](../verification/apple-appearance-reference/observations.md)
identify pending section, navigation and toggle token review. This resolver does
not approve those choices as an exact match for existing iOS output or freeze a
final product design. No numerical native geometry, color, font or raster parity
claim follows from the pure data tests.

## Public data API

```swift
UIAppearanceResolverV1.prepare(
    snapshot: UIRenderSnapshot,
    configuration: UIAppearanceConfigurationV1,
    environment: UIAppearanceEnvironmentV1,
    platform: UIAppearancePlatformV1
) throws -> UIResolvedAppearancePlanV1

plan.node(for: nodeID) -> UIResolvedAppearanceNodeV1?
plan.style(nodeID: nodeID, pressed: false, focused: false)
    -> UIResolvedAppearanceStyleV1?
```

The immutable plan carries the original revision, configuration ID, recipe,
environment, explicitly selected platform, optional declared platform distinction
reason, one shared font source/catalog reference, and one record per node in
document preorder. Each node retains the exact snapshot identity, kind, inherited
disabled state, original child IDs/order, and a closed recipe value. Text content,
labels, field values, actions and accessibility properties remain in the original
snapshot; the data plan does not duplicate or modify them. Missing nodes return
`nil`. Output structs have read-only public properties and no public constructor;
these access restrictions do not make them security receipts.

Shared mode selects the same theme regardless of platform. Its nodes and style
outputs are identical for otherwise equal inputs; only the plan's declared
platform metadata differs. Platform-specific mode requires the existing explicit
configuration alternative with both valid themes and its reviewable reason. The
environment cannot silently choose a different theme. The entire configuration,
including the unselected theme and all resource metadata, is validated on every
prepare call.

No public support boolean, caller-conformable adapter protocol, installed-resource
wrapper, display witness or health proof is introduced. Native adapter admission
must remain closed in its separately implemented integration layer. The public
resolver accepts raw data configuration and therefore cannot supply captured
native configuration to a signed presentation by itself.

## Closed recipes and resolution order

Order: explicit app mode/theme, light/dark palette, kind/role, existing permitted
node overrides, inherited disabled, then ephemeral pressed/focused decoration.

| Kind | Resolved data |
| --- | --- |
| text | Body/headline/title/caption size, weight and line-box floor; selectable and maxLines values. Missing style means body. |
| button | Body type, normal/cancel/destructive role, configured label insets/width/height/radius and aggregate content height floor. Normal/cancel use accent, destructive uses destructive color. |
| textField | Body type, configured insets/height/border and aggregate content height floor; placeholder, caret, selection and border paints. |
| toggle | Body type, snapshot checked value, track/thumb/inset/label-gap/row metrics and aggregate height floor; checked uses accent, unchecked toggleOff, disabled separator; thumb unchanged. |
| vStack | Explicit spacing including zero overrides theme gap; explicit leading/center/trailing overrides theme default. |
| hStack | Same spacing rule; top/center/bottom/firstTextBaseline/lastTextBaseline remain concrete logical semantics. |
| zStack | Explicit nine-way logical alignment or theme default; no synthetic spacing or child fill. |
| list | Configured insets, minimum row, row/group gaps and separator thickness; body-line-aware row floor; canvas background, surface row background and separator paint. |
| section | Optional caption header and configured logical header insets; absent header has no text. Insets apply only to an existing header. |
| navigation | Optional title role, configured title insets/alignment/bar minimum; title-line-aware bar floor when a title exists, configured bar minimum when absent; canvas background. |

All metric names ending `64` remain logical 1/64 point/dp values. Leading/trailing
and inset values remain logical in RTL, with environment direction supplied to
the native layout edge. The resolver never reverses children or rewrites content.
It performs no layout, safe-area calculation, viewport fitting, text shaping,
line breaking, pixel rounding or platform script fallback. Safe-area/viewport
constraints remain native and must not become guest padding or forged revisions.

The normalized textScale1024 and density1024 ranges are checked in full, with no
clamping. Four type roles are scaled once with the foundation's integer ties-up
math. Font size and minimum line box are already scaled in output; native
consumers must not apply semantic/sp scaling again. Layout/control metrics stay
unscaled, and density does not alter logical output. Explicit UI-v1 Double spacing
is quantized once to 64ths by the existing checked spacing operation.

Configured minimum heights remain in their original metric records. Separate
`contentHeightFloor64`, `rowHeightFloor64`, and `barHeightFloor64` values are lower
bounds, never fixed heights: button/field floors include scaled body line box plus
vertical insets; toggle includes body line box and track; list uses body line box;
navigation with a title includes scaled title line box plus title insets. Native
measurement may require still more height and must grow the row without clipping.
Aggregate sums use UInt64 intermediates and checked UInt32 output; they are not
capped to the individual scaled metric maximum. A valid extreme button floor can
be 393216. The foundation's `pixels` helper admits individual resolved metrics only
through 262144; it is not a general final layout-extent conversion API. Native
aggregate extent conversion/overflow admission needs its own integration review.

## State and paint convention

`style` accepts pressed/focused only for button, textField and toggle. Inherited
disabled wins over a descendant's explicit false, disables these decorations and
uses disabledText. Checked/value state comes from the snapshot and changes on
re-resolution of a new document, not from an unrelated style setter. Environment
re-resolution retains the snapshot's existing revision and identities.

Pressed adds the role color with configured pressedOpacityPermille over the
existing background. Focus adds the configured focus outline, and may coexist
with pressed. Neither changes geometry. Field placeholder uses secondaryText or
disabledText, enabled caret uses accent, and enabled selection uses accent with
selectionOpacityPermille. Disabled caret/selection outputs are absent.

Every `UIAppearancePaintV1` retains the original unpremultiplied RGBA8 alpha and a
separate explicit opacityPermille. Effective alpha is
`color.alpha / 255 * opacityPermille / 1000`, applied exactly once. For example,
an accent with alpha 128 and pressed opacity 120 retains alpha 128 and opacity 120;
the color is not premultiplied or rewritten to alpha 15 first. Opaque default paint
modulation is 1000. Native control ripple, elevation, dimming and a second opacity
pass must not add undocumented states. Native editing, selection/IME and
accessibility semantics still need actual adapter implementation and verification.

## Bounds and failure boundary

Before retaining any per-node output, prepare validates the complete descriptor,
normalized environment and document under `UIValidator()` standard limits. A
snapshot created with permissive custom limits is rechecked: 4096 nodes, depth 64,
1000 children per node, 16384 UTF-8 bytes per string, 1 MiB aggregate in-memory content,
and the standard closed properties/actions/structure. Exact serialized wire byte
limits remain the existing codec's responsibility. Output has one record per
node and at most 4096 total. Both standard validation and resolution admit the
entire pending frontier before appending child traversal work.

No part of prepare mutates the snapshot or reconciler. On failure no plan is
returned. This pure behavior does not implement an atomic native presentation
transaction or signed terminal/input/display/health failure rules; the eventual
integration must still enforce them.

Resources remain bounded descriptor references: catalog 64, font files 16,
font faces 16 per theme, file metadata 1...4 MiB, aggregate metadata ≤16 MiB, and the
foundation's identifier/path/digest/variant/face constraints. Success does not
read a file, validate actual byte digests or formats, establish licensing,
verify PostScript identity/glyph coverage/fallback feasibility, capture immutable
installed bytes or assert native support. A descriptor naming a nonexistent font
can deliberately resolve as data; a native resource capture must reject it before
presentation. Unavailable recipes/resources must fail native admission explicitly.

## Executable evidence and remaining gates

`verification/ui-appearance-resolution/verify.py candidate-1` freezes the complete
SDK inputs, relevant contract/reference observations, these tests/docs and public
consumer probes. It records a collection digest, revision, exact commands/tool
versions/log hashes and source stability. It runs complete SDK Debug/Release tests
and official Apple iOS/Swift Android module compilation plus a public cross-module
data access probe. A negative consumer compile demonstrates immutable output
access; it is not a security test. Receipts describe the actual run status.

These are host execution and platform compilation receipts. Native widget
consumption, unsupported recipe admission, resource capture/build packaging,
signed integration, native interaction/accessibility/IME, environment changes,
physical iOS/Android parity, Apple token approval, immutable published FieldLog,
signing/store/customer/operational/GA qualification remain pending. No physical
device discovery, run or reconnection request is made. No dependency was added.
