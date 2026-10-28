# Public native theme boundary: bounded source review

Review date: 2026-10-28. This packet proposes no canonical change and grants no
native, installed-package, appearance-parity, release or GA acceptance.

The public `MixerNativeView` constructs ordinary SwiftUI controls. It sets no
local tint, color scheme or root foreground style. Source review therefore finds
no API obstacle to an enclosing native app supplying its current dynamic tint.
Actual propagation through the consuming app's presentation hierarchy has not
been executed. The current host has no `UIAppearanceConfigurationV2` input.

The shared theme contract already exists: `UIAppearanceConfigurationV2`,
`UIThemeV2`, `mixer.native-appearance.2`, and `measuredShared2`. It describes light
and dark paints, text profiles, control states, field caret/selection/focus,
grouped lists, navigation and layout. The existing codec validates the entire
descriptor. A second appearance format is unnecessary.

## Proposed immediate public API

**No additional public theme API for native tint inheritance.** The existing
surface is sufficient for an explicit native development slice:

```swift
let host = try MixerUIHost(document: document)
MixerNativeView(host: host, onAction: handleAction, onEventFailure: handleFailure)
    .tint(appOwnedDynamicTint)
```

This is a generic public example, not copied consumer source. The app supplies
its own dynamic tint at the enclosing view or this boundary. This does not meet
the shared-theme contract: SwiftUI still supplies most typography, geometry and
control appearance. Keep the existing default wire shape and validators.

After the nine newly prepared public SDK tests pass ordinary remote CI, root may
select separate consumer adoption of the public host and newly authored vertical
text-field axis. That is concrete public SDK adoption work, but a
development slice must not be called theme-preserving completion while the
remaining styling and navigation fidelity below are unresolved.

## Requirements and fidelity boundaries

Generic consumer requirements observed in the read-only review:

- A multiline field must preserve Unicode and line breaks, with native input,
  disabled state and current-owner event routing.
- The accent changes with the actual light/dark native environment.
- Supporting disclosure and storage failure remain readable and visibly
  distinguishable from the editable content. The current public document lacks
  independent secondary/error text paint roles. The existing `caption` role alone
  does not express those distinctions.
- Save/cancel actions and navigation remain discoverable and preserve their
  busy/disabled behavior. The public document currently places action buttons in
  content, while the native consumer has navigation actions. Theme inheritance
  cannot resolve that difference.

An error glyph, exact navigation action placement, inline/expanded title choice
and exact semantic font mapping are visual fidelity decisions for the consumer.
They are not prerequisites for transmitting form values/events, but this review
does not authorize dropping them or declare them optional decorations. Product
plan section 8.3 requires explicit permitted degradation and preview evidence.

The public V2 text paint roles cover body, headline, title, caption, section
header and expanded navigation. They do not include error text. Do not repurpose
a caption/title role as an undocumented error style or use destructive button
paint as an arbitrary text role. Exact semantic styling needs a coordinated
authoring/versioned-contract decision.

## Full V2 route: coordinated platform work

An `appearance: UIAppearanceConfigurationV2` parameter that applies only an accent
and leaves other descriptor fields at SwiftUI defaults would silently ignore a
required contract. Do not ship that partial interpretation.

The existing `AppearanceNativeRendererV2` cannot simply be exposed as the public
task-editor host. Its installation owner accepts a captured bundle descriptor,
its environment path admits a historical narrow runtime, its editor is a
`UITextField`, and its resolver/reconciler use the horizontal-only default
validator. It currently cannot preserve the multiline requirement. Its installed
resource authority and fail-closed checks must not be bypassed to add a facade.

The smallest eventual public appearance surface is an additive, explicit host
construction path using the existing V2 descriptor/installation owner and the
existing `MixerNativeView` event surface. Exact initializer spelling is deferred
until the platform owner coordinates bundle ownership and environment failure
handling. It must atomically validate/prepare before publication, reject every
unsupported theme/resource/operation, preserve stale-event rejection, and admit
vertical fields only once the selected native backend implements them. No
descriptor format or default-wire change is proposed by this packet.

## Ownership and executable follow-up

Current lane owns only `verification/public-ui-theme-contract/`. No canonical or
private consumer file is edited. Root owns coordination and delivery.

Recommended consumer ownership, after the nine public tests pass remote CI and
if selected by root: only the native
task-editor view, its public document builder, and their existing consumer tests.
Use the public host and the public vertical axis; preserve the enclosing app
theme. This lane has read-only access and does not implement that work.

A full V2 host lane would need explicit ownership of
`sdk/Sources/MixerApple/MixerNativeView.swift`, the selected V2 native host/editor
and environment files, any coordinated V2 resolution changes, a new focused
Apple test file and SDK documentation. That crosses the platform-owner boundary
and is not selected or implemented here. No Android owner file is included.

The nine public multiline tests must pass remote CI before private host adoption
is selected. Named executable tests for a later consumer slice:

1. Ordinary remote Swift CI compiles a public consumer using `MixerUIHost`,
   `MixerNativeView`, an app-owned dynamic tint and the vertical field. This is
   public API/type integration evidence only.
2. Consumer host tests assert the authored vertical field, exact multiline and
   Unicode value round-trip, busy/disabled save state, save failure draft retention,
   and stale/wrong-generation event rejection through the same public document.
3. Existing codec/host tests assert horizontal default wire compatibility,
   unsupported-consumer vertical rejection and failed-update preservation.
4. Once native runtime testing is resumed, the consumer must check both schemes,
   focus/selection/IME, native action placement, error/disclosure styling and
   accessibility with the public host. A compile or source inspection cannot pass
   these checks. Physical reference-screen parity remains final acceptance work.

No compiler, test, native rendering, UI automation, screenshot, process inventory,
custody probe, GitHub/API call, commit, push or dispatch ran in this lane. Phones
remain disconnected. Local compiler cleanup, UnitA, custody and native holds are
unchanged. The earlier nine multiline tests remain unrun here. A separately
published immutable dependency consumed by the private repository remains required
for dogfood qualification.
