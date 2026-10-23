# Apple font profiles and bounded contextual candidates

This separate derivative preserves the immutable 359-artifact measurement seal.
It collects all 12 supported SwiftUI DynamicTypeSize preferences from the actual
simulator environment in Debug and Release, using public Font.resolve plus actual
public UIKit navigation-title UIFont properties. Hidden fixed-size `Text("Ag")`
and `Text("Ag\nAg")` probes record native one/two-line layout heights for all four
semantic text roles. These observed boxes and repeat-line increments are kept
separate from CoreText ascent/descent/leading and UIFont lineHeight.

[Findings](../../docs/apple-appearance-font-profile.md),
[type data](type-profiles.json), [candidate comparisons](candidate-comparisons.json),
[normalization proposal](normalization-proposal.json), [gallery](gallery.html).

The candidate changes only three public font modifiers in the separately copied
renderer: Section header Text `.font(.headline)`, Button `.font(.body)` and Toggle
`.font(.body)`. All other fonts, palettes, geometries and native styles stay as in
the frozen source. The hidden line probes and font export are verification-only
harness instrumentation. `candidate-fonts.patch` identifies the exact candidate.

The focused candidate matrix has 12 Debug cases: typography, controls and layouts
at large; Arabic RTL at accessibility-medium; LTR typography and controls at
accessibility-medium; each light/dark. Three Release candidates repeat typography
light, controls dark and Arabic RTL light. Three Debug candidates-disabled PNGs
protect harness nonperturbation. All compare against the prior immutable native
measurement PNGs. Acceptance is limited to observed matches in these cases;
full type-table data does not imply contextual candidate qualification at every
size or a universal hidden-toolkit font rule.

`capture.py` uses only dedicated simulator UDID
`1A7E942B-CF97-4DBB-8786-1D982744EBE4` (`MixerAppearanceMeasurement`, iPhone 18 Pro,
iOS 27.0 24A434). This app has its own bundle/container. No physical inventory,
run, or reconnection request occurs. The source-copy digest is recorded before
builds and checked after captures. Xcode 27.1 / Simulator SDK 27.1 / Swift 6.4
builds and exact commands/output hashes are retained. Both earlier seals are
read-only inputs, never regeneration targets.

For an intentionally separate new version of this evidence:

```sh
python3 verification/apple-appearance-font-profile/scripts/capture.py
python3 verification/apple-appearance-font-profile/scripts/finish.py
python3 verification/apple-appearance-font-profile/scripts/seal.py
python3 verification/apple-appearance-font-profile/scripts/verify-seal.py
```

`finish.py` runs known-byte PNG analysis tests, produces the font/candidate tables,
tests the proposed bounded normalization policy, and verifies inputs/observations.
`seal.py` binds retained artifacts plus the findings document. The scalar policy
is a proposal, not a product/schema change or a validated Android implementation.
Native Android font/preference behavior and physical side-by-side parity remain
pending. Pressed/input/focus/a11y/navigation transitions, other locales/widths/OS
versions, signed display/health, immutable FieldLog and all remaining gates are
outside this simulator-only receipt.
