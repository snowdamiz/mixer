# V2 immutable appearance data resolution

`UIAppearanceResolverV2.prepare(snapshot:configuration:environment:platform:)`
produces a bounded immutable `UIResolvedAppearancePlanV2`. It opts into
`measuredShared2` explicitly. Existing V1 codecs, recipes, resolver, bootstrap and
native consumers keep their existing behavior. The binding design is
[the measured V2 contract](ui-measured-appearance-v2-contract.md), particularly
its immutable-resolution and native-transaction section, under product-plan §8.3.

This is public, untrusted data resolution. Descriptor validation, a resolved plan,
resource references, a selected profile or a host-supplied generation do not prove
native support, installed/captured bytes, font identity/coverage, attachment,
display, signed input/health or release authority. There is no public support proof
or arbitrary support protocol. Internal native resource capture, concrete build
support and atomic snapshot/identity/style/view transactions remain separate work.

## Environment and admission

`UIAppearanceEnvironmentV2` records scheme, logical direction, one selected profile,
normalized density, typed positive viewport, logical safe-area insets, an opaque
locale identifier, typed accessibility visual preferences and an immutable UInt64
generation. It has no uniform text scale. The generation is retained, including
zero, without claiming to verify monotonicity. Native owners must later capture
all values coherently and enforce stale-generation rejection.

Density is checked with the existing V2 geometry helper (128…16384 inclusive).
Viewport dimensions are positive and at most `maximumExtent64`; UInt64 safe-area
sums may not exceed the corresponding dimension. Insets are recorded without
subtracting them or adding window coordinates to content. Locale is nonempty,
control-free and at most 128 UTF8 bytes; this checks raw data bounds, not locale
installation or canonical BCP47 syntax. Bold Text and increased contrast fail
explicitly as unqualified visual operations. Reduce Motion is retained; this
recipe declares snapping without timed animation and does not implement native
accessibility behavior.

Every preparation validates the entire descriptor, including an unselected
platform theme and every resource reference, then the environment and standard
UI document bounds. It preflights all snapshot identities and original node
contents, exact node count, bounded frontier, all derived group/row/gap counts
and aggregate identity references before retaining recipe output. Any List below
another List and every nonroot navigation node fails with
`unsupportedNativeOperation`, including through intermediate Sections/stacks.
Sibling Lists remain valid. The returned node array contains exactly one record
per snapshot node in document preorder, with unchanged ID/generation, original
child IDs, inherited disabled and a closed recipe. No action binding is copied.

## Recipes, grouping and paint selection

All ten current node kinds have V2 payloads. Text and labels preserve original
strings and receive one of six exact descriptor metrics from the selected profile.
Header and expanded-navigation roles remain distinct. Max-lines and selectable
flags are retained. Control label/field/toggle metrics keep semantic content,
visual geometry and minimum hit envelopes distinct. There are no fabricated
native line boxes, final row/group bounds or navigation extents.

VStack emits exactly `max(0, childCount-1)` gaps. An explicit spacing, including
zero, wins and uses `UIAppearanceGeometryV2.spacing64`; absent spacing uses the
body→caption gap only for adjacent direct Text nodes of those roles. Other pairs
use the declared default. HStack emits the same exact count of uniform gaps;
alignment and ZStack original paint order remain logical and unchanged under RTL.
Actual native baseline layout and intrinsic overlay sizing are pending.

Each immediate Section creates group metadata; each direct non-Section run creates
one unheaded group. A group's source and rows reference existing snapshot
identities. Groups never invent document IDs or callbacks. Empty sections retain
metadata: titled ones display a header without outline/header-to-row gap; untitled
ones are invisible. The first visible entry receives topPadding once; later
visible entries receive the separately named headed/unheaded gap. BottomPadding
exists only when content is visible. Row placements reference the owning List,
group index and row index; separators are marked only before a following row in
the same group. Actual group outlines, row surfaces, separator clipping and native
height aggregation remain unimplemented by this data layer.

Immediate list Sections are structural `listGroup` context; their List owns header
and rows. A semantic Section outside a List or anywhere within a List row receives
its own leading header/content policy: header-to-content gap only when both exist,
and default gaps between content children. It receives no additional group wrapper.

`style(nodeID:pressed:focused:)` chooses whole concrete paint values. Disabled
ancestors suppress control press/focus, while ordinary Text retains its exact
role paint. Buttons select normal/destructive/cancel and enabled/pressed/disabled;
focus can coexist with press. Fields ignore press and select enabled/focused/
disabled with explicit caret, selection and outline values. Toggles select on/off
and complete state matrices; focus is independent decoration. Authored RGBA8 alpha
is neither premultiplied nor multiplied by a global disabled opacity. Clear paints
are explicit. Container, list, section, navigation and canvas paints are explicit.
Pure style calls cannot mutate geometry, identities, revision, input routing or
reconciler state.

Closed group clamp, track/thumb paths, mirrored thumb origin, measured extent
admission and raster conversion remain the existing V2 geometry API. Native
consumers must use those helpers when final native measurements exist; this layer
creates no guessed dimensions to pass to them.

## Verification and limitations

The collector in `verification/ui-appearance-resolution-v2/verify.py` freezes actual
SDK source/tests, this documentation and explicit contract inputs. Each candidate
uses new scratch directories for Debug and Release full-SDK tests and separately
compiled host/iOS/official Android public consumers. Receipts bind source revision,
source-tree digest, every command/cwd/tool version, logs, module outputs and the
runtime public-consumer output. Unit expectations independently specify profile
sizes, colors, group membership, spacing, row separator positions and node counts.
They cover all kinds, all profiles, schemes and state precedence, invalid full
configurations/environments, standard bounds and immutable identity/routing.

These are data/compilation checks. They do not qualify native shaping, resources,
IME/selection/focus/scroll preservation, measurement, drawing, accessibility,
transaction rollback, signed presentation or physical two-platform parity. Phones
remain disconnected; no device discovery/run/reconnection request is performed.
Immutable published FieldLog packages from a separate repository and all specified
signing, store, customer, operational and GA evidence remain pending.
