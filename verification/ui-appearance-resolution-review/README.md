# Independent appearance resolver review

Status: **passed within pure data scope**, 2026-10-23. No blocker found in this
scope. Root integration/acceptance remains a separate decision. The reviewer made
no product-source edit, commit, push, device discovery or physical-device run.

The review binds the producer's final canvas-inclusive candidate-2 collection
`a629acb9755307753e7d9dd6e424fde97c4b72641c8b1242241348526b624859`.
Its resolver SHA-256 is
`cbaaeebad2ef3c4015ab4f917df3a35ed68541e52b8b12c8a27a3be07211fcf0`;
its producer test SHA-256 is
`0ddd58e30d2a8744d7ed90c395d9bce9b9b054308620e9098827a002cfede801`.
All 61 producer inputs are independently copied under `candidate-2/inputs/`.

## Executable evidence

Run from the repository root:

```sh
python3 verification/ui-appearance-resolution-review/verify.py
```

The runner uses only the public MixerUI API and the frozen MixerCore/MixerUI
sources through this review's own Swift package. It executes `swift run` for
Debug and optimized Release with `-warnings-as-errors`. It neither imports nor
calls the producer's test helpers. The source oracle uses integer quotient and
remainder calculations and explicit expected semantic tokens instead of calling
the production metric functions.

Observed tools: Python 3.14.8, Apple Swift 6.4 (`swiftlang-6.4.0.34.1`), Xcode 27.1
(`27A9275`), arm64 macOS host. Exact commands, environment override, starting Git
revision/tree, logs, hashes, source collections and counts are in
[`candidate-2/receipt.json`](candidate-2/receipt.json). Both modes produced the
same result:

| Independent corpus | Cases per mode | Assertions per mode |
| --- | ---: | ---: |
| Distinct palette/state matrix | 9,072 | 278,992 |
| Exhaustive normalized scale and aggregate geometry | 3,605 | 53,888 |
| Logical overrides and all spacing ties | 16,423 | 16,491 |
| Standard tree/environment boundaries | 24 | 24 |
| Whole configuration/resource metadata | 24 | 40 |
| Reconciliation identity/routing preservation | 130 | 642 |
| **Total** | **29,278** | **350,077** |

A case is one identified plan scenario, style-state evaluation, quantization
input, environment input or expected rejection; it is not a Swift Testing test
function. Assertions are explicit runtime predicate/required-value checks, with
one assertion for a matching expected error. The runner also completed 186 exact
source checks: 61 inputs in each of the live tree, producer archive and review
archive, plus the three authored review source files.

## Review conclusions

- The source validates the whole raw configuration, both normalized environment
  ranges and the complete standard document before reserving or retaining
  per-node plan output. The review independently rejects permissive snapshots
  beyond 4096 nodes, depth 64, 1000 children, 16384-byte strings and the exact
  1 MiB aggregate content boundary. Inspection confirms both validator and
  resolver admit an entire pending frontier before appending children.
- Records retain snapshot identity, revision, kind, preorder and original child
  order. Reordering, kind replacement, old-plan retention, failed preparation,
  environment re-resolution and event routing were exercised independently.
  Missing-node lookups stay nil. The resolver has no reconciler mutation edge.
- All ten kinds use closed recipes. Distinct palettes prevent accent,
  destructive, focus, secondary, disabled, separator, toggle and canvas tokens
  from passing by accidental equality. Both schemes, shared platforms, control
  states, ancestor/local disabled behavior and irrelevant state requests are
  checked. Explicit platform declarations select the requested complete theme;
  invalid unselected themes still reject.
- Every normalized text scale from 512 through 4096 is checked against an
  independent ties-up oracle. Configured layout/control metrics remain unscaled.
  Configured minima and derived content floors stay distinct. Extreme valid
  aggregate heights reach 393216 without the individual metric cap being
  incorrectly applied. All 16384 permitted half-64th spacing ties and every
  logical stack alignment are exercised. RTL retains logical insets and child
  order.
- Paints retain unpremultiplied RGBA values and a separate single opacity value,
  including transparent and nonopaque palettes and 0/1/499/1000 opacity inputs.
  The plan exposes explicit canvas paint at opacity 1000. Style state does not
  change geometry or identity.
- Resource/font results remain descriptor references. Valid references to
  nonexistent bundled files can resolve as data; malformed references/catalogs
  reject. No file read, native support, installed resource, renderer, display,
  input, health or signing authority is introduced by this API.

## Limits

These results establish public-API host data behavior and reviewed allocation
ordering only. They are not a memory/RSS benchmark or a native rendering test.
The independent run does not repeat the producer's official iOS/Android compiler
matrix; its original receipt is retained as `candidate-2/producer-receipt.json`.

`sharedCandidate1` remains provisional. Navigation titles, section headers,
toggle colors and grouped-list geometry differ from the Apple reference and
require separate approval. No native numerical, glyph, raster or visual parity
follows from these checks. Native adapters still need closed support admission,
widget consumption, resource capture/packaging, actual text shaping and row
growth, interaction/accessibility/IME, atomic presentation and signed authority.
Physical iOS/Android parity, immutable published FieldLog consumption, signing,
store, customer, operational and GA gates remain pending. Phones remain
disconnected; no reconnection request was made.
