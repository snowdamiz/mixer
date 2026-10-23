# Shared authored geometry V2

`UIAppearanceGeometryV2` supplies the closed shapes from the accepted
[measured appearance contract](ui-measured-appearance-v2-contract.md). It is an
opt-in pure SDK API; neither current renderer consumes it yet.

- `group(width64:height64:radius64:)` returns one full-group cubic outline. Its
  tangent-aware radius clamp prevents overlapping corners in small rectangles.
- `track()` and `thumb()` return the exact versioned 63×28 and 37×24 paths.
  `thumbOrigin(checked:direction:)` mirrors the checked end under RTL.
- `measuredExtent64` rounds native measured logical extents upward. `spacing64`
  and `normalizeDensity` use nearest/ties-up rounding with explicit input bounds.
- `pixelEdge` rounds absolute edges once. `pixelCoordinate` preserves fractions
  for cubic controls. An adapter must not apply density again to these pixels.

Coordinates are logical 1/64 point/dp values. Paths are immutable and have no
public constructor or descriptor-supplied command parser. Empty boxes return an
empty group path after validating all inputs. Invalid dimensions, radii, density,
nonfinite measurements and unsupported spacing throw explicit geometry errors.
The authored curves do not promise exact reproduction of private native shapes.

The frozen candidate3 qualification passes all94 SDK tests per Debug/Release,
compares980 group paths, both fixed paths, four RTL states and72 density conversions
per host mode against the sealed contract, and compiles iOS17 and official
Swift6.3.3 Android30 modules/public callers. Candidate1 retains a test-source syntax
failure; candidate2 retains missing V1 fixture errors in the snapshot harness.
Candidate3 corrects the fixture closure without changing product geometry.

See `verification/ui-appearance-geometry-v2/candidate-3/receipt.json` and
`verification/ui-appearance-geometry-v2/acceptance.json`. Native drawing, control
interaction, installed resource capture, appearance descriptor consumption, signed
presentation, physical design-parity review and all GA gates remain pending.
