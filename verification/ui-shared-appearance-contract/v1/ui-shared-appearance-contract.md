# Shared native appearance v1: proposal for root review

Status: **design only**, 2026-10-23. No renderer, SDK default, package, signed
identity or release authority changes. Binding scope: product plan §§8.1–8.4.
Exact reviewed inputs and declaration-only compilation are recorded in
`verification/ui-shared-appearance-contract/receipt.json` and `input-lock.json`.

The existing Apple screen is the design reference. `MixerNativeView` currently
uses semantic fonts and implicit Button/TextField/Toggle/List/NavigationStack
appearance; it supplies no numeric reference for those implicit styles. Android
currently adds different font sizes, text padding, button colors, list insets,
title sizes and child fill rules. Neither adapter meets updated §8.3. Candidate
values below make the intended starting point concrete; they are not measurements
of SwiftUI, proof of parity, or an approved redesign of existing iOS screens.

## 1. One installed app configuration; unchanged documents

Add a small, owned native appearance foundation in MixerUI, consumed by both
native adapters. The app declares **one** immutable configuration/default. Its
shared theme owns content appearance, component recipes and default layout
metrics. UI-v1 continues to own tree/hierarchy/content, explicit stack spacing,
alignment, text style, button role and disabled/accessibility values.

Proposed author-facing seam (declaration probe is separate from product sources):

```swift
public enum UIAppearanceModeV1: Sendable {
    case shared(UIThemeV1)
    case platformSpecific(iOS: UIThemeV1, android: UIThemeV1, reason: String)
}
public struct UIAppearanceConfigurationV1: Sendable {
    public init(id: String, mode: UIAppearanceModeV1) throws
    public static let mixerDefaultV1: Self
}
public enum UIFontSourceV1: Sendable {
    case systemSans
    case bundled(faces: [UIFontFaceV1], fallback: UIFontFallbackV1)
}
public enum UIFontFallbackV1: Sendable { case none, systemSans }
// UIThemeV1 = light/dark palettes + typography + metrics + closed recipes + assets.
// One internal pure resolver prepares a whole validated document before mutation.
```

No user-supplied callback, stylesheet, native class name, URL, executable shader,
selector language or toolkit style ID is part of these values. The ordinary
`MixerUIHost` default must resolve `mixerDefaultV1`; it must not expose `.automatic`
or silently inherit native control appearance. Explicit native appearance can be
added later only as a separately named app declaration and qualified profile.
`platformSpecific` requires both complete themes and a nonempty reviewable reason;
its reference evidence records the declared differences. It is never inferred
from OS, an unavailable asset, or a failed renderer operation.

Native builds package the same bounded local descriptor bytes for Apple and
Android from one app configuration source. Proposed format name is
`mixer.native-appearance.1`, **not UI-v1 or a guest protocol**. A build tool may
emit those data resources from Swift configuration; no independently maintained
Java default table. Root must freeze the descriptor codec and build-consumption
seam before implementation. Initially the exact built-in descriptor can be a
reviewed SDK-owned resource copied unchanged into both native targets.

The descriptor is at most 64KiB: closed fields/enums, exact required token sets,
finite bounded numbers, no duplicate keys, ≤16 font faces and ≤64 asset entries.
IDs are nonempty ≤128 UTF-8 bytes. Colors are sRGB RGBA8; separate alpha is 0...1.
Logical metrics are
0...1024 points/dp, font sizes 1...256, weights one of 400/500/600/700, and scales
0.5...4. No arbitrary property dictionary. Its digest identifies configuration,
not a security receipt. Constructors validate the complete graph and resources.

## 2. Closed descriptor and resolution rules

`UIThemeV1` contains exactly these groups; native adapters may not invent values:

| Group | Required values |
| --- | --- |
| Palette, each light/dark | canvas, surface, primaryText, secondaryText, accent, destructive, disabledText, separator, focus, toggleOff, toggleThumb; pressed overlay color/alpha |
| Typography | font source; body/headline/title/caption size, weight and minimum line box; button/field/toggle map to body; section to caption; navigation title to title |
| Layout | missing stack gap and alignment defaults; list logical insets, row minimum, row gap, group gap, separator thickness; section header insets; navigation content/title metrics |
| Controls | plain button label insets/minimum hit envelope/corner radius; field insets/minimum height/border; toggle track/thumb sizes and label gap; focus ring width/radius; no implicit ripple/elevation |
| Assets | logical ID, kind, bundle-relative path, byte digest, license/provenance reference, supported scale/locale/direction variants; font face entries also name weight/style/PostScript identity |

Internal inputs are a `ValidatedUIDocument`, captured configuration, trusted
adapter-supported recipe set, and native environment (light/dark, logical layout
direction, requested text scale, viewport and system safe-area insets). The
resolver returns a bounded immutable style plan, never execution or health proof.
The environment cannot change theme identity or choose platform-specific mode.
For equal config/node/state/normalized environment, Swift and Java must resolve
equal logical values before native pixel rounding or text shaping.

Proposed internal seam is `prepareAppearance(document:captured:environment:
adapter:) throws -> UIPreparedAppearanceV1`; `document` is validated, `captured`
owns the validated native configuration/resources, and `adapter` is a closed
build-owned support value. The plan has at most one record per bounded document
node and resolves `style(nodeID:pressed:focused:)` using inherited disabled/value
state. It exposes concrete color/type/inset/layout/control values, never a native
view or callback. No caller-supplied conformance can advertise renderer support.

Resolution order is: app mode/theme → environment light/dark → fixed kind/role/
text-style recipe → permitted explicit UI-v1 property → inherited disabled →
native ephemeral pressed/focused state. No per-node theme/style key is added.
`spacing` already present on vStack/hStack wins over theme default, including zero;
missing spacing resolves to 8. Missing stack alignment is center. Logical leading/
trailing mirrors under RTL; child order/content/IDs are unchanged. No CSS cascade.

Prepare and validate the entire candidate style/resource plan **before** view or
reconciler mutation. Ordinary failure preserves the previous tree/snapshot. The
signed path follows its existing terminal presentation failure/retirement rules;
an older displayed tree must not earn new input or health after failure. Applying
document, identities and style plan is one UI-thread transaction. Style changes
must not reset a surviving node's identity, selection, IME composition or scroll.

Environment changes re-resolve the current document without forging a new guest
revision or event. Configuration is immutable for one installed host/session;
replacing it requires a new native bootstrap/host, with old listener/probe cleanup.
Signed presentation must invalidate its current display observation when relevant
environment/style changes affect the tree and earn a fresh real display witness;
resolver success is never that witness.

## 3. Concrete initial recipe candidates

These values are one iOS-oriented candidate for `mixerDefaultV1`, pending an
unchanged-Apple reference capture and root token review. Where that capture
disagrees, revise the shared candidate for both adapters before qualification.
Do not copy today's Android values as the reference.

| Token | Initial shared value and reason |
| --- | --- |
| Fonts | Explicit `systemSans`; body 17/400/22, headline 17/600/22, title 28/400/34, caption 12/400/16 (size/weight/minimum line box). Retains Apple's four semantic roles and hierarchy; Android's current 16/19/26/14 table is removed. These numbers are proposed, not measured SwiftUI metrics. |
| Light palette | canvas #FFFFFF, surface #F2F2F7, primary #000000, secondary #606068, accent/focus #007AFF, destructive #FF3B30, disabled #8E8E93, separator #D1D1D6, toggleOff #E5E5EA, thumb #FFFFFF. Explicit iOS-oriented direction; no Material palette. |
| Dark palette | canvas #000000, surface #1C1C1E, primary #FFFFFF, secondary #AEAEB2, accent/focus #0A84FF, destructive #FF453A, disabled #8E8E93, separator #38383A, toggleOff #39393D, thumb #FFFFFF. All listed colors opaque. |
| Text/stacks | Text has zero added insets; stacks gap 8, center alignment, intrinsic child size constrained by parent. No universal Android child fill or 4×6 text padding. Explicit node spacing/alignment retained. |
| Button | Plain label, normal/cancel accent, destructive uses destructive; clear background, no normal border/elevation, label inset 0; minimum hit envelope 44×44 logical units, corner 8 for state overlays. Review envelope's effect on existing Apple layout. |
| Input/toggle | Field body, clear background, 0 label inset, minimum row 44; normal border 0, cursor/tint accent. Toggle track 51×31, thumb 27, inset 2, label gap 8, minimum row 44. These candidate dimensions need native feasibility and Apple-reference checks. |
| Collections/chrome | Candidate list logical inset 16, top/bottom 8, row minimum 44, row gap 0, group gap 16, separator 1; section caption header inset start/end 0, top 16/bottom 8; app navigation title leading, inset 16, top/bottom 8, minimum bar height 44. Current implicit Apple List/navigation appearance must be captured before freezing these recipes. |

Normal is the base state. Pressed adds accent (destructive for that role) at 12%
over the component's existing background; it adds no padding, scale or animation.
Disabled uses disabledText, disables pointer/keyboard activation and clears
pressed/focus decoration; ancestor disabled wins. Focused adds a 2-unit focus
outline without changing layout. Focus can coexist with pressed; native
VoiceOver/TalkBack focus rings/actions remain native. Toggle checked uses accent
track, unchecked toggleOff; disabled track uses separator and thumb unchanged.
Field placeholder uses secondaryText; disabled uses disabledText; composition,
selection, caret movement, validation events and keyboard handling remain native.
Input selection highlight uses accent at 24%; platform editing menus remain native.
Native disabled dimming, button ripple, font padding and automatic capitalization
must not add a second visual state on top of these resolved values.

The shared resolver multiplies font size/minimum line box by normalized textScale
once; adapters must avoid a second system/sp multiplier. Native preference
translation is explicit and tested; the same requested normalized scale gets the
same values on both platforms. Font scale must not shrink to fit a fixed control:
rows grow to fit content/line boxes, and native shaping may require more height.
No clipping or silent accessibility-size cap. An unsupported environment is an
explicit availability failure, not a smaller font. Logical metrics remain density
independent; the final native boundary rounds positive pixels to nearest with
ties upward. Native safe-area insets constrain the available rect once; they do
not become guest padding. Respect OS layout direction and locale text shaping.

`systemSans` intentionally selects each platform's installed system sans face;
equal scale/weight/hierarchy is required, exact glyph/raster equality is not
claimed. That explicit policy includes native script/emoji font fallback. No
Apple font redistribution or font download is implied. For a specific
shared face, the app supplies licensed, hash-bound native-compatible files to both
bundles; missing face/weight/glyph coverage fails unless an explicit declared
fallback covers that text. `fallback: none` never substitutes systemSans. No
app-owned font or icon asset currently supplied by this proposal is claimed.
UI-v1 has no image/icon node: default app chrome uses no platform icon. Later
required icons use the same app-owned asset IDs/bytes and declared RTL variants;
SF Symbols/Android system icons are not an undeclared shared substitute.

## 4. Coverage and native behavior boundaries

| Current kind | Shared recipe obligation; remaining implementation |
| --- | --- |
| text | Four explicit text roles, wrapping/maxLines, selection flag; preserve native shaping and selectable-text semantics. |
| button | Label/role and four states above; native button accessibility/keyboard activation, existing action routing. |
| textField | Shared field geometry/colors/type; preserve native IME/composition/selection/submit and a11y editable role. |
| toggle | Shared track/thumb/label recipe and value states, native switch role/actions; a default platform switch drawable is insufficient. |
| vStack | Fixed intrinsic layout/gap/logical alignment; first signed implementation priority. |
| hStack | Same sizing/gap and top/center/bottom/baseline semantics; Android currently rejects baseline alignments—no parity claim until implemented or both adapters reject that required profile. |
| zStack | Shared overlay sizing/alignment/order; no Android-only child fill. |
| list | Shared app row/group/background/separator recipe; native scrolling, stable identity and scroll retention. No nested-scroll fallback. |
| section | Shared header/content spacing/type; native grouping semantics remain; no automatic toolkit casing/insets. |
| navigation | One existing root only; shared app title/bar/content chrome; native back/system behavior. No claim of routes, sheets, tabs or predictive-back completion. |

First implementation may qualify only `{vStack,text,button}`. Its support set must
say so; it cannot relabel a ten-kind decoder as ten-kind shared appearance support.
Any missing required recipe, text operation, asset or layout support rejects the
whole candidate. There are no decorative degradation permissions in UI-v1.
Do not fake text fields/toggles with drawn controls or replace native input/a11y.
Status bars, permissions, keyboard, share sheets and other system-owned surfaces
keep native appearance. Native capabilities/views need their later explicit policy.

The entire §8.2 inventory remains required: adaptive/safe-area/grid layout,
localization/links, remaining controls, lazy/paginated/swipe collections, full
navigation/restoration, images/assets/shapes/transitions, gestures, native surfaces
and complete accessibility. This foundation is not whole-UI or FieldLog completion.

## 5. Compatibility, signed integration and ownership

No change to UI-v1 document properties/bytes, ordinary NativePacketV1, signed
guest headers/events/subset/limits, identity/release signature domains or frozen
contracts. Unknown style properties keep rejecting. A configuration digest is not
an extra field accepted from a guest, release envelope or downloaded theme. Future
node-level appearance/font/asset references require an explicitly versioned owned
wire/profile/identity contract and native implementation before release selection.

Capture descriptor bytes plus validated immutable font/asset bytes from the
installed native bundle once, before presentation setup; verify digests, no path
escape/symlink reread or mutable downloaded file. The signed factory must derive
configuration from this installed material and pass that same captured value to
Apple and eventual Android presentation. No app-callable signed-theme setter,
guest-selected config ID or independently supplied “supported” flag. Appearance
source/resource hashes and actual build consumption belong in existing exact
native build/source/dependency closure; root must identify the specific legal
closure bindings without adding frozen identity fields. If that cannot faithfully
bind the configuration, signed use stays pending until a versioned contract does.

Changing native appearance requires a new native build and its own compatibility
evidence. Equal UI-v1 bytes do not prove old package/release compatibility. Signed
activation, event authority, lifecycle, observation and health gates are unchanged.
The stage5 JNI proposal stays frozen: no new `mxis_*` argument, setter or packet
field. Its proposed SignedUiStyle consumes the native captured descriptor through
a later root-approved installation edge; absent that edge, signed styling is
pending. New ordinary `NativePacketV1.swift` encoding is a separate root-owned lane.

Root should assign these serial boundaries before adapters depend on them:

1. **One foundation owner:** proposed new `sdk/Sources/MixerUI/AppearanceV1.swift`,
   closed descriptor codec/default resource and focused SDK tests; freeze numeric
   resolution, limits, provenance and app-build artifact before adapter edits.
2. **Apple owner:** `MixerNativeView.swift` and its host capture/atomic style plan;
   capture unchanged iOS reference before applying candidates. Signed capture in
   capability-activation has one separately coordinated owner; no new public proof.
3. **Android owner:** new owned shared native style consumer used by ordinary and
   separate signed renderers; coordinate descriptor installation with JNI owner.
   `Json`/`UiPacket` parser identity/event semantics stay intact. No copied renderer.
4. **Integration/review owner:** verify exact same app descriptor in both native
   bundles, signed closure consumption, failure atomicity and reference captures;
   then update STATUS/work graph/gates with executed scope only.

This lane owns only this proposal and `verification/ui-shared-appearance-contract/**`.
It changes no production sources, fixed contracts, plans/gates or delivery state.

## 6. Focused executable acceptance to assign after contract freeze

- Swift and real JVM/Java resolve the **same captured descriptor** and independently
  supplied node/state/environment cases: all ten kind mappings, every role/style,
  missing/zero spacing, inherited disable, four states, light/dark, scales 1/1.4/2,
  RTL logical metrics and density rounding ties. Compare complete resolved values;
  verify native widgets consume them, not just two copies of a constants table.
- Negative cases: duplicate/unknown/missing config fields, nonfinite/out-of-range
  values, unsupported required recipe/baseline, absent/wrong-hash/wrong-weight font,
  missing RTL asset, unauthorized fallback and downloaded descriptor. Assert no
  partial view/snapshot replacement; signed failure earns no input/display/health.
- Apple/Android native reference screens exercise text wrapping/truncation/selection,
  plain normal/destructive/cancel buttons and pressed/disabled/keyboard-focused
  states, input composition, toggles, stacks, list/section/title and retained IDs.
  Capture equal content/viewport/logical scale, light/dark and RTL; record exceptions
  for real shaping/raster/density/safe areas and review hierarchy/color/spacing.
- Ordinary/signed subset renders use the same descriptor digest and resolved
  values. Real native event/IME/a11y and signed lifecycle tests must still pass;
  renderer snapshots are not native display or signing receipts.

Host declaration compilation proves only representability of the proposed API.
Swift/Java implementation parity, native screenshots, device accessibility,
performance budgets, immutable separately published FieldLog, compatibility and
accountable GA evidence are pending. Physical iOS/Android side-by-side review is
pending while phones remain disconnected; no discovery/run/reconnect request.
