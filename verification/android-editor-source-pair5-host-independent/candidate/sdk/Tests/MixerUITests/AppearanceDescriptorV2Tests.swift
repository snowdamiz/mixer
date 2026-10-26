import Foundation
import Testing
import MixerUI

private typealias CodecV2 = UIAppearanceDescriptorCodecV2
private let descriptorRootV2 = URL(fileURLWithPath: #filePath)
    .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
private func goldenV2() throws -> Data {
    try Data(contentsOf: descriptorRootV2.appendingPathComponent("verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json"))
}
private func objectV2() throws -> [String: Any] {
    try #require(JSONSerialization.jsonObject(with: goldenV2()) as? [String: Any])
}
// Foundation is only a test mutation authoring tool; product admission uses its
// independently bounded parser and never delegates authority to JSONSerialization.
private func bytesV2(_ object: Any) throws -> Data {
    // Foundation's sortedKeys comparison is not the contract's ASCII ordering
    // for mixed-case keys such as iOS/id; order keys explicitly in this test writer.
    func write(_ value: Any) throws -> Data {
        if let fields = value as? [String: Any] {
            var bytes = Data([123])
            for (index, key) in fields.keys.sorted().enumerated() {
                if index != 0 { bytes.append(44) }
                bytes.append(try write(key)); bytes.append(58)
                bytes.append(try write(fields[key]!))
            }
            bytes.append(125); return bytes
        }
        if let items = value as? [Any] {
            var bytes = Data([91])
            for (index, item) in items.enumerated() {
                if index != 0 { bytes.append(44) }
                bytes.append(try write(item))
            }
            bytes.append(93); return bytes
        }
        return try JSONSerialization.data(withJSONObject: value, options: [.withoutEscapingSlashes, .fragmentsAllowed])
    }
    var result = try write(object)
    result.append(10)
    return result
}
private func changingV2(_ object: [String: Any], _ path: [String], _ replacement: Any?) -> [String: Any] {
    var copy = object
    if path.count == 1 { copy[path[0]] = replacement }
    else { copy[path[0]] = changingV2(copy[path[0]] as! [String: Any], Array(path.dropFirst()), replacement) }
    return copy
}
private func rejectV2(_ object: Any) throws {
    let bytes = try bytesV2(object)
    #expect(throws: UIAppearanceErrorV2.self) { _ = try CodecV2.decode(bytes) }
}
private func resourceV2(_ index: Int, kind: UIResourceKindV1 = .iconPNG,
                        path: String? = nil, bytes: UInt32 = 1, provenance: String = "Owned test metadata",
                        scale: UInt8 = 1, locale: String = "und",
                        direction: UIResourceDirectionV1 = .neutral) -> UIAppearanceResourceV1 {
    UIAppearanceResourceV1(id: "r\(index)", kind: kind, path: path ?? "asset/r\(index).bin",
        sha256: String(repeating: "a", count: 64), bytes: bytes, provenance: provenance,
        scale: scale, locale: locale, direction: direction)
}
private func defaultThemeV2() throws -> UIThemeV2 {
    guard case let .shared(theme) = try CodecV2.mixerDefaultV2().mode else { throw UIAppearanceErrorV2.shape }
    return theme
}
private func invalidGraphV2(_ value: UIAppearanceConfigurationV2) {
    #expect(throws: UIAppearanceErrorV2.self) { try CodecV2.validate(value) }
    #expect(throws: UIAppearanceErrorV2.self) { _ = try CodecV2.canonicalData(value) }
}

@Test func appearanceV2ExactGoldenAndCrossVersionSeparation() throws {
    let fixture = try goldenV2(), value = try CodecV2.mixerDefaultV2()
    #expect(fixture.count == 9587)
    #expect(value.id == "mixer.measured-candidate.v2")
    #expect(value.resources.isEmpty)
    #expect(try CodecV2.canonicalData(value) == fixture)
    #expect(try CodecV2.decode(fixture) == value)
    try CodecV2.validate(value)
    let v1 = try UIAppearanceDescriptorCodecV1.canonicalData(UIAppearanceDescriptorCodecV1.mixerDefaultV1())
    let retainedV1 = try Data(contentsOf: descriptorRootV2.appendingPathComponent("verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json"))
    #expect(v1.count == 1906)
    #expect(v1 == retainedV1)
    #expect(throws: UIAppearanceErrorV1.self) { _ = try UIAppearanceDescriptorCodecV1.decode(fixture) }
    #expect(throws: UIAppearanceErrorV2.self) { _ = try CodecV2.decode(v1) }
    let decode: (Data) throws -> UIAppearanceConfigurationV2 = CodecV2.decode
    let encode: (UIAppearanceConfigurationV2) throws -> Data = CodecV2.canonicalData
    #expect(try encode(decode(fixture)) == fixture)
}

@Test func appearanceV2EveryNestedObjectRejectsMissingUnknownFields() throws {
    let base = try objectV2()
    var paths: [[String]] = []
    func walk(_ object: [String: Any], _ path: [String]) {
        paths.append(path)
        for (key, value) in object { if let child = value as? [String: Any] { walk(child, path + [key]) } }
    }
    walk(base, [])
    #expect(paths.count > 100)
    for path in paths {
        var object = base
        var current = base
        for key in path { current = current[key] as! [String: Any] }
        let key = try #require(current.keys.sorted().first)
        if path.isEmpty {
            object["unknown"] = 0; try rejectV2(object)
            object = base; object[key] = nil; try rejectV2(object)
        } else {
            try rejectV2(changingV2(base, path + ["unknown"], 0))
            try rejectV2(changingV2(base, path + [key], nil))
        }
    }
}

@Test func appearanceV2RejectsLexicalAndCanonicalAlternatives() throws {
    let fixture = try goldenV2(), text = String(decoding: fixture, as: UTF8.self)
    for token in ["-0", "+1", "01", "512.0", "512e0", "512E+0", "true", "null", "NaN", "Infinity",
                  "18446744073709551615", "18446744073709551616", "100000000000000000000", "65537"] {
        let bytes = Data(text.replacingOccurrences(of: "\"defaultGap64\":512", with: "\"defaultGap64\":\(token)").utf8)
        #expect(throws: UIAppearanceErrorV2.self, Comment(rawValue: token)) { _ = try CodecV2.decode(bytes) }
    }
    var malformed: [Data] = [Data(), Data(repeating: 32, count: 65537)]
    malformed.append(Data([239,187,191]) + fixture)
    malformed.append(Data([255]) + fixture)
    malformed.append(fixture + Data(" ".utf8))
    malformed.append(Data(fixture.dropLast()))
    malformed.append(fixture + Data("\n".utf8))
    malformed.append(Data(" ".utf8) + fixture)
    malformed.append(Data(text.replacingOccurrences(of: "\"format\":", with: "\"format\" :").utf8))
    malformed.append(Data(text.replacingOccurrences(of: "mixer.measured-candidate.v2", with: "mixer.\\u006deasured-candidate.v2").utf8))
    let ordered = "\"format\":\"mixer.native-appearance.2\",\"id\":\"mixer.measured-candidate.v2\""
    let unordered = "\"id\":\"mixer.measured-candidate.v2\",\"format\":\"mixer.native-appearance.2\""
    malformed.append(Data(text.replacingOccurrences(of: ordered, with: unordered).utf8))
    for data in malformed {
        #expect(throws: UIAppearanceErrorV2.self) { _ = try CodecV2.decode(data) }
    }
    for key in ["mode", "m\\u006fde"] {
        let bytes = Data(text.replacingOccurrences(of: "\"mode\":\"shared\"", with: "\"mode\":\"shared\",\"\(key)\":\"shared\"").utf8)
        #expect(throws: UIAppearanceErrorV2.duplicateKey) { _ = try CodecV2.decode(bytes) }
    }
}

@Test func appearanceV2ParserAdmitsBoundsBeforeRetainingChildren() throws {
    for (count, error) in [(20, UIAppearanceErrorV2.shape), (21, .depthLimit)] {
        let bytes = Data((String(repeating: "[", count: count) + "0" + String(repeating: "]", count: count) + "\n").utf8)
        #expect(throws: error) { _ = try CodecV2.decode(bytes) }
    }
    for (count, error) in [(64, UIAppearanceErrorV2.shape), (65, .arrayLimit)] {
        let bytes = Data(("[" + Array(repeating: "0", count: count).joined(separator: ",") + "]\n").utf8)
        #expect(throws: error) { _ = try CodecV2.decode(bytes) }
    }
    let full = Array(repeating: Array(repeating: 0, count: 64), count: 64)
    var second = Array(repeating: Array(repeating: 0, count: 64), count: 62)
    second[61].removeLast() // root1 + first4161 + second4030 = exactly8192 values.
    let exact = try bytesV2([full, second])
    #expect(throws: UIAppearanceErrorV2.shape) { _ = try CodecV2.decode(exact) }
    second[61].append(0)
    let excess = try bytesV2([full, second])
    #expect(throws: UIAppearanceErrorV2.valueLimit) { _ = try CodecV2.decode(excess) }
}

@Test func appearanceV2FullFrozenProfileFamilyAndDefaultProfileChoices() throws {
    let base = try objectV2()
    let rows = [[14,25,11,31],[15,26,11,32],[16,27,11,33],[17,28,12,34],
        [19,30,14,36],[21,32,16,38],[23,34,18,40],[28,38,22,44],
        [33,43,26,48],[40,48,32,52],[47,53,37,56],[53,58,43,60]]
    let roles = ["body", "headline", "title", "caption", "sectionHeader", "navigationExpanded"]
    let profiles = UISharedTextProfileV1.allCases
    for (profile, sizes) in zip(profiles, rows) {
        let authoredSizes = [sizes[0], sizes[0], sizes[1], sizes[2], sizes[0], sizes[3]]
        let weights = [400,600,400,400,600,700]
        for index in roles.indices {
            let path = ["theme", "typography", "profiles", profile.rawValue, roles[index]]
            var metric = base
            for key in path { metric = metric[key] as! [String: Any] }
            #expect((metric["size64"] as? Int) == authoredSizes[index] * 64)
            #expect((metric["weight"] as? Int) == weights[index])
            let bytes = try bytesV2(changingV2(base, path + ["size64"], authoredSizes[index] * 64 + 1))
            #expect(throws: UIAppearanceErrorV2.unsupportedProfile) { _ = try CodecV2.decode(bytes) }
            let changedWeight = try bytesV2(changingV2(base, path + ["weight"], 500))
            #expect(throws: UIAppearanceErrorV2.unsupportedProfile) { _ = try CodecV2.decode(changedWeight) }
        }
        let bytes = try bytesV2(changingV2(base, ["theme", "typography", "defaultProfile"], profile.rawValue))
        #expect(try CodecV2.canonicalData(CodecV2.decode(bytes)) == bytes)
    }
    try rejectV2(changingV2(base, ["theme", "typography", "defaultProfile"], "unknown"))
    try rejectV2(changingV2(base, ["theme", "typography", "preferencePolicy"], "clamp"))
}

@Test func appearanceV2ExplicitPlatformsRetainIndependentThemesAndEscaping() throws {
    var base = try objectV2()
    let theme = base.removeValue(forKey: "theme") as! [String: Any]
    base["mode"] = "platformSpecific"
    base["iOS"] = theme
    base["android"] = changingV2(theme, ["stacks", "defaultGap64"], 0)
    base["reason"] = "App \"choice\" \\ parity review"
    let bytes = try bytesV2(base), value = try CodecV2.decode(bytes)
    #expect(try CodecV2.canonicalData(value) == bytes)
    guard case let .platformSpecific(iOS, android, reason) = value.mode else { throw UIAppearanceErrorV2.shape }
    #expect(iOS.stacks.defaultGap64 == 512)
    #expect(android.stacks.defaultGap64 == 0)
    #expect(reason == "App \"choice\" \\ parity review")
    for reason in ["", " ", " leading", "trailing ", "tab\t", "é"] { try rejectV2(changingV2(base, ["reason"], reason)) }
    for field in ["iOS", "android", "reason"] { try rejectV2(changingV2(base, [field], nil)) }
    try rejectV2(changingV2(base, ["theme"], theme))
}

@Test func appearanceV2CustomPaintsAndBoundedGeometryRemainExplicit() throws {
    let base = try objectV2()
    var custom = changingV2(base, ["theme", "light", "text", "body"], "#12345678")
    custom = changingV2(custom, ["theme", "dark", "button", "normal", "pressed", "background"], "#ABCDEFFF")
    for path in [["stacks", "defaultGap64"], ["groupedList", "radius64"], ["button", "overlayRadius64"],
                 ["groupedList", "separatorThickness64"], ["toggle", "labelGap64"]] {
        for bound in [0, 65536] {
            let data = try bytesV2(changingV2(custom, ["theme"] + path, bound))
            #expect(try CodecV2.canonicalData(CodecV2.decode(data)) == data)
        }
        try rejectV2(changingV2(custom, ["theme"] + path, 65537))
    }
    let bytes = try bytesV2(custom)
    #expect(try CodecV2.canonicalData(CodecV2.decode(bytes)) == bytes)
    for color in ["#1234567a", "#123456", "#123456789", "#GG000000", "123456789"] {
        try rejectV2(changingV2(base, ["theme", "light", "canvas"], color))
    }
    for path in [["toggle", "trackWidth64"], ["toggle", "thumbWidth64"], ["toggle", "thumbInset64"]] {
        try rejectV2(changingV2(base, ["theme"] + path, 0))
    }
    try rejectV2(changingV2(base, ["theme", "groupedList", "outline"], "track63x28Continuous2"))
    try rejectV2(changingV2(base, ["theme", "navigation", "expandedRole"], "title"))
    try rejectV2(changingV2(base, ["theme", "navigation", "minimumExpandedBar64"], 1))
    try rejectV2(changingV2(base, ["theme", "groupedList", "profileFloors64", "xs"], 1791))
    try rejectV2(changingV2(base, ["theme", "groupedList", "profileFloors64", "s"], 3000))
}

@Test func appearanceV2DisabledPaintInvariantsNeverDeriveOpacityFallback() throws {
    let base = try objectV2()
    for scheme in ["light", "dark"] {
        for role in ["normal", "destructive", "cancel"] {
            try rejectV2(changingV2(base, ["theme", scheme, "button", role, "disabled", "background"], "#FF000000"))
        }
        for field in ["caret", "selection"] {
            try rejectV2(changingV2(base, ["theme", scheme, "field", "disabled", field], "#00000001"))
        }
        for state in ["enabled", "disabled"] {
            try rejectV2(changingV2(base, ["theme", scheme, "field", state, "outline", "width64"], 1))
        }
        for state in ["on", "off"] {
            try rejectV2(changingV2(base, ["theme", scheme, "toggle", state, "disabled", "overlay"], "#00000001"))
        }
    }
}

@Test func appearanceV2ResourceCatalogBoundsPathsAndMetadata() throws {
    let theme = try defaultThemeV2()
    func config(_ resources: [UIAppearanceResourceV1]) -> UIAppearanceConfigurationV2 {
        UIAppearanceConfigurationV2(id: "catalog", mode: .shared(theme), resources: resources)
    }
    let resources = (0..<64).map { resourceV2($0, bytes: 262144) }
    let maxCatalog = config(resources), data = try CodecV2.canonicalData(maxCatalog)
    #expect(try CodecV2.decode(data) == maxCatalog) // Exactly16MiB,64entries.
    invalidGraphV2(config(resources + [resourceV2(64)]))
    invalidGraphV2(config([resourceV2(0), resourceV2(0, path: "other.bin")]))
    invalidGraphV2(config([resourceV2(0, path: "A.bin"), resourceV2(1, path: "a.bin")]))
    invalidGraphV2(config((0..<5).map { resourceV2($0, bytes: 4194304) }))
    for path in ["", "/root", "../x", "a/../x", "a/./x", "a//b", "a/", ".hidden", "a/.hidden", "a\\b", "a:b", "é"] {
        invalidGraphV2(config([resourceV2(0, path: path)]))
    }
    for bytes: UInt32 in [0, 4194305] { invalidGraphV2(config([resourceV2(0, bytes: bytes)])) }
    for provenance in ["", " ", " leading", "trailing ", "line\n"] { invalidGraphV2(config([resourceV2(0, provenance: provenance)])) }
    for locale in ["", "-en", "en-", "en--US", "en_US"] { invalidGraphV2(config([resourceV2(0, locale: locale)])) }
    for scale: UInt8 in [0, 5] { invalidGraphV2(config([resourceV2(0, scale: scale)])) }
    for resource in [resourceV2(0, kind: .fontSFNT, scale: 2), resourceV2(0, kind: .fontSFNT, locale: "en"),
                     resourceV2(0, kind: .fontSFNT, direction: .leftToRight)] { invalidGraphV2(config([resource])) }
    invalidGraphV2(config((0..<17).map { resourceV2($0, kind: .fontSFNT) }))
    let escaped = config([resourceV2(0, path: "folder/a-b_1.png", provenance: "Owned \"quote\" \\ slash", locale: "en-US", direction: .rightToLeft)])
    #expect(try CodecV2.decode(CodecV2.canonicalData(escaped)) == escaped)
}

@Test func appearanceV2BundledFontsCloseReferencesAndWeightPairs() throws {
    let base = try objectV2()
    let resources = (0..<3).map { resourceV2($0, kind: .fontSFNT) }
    func faces(_ weights: [Int], italic: Bool = false) -> [[String: Any]] {
        weights.enumerated().map { i, weight in ["resourceID": "r\(i % 3)", "postScriptName": "OwnedFace\(weight)", "weight": weight, "style": italic ? "italic" : "normal"] }
    }
    let entries: [[String: Any]] = resources.map { r in
        ["id": r.id, "kind": r.kind.rawValue, "path": r.path, "sha256": r.sha256, "bytes": r.bytes,
         "provenance": r.provenance, "scale": r.scale, "locale": r.locale, "direction": r.direction.rawValue]
    }
    var fontConfig = changingV2(base, ["resources"], entries)
    for fallback in ["none", "systemSans"] {
        fontConfig = changingV2(fontConfig, ["theme", "typography", "font"], ["kind": "bundled", "faces": faces([400,600,700]), "fallback": fallback])
        let bytes = try bytesV2(fontConfig)
        #expect(try CodecV2.canonicalData(CodecV2.decode(bytes)) == bytes)
    }
    for invalidFaces in [faces([]), faces([400,600]), faces([400,600,700,400]),
                         faces([400,600,700]) + faces([500], italic: true),
                         Array(repeating: faces([400])[0], count: 17)] {
        try rejectV2(changingV2(fontConfig, ["theme", "typography", "font", "faces"], invalidFaces))
    }
    let allFaces = faces([400,500,600,700]) + faces([400,500,600,700], italic: true)
    let complete = try bytesV2(changingV2(fontConfig, ["theme", "typography", "font", "faces"], allFaces))
    #expect(try CodecV2.canonicalData(CodecV2.decode(complete)) == complete)
    try rejectV2(changingV2(fontConfig, ["resources"], []))
    var wrongKind = entries; wrongKind[0]["kind"] = "iconPNG"
    try rejectV2(changingV2(fontConfig, ["resources"], wrongKind))
    var escaped = faces([400,600,700]); escaped[0]["postScriptName"] = "bad name"
    try rejectV2(changingV2(fontConfig, ["theme", "typography", "font", "faces"], escaped))
}

@Test func appearanceV2RawTypedValuesAreRevalidatedByBothEntries() throws {
    let theme = try defaultThemeV2()
    for id in ["", "space id", String(repeating: "x", count: 129), "é"] {
        invalidGraphV2(UIAppearanceConfigurationV2(id: id, mode: .shared(theme)))
    }
    let invalidStacks = UIStackMetricsV2(defaultGap64: .max, bodyCaptionGap64: 0,
        missingVStackGap: .bodyThenCaptionPairOtherwiseDefault,
        vStackAlignment: .center, hStackAlignment: .center, zStackAlignment: .center)
    let invalidTheme = UIThemeV2(recipe: theme.recipe, typography: theme.typography, light: theme.light, dark: theme.dark,
        stacks: invalidStacks, groupedList: theme.groupedList, button: theme.button, field: theme.field,
        toggle: theme.toggle, navigation: theme.navigation)
    invalidGraphV2(UIAppearanceConfigurationV2(id: "invalid", mode: .shared(invalidTheme)))
    let badResource = UIAppearanceResourceV1(id: "asset", kind: .iconPNG, path: "asset.png",
        sha256: String(repeating: "A", count: 64), bytes: 1, provenance: "Owned", scale: 1, locale: "und", direction: .neutral)
    invalidGraphV2(UIAppearanceConfigurationV2(id: "invalid", mode: .shared(theme), resources: [badResource]))
    invalidGraphV2(UIAppearanceConfigurationV2(id: "invalid", mode: .platformSpecific(iOS: theme, android: invalidTheme, reason: "Explicit")))
}

@Test func appearanceV2ExactWireBoundaryAndTypedBytePreflight() throws {
    var object = try objectV2()
    var resources: [[String: Any]] = (0..<64).map { index in
        ["id": "r\(index)", "kind": "iconPNG", "path": String(repeating: "a", count: 250) + String(index),
         "sha256": String(repeating: "a", count: 64), "bytes": 1, "provenance": String(repeating: "p", count: 512),
         "scale": 1, "locale": String(repeating: "e", count: 64), "direction": "neutral"]
    }
    object["resources"] = resources
    let initial = try bytesV2(object).count
    #expect(initial > 65536)
    var excess = initial - 65536
    for index in resources.indices where excess > 0 {
        let trim = min(excess, 511)
        resources[index]["provenance"] = String(repeating: "p", count: 512 - trim)
        excess -= trim
    }
    #expect(excess == 0)
    object["resources"] = resources
    let exact = try bytesV2(object)
    #expect(exact.count == 65536)
    let value = try CodecV2.decode(exact)
    #expect(try CodecV2.canonicalData(value) == exact)
    try CodecV2.validate(value)
    #expect(throws: UIAppearanceErrorV2.byteLimit) { _ = try CodecV2.decode(exact + Data([10])) }
    let theme = try defaultThemeV2()
    let largeResources = (0..<64).map { index in
        resourceV2(index, path: String(repeating: "a", count: 250) + String(index),
                   provenance: String(repeating: "p", count: 512), locale: String(repeating: "e", count: 64))
    }
    let large = UIAppearanceConfigurationV2(id: "large", mode: .platformSpecific(iOS: theme, android: theme,
        reason: String(repeating: "r", count: 512)), resources: largeResources)
    #expect(throws: UIAppearanceErrorV2.byteLimit) { try CodecV2.validate(large) }
    #expect(throws: UIAppearanceErrorV2.byteLimit) { _ = try CodecV2.canonicalData(large) }
}
