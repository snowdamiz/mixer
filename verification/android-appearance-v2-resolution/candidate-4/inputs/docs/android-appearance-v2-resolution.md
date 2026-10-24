# Android V2 immutable appearance data resolution

`AppearanceResolverV2.prepare(packetBytes, canonicalDescriptorBytes, environment,
platform)` independently decodes the complete actual `UiPacket` and V2 descriptor
before retaining immutable data recipes. The API is package-private, explicitly
V2, and does not alter V1 resolution, packets, rendering, JNI or bootstrap.
It implements the data-resolution seam in product-plan §8.3 and the
[measured V2 contract](ui-measured-appearance-v2-contract.md), consistent with the
[Swift candidate](ui-appearance-resolution-v2.md). That candidate's actual frozen
bytes are comparison inputs, not an acceptance claim.

The input descriptor is the exact canonical Swift V2 format. There is no Java
default theme table. Every preparation validates both complete platform themes
and all resource/font references, including an unselected platform. Resource and
font metadata remain references only. No bytes are loaded or native fonts installed.

Environment contains scheme, direction, one selected six-role profile, normalized
density, positive logical viewport, safe area, opaque locale, visual preferences,
and an exact canonical UInt64 decimal generation including zero. It contains no
uniform text scale. Density must be 128…16384; viewport and each safe-area side
are bounded by Int32.max, and opposing side sums cannot exceed the viewport.
UTF8 locale size is 1…128 bytes, with controls/format characters and malformed
UTF16 rejected before replacement encoding. Bold Text and increased contrast are
explicit unsupported operations. Reduce Motion and generation are retained; pure
preparation cannot verify coherent native capture or monotonicity.

The actual V1 packet profile remains in force: schema 1; at most 1 MiB; 4,096
nodes; depth 64; 1,000 children; exact identity coverage with nonzero unique UInt64
generations; required control actions; bounded strings/properties/actions; closed
node kinds/properties. It rejects a List beneath any List, including through
intermediate containers. Explicit HStack alignment accepts top/center/bottom and
rejects first/last baseline. A V2 theme may name a baseline default, which this
pure recipe retains; a later native consumer must reject unsupported operation
support. Resolver preparation additionally rejects every nonroot navigation node.
None of these limits is bypassed with fabricated test Nodes or widened validation.

Plan records are copied into immutable lists/maps in exact document preorder,
with exact original revision, ID/generation strings, child order and inherited
disabled state. The plan holds no action bindings. Six-role metrics preserve
text, selection/max-lines and body/control/header/navigation role distinctions.
All ten kinds have closed recipes, including exact childCount−1 VStack/HStack
gaps, explicit-zero spacing precedence, direct adjacent body→caption spacing,
logical alignment, original ZStack order and distinct label/control/hit metrics.
No native text box, line advance, row/group/navigation extent is fabricated.

Immediate list Sections retain group metadata; direct non-Section runs create
unheaded groups referencing existing nodes. Header-only and invisible empty groups
have distinct visibility/outline/gap behavior. Top padding is charged once to the
first visible entry; later groups use headed/unheaded gaps; bottom padding exists
only for visible content. Rows refer to exact owning List/group/row identities;
only interior rows of that group receive separatorAfter. Immediate Sections are
structural listGroup context; semantic Sections outside a List or inside a row
retain their own header/content policy without an extra group wrapper.

`Plan.style(id, pressed, focused)` selects whole concrete paints with authored
unpremultiplied RGBA8 alpha applied once. Disabled suppresses control press/focus,
text retains its role paint, field ignores press, and button/toggle focus may
coexist with press. Canvas, backgrounds, separators, outlines, carets, selections
and clear paints are explicit. Style calls cannot change geometry or identities.

`verification/android-appearance-v2-resolution/verify.py` archives actual source,
contract, descriptor, corpus, command/cwd/tool outputs and digests. Each Swift
Debug/Release and JVM default/-Xint variant receives a fresh source copy and build
directory; JDK25 compiles with `--release 17 -Xlint:all -Werror`. The probe exports
packets from actual Swift snapshots and compares complete resolved fields/state
paints across languages. Independent Java checks cover semantic expectations,
invalid raw environments, real decoder restrictions, node/depth limits, exact
UInt64 preservation, defensive ownership and immutable plan collections.

This is pure host data verification. Android framework/native preference capture,
resources/fonts, shaping, baseline layout, drawing, scrolling/IME/focus/selection,
accessibility, atomic native transactions and stale-environment enforcement are
pending. No build support, public proof, signed V2, display/input/health authority
or OTA publication is supplied. Phones remain disconnected. Physical parity,
immutable published FieldLog packages from a separate repository, signing, store,
customer, operational and all GA gates remain pending.
