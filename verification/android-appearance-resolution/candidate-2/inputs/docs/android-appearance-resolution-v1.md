# Android appearance data resolution v1

This private Java resolver consumes the same canonical app descriptor as the
accepted public Swift `UIAppearanceResolverV1`. It implements the provisional
`sharedCandidate1` data contract for all ten UI-v1 kinds. It changes no native
widget, renderer, resource installation, signed factory or release authority.
Apple typography, list, navigation and toggle token measurements remain a
separate review; this candidate does not approve a new product appearance.

`AppearanceResolutionV1.prepare(UiPacket, AppearanceDescriptorV1, Environment,
Platform)` returns an immutable plan. The environment explicitly selects light or
dark, logical direction, textScale1024 in 512...4096 and density1024 in 128...16384.
Invalid or absent input fails before a plan is returned. The private outer
constructors of both inputs admit only their full validated decoder results.
`AppearanceDescriptorV1` recursively freezes its complete canonical graph,
including both platform themes and resource metadata. `UiPacket.decode` builds
properties/actions/children/node maps in private local builders and exposes only
unmodifiable wrappers; String, Boolean and final Json.Num leaves have no mutable
state. The resolver copies its child ID lists and final preorder node list and
retains only immutable descriptor references. No parser trust is extended to an
arbitrary node assembled with the package-private Node constructor.

The plan retains exact decimal UInt64 revision and node generations, original
IDs, kind, inherited disabled value, and original child order. It exposes a closed
sealed recipe family with typed immutable text and metrics for every kind.
`node(id)` and `style(id, pressed, focused)` return null for missing IDs. Text,
labels, field contents, actions and accessibility data continue to belong to the
original packet. The resolver never changes event encoding or node identity.

All metrics stay logical 1/64 point/dp values. Four type roles use integer
`(metric64 * textScale1024 + 512) / 1024` once; density does not change logical
output. Explicit stack spacing uses the same finite bounded Double quantization
as Swift. Logical insets and alignments remain logical under RTL and children
retain packet order. Aggregate minimum height floors include scaled line boxes
and vertical insets, use long intermediates and checked UInt32 output, and can
reach 393216. They are lower bounds, not fixed sizes or native measurements.
Native aggregate extent conversion and layout overflow admission remain pending.

Canvas paint is explicit. Each paint retains original unpremultiplied #RRGGBBAA
and a separate opacityPermille; effective alpha is alpha/255 * opacity/1000,
applied once. Disabled ancestors override descendant false and suppress transient
states. Buttons, fields and toggles alone admit press/focus. All optional paints,
focus outline and role colors match Swift. The Java resolver supplies no default
theme, native ripple, elevation, fallback, dimming or implicit semantic scaling.
Font and resource references can deliberately name nonexistent bytes; this data
operation grants no file/digest/PostScript/glyph/licensing or installed authority.

Standard packet limits bound bytes to 1 MiB, nodes to 4096, depth to 64, children to
1000 and each content string to 16384 UTF-8 bytes. The packet byte bound is at
least as restrictive as the Swift in-memory aggregate content bound. Resolution
also checks packet identity/coverage and admits the full pending frontier before
adding traversal work. Existing native packet admission is narrower than Swift:
explicit hStack firstTextBaseline/lastTextBaseline and nested scrolling lists are
rejected by UiPacket. Descriptor-selected baseline defaults resolve as concrete
logical values. This lane preserves those existing parser boundaries; native
adapter support and coordinated parser widening remain separate work.

`verification/android-appearance-resolution/verify.py candidate-N` freezes exact
Java and SDK sources, docs, scripts, canonical descriptor and accepted Swift
receipt. It records revision, source digest, commands, versions, output hashes and
unchanged-source checks. The independently generated corpus supplies descriptors,
documents and environments. A separately compiled public Swift consumer exports
the actual reconciler packet and canonical SHA256 of every retained plan field,
all ten recipes and all four pressed/focused states. Java compares complete
retained output, exact identity/revision/event bytes and immutable collections.
Swift Debug/Release outputs must agree byte for byte; Java compiles with
`--release 17 -Xlint:all -Werror` and executes default and `-Xint` against both.
These are host data tests, not physical Android/iOS, native geometry/raster,
interaction/accessibility/IME, resource capture, signed/display/health, immutable
published FieldLog, store, customer, operational or GA receipts. Phones remain
disconnected; no device discovery, run or reconnection request is made. No
dependency is added.
