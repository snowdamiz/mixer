# Appearance foundation: design iteration 2

Status: **ready for root contract review; design/data probes only**. This iteration
specifies descriptor format 1; “v2” is the proposal revision, not a new wire schema.
It refines §§1–3/5 of the primary proposal. Its behavioral/native/GA limits remain.
No SDK, renderer, build generator, frozen protocol or identity field changed.

The original primary proposal is preserved in `../v1/ui-shared-appearance-contract.md`.
Its original receipt, lock, collector and declaration probe remain unchanged.
`../v1/recovery.json` identifies 17/19 recovered original input byte sets. The two
transient PLAN/STATUS observations retain their original hashes but have no saved
byte copies; neither was the binding product specification. This iteration binds
36 exact source files captured during design, including root's final bounded
Validation.swift. Concurrent status/ordinary packet-adoption edits after capture
are separate observations, not replacements for these historical byte snapshots.

## 1. Exact public values and codec to assign

`AppearanceV1Declarations.swift` is the complete proposed public value-type list:
all fields, enums, associated values and raw constructors are concrete. It includes
every default value through typed initializer calls. There are no placeholder
structs or external renderer-support protocols. Raw constructors establish no
validation or provenance; all codec and prepare paths must validate the whole graph.

The production codec has this exact proposed surface (not implemented in Swift by
this design task; function types are checked in the declaration probe):

```swift
public enum UIAppearanceDescriptorCodecV1 {
    public static func decode(_ bytes: Data) throws -> UIAppearanceConfigurationV1
    public static func validate(_ value: UIAppearanceConfigurationV1) throws
    public static func canonicalData(_ value: UIAppearanceConfigurationV1) throws -> Data
    public static func mixerDefaultV1() throws -> UIAppearanceConfigurationV1
}
```

`decode` accepts only the closed canonical descriptor below. `canonicalData` first
validates a programmatically constructed value, then emits those canonical bytes;
it does not bless an invalid raw constructor. `mixerDefaultV1()` decodes the exact
reviewed default bytes and propagates failure. A future host initializer defaults
to that operation; it must not fall back to toolkit appearance if loading fails.
No public API here constructs installed/signed material, a view, a health receipt,
or a supposedly validated resource bundle. Fixed `UIAppearanceErrorV1` cases in the
declarations classify failures; no unbounded input strings are error authority.

The proposed first foundation slice owns only new value/codec/math sources and
their actual SDK tests. It does not change `MixerUIHost`, document reconciliation,
ordinary/signed packet bytes, or the private signed factory. Proposed single-owner
files: `sdk/Sources/MixerUI/AppearanceValuesV1.swift`, `AppearanceDescriptorV1.swift`,
`AppearanceMetricMathV1.swift`, the canonical default data source and focused
`sdk/Tests/MixerUITests/AppearanceV1Tests.swift`. Root assigns exact paths before
work. Defaults must come from that one byte source; hand-maintained Java/Swift
literal tables are prohibited. The declaration fixture's typed literal is only a
compiler probe, generated from the same design data; it is not a product default.

## 2. Closed descriptor bytes and exact rules

`descriptor-schema.json` is the complete closed JSON Schema. Every object rejects
unknown/missing keys. The two root alternatives are exactly:

```text
shared: format, id, mode="shared", theme, resources
platformSpecific: format, id, mode="platformSpecific", iOS, android, reason, resources
```

Both themes are mandatory for the explicit platform alternative. `format` is
`mixer.native-appearance.1`. The font alternatives are exactly `{kind:"systemSans"}`
or `{kind:"bundled",faces:[...],fallback:"none"|"systemSans"}`. All root/theme/
font/control/resource fields, enum spellings and numeric ranges are in the schema;
the Swift names correspond directly, except RGBA8 is encoded as `#RRGGBBAA` and
associated enums flatten to the closed alternatives just shown.

`mixer-default-appearance-v1.json` is the actual 1,906-byte candidate default:
SHA-256 `e94f6988744bde16b83001db8e5047aeac4f15f6b045f99a4660445e7e2062d2`.
It declares shared `systemSans`, no bundled fonts/icons, the original iOS-oriented
candidate palette and 17/17/28/12 type hierarchy, gap8, plain buttons and explicit
control/list/title metrics. `sharedCandidate1` names this closed recipe algorithm;
it is not a measured Apple appearance or a supported native profile. Candidate
tokens still need unchanged-Apple reference capture before adapter qualification.

Codec requirements, including constraints beyond JSON Schema:

- At most65,536 UTF-8 bytes including final LF, depth16 and4,096 values. Reject
  malformed UTF-8, BOM, surrogates, trailing data, duplicate **decoded** keys
  (including escaped spellings), and resource-limit excess before admission.
- Canonical output is compact ASCII JSON, keys sorted by ASCII bytes, no spaces,
  ASCII escaping and exactly one final LF. Every string in this native descriptor
  is ASCII by its schema; this places no new restriction on UI-v1 app text.
  Decode requires byte-for-byte canonical input; valid alternate JSON spellings
  are not accepted. Duplicate rejection precedes canonical comparison.
- Every numeric token is shortest unsigned base10 integer, at most20 digits and
  UInt64 range before narrower field checks. No negative zero, sign, fraction,
  exponent, boolean coercion, NaN or infinity. Metric fields ending64 are raw
  1/64-point/dp counts,0...65,536 (0...1024 units). Type sizes64 are64...16,384;
  line boxes64 are64...65,536 and must be at least their font size.
- Weights are400/500/600/700; style is normal/italic. Opacity is integer permille
  0...1000. Colors are exactly uppercase `#RRGGBBAA`, sRGB unpremultiplied RGBA8.
  Native compositing uses the resolved color and explicit permille exactly once.
- Resource IDs and paths are unique; ASCII case-fold path collisions also reject.
  Paths are relative printable ASCII components under the fixed appearance root:
  no empty, dot/dotdot, leading slash or backslash components. Each file is1...4MiB,
  catalog≤64 files, font resources≤16 and aggregate bytes≤16MiB. Digests are64
  lowercase hex; provenance/reason is1...512 printable ASCII with no boundary
  whitespace and cannot be all spaces. No URL is dereferenced by this codec.
- Bundled face(weight,style) pairs are unique, reference fontSFNT catalog entries,
  and supply every normal weight requested by the four text styles. Font resources
  have scale1/locale `und`/neutral direction. Declared systemSans fallback covers
  missing script/emoji glyphs only; it does not conceal a missing required face.
  No fallback is inferred for `none`. Actual font/PNG validity, metadata identity,
  glyph coverage, licensing and native support require separate resource capture.
- Toggle thumb+2×inset must fit both track dimensions; minimum row fits track.
  All current catalog entries are required at native capture, even if not visible.
  iconPNG metadata creates no image/icon UI operation or platform substitution.

The stdlib-only `validate_descriptor.py` executes these shape/canonical/semantic
rules against the schema. Its50 adversarial tests run in normal and optimized
Python; this is an independently authored design oracle, not production Swift/
Java codec equivalence, a resource verifier or a release-authorization mechanism.

## 3. Exact math and bounded resolution boundary

The pure foundation must implement checked integer operations, not float JSON:

```swift
public enum UIAppearanceMetricMathV1 {
    public static func scaled64(_ metric64: UInt32, textScale1024: UInt16) throws -> UInt32
    public static func pixels(_ metric64: UInt32, density1024: UInt16) throws -> UInt32
    public static func spacing64(_ value: Double) throws -> UInt32
    public static func normalizeTextScale(_ value: Double) throws -> UInt16
    public static func normalizeDensity(_ value: Double) throws -> UInt16
}
```

```text
scaled64(metric64, textScale1024) = (UInt64(metric64)*textScale1024 +512) /1024
pixels(metric64, density1024) = (UInt64(metric64)*density1024 +32768) /65536
```

Division truncates toward zero: these round positive ties upward. `scaled64` accepts
metric64 0...65,536 and returns0...262,144; `pixels` accepts resolved metric64
0...262,144 and returns0...65,536. Validate ranges before multiplication and use
UInt64 intermediates. `textScale1024` is512...4096
(0.5...4); density1024 is128...16384 (0.125...16). Environment direction is only
leftToRight/rightToLeft; `neutral` is a resource-variant value, not layout direction.
Native user preference/density scalars are normalized once to those units by
positive ties-up rounding; outside-range preferences fail availability explicitly,
never silently clamp. Native category→requested-scalar mappings remain an adapter
contract to review, not a numeric constant inferred from this data probe.

Scale font size/minimum line box once. Do not apply Android sp scaling or Apple
semantic-font scaling a second time. Layout metrics remain logical unscaled units;
rows expand to native measured content/line height. Native shaping may need more
than the minimum line box. Safe-area/viewport geometry stays in the native layout
environment and is not serialized or used to forge guest padding/revisions.
For UI-v1 stack spacing (already a finite Double0...256), explicit spacing wins;
quantize to64ths with `floor(value*64+0.5)` on both adapters. Absent spacing uses
descriptor stackGap64; all leading/trailing/inset alignment uses logical direction.

The internal prepare operation takes a validated document plus validated config,
captured resources and a closed build-owned support set. Its bounded per-node
records reference the immutable theme/recipe rather than copy whole catalogs.
Kinds/roles/style select fixed algorithms; state resolution retains primary-proposal
rules: inherited disabled wins, then native pressed/focused decoration, no layout
mutation from state. Body maps field/toggle/button, caption maps section header,
title maps navigation title. normal/cancel button uses accent, destructive uses
destructive. All other text uses primary except placeholder/disabled as specified.
Pressed overlay is behind the label, uses role color at120permille; input selection
uses accent at240permille. No implicit native ripple/elevation/dimming is added.

No public “supported” boolean or conformable support protocol is introduced.
The initial implementation support set may be exactly vStack/text/button; all
other required operations reject until implemented. Document and style preparation
must finish before atomic native mutation; existing signed terminal/display/health
rules remain. Foundation acceptance proves none of those renderer operations.

## 4. Concrete native build and installed consumption points

One proposed app source is `Resources/MixerAppearance/mixer-appearance-v1.json`
plus its relative catalog files. If absent, the build deliberately selects the
exact SDK default; an explicitly supplied bad/missing requested file is an error.
The build selects/copies bytes once from captured inputs and never reconstructs
different JSON per platform. Apple packaged base is `MixerAppearance/` in the app
resource bundle; Android base is `assets/mixer/appearance/` in the APK. Both have
the same logical descriptor/catalog bytes. Packaging receipts compare complete
copied entry hashes, not merely equal app theme IDs.

| Current exact consumption point | Necessary separate implementation/acceptance |
| --- | --- |
| `cli/.../ProjectGenerator.swift` appleApp creates MixerUIHost without config; `AppleProject.swift` has an empty PBXResourcesBuildPhase | Generator must add captured descriptor/catalog entries, generated fixed bootstrap index and ordinary app bootstrap capture before constructing host. Verify extracted `.app` bytes; current source has no such support. |
| `AndroidProject.build` and `Resources/android-build.py` reject all app Resources; adapter snapshot explicitly lists Java sources; APK driver copies only current apk staging entries/dex | One build owner updates resource rejection/allowlist only for the validated owned format, stages exact APK assets and includes new consumer sources. Current source-tree before/after checks and APK entry hashes are local observations, not immutable consumption proof. |
| `MixerActivity.onCreate` constructs NativeRenderer directly; Java renderer has no config; Swift AndroidDocumentSession creates unchanged documents/packets | Ordinary native bootstrap must capture/verify asset bytes once and pass an immutable closed style value to renderer. Its appearance is not added to packets or event exchange. Swift/Java consumers must bind the same descriptor digest. |
| `InstalledCapabilityExecution` has only bridge/configuration/grant roles and verifies fixed material/root hashes; no appearance slot | Do not repurpose those capability files or add a public appearance authority setter. A new private installed capture must be separately contracted and accepted before signed use. |
| `GuestUIPresentation.consume` privately creates MixerUIHost without config; Android stage5 JNI installation is separately frozen | Later sole owners pass the same private captured native appearance into Apple host and eventual SignedUiStyle installation. No new mxis_* argument/packet/header field is implied; Android installation seam remains pending. |

Existing runtime identity2 has no appearance field. `capture-v2.py` supports an
exact collection binding at `/build/link_inputs_sha256`, but it does not discover
the graph or prove a linker/build consumed it. Loose bundle resources cannot just
be renamed linker inputs. Proposed compatible binding: build a real pre-identity
bootstrap object containing descriptor bytes/digest and a closed resource index
(logical path, size, digest); include **that actual object** in the complete
captured linker-input collection and consume it in the final native link. Native
capture verifies actual installed bundle/asset bytes against that linked index and
retains bounded immutable snapshots. Index metadata alone is not actual capture.

The generated schema2 identity source is emitted after those pre-embedding inputs;
do not create a self-referential fingerprint by hashing the final identity-bearing
binary back into its descriptor. Final app/container signing/attestation separately
binds the final linked binary and packaged resources. Foundation/codec/renderer/
packager source/tool objects also belong to their actual existing source/dependency/
link closures, with exact collection bindings declared by the build owner.

`embed-v2.py` currently emits compiled identity bytes/fingerprint only; no linked
appearance index, bundle consumption, private installed reader or source→final
container closure exists today. The above index/capture wiring is a proposed
separate native-build contract, not supported installed authority. If that
contract cannot bind the real consumed material without a schema change, signed
appearance stays pending until a versioned identity/profile contract is approved.
Equal wire bytes or an untrusted data-codec success never imply compatibility.

## 5. Freeze recommendation and executable next evidence

Freeze the concrete value/codec schema, default bytes and integer math first;
assign one SDK owner to implement/test those pure operations. Then freeze native
resource/index capture and app-build installation separately before assigning the
Apple/Android/signed adapter owners. No renderer or signed factory should depend
on a half-implemented codec or a caller-created “installed” configuration.

Future SDK and real JVM tests must consume these same canonical default bytes and
shared mutation corpus, compare full decoded/canonical values and checked math,
and reject duplicates before normal deserialization. Native reference captures
must show widgets consume resolved values through all four states, light/dark,
normalized text sizes and RTL. Separate tests prove real bundle/APK extraction,
linked-index consumption, private captured ownership, atomic failure and signed
no-input/no-display-health failure behavior. The entire ten-kind/§8.2 inventory,
font/asset support, physical iOS/Android parity, a11y, performance, immutable
published FieldLog, signing/store/customer/GA gates remain pending. Phones remain
disconnected; this iteration performs no discovery, native run or reconnect request.
