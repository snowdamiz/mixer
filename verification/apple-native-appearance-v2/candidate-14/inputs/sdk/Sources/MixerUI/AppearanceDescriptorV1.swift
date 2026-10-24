import Foundation

/// A closed data codec only. Success establishes no native support, resource validity,
/// installed provenance, presentation, health, or release authority.
public enum UIAppearanceDescriptorCodecV1 {
    public static func decode(_ bytes: Data) throws -> UIAppearanceConfigurationV1 {
        guard !bytes.isEmpty, bytes.count <= 65_536 else { throw UIAppearanceErrorV1.byteLimit }
        var reader = AppearanceReaderV1(bytes)
        let tree = try reader.read()
        let value = try UIAppearanceConfigurationV1.appearanceRead(tree)
        try appearanceSemanticsV1(value)
        let canonical = try appearanceCanonicalV1(tree)
        guard canonical == bytes else { throw UIAppearanceErrorV1.noncanonical }
        return value
    }

    public static func validate(_ value: UIAppearanceConfigurationV1) throws {
        _ = try checkedTree(value)
    }

    public static func canonicalData(_ value: UIAppearanceConfigurationV1) throws -> Data {
        try appearanceCanonicalV1(checkedTree(value))
    }

    private static func checkedTree(_ value: UIAppearanceConfigurationV1) throws -> AppearanceJSONV1 {
        // This fixed graph has no recursive raw values. Counts are checked before map;
        // strings are checked without copying before retention. The two themes plus
        // 64 resources and two 16-face catalogs fit the global 4096-value bound.
        let tree = try value.appearanceWrite()
        let checked = try UIAppearanceConfigurationV1.appearanceRead(tree)
        try appearanceSemanticsV1(checked)
        var measurement = AppearanceWriterV1()
        try measurement.write(tree)
        try measurement.byte(10)
        return tree
    }
}

private indirect enum AppearanceJSONV1 {
    case object([String: AppearanceJSONV1]), array([AppearanceJSONV1]), string(String), uint(UInt64)

    func fields(_ keys: [String]) throws -> [String: AppearanceJSONV1] {
        guard case let .object(fields) = self, fields.count == keys.count,
              keys.allSatisfy({ fields[$0] != nil }) else { throw UIAppearanceErrorV1.shape }
        return fields
    }
    func text() throws -> String {
        guard case let .string(value) = self else { throw UIAppearanceErrorV1.shape }
        return value
    }
    func number(_ low: UInt64 = 0, _ high: UInt64 = 65_536) throws -> UInt64 {
        guard case let .uint(value) = self, (low...high).contains(value) else { throw UIAppearanceErrorV1.number }
        return value
    }
    func items(_ minimum: Int = 0, _ maximum: Int) throws -> [AppearanceJSONV1] {
        guard case let .array(values) = self, (minimum...maximum).contains(values.count) else {
            throw UIAppearanceErrorV1.shape
        }
        return values
    }
}

private struct AppearanceReaderV1 {
    private let bytes: [UInt8]
    private var cursor = 0
    private var values = 0
    init(_ data: Data) { bytes = Array(data) } // caller admits <=64KiB before this copy
    private var next: UInt8? { cursor < bytes.count ? bytes[cursor] : nil }
    private mutating func whitespace() {
        while let byte = next, byte == 32 || byte == 10 || byte == 13 || byte == 9 { cursor += 1 }
    }
    private mutating func consume(_ byte: UInt8) throws {
        guard next == byte else { throw UIAppearanceErrorV1.syntax }
        cursor += 1
    }
    mutating func read() throws -> AppearanceJSONV1 {
        // All descriptor strings are ASCII. Reject malformed UTF8/BOM/nonASCII
        // before parsing; no Unicode decoder or replacement characters are used.
        guard bytes.allSatisfy({ $0 < 128 }) else { throw UIAppearanceErrorV1.invalidEncoding }
        let value = try value(depth: 1)
        whitespace()
        guard cursor == bytes.count else { throw UIAppearanceErrorV1.syntax }
        return value
    }
    private mutating func value(depth: Int) throws -> AppearanceJSONV1 {
        guard depth <= 16 else { throw UIAppearanceErrorV1.depthLimit }
        guard values < 4096 else { throw UIAppearanceErrorV1.valueLimit }
        values += 1
        whitespace()
        guard let token = next else { throw UIAppearanceErrorV1.syntax }
        switch token {
        case 123:
            cursor += 1
            var result: [String: AppearanceJSONV1] = [:]
            whitespace()
            if next == 125 { cursor += 1; return .object(result) }
            while true {
                whitespace()
                let key = try string()
                guard result[key] == nil else { throw UIAppearanceErrorV1.duplicateKey }
                whitespace(); try consume(58)
                // Child value count is admitted before any dictionary insertion.
                result[key] = try value(depth: depth + 1)
                whitespace()
                if next == 125 { cursor += 1; break }
                try consume(44)
            }
            return .object(result)
        case 91:
            cursor += 1
            var result: [AppearanceJSONV1] = []
            whitespace()
            if next == 93 { cursor += 1; return .array(result) }
            while true {
                // No accepted array can exceed the resource catalog's 64 items.
                guard result.count < 64 else { throw UIAppearanceErrorV1.shape }
                let child = try value(depth: depth + 1)
                result.append(child)
                whitespace()
                if next == 93 { cursor += 1; break }
                try consume(44)
            }
            return .array(result)
        case 34: return .string(try string())
        case 48...57:
            let start = cursor
            var number: UInt64 = 0
            while let byte = next, (48...57).contains(byte) {
                guard cursor - start < 20, cursor == start || bytes[start] != 48 else {
                    throw UIAppearanceErrorV1.number
                }
                let (product, overflow) = number.multipliedReportingOverflow(by: 10)
                let (sum, carry) = product.addingReportingOverflow(UInt64(byte - 48))
                guard !overflow, !carry else { throw UIAppearanceErrorV1.number }
                number = sum; cursor += 1
            }
            if let byte = next, byte == 46 || byte == 101 || byte == 69 { throw UIAppearanceErrorV1.number }
            return .uint(number)
        case 45, 43: throw UIAppearanceErrorV1.number
        default: throw UIAppearanceErrorV1.syntax
        }
    }
    private mutating func string() throws -> String {
        try consume(34)
        var result: [UInt8] = []
        while let byte = next {
            if byte == 34 { cursor += 1; return String(decoding: result, as: UTF8.self) }
            guard result.count < 512 else { throw UIAppearanceErrorV1.shape }
            guard byte >= 32 else { throw UIAppearanceErrorV1.syntax }
            cursor += 1
            if byte != 92 { result.append(byte); continue }
            guard let escape = next else { throw UIAppearanceErrorV1.syntax }
            cursor += 1
            let decoded: UInt8
            switch escape {
            case 34, 92, 47: decoded = escape
            case 98: decoded = 8
            case 102: decoded = 12
            case 110: decoded = 10
            case 114: decoded = 13
            case 116: decoded = 9
            case 117:
                var scalar: UInt16 = 0
                for _ in 0..<4 {
                    guard let digit = next else { throw UIAppearanceErrorV1.syntax }
                    cursor += 1
                    let hex: UInt16
                    switch digit {
                    case 48...57: hex = UInt16(digit - 48)
                    case 65...70: hex = UInt16(digit - 55)
                    case 97...102: hex = UInt16(digit - 87)
                    default: throw UIAppearanceErrorV1.syntax
                    }
                    scalar = scalar * 16 + hex
                }
                guard scalar < 128 else { throw UIAppearanceErrorV1.invalidEncoding }
                decoded = UInt8(scalar)
            default: throw UIAppearanceErrorV1.syntax
            }
            result.append(decoded)
        }
        throw UIAppearanceErrorV1.syntax
    }
}

private struct AppearanceWriterV1 {
    private(set) var count = 0
    private(set) var data: Data?
    private var values = 0
    init(capacity: Int? = nil) { if let capacity { data = Data(capacity: capacity) } }
    mutating func byte(_ value: UInt8) throws {
        guard count < 65_536 else { throw UIAppearanceErrorV1.byteLimit }
        count += 1; data?.append(value)
    }
    private mutating func string(_ value: String) throws {
        try byte(34)
        for byte in value.utf8 {
            if byte == 34 || byte == 92 { try self.byte(92) }
            try self.byte(byte)
        }
        try byte(34)
    }
    mutating func write(_ value: AppearanceJSONV1, depth: Int = 1) throws {
        guard depth <= 16 else { throw UIAppearanceErrorV1.depthLimit }
        guard values < 4096 else { throw UIAppearanceErrorV1.valueLimit }
        values += 1
        switch value {
        case let .object(fields):
            try byte(123)
            for (index, key) in fields.keys.sorted().enumerated() {
                if index != 0 { try byte(44) }
                try string(key); try byte(58); try write(fields[key]!, depth: depth + 1)
            }
            try byte(125)
        case let .array(items):
            guard items.count <= 64 else { throw UIAppearanceErrorV1.shape }
            try byte(91)
            for (index, item) in items.enumerated() {
                if index != 0 { try byte(44) }
                try write(item, depth: depth + 1)
            }
            try byte(93)
        case let .string(value): try string(value)
        case let .uint(value): for byte in String(value).utf8 { try self.byte(byte) }
        }
    }
}

private func appearanceCanonicalV1(_ value: AppearanceJSONV1) throws -> Data {
    var measurement = AppearanceWriterV1()
    try measurement.write(value); try measurement.byte(10)
    var writer = AppearanceWriterV1(capacity: measurement.count)
    try writer.write(value); try writer.byte(10)
    return writer.data!
}

// Bounded ASCII checks happen before retaining raw caller strings in a new graph.
private func appearanceStringV1(_ value: String, _ maximum: Int = 512) throws -> AppearanceJSONV1 {
    var count = 0
    for byte in value.utf8 {
        guard count < maximum, byte < 128 else { throw UIAppearanceErrorV1.shape }
        count += 1
    }
    return .string(value)
}

private func appearanceTextV1(_ value: AppearanceJSONV1, _ minimum: Int = 1, _ maximum: Int,
                              allowed: (UInt8) -> Bool) throws -> String {
    let text = try value.text()
    var count = 0
    for byte in text.utf8 {
        guard count < maximum, allowed(byte) else { throw UIAppearanceErrorV1.shape }
        count += 1
    }
    guard count >= minimum else { throw UIAppearanceErrorV1.shape }
    return text
}
private func appearanceAlphanumericV1(_ byte: UInt8) -> Bool {
    (65...90).contains(byte) || (97...122).contains(byte) || (48...57).contains(byte)
}
private func appearanceIDV1(_ value: AppearanceJSONV1) throws -> String {
    try appearanceTextV1(value, 1, 128) { appearanceAlphanumericV1($0) || $0 == 95 || $0 == 46 || $0 == 45 }
}
private func appearancePrintableV1(_ value: AppearanceJSONV1, maximum: Int = 512) throws -> String {
    try appearanceTextV1(value, 1, maximum) { (32...126).contains($0) }
}
private func appearanceEnumV1<T: RawRepresentable>(_ value: AppearanceJSONV1, _: T.Type) throws -> T where T.RawValue == String {
    guard let result = T(rawValue: try value.text()) else { throw UIAppearanceErrorV1.shape }
    return result
}

private extension UIInsets64V1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        let f = try value.fields(["top", "leading", "bottom", "trailing"])
        return Self(top: UInt32(try f["top"]!.number(0, 65536)),
            leading: UInt32(try f["leading"]!.number(0, 65536)),
            bottom: UInt32(try f["bottom"]!.number(0, 65536)),
            trailing: UInt32(try f["trailing"]!.number(0, 65536)))
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        .object(["top": .uint(UInt64(top)),
            "leading": .uint(UInt64(leading)),
            "bottom": .uint(UInt64(bottom)),
            "trailing": .uint(UInt64(trailing))])
    }
}

private extension UIPaletteV1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        let f = try value.fields(["canvas", "surface", "primaryText", "secondaryText", "accent", "destructive", "disabledText", "separator", "focus", "toggleOff", "toggleThumb"])
        return Self(canvas: try UIRGBA8V1.appearanceRead(f["canvas"]!),
            surface: try UIRGBA8V1.appearanceRead(f["surface"]!),
            primaryText: try UIRGBA8V1.appearanceRead(f["primaryText"]!),
            secondaryText: try UIRGBA8V1.appearanceRead(f["secondaryText"]!),
            accent: try UIRGBA8V1.appearanceRead(f["accent"]!),
            destructive: try UIRGBA8V1.appearanceRead(f["destructive"]!),
            disabledText: try UIRGBA8V1.appearanceRead(f["disabledText"]!),
            separator: try UIRGBA8V1.appearanceRead(f["separator"]!),
            focus: try UIRGBA8V1.appearanceRead(f["focus"]!),
            toggleOff: try UIRGBA8V1.appearanceRead(f["toggleOff"]!),
            toggleThumb: try UIRGBA8V1.appearanceRead(f["toggleThumb"]!))
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        .object(["canvas": try canvas.appearanceWrite(),
            "surface": try surface.appearanceWrite(),
            "primaryText": try primaryText.appearanceWrite(),
            "secondaryText": try secondaryText.appearanceWrite(),
            "accent": try accent.appearanceWrite(),
            "destructive": try destructive.appearanceWrite(),
            "disabledText": try disabledText.appearanceWrite(),
            "separator": try separator.appearanceWrite(),
            "focus": try focus.appearanceWrite(),
            "toggleOff": try toggleOff.appearanceWrite(),
            "toggleThumb": try toggleThumb.appearanceWrite()])
    }
}

private extension UITextMetricV1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        let f = try value.fields(["size64", "weight", "minimumLineBox64"])
        return Self(size64: UInt32(try f["size64"]!.number(64, 16384)),
            weight: try appearanceWeightV1(f["weight"]!),
            minimumLineBox64: UInt32(try f["minimumLineBox64"]!.number(64, 65536)))
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        .object(["size64": .uint(UInt64(size64)),
            "weight": .uint(UInt64(weight.rawValue)),
            "minimumLineBox64": .uint(UInt64(minimumLineBox64))])
    }
}

private extension UIFontFaceV1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        let f = try value.fields(["resourceID", "postScriptName", "weight", "style"])
        return Self(resourceID: try appearanceIDV1(f["resourceID"]!),
            postScriptName: try appearanceTextV1(f["postScriptName"]!, 1, 128) { (33...126).contains($0) },
            weight: try appearanceWeightV1(f["weight"]!),
            style: try appearanceEnumV1(f["style"]!, UIFontStyleV1.self))
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        .object(["resourceID": try appearanceStringV1(resourceID, 128),
            "postScriptName": try appearanceStringV1(postScriptName, 128),
            "weight": .uint(UInt64(weight.rawValue)),
            "style": .string(style.rawValue)])
    }
}

private extension UITypographyV1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        let f = try value.fields(["font", "body", "headline", "title", "caption"])
        return Self(font: try UIFontSourceV1.appearanceRead(f["font"]!),
            body: try UITextMetricV1.appearanceRead(f["body"]!),
            headline: try UITextMetricV1.appearanceRead(f["headline"]!),
            title: try UITextMetricV1.appearanceRead(f["title"]!),
            caption: try UITextMetricV1.appearanceRead(f["caption"]!))
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        .object(["font": try font.appearanceWrite(),
            "body": try body.appearanceWrite(),
            "headline": try headline.appearanceWrite(),
            "title": try title.appearanceWrite(),
            "caption": try caption.appearanceWrite()])
    }
}

private extension UIListMetricsV1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        let f = try value.fields(["insets64", "minimumRow64", "rowGap64", "groupGap64", "separator64"])
        return Self(insets64: try UIInsets64V1.appearanceRead(f["insets64"]!),
            minimumRow64: UInt32(try f["minimumRow64"]!.number(0, 65536)),
            rowGap64: UInt32(try f["rowGap64"]!.number(0, 65536)),
            groupGap64: UInt32(try f["groupGap64"]!.number(0, 65536)),
            separator64: UInt32(try f["separator64"]!.number(0, 65536)))
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        .object(["insets64": try insets64.appearanceWrite(),
            "minimumRow64": .uint(UInt64(minimumRow64)),
            "rowGap64": .uint(UInt64(rowGap64)),
            "groupGap64": .uint(UInt64(groupGap64)),
            "separator64": .uint(UInt64(separator64))])
    }
}

private extension UINavigationMetricsV1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        let f = try value.fields(["titleInsets64", "minimumBarHeight64", "titleAlignment"])
        return Self(titleInsets64: try UIInsets64V1.appearanceRead(f["titleInsets64"]!),
            minimumBarHeight64: UInt32(try f["minimumBarHeight64"]!.number(0, 65536)),
            titleAlignment: try appearanceEnumV1(f["titleAlignment"]!, UIHorizontalAlignmentV1.self))
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        .object(["titleInsets64": try titleInsets64.appearanceWrite(),
            "minimumBarHeight64": .uint(UInt64(minimumBarHeight64)),
            "titleAlignment": .string(titleAlignment.rawValue)])
    }
}

private extension UILayoutMetricsV1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        let f = try value.fields(["stackGap64", "vStackAlignment", "hStackAlignment", "zStackAlignment", "list", "sectionHeaderInsets64", "navigation"])
        return Self(stackGap64: UInt32(try f["stackGap64"]!.number(0, 65536)),
            vStackAlignment: try appearanceEnumV1(f["vStackAlignment"]!, UIHorizontalAlignmentV1.self),
            hStackAlignment: try appearanceEnumV1(f["hStackAlignment"]!, UIVerticalAlignmentV1.self),
            zStackAlignment: try appearanceEnumV1(f["zStackAlignment"]!, UIOverlayAlignmentV1.self),
            list: try UIListMetricsV1.appearanceRead(f["list"]!),
            sectionHeaderInsets64: try UIInsets64V1.appearanceRead(f["sectionHeaderInsets64"]!),
            navigation: try UINavigationMetricsV1.appearanceRead(f["navigation"]!))
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        .object(["stackGap64": .uint(UInt64(stackGap64)),
            "vStackAlignment": .string(vStackAlignment.rawValue),
            "hStackAlignment": .string(hStackAlignment.rawValue),
            "zStackAlignment": .string(zStackAlignment.rawValue),
            "list": try list.appearanceWrite(),
            "sectionHeaderInsets64": try sectionHeaderInsets64.appearanceWrite(),
            "navigation": try navigation.appearanceWrite()])
    }
}

private extension UIButtonMetricsV1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        let f = try value.fields(["labelInsets64", "minimumWidth64", "minimumHeight64", "radius64"])
        return Self(labelInsets64: try UIInsets64V1.appearanceRead(f["labelInsets64"]!),
            minimumWidth64: UInt32(try f["minimumWidth64"]!.number(0, 65536)),
            minimumHeight64: UInt32(try f["minimumHeight64"]!.number(0, 65536)),
            radius64: UInt32(try f["radius64"]!.number(0, 65536)))
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        .object(["labelInsets64": try labelInsets64.appearanceWrite(),
            "minimumWidth64": .uint(UInt64(minimumWidth64)),
            "minimumHeight64": .uint(UInt64(minimumHeight64)),
            "radius64": .uint(UInt64(radius64))])
    }
}

private extension UIFieldMetricsV1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        let f = try value.fields(["insets64", "minimumHeight64", "border64"])
        return Self(insets64: try UIInsets64V1.appearanceRead(f["insets64"]!),
            minimumHeight64: UInt32(try f["minimumHeight64"]!.number(0, 65536)),
            border64: UInt32(try f["border64"]!.number(0, 65536)))
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        .object(["insets64": try insets64.appearanceWrite(),
            "minimumHeight64": .uint(UInt64(minimumHeight64)),
            "border64": .uint(UInt64(border64))])
    }
}

private extension UIToggleMetricsV1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        let f = try value.fields(["trackWidth64", "trackHeight64", "thumb64", "inset64", "labelGap64", "minimumRow64"])
        return Self(trackWidth64: UInt32(try f["trackWidth64"]!.number(0, 65536)),
            trackHeight64: UInt32(try f["trackHeight64"]!.number(0, 65536)),
            thumb64: UInt32(try f["thumb64"]!.number(0, 65536)),
            inset64: UInt32(try f["inset64"]!.number(0, 65536)),
            labelGap64: UInt32(try f["labelGap64"]!.number(0, 65536)),
            minimumRow64: UInt32(try f["minimumRow64"]!.number(0, 65536)))
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        .object(["trackWidth64": .uint(UInt64(trackWidth64)),
            "trackHeight64": .uint(UInt64(trackHeight64)),
            "thumb64": .uint(UInt64(thumb64)),
            "inset64": .uint(UInt64(inset64)),
            "labelGap64": .uint(UInt64(labelGap64)),
            "minimumRow64": .uint(UInt64(minimumRow64))])
    }
}

private extension UIControlMetricsV1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        let f = try value.fields(["button", "field", "toggle", "focusWidth64", "focusRadius64", "pressedOpacityPermille", "selectionOpacityPermille"])
        return Self(button: try UIButtonMetricsV1.appearanceRead(f["button"]!),
            field: try UIFieldMetricsV1.appearanceRead(f["field"]!),
            toggle: try UIToggleMetricsV1.appearanceRead(f["toggle"]!),
            focusWidth64: UInt32(try f["focusWidth64"]!.number(0, 65536)),
            focusRadius64: UInt32(try f["focusRadius64"]!.number(0, 65536)),
            pressedOpacityPermille: UInt16(try f["pressedOpacityPermille"]!.number(0, 1000)),
            selectionOpacityPermille: UInt16(try f["selectionOpacityPermille"]!.number(0, 1000)))
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        .object(["button": try button.appearanceWrite(),
            "field": try field.appearanceWrite(),
            "toggle": try toggle.appearanceWrite(),
            "focusWidth64": .uint(UInt64(focusWidth64)),
            "focusRadius64": .uint(UInt64(focusRadius64)),
            "pressedOpacityPermille": .uint(UInt64(pressedOpacityPermille)),
            "selectionOpacityPermille": .uint(UInt64(selectionOpacityPermille))])
    }
}

private extension UIThemeV1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        let f = try value.fields(["recipe", "light", "dark", "typography", "layout", "controls"])
        return Self(recipe: try appearanceEnumV1(f["recipe"]!, UIRecipeV1.self),
            light: try UIPaletteV1.appearanceRead(f["light"]!),
            dark: try UIPaletteV1.appearanceRead(f["dark"]!),
            typography: try UITypographyV1.appearanceRead(f["typography"]!),
            layout: try UILayoutMetricsV1.appearanceRead(f["layout"]!),
            controls: try UIControlMetricsV1.appearanceRead(f["controls"]!))
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        .object(["recipe": .string(recipe.rawValue),
            "light": try light.appearanceWrite(),
            "dark": try dark.appearanceWrite(),
            "typography": try typography.appearanceWrite(),
            "layout": try layout.appearanceWrite(),
            "controls": try controls.appearanceWrite()])
    }
}

private extension UIAppearanceResourceV1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        let f = try value.fields(["id", "kind", "path", "sha256", "bytes", "provenance", "scale", "locale", "direction"])
        return Self(id: try appearanceIDV1(f["id"]!),
            kind: try appearanceEnumV1(f["kind"]!, UIResourceKindV1.self),
            path: try appearancePathV1(f["path"]!),
            sha256: try appearanceSha256V1(f["sha256"]!),
            bytes: UInt32(try f["bytes"]!.number(1, 4194304)),
            provenance: try appearancePrintableV1(f["provenance"]!),
            scale: UInt8(try f["scale"]!.number(1, 4)),
            locale: try appearanceLocaleV1(f["locale"]!),
            direction: try appearanceEnumV1(f["direction"]!, UIResourceDirectionV1.self))
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        .object(["id": try appearanceStringV1(id, 128),
            "kind": .string(kind.rawValue),
            "path": try appearanceStringV1(path, 256),
            "sha256": try appearanceStringV1(sha256, 64),
            "bytes": .uint(UInt64(bytes)),
            "provenance": try appearanceStringV1(provenance, 512),
            "scale": .uint(UInt64(scale)),
            "locale": try appearanceStringV1(locale, 64),
            "direction": .string(direction.rawValue)])
    }
}

private func appearancePathV1(_ value: AppearanceJSONV1) throws -> String {
    let path = try appearanceTextV1(value, 1, 256) {
        appearanceAlphanumericV1($0) || $0 == 95 || $0 == 46 || $0 == 45 || $0 == 47
    }
    var first = true
    for byte in path.utf8 {
        if byte == 47 {
            guard !first else { throw UIAppearanceErrorV1.shape }
            first = true
        } else {
            guard !first || byte != 46 else { throw UIAppearanceErrorV1.shape }
            first = false
        }
    }
    guard !first else { throw UIAppearanceErrorV1.shape }
    return path
}
private func appearanceLocaleV1(_ value: AppearanceJSONV1) throws -> String {
    let locale = try appearanceTextV1(value, 1, 64) { appearanceAlphanumericV1($0) || $0 == 45 }
    var first = true
    for byte in locale.utf8 {
        if byte == 45 {
            guard !first else { throw UIAppearanceErrorV1.shape }
            first = true
        } else { first = false }
    }
    guard !first else { throw UIAppearanceErrorV1.shape }
    return locale
}
private func appearanceSha256V1(_ value: AppearanceJSONV1) throws -> String {
    try appearanceTextV1(value, 64, 64) { (48...57).contains($0) || (97...102).contains($0) }
}
private func appearanceWeightV1(_ value: AppearanceJSONV1) throws -> UIFontWeightV1 {
    guard let weight = UIFontWeightV1(rawValue: UInt16(try value.number(400, 700))) else {
        throw UIAppearanceErrorV1.number
    }
    return weight
}
private extension UIRGBA8V1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        let text = try appearanceTextV1(value, 9, 9) { $0 == 35 || (48...57).contains($0) || (65...70).contains($0) }
        let bytes = Array(text.utf8)
        guard bytes[0] == 35, !bytes.dropFirst().contains(35) else { throw UIAppearanceErrorV1.shape }
        func channel(_ offset: Int) -> UInt8 {
            func hex(_ byte: UInt8) -> UInt8 { byte <= 57 ? byte - 48 : byte - 55 }
            return hex(bytes[offset]) * 16 + hex(bytes[offset + 1])
        }
        return Self(red: channel(1), green: channel(3), blue: channel(5), alpha: channel(7))
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        let hex = Array("0123456789ABCDEF".utf8)
        var bytes: [UInt8] = [35]
        for byte in [red, green, blue, alpha] { bytes.append(hex[Int(byte >> 4)]); bytes.append(hex[Int(byte & 15)]) }
        return .string(String(decoding: bytes, as: UTF8.self))
    }
}
private extension UIFontSourceV1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        guard case let .object(f) = value, let kind = f["kind"] else { throw UIAppearanceErrorV1.shape }
        switch try kind.text() {
        case "systemSans":
            _ = try value.fields(["kind"])
            return .systemSans
        case "bundled":
            _ = try value.fields(["kind", "faces", "fallback"])
            return .bundled(faces: try f["faces"]!.items(1, 16).map { try UIFontFaceV1.appearanceRead($0) },
                            fallback: try appearanceEnumV1(f["fallback"]!, UIFontFallbackV1.self))
        default: throw UIAppearanceErrorV1.shape
        }
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        switch self {
        case .systemSans: return .object(["kind": .string("systemSans")])
        case let .bundled(faces, fallback):
            guard (1...16).contains(faces.count) else { throw UIAppearanceErrorV1.fontCatalog }
            return .object(["kind": .string("bundled"), "fallback": .string(fallback.rawValue),
                            "faces": .array(try faces.map { try $0.appearanceWrite() })])
        }
    }
}
private extension UIAppearanceConfigurationV1 {
    static func appearanceRead(_ value: AppearanceJSONV1) throws -> Self {
        guard case let .object(f) = value, let mode = f["mode"] else { throw UIAppearanceErrorV1.shape }
        let parsedMode: UIAppearanceModeV1
        switch try mode.text() {
        case "shared":
            _ = try value.fields(["format", "id", "mode", "theme", "resources"])
            parsedMode = .shared(try UIThemeV1.appearanceRead(f["theme"]!))
        case "platformSpecific":
            _ = try value.fields(["format", "id", "mode", "iOS", "android", "reason", "resources"])
            parsedMode = .platformSpecific(iOS: try UIThemeV1.appearanceRead(f["iOS"]!),
                android: try UIThemeV1.appearanceRead(f["android"]!), reason: try appearancePrintableV1(f["reason"]!))
        default: throw UIAppearanceErrorV1.shape
        }
        guard try f["format"]!.text() == format else { throw UIAppearanceErrorV1.shape }
        return Self(id: try appearanceIDV1(f["id"]!), mode: parsedMode,
            resources: try f["resources"]!.items(0, 64).map { try UIAppearanceResourceV1.appearanceRead($0) })
    }
    func appearanceWrite() throws -> AppearanceJSONV1 {
        guard resources.count <= 64 else { throw UIAppearanceErrorV1.resourceCatalog }
        var fields: [String: AppearanceJSONV1] = ["format": .string(Self.format),
            "id": try appearanceStringV1(id, 128), "resources": .array(try resources.map { try $0.appearanceWrite() })]
        switch mode {
        case let .shared(theme):
            fields["mode"] = .string("shared"); fields["theme"] = try theme.appearanceWrite()
        case let .platformSpecific(iOS, android, reason):
            fields["mode"] = .string("platformSpecific")
            fields["iOS"] = try iOS.appearanceWrite(); fields["android"] = try android.appearanceWrite()
            fields["reason"] = try appearanceStringV1(reason)
        }
        return .object(fields)
    }
}

private func appearanceSemanticsV1(_ value: UIAppearanceConfigurationV1) throws {
    var ids: Set<String> = [], paths: Set<String> = []
    var total: UInt64 = 0
    var fonts = 0
    for resource in value.resources {
        guard ids.insert(resource.id).inserted, paths.insert(resource.path.lowercased()).inserted,
              resource.provenance.first != " ", resource.provenance.last != " " else {
            throw UIAppearanceErrorV1.resourceCatalog
        }
        total += UInt64(resource.bytes)
        guard total <= 16 * 1024 * 1024 else { throw UIAppearanceErrorV1.resourceCatalog }
        if resource.kind == .fontSFNT {
            fonts += 1
            guard fonts <= 16, resource.scale == 1, resource.locale == "und", resource.direction == .neutral else {
                throw UIAppearanceErrorV1.fontCatalog
            }
        }
    }
    func theme(_ theme: UIThemeV1) throws {
        let typography = theme.typography
        let styles = [typography.body, typography.headline, typography.title, typography.caption]
        guard styles.allSatisfy({ $0.minimumLineBox64 >= $0.size64 }) else { throw UIAppearanceErrorV1.geometry }
        if case let .bundled(faces, _) = typography.font {
            var pairs: Set<String> = []
            var normals: Set<UInt16> = []
            for face in faces {
                let key = String(face.weight.rawValue) + ":" + face.style.rawValue
                guard pairs.insert(key).inserted,
                      let resource = value.resources.first(where: { $0.id == face.resourceID }),
                      resource.kind == .fontSFNT else { throw UIAppearanceErrorV1.fontCatalog }
                if face.style == .normal { normals.insert(face.weight.rawValue) }
            }
            guard styles.allSatisfy({ normals.contains($0.weight.rawValue) }) else { throw UIAppearanceErrorV1.fontCatalog }
        }
        let toggle = theme.controls.toggle
        let envelope = UInt64(toggle.thumb64) + 2 * UInt64(toggle.inset64)
        guard envelope <= UInt64(toggle.trackWidth64), envelope <= UInt64(toggle.trackHeight64),
              toggle.minimumRow64 >= toggle.trackHeight64 else { throw UIAppearanceErrorV1.geometry }
    }
    switch value.mode {
    case let .shared(value): try theme(value)
    case let .platformSpecific(iOS, android, reason):
        guard reason.first != " ", reason.last != " " else { throw UIAppearanceErrorV1.shape }
        try theme(iOS); try theme(android)
    }
}
