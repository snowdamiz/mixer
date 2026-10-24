# Apple native paths for measuredShared2

The internal `AppearanceNativePathsV2.make(_:density1024:)` converts only the
closed `UIAppearanceGeometryV2.Path` recipes into a fresh immutable `CGPath`.
It emits each move, line, cubic and close command directly. Each coordinate is
converted from logical 64ths into fractional physical pixels once; control
points do not use integer edge rounding. Invalid normalized density fails even
for empty geometry. A failed native copy throws rather than returning a partial
path. The helper does not cache paths or accept arbitrary descriptor commands.

The consumer must establish a top-left pixel coordinate system, place/clip the
path, and use nonzero winding fill. For a default bitmap context this can require
an origin translation and y-axis flip; no second density scaling is permitted.
CoreGraphics uses CGFloat precision on these targets. Android's corresponding
native Path stores float coordinates, so their native coordinate representations
can differ at large extents. This primitive does not substitute a platform corner
radius or claim equivalence to Apple's private shapes.

`verification/apple-appearance-native-paths-v2/candidate-2/receipt.json` records
131 full SDK tests per Debug/Release, including four new actual CoreGraphics
tests. They inspect all commands/coordinates for five shapes at five densities,
exercise zero-area/invalid-density behavior and independent mutable copies, and
check actual bitmap clipping/fill, bounds and interior/exterior samples at 2x
density. All three Core/UI/Apple modules compile for arm64 iOS17 with warnings
as errors. These are host native-primitive tests and iOS compilation, not an iOS
display observation.

Candidate1 is retained as a failed harness run: the snapshot omitted three
existing SDK fixture files, and its bitmap test assumed the default CGContext
used top-left coordinates. Candidate2 copies the required fixtures and explicitly
sets the bitmap coordinate convention. The production adapter is unchanged
between those attempts. Reproduce into a fresh directory with:

```sh
python3 verification/apple-appearance-native-paths-v2/verify.py candidate-new
```

The ordinary renderer does not yet consume this helper. Native descriptor and
resource capture, fonts and actual layout, every widget's shared style, atomic
attachment/state preservation, physical side-by-side design parity, signed V2,
published FieldLog and all GA gates remain pending. No new dependency or asset
is introduced, and phones remain disconnected.
