import Foundation

// Independent executable probe. Compiled only with copied, hash-checked producer
// appearance sources; no producer test helpers or design Python oracle are used.
struct ProbeCase: Decodable {
    let name: String
    let base64: String
    let accepted: Bool
    let error: String?
}
struct ProbeFailure: Codable {
    let name: String
    let detail: String
}
var failures: [ProbeFailure] = []
var assertions = 0
func check(_ condition: Bool, _ name: String, _ detail: String = "unexpected result") {
    assertions += 1
    if !condition { failures.append(ProbeFailure(name: name, detail: detail)) }
}
func reject(_ name: String, _ operation: () throws -> Void) {
    do { try operation(); check(false, name, "accepted invalid raw constructor") }
    catch is UIAppearanceErrorV1 { check(true, name) }
    catch { check(false, name, "unexpected error: \(error)") }
}
func bothReject(_ name: String, _ value: UIAppearanceConfigurationV1) {
    reject(name + ":validate") { try UIAppearanceDescriptorCodecV1.validate(value) }
    reject(name + ":canonicalData") { _ = try UIAppearanceDescriptorCodecV1.canonicalData(value) }
}
func replacing(_ theme: UIThemeV1, font: UIFontSourceV1? = nil,
               body: UITextMetricV1? = nil, controls: UIControlMetricsV1? = nil) -> UIThemeV1 {
    let t = theme.typography
    return UIThemeV1(recipe: theme.recipe, light: theme.light, dark: theme.dark,
        typography: UITypographyV1(font: font ?? t.font, body: body ?? t.body,
            headline: t.headline, title: t.title, caption: t.caption),
        layout: theme.layout, controls: controls ?? theme.controls)
}
func resource(_ id: String = "r", kind: UIResourceKindV1 = .iconPNG, path: String = "icons/a.png",
              digest: String = String(repeating: "a", count: 64), bytes: UInt32 = 1,
              provenance: String = "Independent metadata", scale: UInt8 = 1, locale: String = "und",
              direction: UIResourceDirectionV1 = .neutral) -> UIAppearanceResourceV1 {
    UIAppearanceResourceV1(id: id, kind: kind, path: path, sha256: digest, bytes: bytes,
        provenance: provenance, scale: scale, locale: locale, direction: direction)
}

let corpus = try JSONDecoder().decode([ProbeCase].self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
var accepted = 0
var rejected = 0
for entry in corpus {
    let raw = Data(base64Encoded: entry.base64)!
    do {
        let value = try UIAppearanceDescriptorCodecV1.decode(raw)
        check(entry.accepted, entry.name, "decode accepted expected rejection")
        if entry.accepted {
            accepted += 1
            try UIAppearanceDescriptorCodecV1.validate(value)
            let canonical = try UIAppearanceDescriptorCodecV1.canonicalData(value)
            check(canonical == raw, entry.name + ":canonical")
            check(try UIAppearanceDescriptorCodecV1.decode(canonical) == value, entry.name + ":equatable")
        }
    } catch {
        rejected += 1
        check(!entry.accepted, entry.name, "decode rejected expected success: \(error)")
        if let expected = entry.error {
            check(String(describing: error) == expected, entry.name + ":error", "expected \(expected), observed \(error)")
        }
    }
}

let value = try UIAppearanceDescriptorCodecV1.mixerDefaultV1()
let embeddedDefault = try UIAppearanceDescriptorCodecV1.canonicalData(value)
try embeddedDefault.write(to: URL(fileURLWithPath: CommandLine.arguments[2]))
check(embeddedDefault.count == 1906, "embedded-default-length")
guard case let .shared(theme) = value.mode else { fatalError("default mode is not shared") }
check(theme.typography.font == .systemSans, "explicit-systemSans")
check(value.resources.isEmpty, "default-no-resource-catalog")

// Raw callers have no validation authority. Exercise independent limits without
// allocating a serialized invalid document or exposing native/installed handles.
for s in ["", "a b", "a\u{7f}", "aé", String(repeating: "a", count: 129), String(repeating: "a", count: 2_000_000)] {
    bothReject("raw-id-\(s.utf8.count)", UIAppearanceConfigurationV1(id: s, mode: value.mode))
}
for s in ["", " ", " leading", "trailing ", "a\nb", "é", String(repeating: "r", count: 513), String(repeating: "r", count: 2_000_000)] {
    bothReject("raw-reason-\(s.utf8.count)", UIAppearanceConfigurationV1(id: "r", mode: .platformSpecific(iOS: theme, android: theme, reason: s)))
}
let invalidResources = [
    resource(String(repeating: "a", count: 129)),
    resource(path: String(repeating: "a", count: 257)),
    resource(digest: String(repeating: "a", count: 65)),
    resource(bytes: 0), resource(bytes: UInt32.max),
    resource(provenance: String(repeating: "a", count: 513)), resource(provenance: " "),
    resource(scale: 0), resource(scale: UInt8.max), resource(locale: String(repeating: "a", count: 65)),
    resource(kind: .fontSFNT, scale: 2), resource(kind: .fontSFNT, locale: "en"),
    resource(kind: .fontSFNT, direction: .leftToRight)
]
for (i, r) in invalidResources.enumerated() {
    bothReject("raw-resource-\(i)", UIAppearanceConfigurationV1(id: "r", mode: value.mode, resources: [r]))
}
bothReject("raw-resource-count", UIAppearanceConfigurationV1(id: "r", mode: value.mode,
    resources: Array(repeating: resource(), count: 100_000)))
let face = UIFontFaceV1(resourceID: "r", postScriptName: "Review-Regular", weight: .w400, style: .normal)
for faces in [[], Array(repeating: face, count: 17), Array(repeating: face, count: 100_000),
              [UIFontFaceV1(resourceID: String(repeating: "a", count: 129), postScriptName: "R", weight: .w400, style: .normal)],
              [UIFontFaceV1(resourceID: "r", postScriptName: String(repeating: "a", count: 129), weight: .w400, style: .normal)]] {
    let badTheme = replacing(theme, font: .bundled(faces: faces, fallback: .systemSans))
    bothReject("raw-font-count-\(faces.count)", UIAppearanceConfigurationV1(id: "r", mode: .shared(badTheme), resources: [resource(kind: .fontSFNT)]))
}
for metric in [UITextMetricV1(size64: UInt32.max, weight: .w400, minimumLineBox64: UInt32.max),
               UITextMetricV1(size64: 64, weight: .w400, minimumLineBox64: 63),
               UITextMetricV1(size64: 16385, weight: .w400, minimumLineBox64: 65536)] {
    let badTheme = replacing(theme, body: metric)
    bothReject("raw-typography", UIAppearanceConfigurationV1(id: "r", mode: .platformSpecific(iOS: theme, android: badTheme, reason: "Review")))
}
let c = theme.controls
let badToggle = UIToggleMetricsV1(trackWidth64: 65536, trackHeight64: 65536,
    thumb64: UInt32.max, inset64: UInt32.max, labelGap64: 0, minimumRow64: 65536)
let badControls = UIControlMetricsV1(button: c.button, field: c.field, toggle: badToggle,
    focusWidth64: c.focusWidth64, focusRadius64: c.focusRadius64,
    pressedOpacityPermille: UInt16.max, selectionOpacityPermille: UInt16.max)
bothReject("raw-geometry-overflow", UIAppearanceConfigurationV1(id: "r", mode: .shared(replacing(theme, controls: badControls))))

// Independent reference uses quotient/remainder, without the implementation's
// rounding-addend formula. Sweep every admitted metric with boundary scales.
func round(_ numerator: UInt64, denominator: UInt64) -> UInt32 {
    let (q, r) = (numerator / denominator, numerator % denominator)
    return UInt32(q + (r >= denominator / 2 ? 1 : 0))
}
var scaledCases = 0
for scale: UInt16 in [512, 513, 1023, 1024, 1025, 2047, 2048, 4095, 4096] {
    for metric: UInt32 in 0...65536 {
        let expected = round(UInt64(metric) * UInt64(scale), denominator: 1024)
        check(try UIAppearanceMetricMathV1.scaled64(metric, textScale1024: scale) == expected, "scaled64:\(metric):\(scale)")
        scaledCases += 1
    }
}
var pixelCases = 0
for density: UInt16 in [128, 129, 1023, 1024, 1025, 16383, 16384] {
    for metric: UInt32 in 0...262144 {
        let expected = round(UInt64(metric) * UInt64(density), denominator: 65536)
        check(try UIAppearanceMetricMathV1.pixels(metric, density1024: density) == expected, "pixels:\(metric):\(density)")
        pixelCases += 1
    }
}
var normalizationCases = 0
for (kind, low, high) in [("text", 512, 4096), ("density", 128, 16384)] {
    for n in low..<high {
        let tie = (Double(n) + 0.5) / 1024
        for (input, expected) in [(tie.nextDown, n), (tie, n + 1), (tie.nextUp, n + 1)] {
            let result = try kind == "text" ? UIAppearanceMetricMathV1.normalizeTextScale(input) : UIAppearanceMetricMathV1.normalizeDensity(input)
            check(result == UInt16(expected), "normalize:\(kind):\(input)")
            normalizationCases += 1
        }
    }
}
for n in 0..<16384 {
    let tie = (Double(n) + 0.5) / 64
    check(try UIAppearanceMetricMathV1.spacing64(tie) == UInt32(n + 1), "spacing-tie:\(n)")
}
// spacing's frozen contract explicitly says floor(value*64+0.5); the nearest
// representable input below its first tie therefore rounds upward after addition.
check(try UIAppearanceMetricMathV1.spacing64((0.5 / 64).nextDown) == 1, "spacing-first-nextDown-frozen-formula")
for metric: UInt32 in [65537, UInt32.max] {
    reject("scaled-outside") { _ = try UIAppearanceMetricMathV1.scaled64(metric, textScale1024: 1024) }
}
for scale: UInt16 in [0, 511, 4097, UInt16.max] {
    reject("scale-outside") { _ = try UIAppearanceMetricMathV1.scaled64(65536, textScale1024: scale) }
}
for metric: UInt32 in [262145, UInt32.max] {
    reject("pixels-outside") { _ = try UIAppearanceMetricMathV1.pixels(metric, density1024: 1024) }
}
for density: UInt16 in [0, 127, 16385, UInt16.max] {
    reject("density-outside") { _ = try UIAppearanceMetricMathV1.pixels(262144, density1024: density) }
}
for x in [Double.nan, Double.infinity, -Double.infinity, -1, 256.0.nextUp] {
    reject("spacing-outside") { _ = try UIAppearanceMetricMathV1.spacing64(x) }
}
for x in [Double.nan, Double.infinity, -Double.infinity, 0.5.nextDown, 4.0.nextUp] {
    reject("text-normalization-outside") { _ = try UIAppearanceMetricMathV1.normalizeTextScale(x) }
}
for x in [Double.nan, Double.infinity, -Double.infinity, 0.125.nextDown, 16.0.nextUp] {
    reject("density-normalization-outside") { _ = try UIAppearanceMetricMathV1.normalizeDensity(x) }
}
struct Summary: Codable {
    let descriptorCases, accepted, rejected, scaledCases, pixelCases, normalizationCases, assertions: Int
    let failures: [ProbeFailure]
}
let summary = Summary(descriptorCases: corpus.count, accepted: accepted, rejected: rejected,
    scaledCases: scaledCases, pixelCases: pixelCases, normalizationCases: normalizationCases,
    assertions: assertions, failures: failures)
let json = try JSONEncoder().encode(summary)
print(String(decoding: json, as: UTF8.self))
if !failures.isEmpty { exit(1) }
