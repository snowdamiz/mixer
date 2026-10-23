# Opt-in measured appearance V2 values and descriptor codec

This implements the data-only portion of the frozen [measured appearance V2 contract](ui-measured-appearance-v2-contract.md) for product-plan §8.3. It supplies public `Sendable`/`Equatable` values with explicit initializers, the canonical `mixer.measured-candidate.v2` default, and the separate `UIAppearanceDescriptorCodecV2` entry points:

```swift
let configuration = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
try UIAppearanceDescriptorCodecV2.validate(configuration)
let bytes = try UIAppearanceDescriptorCodecV2.canonicalData(configuration)
let decoded = try UIAppearanceDescriptorCodecV2.decode(bytes)
```

Callers explicitly choose V2. Existing V1 types, recipe, 1,906-byte default, codec, resolver, and native bootstrap remain unchanged. Both codecs reject the other wire format. The V2 default is exactly 9,587 bytes including its terminal LF, SHA-256 `1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3`.

`UIAppearanceConfigurationV2` holds either a complete shared theme or two complete independent `iOS`/`android` themes and a nonblank trimmed printable ASCII reason. All nested theme values have named fields. `UINativeShapeV2` is defined once by the separate [geometry implementation](../sdk/Sources/MixerUI/AppearanceGeometryV2.swift); no custom descriptor path or native style name is accepted.

## Admission and canonical bytes

The private streaming parser admits input bytes before copying (1…65,536), checks ASCII, and admits each value/container before retaining children. The limits are 20 container levels, 8,192 JSON values including the root and excluding object keys, and 64 entries in any array. Strings are capped at 512 decoded ASCII bytes before append and then checked against field-specific limits/characters. Object keys must be unique after escape decoding. Arrays preserve authored order.

The parser accepts only objects, arrays, strings, and checked UInt64 unsigned integer tokens. Signs, fractions, exponents, booleans, null, invalid escapes, Unicode/non-ASCII, duplicate keys, overflow and trailing values fail. Closed typed conversion rejects all missing/extra fields and unknown enums. The codec then requires exact equality with its canonical output: ASCII lexicographic object-key order, shortest required quote/backslash escaping, no outside-string whitespace, no integer leading zeros, and exactly one terminal LF. It never uses `JSONSerialization` for product admission.

Raw typed values are untrusted. Both `validate` and `canonicalData` recheck the complete graph. Variable arrays are capped before `map`; caller strings are checked before adding them to the bounded fixed-shape tree. A count-only writer measures canonical bytes before allocation of output data. Printable reason/provenance may contain literal quotes and backslashes, which are escaped canonically.

## Required semantics

The twelve profile rows and all six role metrics must exactly equal the frozen shared text family. There is no added line-height/clipping box, semantic scale multiplier or profile fallback. A valid default profile may be any of the twelve named rows; native preference conversion is outside this codec. Colors use explicit uppercase unpremultiplied sRGB `#RRGGBBAA`; every state table is retained without derived opacity.

Scalar geometry is bounded by its field schema. App geometry and paints remain customizable where permitted. Shape names, switch dimensions/radii/inset/end, navigation roles/alignments and closed algorithms are fixed. Row floors must be nondecreasing and contain the fixed track; expanded navigation's floor must be at least compact. Disabled button backgrounds, disabled field caret/selection and disabled toggle overlays must be canonical `#00000000`; enabled/disabled field outline widths must be zero.

Resource references retain the V1 closed shape: ≤64 entries, 1 byte…4 MiB each, ≤16 MiB total; unique IDs and case-insensitive paths; relative bounded ASCII paths with no empty/dot-leading segment; lowercase SHA-256; printable trimmed nonblank provenance; explicit locale/direction/scale. Font resources are limited to sixteen and require scale 1, locale `und`, neutral direction. Bundled faces have unique weight/style pairs, resolve to declared font resources, include normal 400/600/700, and include a normal counterpart for every italic weight. No actual bytes are loaded, hashed, interpreted, installed, or qualified.

`UIAppearanceErrorV2` distinguishes byte/encoding/syntax/duplicate/depth/value/array admission errors, noncanonical bytes, closed-shape/number violations, resource/font catalog failures, frozen-profile mismatch and geometry semantics. Native-operation/layout/attachment cases are reserved for later coordinated consumers; this codec creates no native implementation or capability proof.

## Evidence and limitations

The [snapshot receipt](../verification/ui-appearance-descriptor-v2/candidate-1/receipt.json) retains every command, actual frozen working directory, tool version, exit status, output hash, source revision/Git tree, exact source snapshot manifest and digest. The [public consumer](../verification/ui-appearance-descriptor-v2/PublicConsumer.swift) constructs every new public value type and checks shared/platform-specific/synthetic-font reference roundtrips. The run script preserves source/fixture closure before executing full SDK Debug/Release tests, host public-caller execution, and iOS17 ARM64 / official Swift6.3.3 Android30 AArch64 module/public-caller compilation.

The twelve new test methods cover exact default and V1 separation, all nested object fields, full frozen profiles, malformed/canonical inputs, exact parser limits, exact 65,536-byte encoding, platform-specific reasons and independent themes, customizable paints/metrics, fixed geometry and disabled-state invariants, resource/path/catalog limits, font reference/style pairing, and raw typed graph revalidation. The first test-compile attempt exceeded Swift's expression typechecking budget; splitting its Data array fixed it. The next iteration exposed Foundation's test-only mixed-case `sortedKeys` ordering; explicit ASCII test-fixture ordering fixed it. Both failed logs are retained. Product parsing/writing was not changed for either harness issue.

This is descriptor data qualification only. Resource capture/bootstrap, V2 resolver, build support, actual native consumers, native shaping/layout/control and failure-atomic updates, and signed identity/presentation binding remain separate work. Pure data success and iOS/Android compilation do not establish design parity, installed resources, rendering, interaction, accessibility, event/display/health authority or release readiness. Phones remain disconnected. Physical parity/workflows, signed evidence, immutable published FieldLog packages from its separate repository, store/customer/operational qualification and all GA gates remain pending.

The completed candidate passed **106 full SDK tests per Debug/Release mode** (8 XCTest, 86 MixerUI, 10 MixerCore, 2 MixerApple), both host public caller executions, and both cross-target module/public-caller checks. Its exact input-tree SHA-256 is `21e386bb8d5632d7022d6ba39ce956d78c2fbc59be1b73aeec479bb446c995ba`; all live input bindings still matched at completion. Run `python3 verification/ui-appearance-descriptor-v2/scripts/verify-seal.py` to check the retained evidence and current owned product files.
