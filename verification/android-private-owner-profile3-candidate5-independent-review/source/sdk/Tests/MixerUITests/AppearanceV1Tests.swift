import Foundation
import Testing
import MixerUI

private let appearanceRootV1 = URL(fileURLWithPath: #filePath)
    .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
private typealias AppearanceCodec = UIAppearanceDescriptorCodecV1
private typealias AppearanceMath = UIAppearanceMetricMathV1
private func appearanceFixtureV1() throws -> Data {
    try Data(contentsOf: appearanceRootV1.appendingPathComponent("verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json"))
}
private func appearanceThemeV1() throws -> UIThemeV1 {
    guard case let .shared(theme) = try AppearanceCodec.mixerDefaultV1().mode else { throw UIAppearanceErrorV1.shape }
    return theme
}
private func appearanceReplaceV1(_ original: Data, _ old: String, _ new: String) -> Data {
    Data(String(decoding: original, as: UTF8.self).replacingOccurrences(of: old, with: new).utf8)
}
private func appearanceResourceV1(_ index: Int = 0, kind: UIResourceKindV1 = .iconPNG,
                                  path: String? = nil, bytes: UInt32 = 1,
                                  provenance: String = "Metadata fixture", scale: UInt8 = 1,
                                  locale: String = "und", direction: UIResourceDirectionV1 = .neutral) -> UIAppearanceResourceV1 {
    UIAppearanceResourceV1(id: "r\(index)", kind: kind, path: path ?? "r\(index).bin", sha256: String(repeating: "a", count: 64),
        bytes: bytes, provenance: provenance, scale: scale, locale: locale, direction: direction)
}
private func appearanceRethemeV1(_ theme: UIThemeV1, font: UIFontSourceV1? = nil,
                                body: UITextMetricV1? = nil, layout: UILayoutMetricsV1? = nil,
                                controls: UIControlMetricsV1? = nil) -> UIThemeV1 {
    UIThemeV1(recipe: theme.recipe, light: theme.light, dark: theme.dark,
        typography: UITypographyV1(font: font ?? theme.typography.font, body: body ?? theme.typography.body,
            headline: theme.typography.headline, title: theme.typography.title, caption: theme.typography.caption),
        layout: layout ?? theme.layout, controls: controls ?? theme.controls)
}
private func appearanceInvalidGraphV1(_ value: UIAppearanceConfigurationV1) {
    #expect(throws: UIAppearanceErrorV1.self) { try AppearanceCodec.validate(value) }
    #expect(throws: UIAppearanceErrorV1.self) { _ = try AppearanceCodec.canonicalData(value) }
}

@Test func appearanceV1ExactDefaultAndClosedPublicSurface() throws {
    // Function assignment checks labels/throws/return types through public imports.
    let decode: (Data) throws -> UIAppearanceConfigurationV1 = AppearanceCodec.decode
    let encode: (UIAppearanceConfigurationV1) throws -> Data = AppearanceCodec.canonicalData
    let validate: (UIAppearanceConfigurationV1) throws -> Void = AppearanceCodec.validate
    let fixture = try appearanceFixtureV1()
    let value = try AppearanceCodec.mixerDefaultV1()
    #expect(fixture.count == 1906)
    #expect(try encode(value) == fixture)
    #expect(try decode(fixture) == value)
    try validate(value)
    #expect(value.id == "mixer.default.v1")
    #expect(value.resources.isEmpty)
    let theme = try appearanceThemeV1()
    #expect(theme.typography.font == .systemSans)
    #expect(theme.typography.body == UITextMetricV1(size64: 1088, weight: .w400, minimumLineBox64: 1408))
    #expect(theme.layout.stackGap64 == 512)
    #expect(theme.light.accent == UIRGBA8V1(red: 0, green: 122, blue: 255, alpha: 255))
    #expect(theme.dark.accent == UIRGBA8V1(red: 10, green: 132, blue: 255, alpha: 255))
}

@Test func appearanceV1ExecutesEntireSealedDesignCorpusInSwift() throws {
    struct Case: Decodable { let name: String; let base64: String; let accepted: Bool }
    let url = appearanceRootV1.appendingPathComponent("verification/ui-appearance-foundation/design-corpus.json")
    let corpus = try JSONDecoder().decode([Case].self, from: Data(contentsOf: url))
    #expect(corpus.count == 50)
    #expect(corpus.filter(\.accepted).count == 3)
    for test in corpus {
        let data = try #require(Data(base64Encoded: test.base64), Comment(rawValue: test.name))
        if test.accepted {
            let value = try AppearanceCodec.decode(data)
            #expect(try AppearanceCodec.canonicalData(value) == data, Comment(rawValue: test.name))
            try AppearanceCodec.validate(value)
        } else {
            #expect(throws: UIAppearanceErrorV1.self, Comment(rawValue: test.name)) { _ = try AppearanceCodec.decode(data) }
        }
    }
}

@Test func appearanceV1ExplicitPlatformsAndEscapedPrintableStringsRoundTrip() throws {
    let theme = try appearanceThemeV1()
    let resource = appearanceResourceV1(provenance: "Owned \"fixture\" \\ provenance")
    let value = UIAppearanceConfigurationV1(id: "app.theme", mode: .platformSpecific(
        iOS: theme, android: theme, reason: "Explicit \"choice\" \\ pair"), resources: [resource])
    let bytes = try AppearanceCodec.canonicalData(value)
    #expect(bytes.last == 10)
    #expect(try AppearanceCodec.decode(bytes) == value)
    #expect(String(decoding: bytes, as: UTF8.self).contains("\\\"choice\\\""))
    #expect(try AppearanceCodec.canonicalData(AppearanceCodec.decode(bytes)) == bytes)
}

@Test func appearanceV1RejectsDecodedDuplicatesBeforeCanonicalComparison() throws {
    let fixture = try appearanceFixtureV1()
    for duplicate in ["\"mode\":\"shared\",\"mode\":\"shared\"", "\"mode\":\"shared\",\"m\\u006fde\":\"shared\""] {
        let bytes = appearanceReplaceV1(fixture, "\"mode\":\"shared\"", duplicate)
        #expect(throws: UIAppearanceErrorV1.duplicateKey) { _ = try AppearanceCodec.decode(bytes) }
    }
    let nested = appearanceReplaceV1(fixture, "\"canvas\":\"#000000FF\"", "\"canvas\":\"#000000FF\",\"can\\u0076as\":\"#000000FF\"")
    #expect(throws: UIAppearanceErrorV1.duplicateKey) { _ = try AppearanceCodec.decode(nested) }
}

@Test func appearanceV1RejectsIntegerLexicalFormsAndUInt64Overflow() throws {
    let fixture = try appearanceFixtureV1()
    for token in ["-0", "+1", "01", "-1", "512.0", "512e0", "512E+0", "NaN", "Infinity", "true", "null",
                  "18446744073709551615", "18446744073709551616", "100000000000000000000", "65537"] {
        let bytes = appearanceReplaceV1(fixture, "\"stackGap64\":512", "\"stackGap64\":\(token)")
        #expect(throws: UIAppearanceErrorV1.self, Comment(rawValue: token)) { _ = try AppearanceCodec.decode(bytes) }
    }
}

@Test func appearanceV1RejectsAlternativeJSONAndInvalidASCIIEncodings() throws {
    let fixture = try appearanceFixtureV1()
    for bytes in [Data(), Data([0xEF, 0xBB, 0xBF]) + fixture, Data([0xFF]) + fixture,
                  Data(" ".utf8) + fixture, fixture.dropLast(), fixture + Data([10]), fixture + Data("{}".utf8),
                  appearanceReplaceV1(fixture, "mixer.default.v1", "mixer.default.v\\u0031"),
                  appearanceReplaceV1(fixture, "mixer.default.v1", "é"),
                  appearanceReplaceV1(fixture, "mixer.default.v1", "\\ud800"),
                  appearanceReplaceV1(fixture, "mixer.default.v1", "\\ud83d\\ude00"),
                  appearanceReplaceV1(fixture, "mixer.default.v1", "\\u00e9")] {
        #expect(throws: UIAppearanceErrorV1.self) { _ = try AppearanceCodec.decode(Data(bytes)) }
    }
}

@Test func appearanceV1PreflightByteDepthValueArrayAndStringBounds() throws {
    #expect(throws: UIAppearanceErrorV1.byteLimit) { _ = try AppearanceCodec.decode(Data(repeating: 32, count: 65_537)) }
    #expect(throws: UIAppearanceErrorV1.depthLimit) {
        _ = try AppearanceCodec.decode(Data((String(repeating: "{\"a\":", count: 16) + "0" + String(repeating: "}", count: 16)).utf8))
    }
    let manyFields = "{" + (0..<4096).map { "\"k\($0)\":0" }.joined(separator: ",") + "}"
    #expect(throws: UIAppearanceErrorV1.valueLimit) { _ = try AppearanceCodec.decode(Data(manyFields.utf8)) }
    let array65 = "[" + Array(repeating: "0", count: 65).joined(separator: ",") + "]"
    #expect(throws: UIAppearanceErrorV1.shape) { _ = try AppearanceCodec.decode(Data(array65.utf8)) }
    #expect(throws: UIAppearanceErrorV1.shape) { _ = try AppearanceCodec.decode(Data(("\"" + String(repeating: "x", count: 513) + "\"").utf8)) }
    // Escaped bytes do not bypass the decoded string bound.
    #expect(throws: UIAppearanceErrorV1.shape) { _ = try AppearanceCodec.decode(Data(("\"" + String(repeating: "\\u0061", count: 513) + "\"").utf8)) }
}

@Test func appearanceV1RawConstructorsRequireWholeGraphValidation() throws {
    let theme = try appearanceThemeV1()
    for id in ["", "has space", String(repeating: "x", count: 129), "app.é", String(repeating: "x", count: 2_000_000)] {
        appearanceInvalidGraphV1(UIAppearanceConfigurationV1(id: id, mode: .shared(theme)))
    }
    for reason in ["", " ", " leading", "trailing ", "line\nfeed", String(repeating: "x", count: 513)] {
        appearanceInvalidGraphV1(UIAppearanceConfigurationV1(id: "app", mode: .platformSpecific(iOS: theme, android: theme, reason: reason)))
    }
    let body = UITextMetricV1(size64: 16_385, weight: .w400, minimumLineBox64: 65_536)
    let shortLine = UITextMetricV1(size64: 1088, weight: .w400, minimumLineBox64: 64)
    let overflowLine = UITextMetricV1(size64: 64, weight: .w400, minimumLineBox64: .max)
    for bad in [body, shortLine, overflowLine] {
        appearanceInvalidGraphV1(UIAppearanceConfigurationV1(id: "app", mode: .shared(appearanceRethemeV1(theme, body: bad))))
    }
    let layout = theme.layout
    let invalidLayout = UILayoutMetricsV1(stackGap64: .max, vStackAlignment: layout.vStackAlignment,
        hStackAlignment: layout.hStackAlignment, zStackAlignment: layout.zStackAlignment, list: layout.list,
        sectionHeaderInsets64: layout.sectionHeaderInsets64, navigation: layout.navigation)
    appearanceInvalidGraphV1(UIAppearanceConfigurationV1(id: "app", mode: .shared(appearanceRethemeV1(theme, layout: invalidLayout))))
}

@Test func appearanceV1ResourceCatalogRejectsPathsVariantsAndTotals() throws {
    let theme = try appearanceThemeV1()
    func invalid(_ resources: [UIAppearanceResourceV1]) {
        appearanceInvalidGraphV1(UIAppearanceConfigurationV1(id: "app", mode: .shared(theme), resources: resources))
    }
    for path in ["/absolute", "../font.ttf", "a/./b", "a/../b", "a//b", "a/", "a\\b", ".hidden", "a/.hidden", "a:link"] {
        invalid([appearanceResourceV1(path: path)])
    }
    for locale in ["-en", "en-", "en--US", "en_US"] { invalid([appearanceResourceV1(locale: locale)]) }
    for bytes: UInt32 in [0, 4_194_305, .max] { invalid([appearanceResourceV1(bytes: bytes)]) }
    for scale: UInt8 in [0, 5, .max] { invalid([appearanceResourceV1(scale: scale)]) }
    for provenance in [" ", " Leading", "Trailing ", "bad\tref", String(repeating: "a", count: 513)] {
        invalid([appearanceResourceV1(provenance: provenance)])
    }
    invalid([appearanceResourceV1(), appearanceResourceV1()])
    invalid([appearanceResourceV1(path: "A/font.bin"), appearanceResourceV1(1, path: "a/FONT.bin")])
    invalid((0..<65).map { appearanceResourceV1($0) })
    invalid(Array(repeating: appearanceResourceV1(), count: 100_000))
    invalid((0..<17).map { appearanceResourceV1($0, kind: .fontSFNT) })
    invalid((0..<5).map { appearanceResourceV1($0, bytes: 4_194_304) })
    // The documented font-variant rule also covers unreferenced catalog entries.
    invalid([appearanceResourceV1(kind: .fontSFNT, scale: 2)])
    invalid([appearanceResourceV1(kind: .fontSFNT, locale: "en")])
    invalid([appearanceResourceV1(kind: .fontSFNT, direction: .leftToRight)])
}

@Test func appearanceV1ProgrammaticDescriptorBytesAreMeasuredBeforeSerialization() throws {
    let theme = try appearanceThemeV1()
    // Each entry obeys its individual schema; the complete canonical document exceeds64KiB.
    let resources = (0..<64).map { index in
        appearanceResourceV1(index, path: String(repeating: "a", count: 250) + String(index),
                             provenance: String(repeating: "p", count: 512), locale: String(repeating: "e", count: 64))
    }
    let value = UIAppearanceConfigurationV1(id: "app", mode: .platformSpecific(iOS: theme, android: theme,
        reason: String(repeating: "r", count: 512)), resources: resources)
    #expect(throws: UIAppearanceErrorV1.byteLimit) { try AppearanceCodec.validate(value) }
    #expect(throws: UIAppearanceErrorV1.byteLimit) { _ = try AppearanceCodec.canonicalData(value) }
}

@Test func appearanceV1BundledFacesAndRequiredWeightsAreClosed() throws {
    let theme = try appearanceThemeV1()
    let regular = UIFontFaceV1(resourceID: "r0", postScriptName: "Fixture-Regular", weight: .w400, style: .normal)
    let semibold = UIFontFaceV1(resourceID: "r1", postScriptName: "Fixture-Semibold", weight: .w600, style: .normal)
    let resources = [appearanceResourceV1(kind: .fontSFNT), appearanceResourceV1(1, kind: .fontSFNT)]
    for fallback: UIFontFallbackV1 in [.none, .systemSans] {
        let valid = UIAppearanceConfigurationV1(id: "app", mode: .shared(appearanceRethemeV1(theme,
            font: .bundled(faces: [regular, semibold], fallback: fallback))), resources: resources)
        #expect(try AppearanceCodec.decode(AppearanceCodec.canonicalData(valid)) == valid)
        for faces in [[], [regular], [regular, semibold, regular], Array(repeating: regular, count: 17),
                      [regular, UIFontFaceV1(resourceID: "r1", postScriptName: "Italic", weight: .w600, style: .italic)],
                      [regular, UIFontFaceV1(resourceID: "missing", postScriptName: "Missing", weight: .w600, style: .normal)],
                      [regular, UIFontFaceV1(resourceID: "r1", postScriptName: "Invalid Name", weight: .w600, style: .normal)]] {
            appearanceInvalidGraphV1(UIAppearanceConfigurationV1(id: "app", mode: .shared(appearanceRethemeV1(theme,
                font: .bundled(faces: faces, fallback: fallback))), resources: resources))
        }
        appearanceInvalidGraphV1(UIAppearanceConfigurationV1(id: "app", mode: valid.mode, resources: [appearanceResourceV1(), resources[1]]))
    }
}

@Test func appearanceV1GeometryAndOpacityAreValidatedForBothThemes() throws {
    let theme = try appearanceThemeV1()
    let c = theme.controls
    let badToggle = UIToggleMetricsV1(trackWidth64: 3264, trackHeight64: 1984, thumb64: .max, inset64: .max,
                                      labelGap64: 512, minimumRow64: 2816)
    let shortRow = UIToggleMetricsV1(trackWidth64: 3264, trackHeight64: 1984, thumb64: 1728, inset64: 128,
                                     labelGap64: 512, minimumRow64: 1983)
    for (toggle, opacity) in [(badToggle, UInt16(120)), (shortRow, UInt16(120)), (c.toggle, UInt16(1001))] {
        let bad = appearanceRethemeV1(theme, controls: UIControlMetricsV1(button: c.button, field: c.field, toggle: toggle,
            focusWidth64: c.focusWidth64, focusRadius64: c.focusRadius64, pressedOpacityPermille: opacity,
            selectionOpacityPermille: c.selectionOpacityPermille))
        appearanceInvalidGraphV1(UIAppearanceConfigurationV1(id: "app", mode: .shared(bad)))
        appearanceInvalidGraphV1(UIAppearanceConfigurationV1(id: "app", mode: .platformSpecific(iOS: theme, android: bad, reason: "Explicit")))
    }
}

@Test func appearanceV1CheckedMathTiesExtremesAndInvalidInputs() throws {
    #expect(try AppearanceMath.scaled64(1, textScale1024: 512) == 1)
    #expect(try AppearanceMath.scaled64(1, textScale1024: 511 + 2) == 1)
    #expect(try AppearanceMath.scaled64(65_536, textScale1024: 4096) == 262_144)
    #expect(try AppearanceMath.scaled64(0, textScale1024: 512) == 0)
    #expect(try AppearanceMath.pixels(32, density1024: 1024) == 1)
    #expect(try AppearanceMath.pixels(31, density1024: 1024) == 0)
    #expect(try AppearanceMath.pixels(262_144, density1024: 16_384) == 65_536)
    #expect(try AppearanceMath.pixels(0, density1024: 128) == 0)
    #expect(try AppearanceMath.spacing64(0.5 / 64) == 1)
    #expect(try AppearanceMath.spacing64((0.5 / 64).nextDown.nextDown) == 0)
    #expect(try AppearanceMath.spacing64(256) == 16_384)
    #expect(try AppearanceMath.normalizeTextScale(0.5) == 512)
    #expect(try AppearanceMath.normalizeTextScale(4) == 4096)
    #expect(try AppearanceMath.normalizeTextScale(1024.5 / 1024) == 1025)
    #expect(try AppearanceMath.normalizeDensity(0.125) == 128)
    #expect(try AppearanceMath.normalizeDensity(16) == 16_384)
    #expect(try AppearanceMath.normalizeDensity(128.5 / 1024) == 129)
    for value in [Double.nan, .infinity, -.infinity, -1, 256.001] {
        #expect(throws: UIAppearanceErrorV1.number) { _ = try AppearanceMath.spacing64(value) }
    }
    for value in [Double.nan, .infinity, 0.5.nextDown, 4.0.nextUp] {
        #expect(throws: UIAppearanceErrorV1.number) { _ = try AppearanceMath.normalizeTextScale(value) }
    }
    for value in [Double.nan, -.infinity, 0.125.nextDown, 16.0.nextUp] {
        #expect(throws: UIAppearanceErrorV1.number) { _ = try AppearanceMath.normalizeDensity(value) }
    }
    for metric: UInt32 in [65_537, .max] {
        #expect(throws: UIAppearanceErrorV1.number) { _ = try AppearanceMath.scaled64(metric, textScale1024: 4096) }
    }
    for scale: UInt16 in [0, 511, 4097, .max] {
        #expect(throws: UIAppearanceErrorV1.number) { _ = try AppearanceMath.scaled64(1, textScale1024: scale) }
    }
    for metric: UInt32 in [262_145, .max] {
        #expect(throws: UIAppearanceErrorV1.number) { _ = try AppearanceMath.pixels(metric, density1024: 16_384) }
    }
    for density: UInt16 in [0, 127, 16_385, .max] {
        #expect(throws: UIAppearanceErrorV1.number) { _ = try AppearanceMath.pixels(1, density1024: density) }
    }
}

@Test func appearanceV1ExactWireByteBoundaryIncludesFinalLF() throws {
    var object = try #require(JSONSerialization.jsonObject(with: appearanceFixtureV1()) as? [String: Any])
    var resources: [[String: Any]] = (0..<64).map { index in
        ["id": "r\(index)", "kind": "iconPNG", "path": String(repeating: "a", count: 250) + String(index),
         "sha256": String(repeating: "a", count: 64), "bytes": 1, "provenance": String(repeating: "p", count: 512),
         "scale": 1, "locale": String(repeating: "e", count: 64), "direction": "neutral"]
    }
    object["resources"] = resources
    func bytes() throws -> Data {
        try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys, .withoutEscapingSlashes]) + Data([10])
    }
    let initial = try bytes().count
    #expect(initial > 65_536)
    // Trim only bounded provenance strings, retaining every other closed field.
    var excess = initial - 65_536
    for index in resources.indices where excess > 0 {
        let remove = min(excess, 511)
        resources[index]["provenance"] = String(repeating: "p", count: 512 - remove)
        excess -= remove
    }
    #expect(excess == 0)
    object["resources"] = resources
    let exact = try bytes()
    #expect(exact.count == 65_536)
    let value = try AppearanceCodec.decode(exact)
    #expect(try AppearanceCodec.canonicalData(value) == exact)
    try AppearanceCodec.validate(value)
    #expect(throws: UIAppearanceErrorV1.byteLimit) { _ = try AppearanceCodec.decode(exact + Data([10])) }
}

@Test func appearanceV1ParserBoundaryClassificationsPrecedeClosedShape() throws {
    // These shapes are deliberately invalid, but remain inside the parser budget.
    let sixteen = String(repeating: "{\"a\":", count: 15) + "0" + String(repeating: "}", count: 15)
    #expect(throws: UIAppearanceErrorV1.shape) { _ = try AppearanceCodec.decode(Data(sixteen.utf8)) }
    let fields4095 = "{" + (0..<4095).map { "\"k\($0)\":0" }.joined(separator: ",") + "}"
    #expect(throws: UIAppearanceErrorV1.shape) { _ = try AppearanceCodec.decode(Data(fields4095.utf8)) }
    #expect(throws: UIAppearanceErrorV1.syntax) { _ = try AppearanceCodec.decode(Data(repeating: 32, count: 65_536)) }
}
