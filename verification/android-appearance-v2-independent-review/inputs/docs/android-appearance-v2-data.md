# Android measured appearance V2 data

This slice supplies `AppearanceDescriptorV2` and `AppearanceGeometryV2` as package-private,
Android-framework-independent Java data code. It implements the frozen
[measured appearance contract](ui-measured-appearance-v2-contract.md), accepted by
[root for implementation only](../verification/ui-measured-appearance-v2-root-review/acceptance.json).
Both native platforms must eventually consume the same supplied app design under
product-plan §8.3. This slice supplies no native rendering or parity evidence.

`AppearanceDescriptorV2.decode(byte[])` accepts canonical
`mixer.native-appearance.2` bytes and returns a final descriptor with an explicit
`Mode`, typed `Theme iOS` / `Theme android`, immutable `List<Resource>`, ID, and an
explicit platform-specific reason where applicable. A shared descriptor retains
one theme for both platforms. There is no Java default theme, implicit Android
styling, automatic platform branch, or native resource fallback.

Every theme component is a named immutable record or closed enum: six-role,
twelve-profile typography; sealed system/bundled font sources and faces; RGBA8
channels; all button, field and toggle paint states; outlines; insets; stack,
grouped-list, control and navigation metrics. Lists defensively copy their input.
Raw parser maps and input bytes never escape the decoder. The fixed profile
family is checked as a recipe invariant; its validation table supplies no theme,
paints, metric defaults or resource bytes.

The byte reader admits 1–65,536 ASCII bytes before copying. It admits each value
before constructing it (8,192 maximum), every container before descent (20 levels),
and every array slot before its child (64 maximum). It bounds strings before
retaining another character. It requires sorted unique ASCII keys, unsigned
canonical integers, shortest quote/backslash escapes for the admitted printable
string domain, and exactly one terminal LF. Unknown/missing fields, foreign
formats and enum values fail closed. The subsequent typed reader applies all
schema bounds and cross-field rules, including fixed switch shapes/sizes,
unchanged profile metrics, monotonic row floors, navigation floors, clear disabled
paints, catalog totals and uniqueness, and bundled font reference/weight rules.

`AppearanceDescriptorV2.Failure.code` distinguishes byte, encoding, syntax,
duplicate, depth, count, array, canonical, shape, number, catalog, font, profile
and geometry errors. The error family reserves distinct native-operation, layout
and native-attachment failures for later consumers. Decoder success establishes
none of those native capabilities.

`AppearanceGeometryV2` provides only the three closed `Shape` cases. Private path
construction produces immutable commands and points; descriptors cannot provide
paths. `group(width64,height64,radius64)` uses the specified seven coefficients,
full-group closure, tangent-aware integer radius clamp and ties-up offset rounding.
Zero width or height yields an empty path after argument validation. Track/thumb
paths contain the exact frozen integer coordinates. `thumbOrigin` applies logical
trailing placement for checked state in both directions.

The geometry helpers preserve Swift's measured-extent ceiling, spacing and density
nearest rounding with ties up, raw finite/support checks before quantization, exact
fractional pixel coordinates, and absolute-edge pixel rounding. Nonnegative
admitted products fit Java `long`: the largest group clamp product is below 2^51,
and pixel products are below 2^45. No signed overflow or narrowing precedes
admission. Java's additional signed argument domain rejects negative and oversized
values. Fractional rounding compares the remainder with 0.5 so a value just below
a half cannot round up because of an intermediate addition.

The retained [candidate-3 receipt](../verification/android-appearance-v2-data/candidate-3/receipt.json)
records explicit commands, cwd, tool versions, git revision/tree, a digest of all
frozen inputs, exact descriptor input hashes, artifact hashes and output logs.
The corpus is authored independently of both product readers. Every accepted Java
descriptor is traversed through every typed field and independently reconstructed
in test code; those exact bytes agree with Swift's actual typed decode/canonical
encode result. The test encoder is not product admission authority. Swift inputs
are frozen actual product sources bound to the existing codec receipt.

The checks compare Swift `-Onone` / `-O` with JVM default / `-Xint`, compile using
JDK 25 with `--release 17 -Xlint:all -Werror`, compare all closed geometry outputs,
and independently check the fixed paths against `shape-definitions.json`. They
exercise complete shared/platform-specific themes, custom paints/metrics, synthetic
bundled-font metadata, every default object field's omission/type/unknown-field
rejection, catalog boundaries, malformed wire forms, exact 65,536-byte complete
descriptors, exact 8,192-value parser admission and overflow, rounding neighbors,
UInt32/extent limits, RTL and immutability. The preexisting V1 corpus and the
1,906-byte golden remain unchanged and are executed in both JVM modes.

To reproduce with a fresh evidence directory:

```sh
python3 verification/android-appearance-v2-data/scripts/run-checks.py candidate-N
python3 verification/android-appearance-v2-data/scripts/verify-seal.py
```

Candidate 1 retains a failed Swift probe compile caused by a wrong test-harness
factory owner; no product source correction was needed. Candidate 2 passed the
initial corpus. Candidate 3 adds complete descriptors at the byte boundary and
exact global-value-count probes. The final receipt and seal identify qualification.

Native consumers, resource loading/capture, real font identity/coverage,
measurement and raster, preference/window/configuration handling, accessibility,
interaction semantics, supported-operation checks, packet/JNI/bootstrap integration,
signing, native attachment/display health and OTA authority remain separate work.
Phones remain disconnected, so physical iOS/Android checks remain pending without
new discovery or execution. No compiler, signing, store, customer, operational,
published separate-repository FieldLog or GA gate is passed by these host data tests.
