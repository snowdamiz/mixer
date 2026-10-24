# Internal native V2 implementation boundary

Root accepts the concrete ownership and sequencing in
`native-appearance-v2-staging.md` as an internal implementation direction.
Its compiler receipts establish API declaration feasibility only. Actual consumers
must supply native execution evidence. Neither the public bootstrap nor signed
presentation support is enabled by this decision.

The first Apple consumer is an internal UIKit controller; the first Android
consumer extends the concrete `NativeRenderer` through separate V2 methods.
They use the accepted resolvers and native path adapters. Test applications may
package the canonical descriptor at `MixerAppearanceV2/descriptor.json` and
catalog entries under `MixerAppearanceV2/resources/`. These are internal test
paths, not a newly published CLI configuration or installed-resource contract.

Each native owner captures its actual bundle and window. Application-provided
data cannot establish native support. A first implementation may accept only
`systemSans` with an empty catalog, provided all other configurations are rejected
before attachment. The complete product still requires bundled resources/fonts.
API-specific prototype limitations do not change the product Android API28 or
iOS26.0-and-later targets. The iOS baseline includes iOS27 and subsequent releases;
each supported version still needs runtime qualification. Record the operating
systems actually executed.

Candidates are bound to one owner, one base revision/identity set and one complete
window generation. They are single use. Prepare performs native measurement and
detached construction before changing live native controls. Attach gates callbacks;
successful finish uses only prepared reference swaps and reopens the gate.
Unrecoverable attachment failure retires, hides and gates the owner explicitly;
it is not a claim that the old screen was restored. Unsupported composing-editor
mutations are rejected before changing the native editor. A journal of text,
focus or selected range is not proof of restoring native composition.

Apple's internal commit may return `UIChangeSet?`: a document commit returns its
change set, while a successful environment-only commit returns `nil` and keeps
the document revision and identities unchanged. This avoids changing the public
reconciler solely for the private consumer. A thrown failure remains distinct
from a successful environment-only commit.

For the initial private HStack consumer, both adapters use this authored policy:

1. Measure every child under the full available width. If the sum of measured
   widths and the exact resolved gaps fits, retain those extents.
2. Otherwise, subtract the checked gap sum and divide the remaining logical64
   width equally. Give one additional logical64 unit to each earliest child in
   source order until the remainder is exhausted; remeasure each child under
   its resulting proposal.
3. Do not stretch a narrower result or redistribute its unused width. A fixed
   visual/hit footprint exceeding its proposal rejects the candidate. Never clip
   or shrink content to conceal overflow. RTL mirrors final placement and does
   not reverse the source-order remainder allocation.

This policy needs unequal short/long-child and overflow tests on both native
consumers. It is a shared authored behavior, not a claim of reproducing an
unmeasured SwiftUI width-allocation algorithm.

The ordinary Android engine/native commit gap remains a separate integration
dependency: current `exchange` commits before native attachment. Renderer-only
tests cannot qualify atomic engine-and-screen updates. The prepare/commit/abort
bridge proposal needs executable engine, JNI and Activity integration before
ordinary V2 bootstrap is enabled. Existing legacy and signed routes remain on
their established paths during these private implementation lanes.

The user's October 23 instruction accepts simulator/emulator results for
development acceptance and dependent work. Physical-phone validation moves to
final acceptance, followed by any required corrections. No current native
consumer slice passes the broader GA, store, customer or published FieldLog gates.
