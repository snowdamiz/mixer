import Foundation

/// A closed data codec only. Success establishes no native support, resource validity,
/// installed provenance, presentation, health, or release authority.
public enum UIAppearanceDescriptorCodecV2 {
    public static func decode(_ bytes: Data) throws -> UIAppearanceConfigurationV2 {
        guard !bytes.isEmpty, bytes.count <= 65_536 else { throw UIAppearanceErrorV2.byteLimit }
        var reader = AppearanceReaderV2(bytes)
        let tree = try reader.read()
        let value = try UIAppearanceConfigurationV2.appearanceReadV2(tree)
        try appearanceSemanticsV2(value)
        let canonical = try appearanceCanonicalV2(tree)
        guard canonical == bytes else { throw UIAppearanceErrorV2.noncanonical }
        return value
    }

    public static func validate(_ value: UIAppearanceConfigurationV2) throws {
        _ = try checkedTree(value)
    }

    public static func canonicalData(_ value: UIAppearanceConfigurationV2) throws -> Data {
        try appearanceCanonicalV2(checkedTree(value))
    }

    private static func checkedTree(_ value: UIAppearanceConfigurationV2) throws -> AppearanceJSONV2 {
        // This fixed graph has no recursive raw values. Counts are checked before map;
        // strings are checked without copying before retention. The two themes plus
        // 64 resources and two 16-face catalogs fit the global 8192-value bound.
        let tree = try value.appearanceWriteV2()
        let checked = try UIAppearanceConfigurationV2.appearanceReadV2(tree)
        try appearanceSemanticsV2(checked)
        var measurement = AppearanceWriterV2()
        try measurement.write(tree)
        try measurement.byte(10)
        return tree
    }
}

private indirect enum AppearanceJSONV2 {
    case object([String: AppearanceJSONV2]), array([AppearanceJSONV2]), string(String), uint(UInt64)

    func fields(_ keys: [String]) throws -> [String: AppearanceJSONV2] {
        guard case let .object(fields) = self, fields.count == keys.count,
              keys.allSatisfy({ fields[$0] != nil }) else { throw UIAppearanceErrorV2.shape }
        return fields
    }
    func text() throws -> String {
        guard case let .string(value) = self else { throw UIAppearanceErrorV2.shape }
        return value
    }
    func number(_ low: UInt64 = 0, _ high: UInt64 = 65_536) throws -> UInt64 {
        guard case let .uint(value) = self, (low...high).contains(value) else { throw UIAppearanceErrorV2.number }
        return value
    }
    func items(_ minimum: Int = 0, _ maximum: Int) throws -> [AppearanceJSONV2] {
        guard case let .array(values) = self, (minimum...maximum).contains(values.count) else {
            throw UIAppearanceErrorV2.shape
        }
        return values
    }
}

private struct AppearanceReaderV2 {
    private let bytes: [UInt8]
    private var cursor = 0
    private var values = 0
    init(_ data: Data) { bytes = Array(data) } // caller admits <=64KiB before this copy
    private var next: UInt8? { cursor < bytes.count ? bytes[cursor] : nil }
    private mutating func whitespace() {
        while let byte = next, byte == 32 || byte == 10 || byte == 13 || byte == 9 { cursor += 1 }
    }
    private mutating func consume(_ byte: UInt8) throws {
        guard next == byte else { throw UIAppearanceErrorV2.syntax }
        cursor += 1
    }
    mutating func read() throws -> AppearanceJSONV2 {
        // All descriptor strings are ASCII. Reject malformed UTF8/BOM/nonASCII
        // before parsing; no Unicode decoder or replacement characters are used.
        guard bytes.allSatisfy({ $0 < 128 }) else { throw UIAppearanceErrorV2.invalidEncoding }
        let value = try value(depth: 1)
        whitespace()
        guard cursor == bytes.count else { throw UIAppearanceErrorV2.syntax }
        return value
    }
    private mutating func value(depth: Int) throws -> AppearanceJSONV2 {
        guard values < 8192 else { throw UIAppearanceErrorV2.valueLimit }
        values += 1
        whitespace()
        guard let token = next else { throw UIAppearanceErrorV2.syntax }
        switch token {
        case 123:
            guard depth <= 20 else { throw UIAppearanceErrorV2.depthLimit }
            cursor += 1
            var result: [String: AppearanceJSONV2] = [:]
            whitespace()
            if next == 125 { cursor += 1; return .object(result) }
            while true {
                whitespace()
                let key = try string()
                guard result[key] == nil else { throw UIAppearanceErrorV2.duplicateKey }
                whitespace(); try consume(58)
                // Child value count is admitted before any dictionary insertion.
                result[key] = try value(depth: depth + 1)
                whitespace()
                if next == 125 { cursor += 1; break }
                try consume(44)
            }
            return .object(result)
        case 91:
            guard depth <= 20 else { throw UIAppearanceErrorV2.depthLimit }
            cursor += 1
            var result: [AppearanceJSONV2] = []
            whitespace()
            if next == 93 { cursor += 1; return .array(result) }
            while true {
                // No accepted array can exceed the resource catalog's 64 items.
                guard result.count < 64 else { throw UIAppearanceErrorV2.arrayLimit }
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
                    throw UIAppearanceErrorV2.number
                }
                let (product, overflow) = number.multipliedReportingOverflow(by: 10)
                let (sum, carry) = product.addingReportingOverflow(UInt64(byte - 48))
                guard !overflow, !carry else { throw UIAppearanceErrorV2.number }
                number = sum; cursor += 1
            }
            if let byte = next, byte == 46 || byte == 101 || byte == 69 { throw UIAppearanceErrorV2.number }
            return .uint(number)
        case 45, 43: throw UIAppearanceErrorV2.number
        default: throw UIAppearanceErrorV2.syntax
        }
    }
    private mutating func string() throws -> String {
        try consume(34)
        var result: [UInt8] = []
        while let byte = next {
            if byte == 34 { cursor += 1; return String(decoding: result, as: UTF8.self) }
            guard result.count < 512 else { throw UIAppearanceErrorV2.shape }
            guard byte >= 32 else { throw UIAppearanceErrorV2.syntax }
            cursor += 1
            if byte != 92 { result.append(byte); continue }
            guard let escape = next else { throw UIAppearanceErrorV2.syntax }
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
                    guard let digit = next else { throw UIAppearanceErrorV2.syntax }
                    cursor += 1
                    let hex: UInt16
                    switch digit {
                    case 48...57: hex = UInt16(digit - 48)
                    case 65...70: hex = UInt16(digit - 55)
                    case 97...102: hex = UInt16(digit - 87)
                    default: throw UIAppearanceErrorV2.syntax
                    }
                    scalar = scalar * 16 + hex
                }
                guard scalar < 128 else { throw UIAppearanceErrorV2.invalidEncoding }
                decoded = UInt8(scalar)
            default: throw UIAppearanceErrorV2.syntax
            }
            result.append(decoded)
        }
        throw UIAppearanceErrorV2.syntax
    }
}

private struct AppearanceWriterV2 {
    private(set) var count = 0
    private(set) var data: Data?
    private var values = 0
    init(capacity: Int? = nil) { if let capacity { data = Data(capacity: capacity) } }
    mutating func byte(_ value: UInt8) throws {
        guard count < 65_536 else { throw UIAppearanceErrorV2.byteLimit }
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
    mutating func write(_ value: AppearanceJSONV2, depth: Int = 1) throws {
        guard values < 8192 else { throw UIAppearanceErrorV2.valueLimit }
        values += 1
        switch value {
        case let .object(fields):
            guard depth <= 20 else { throw UIAppearanceErrorV2.depthLimit }
            try byte(123)
            for (index, key) in fields.keys.sorted().enumerated() {
                if index != 0 { try byte(44) }
                try string(key); try byte(58); try write(fields[key]!, depth: depth + 1)
            }
            try byte(125)
        case let .array(items):
            guard depth <= 20 else { throw UIAppearanceErrorV2.depthLimit }
            guard items.count <= 64 else { throw UIAppearanceErrorV2.arrayLimit }
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

private func appearanceCanonicalV2(_ value: AppearanceJSONV2) throws -> Data {
    var measurement = AppearanceWriterV2()
    try measurement.write(value); try measurement.byte(10)
    var writer = AppearanceWriterV2(capacity: measurement.count)
    try writer.write(value); try writer.byte(10)
    return writer.data!
}

// Bounded ASCII checks happen before retaining raw caller strings in a new graph.
private func appearanceStringV2(_ value: String, _ maximum: Int = 512) throws -> AppearanceJSONV2 {
    var count = 0
    for byte in value.utf8 {
        guard count < maximum, byte < 128 else { throw UIAppearanceErrorV2.shape }
        count += 1
    }
    return .string(value)
}

private func appearanceTextV2(_ value: AppearanceJSONV2, _ minimum: Int = 1, _ maximum: Int,
                              allowed: (UInt8) -> Bool) throws -> String {
    let text = try value.text()
    var count = 0
    for byte in text.utf8 {
        guard count < maximum, allowed(byte) else { throw UIAppearanceErrorV2.shape }
        count += 1
    }
    guard count >= minimum else { throw UIAppearanceErrorV2.shape }
    return text
}
private func appearanceAlphanumericV2(_ byte: UInt8) -> Bool {
    (65...90).contains(byte) || (97...122).contains(byte) || (48...57).contains(byte)
}
private func appearanceIDV2(_ value: AppearanceJSONV2) throws -> String {
    try appearanceTextV2(value, 1, 128) { appearanceAlphanumericV2($0) || $0 == 95 || $0 == 46 || $0 == 45 }
}
private func appearancePrintableV2(_ value: AppearanceJSONV2, maximum: Int = 512) throws -> String {
    try appearanceTextV2(value, 1, maximum) { (32...126).contains($0) }
}
private func appearanceEnumV2<T: RawRepresentable>(_ value: AppearanceJSONV2, _: T.Type) throws -> T where T.RawValue == String {
    guard let result = T(rawValue: try value.text()) else { throw UIAppearanceErrorV2.shape }
    return result
}


private extension UIRoleMetricsV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["body", "headline", "title", "caption", "sectionHeader", "navigationExpanded"])
        return Self(body: try UISharedTextMetricsV1.appearanceReadV2(f["body"]!),
            headline: try UISharedTextMetricsV1.appearanceReadV2(f["headline"]!),
            title: try UISharedTextMetricsV1.appearanceReadV2(f["title"]!),
            caption: try UISharedTextMetricsV1.appearanceReadV2(f["caption"]!),
            sectionHeader: try UISharedTextMetricsV1.appearanceReadV2(f["sectionHeader"]!),
            navigationExpanded: try UISharedTextMetricsV1.appearanceReadV2(f["navigationExpanded"]!))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["body": try body.appearanceWriteV2(),
            "headline": try headline.appearanceWriteV2(),
            "title": try title.appearanceWriteV2(),
            "caption": try caption.appearanceWriteV2(),
            "sectionHeader": try sectionHeader.appearanceWriteV2(),
            "navigationExpanded": try navigationExpanded.appearanceWriteV2()])
    }
}

private extension UIProfilesV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["xs", "s", "m", "l", "xl", "xxl", "xxxl", "a1", "a2", "a3", "a4", "a5"])
        return Self(xs: try UIRoleMetricsV2.appearanceReadV2(f["xs"]!),
            s: try UIRoleMetricsV2.appearanceReadV2(f["s"]!),
            m: try UIRoleMetricsV2.appearanceReadV2(f["m"]!),
            l: try UIRoleMetricsV2.appearanceReadV2(f["l"]!),
            xl: try UIRoleMetricsV2.appearanceReadV2(f["xl"]!),
            xxl: try UIRoleMetricsV2.appearanceReadV2(f["xxl"]!),
            xxxl: try UIRoleMetricsV2.appearanceReadV2(f["xxxl"]!),
            a1: try UIRoleMetricsV2.appearanceReadV2(f["a1"]!),
            a2: try UIRoleMetricsV2.appearanceReadV2(f["a2"]!),
            a3: try UIRoleMetricsV2.appearanceReadV2(f["a3"]!),
            a4: try UIRoleMetricsV2.appearanceReadV2(f["a4"]!),
            a5: try UIRoleMetricsV2.appearanceReadV2(f["a5"]!))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["xs": try xs.appearanceWriteV2(),
            "s": try s.appearanceWriteV2(),
            "m": try m.appearanceWriteV2(),
            "l": try l.appearanceWriteV2(),
            "xl": try xl.appearanceWriteV2(),
            "xxl": try xxl.appearanceWriteV2(),
            "xxxl": try xxxl.appearanceWriteV2(),
            "a1": try a1.appearanceWriteV2(),
            "a2": try a2.appearanceWriteV2(),
            "a3": try a3.appearanceWriteV2(),
            "a4": try a4.appearanceWriteV2(),
            "a5": try a5.appearanceWriteV2()])
    }
}

private extension UIProfileFloorsV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["xs", "s", "m", "l", "xl", "xxl", "xxxl", "a1", "a2", "a3", "a4", "a5"])
        return Self(xs: UInt32(try f["xs"]!.number(1, 65536)),
            s: UInt32(try f["s"]!.number(1, 65536)),
            m: UInt32(try f["m"]!.number(1, 65536)),
            l: UInt32(try f["l"]!.number(1, 65536)),
            xl: UInt32(try f["xl"]!.number(1, 65536)),
            xxl: UInt32(try f["xxl"]!.number(1, 65536)),
            xxxl: UInt32(try f["xxxl"]!.number(1, 65536)),
            a1: UInt32(try f["a1"]!.number(1, 65536)),
            a2: UInt32(try f["a2"]!.number(1, 65536)),
            a3: UInt32(try f["a3"]!.number(1, 65536)),
            a4: UInt32(try f["a4"]!.number(1, 65536)),
            a5: UInt32(try f["a5"]!.number(1, 65536)))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["xs": .uint(UInt64(xs)),
            "s": .uint(UInt64(s)),
            "m": .uint(UInt64(m)),
            "l": .uint(UInt64(l)),
            "xl": .uint(UInt64(xl)),
            "xxl": .uint(UInt64(xxl)),
            "xxxl": .uint(UInt64(xxxl)),
            "a1": .uint(UInt64(a1)),
            "a2": .uint(UInt64(a2)),
            "a3": .uint(UInt64(a3)),
            "a4": .uint(UInt64(a4)),
            "a5": .uint(UInt64(a5))])
    }
}

private extension UITypographyV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["font", "profiles", "defaultProfile", "preferencePolicy"])
        return Self(font: try UIFontSourceV1.appearanceReadV2(f["font"]!),
            profiles: try UIProfilesV2.appearanceReadV2(f["profiles"]!),
            defaultProfile: try appearanceEnumV2(f["defaultProfile"]!, UISharedTextProfileV1.self),
            preferencePolicy: try appearanceConstantV2(f["preferencePolicy"]!, "nearestBody64TiesUpRejectOutside", .nearestBody64TiesUpRejectOutside))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["font": try font.appearanceWriteV2(),
            "profiles": try profiles.appearanceWriteV2(),
            "defaultProfile": .string(defaultProfile.rawValue),
            "preferencePolicy": .string(preferencePolicy.rawValue)])
    }
}

private extension UIRolePaintsV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["body", "headline", "title", "caption", "sectionHeader", "navigationExpanded"])
        return Self(body: try UIRGBA8V1.appearanceReadV2(f["body"]!),
            headline: try UIRGBA8V1.appearanceReadV2(f["headline"]!),
            title: try UIRGBA8V1.appearanceReadV2(f["title"]!),
            caption: try UIRGBA8V1.appearanceReadV2(f["caption"]!),
            sectionHeader: try UIRGBA8V1.appearanceReadV2(f["sectionHeader"]!),
            navigationExpanded: try UIRGBA8V1.appearanceReadV2(f["navigationExpanded"]!))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["body": try body.appearanceWriteV2(),
            "headline": try headline.appearanceWriteV2(),
            "title": try title.appearanceWriteV2(),
            "caption": try caption.appearanceWriteV2(),
            "sectionHeader": try sectionHeader.appearanceWriteV2(),
            "navigationExpanded": try navigationExpanded.appearanceWriteV2()])
    }
}

private extension UIOutlineV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["color", "width64", "radius64"])
        return Self(color: try UIRGBA8V1.appearanceReadV2(f["color"]!),
            width64: UInt32(try f["width64"]!.number(0, 65536)),
            radius64: UInt32(try f["radius64"]!.number(0, 65536)))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["color": try color.appearanceWriteV2(),
            "width64": .uint(UInt64(width64)),
            "radius64": .uint(UInt64(radius64))])
    }
}

private extension UIButtonPaintV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["label", "background"])
        return Self(label: try UIRGBA8V1.appearanceReadV2(f["label"]!),
            background: try UIRGBA8V1.appearanceReadV2(f["background"]!))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["label": try label.appearanceWriteV2(),
            "background": try background.appearanceWriteV2()])
    }
}

private extension UIButtonStatesV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["enabled", "pressed", "disabled", "focus"])
        return Self(enabled: try UIButtonPaintV2.appearanceReadV2(f["enabled"]!),
            pressed: try UIButtonPaintV2.appearanceReadV2(f["pressed"]!),
            disabled: try UIButtonPaintV2.appearanceReadV2(f["disabled"]!),
            focus: try UIOutlineV2.appearanceReadV2(f["focus"]!))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["enabled": try enabled.appearanceWriteV2(),
            "pressed": try pressed.appearanceWriteV2(),
            "disabled": try disabled.appearanceWriteV2(),
            "focus": try focus.appearanceWriteV2()])
    }
}

private extension UIButtonRolesV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["normal", "destructive", "cancel"])
        return Self(normal: try UIButtonStatesV2.appearanceReadV2(f["normal"]!),
            destructive: try UIButtonStatesV2.appearanceReadV2(f["destructive"]!),
            cancel: try UIButtonStatesV2.appearanceReadV2(f["cancel"]!))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["normal": try normal.appearanceWriteV2(),
            "destructive": try destructive.appearanceWriteV2(),
            "cancel": try cancel.appearanceWriteV2()])
    }
}

private extension UIFieldPaintV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["text", "placeholder", "background", "caret", "selection", "outline"])
        return Self(text: try UIRGBA8V1.appearanceReadV2(f["text"]!),
            placeholder: try UIRGBA8V1.appearanceReadV2(f["placeholder"]!),
            background: try UIRGBA8V1.appearanceReadV2(f["background"]!),
            caret: try UIRGBA8V1.appearanceReadV2(f["caret"]!),
            selection: try UIRGBA8V1.appearanceReadV2(f["selection"]!),
            outline: try UIOutlineV2.appearanceReadV2(f["outline"]!))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["text": try text.appearanceWriteV2(),
            "placeholder": try placeholder.appearanceWriteV2(),
            "background": try background.appearanceWriteV2(),
            "caret": try caret.appearanceWriteV2(),
            "selection": try selection.appearanceWriteV2(),
            "outline": try outline.appearanceWriteV2()])
    }
}

private extension UIFieldStatesV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["enabled", "focused", "disabled"])
        return Self(enabled: try UIFieldPaintV2.appearanceReadV2(f["enabled"]!),
            focused: try UIFieldPaintV2.appearanceReadV2(f["focused"]!),
            disabled: try UIFieldPaintV2.appearanceReadV2(f["disabled"]!))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["enabled": try enabled.appearanceWriteV2(),
            "focused": try focused.appearanceWriteV2(),
            "disabled": try disabled.appearanceWriteV2()])
    }
}

private extension UITogglePaintV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["label", "track", "thumb", "overlay"])
        return Self(label: try UIRGBA8V1.appearanceReadV2(f["label"]!),
            track: try UIRGBA8V1.appearanceReadV2(f["track"]!),
            thumb: try UIRGBA8V1.appearanceReadV2(f["thumb"]!),
            overlay: try UIRGBA8V1.appearanceReadV2(f["overlay"]!))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["label": try label.appearanceWriteV2(),
            "track": try track.appearanceWriteV2(),
            "thumb": try thumb.appearanceWriteV2(),
            "overlay": try overlay.appearanceWriteV2()])
    }
}

private extension UIToggleStatesV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["enabled", "pressed", "disabled", "focus"])
        return Self(enabled: try UITogglePaintV2.appearanceReadV2(f["enabled"]!),
            pressed: try UITogglePaintV2.appearanceReadV2(f["pressed"]!),
            disabled: try UITogglePaintV2.appearanceReadV2(f["disabled"]!),
            focus: try UIOutlineV2.appearanceReadV2(f["focus"]!))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["enabled": try enabled.appearanceWriteV2(),
            "pressed": try pressed.appearanceWriteV2(),
            "disabled": try disabled.appearanceWriteV2(),
            "focus": try focus.appearanceWriteV2()])
    }
}

private extension UIToggleValuesV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["on", "off"])
        return Self(on: try UIToggleStatesV2.appearanceReadV2(f["on"]!),
            off: try UIToggleStatesV2.appearanceReadV2(f["off"]!))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["on": try on.appearanceWriteV2(),
            "off": try off.appearanceWriteV2()])
    }
}

private extension UIPaintsV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["canvas", "surface", "separator", "text", "button", "field", "toggle"])
        return Self(canvas: try UIRGBA8V1.appearanceReadV2(f["canvas"]!),
            surface: try UIRGBA8V1.appearanceReadV2(f["surface"]!),
            separator: try UIRGBA8V1.appearanceReadV2(f["separator"]!),
            text: try UIRolePaintsV2.appearanceReadV2(f["text"]!),
            button: try UIButtonRolesV2.appearanceReadV2(f["button"]!),
            field: try UIFieldStatesV2.appearanceReadV2(f["field"]!),
            toggle: try UIToggleValuesV2.appearanceReadV2(f["toggle"]!))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["canvas": try canvas.appearanceWriteV2(),
            "surface": try surface.appearanceWriteV2(),
            "separator": try separator.appearanceWriteV2(),
            "text": try text.appearanceWriteV2(),
            "button": try button.appearanceWriteV2(),
            "field": try field.appearanceWriteV2(),
            "toggle": try toggle.appearanceWriteV2()])
    }
}

private extension UIStackMetricsV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["defaultGap64", "bodyCaptionGap64", "missingVStackGap", "vStackAlignment", "hStackAlignment", "zStackAlignment"])
        return Self(defaultGap64: UInt32(try f["defaultGap64"]!.number(0, 65536)),
            bodyCaptionGap64: UInt32(try f["bodyCaptionGap64"]!.number(0, 65536)),
            missingVStackGap: try appearanceConstantV2(f["missingVStackGap"]!, "bodyThenCaptionPairOtherwiseDefault", .bodyThenCaptionPairOtherwiseDefault),
            vStackAlignment: try appearanceEnumV2(f["vStackAlignment"]!, UIHorizontalAlignmentV1.self),
            hStackAlignment: try appearanceEnumV2(f["hStackAlignment"]!, UIVerticalAlignmentV1.self),
            zStackAlignment: try appearanceEnumV2(f["zStackAlignment"]!, UIOverlayAlignmentV1.self))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["defaultGap64": .uint(UInt64(defaultGap64)),
            "bodyCaptionGap64": .uint(UInt64(bodyCaptionGap64)),
            "missingVStackGap": .string(missingVStackGap.rawValue),
            "vStackAlignment": .string(vStackAlignment.rawValue),
            "hStackAlignment": .string(hStackAlignment.rawValue),
            "zStackAlignment": .string(zStackAlignment.rawValue)])
    }
}

private extension UIGroupedListMetricsV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["outerHorizontal64", "contentInsets64", "topPadding64", "bottomPadding64", "headerToGroup64", "groupToNextHeader64", "groupWithoutHeaderGap64", "profileFloors64", "separatorInset64", "separatorThickness64", "outline", "radius64", "rowPolicy", "separatorPolicy"])
        return Self(outerHorizontal64: UInt32(try f["outerHorizontal64"]!.number(0, 65536)),
            contentInsets64: try UIInsets64V1.appearanceReadV2(f["contentInsets64"]!),
            topPadding64: UInt32(try f["topPadding64"]!.number(0, 65536)),
            bottomPadding64: UInt32(try f["bottomPadding64"]!.number(0, 65536)),
            headerToGroup64: UInt32(try f["headerToGroup64"]!.number(0, 65536)),
            groupToNextHeader64: UInt32(try f["groupToNextHeader64"]!.number(0, 65536)),
            groupWithoutHeaderGap64: UInt32(try f["groupWithoutHeaderGap64"]!.number(0, 65536)),
            profileFloors64: try UIProfileFloorsV2.appearanceReadV2(f["profileFloors64"]!),
            separatorInset64: UInt32(try f["separatorInset64"]!.number(0, 65536)),
            separatorThickness64: UInt32(try f["separatorThickness64"]!.number(0, 65536)),
            outline: try appearanceConstantV2(f["outline"]!, "fullGroupContinuousCubic2", .fullGroupContinuousCubic2),
            radius64: UInt32(try f["radius64"]!.number(0, 65536)),
            rowPolicy: try appearanceConstantV2(f["rowPolicy"]!, "maxProfileFloorSemanticContentPlusInsets", .maxProfileFloorSemanticContentPlusInsets),
            separatorPolicy: try appearanceConstantV2(f["separatorPolicy"]!, "interiorRowsOnly", .interiorRowsOnly))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["outerHorizontal64": .uint(UInt64(outerHorizontal64)),
            "contentInsets64": try contentInsets64.appearanceWriteV2(),
            "topPadding64": .uint(UInt64(topPadding64)),
            "bottomPadding64": .uint(UInt64(bottomPadding64)),
            "headerToGroup64": .uint(UInt64(headerToGroup64)),
            "groupToNextHeader64": .uint(UInt64(groupToNextHeader64)),
            "groupWithoutHeaderGap64": .uint(UInt64(groupWithoutHeaderGap64)),
            "profileFloors64": try profileFloors64.appearanceWriteV2(),
            "separatorInset64": .uint(UInt64(separatorInset64)),
            "separatorThickness64": .uint(UInt64(separatorThickness64)),
            "outline": .string(outline.rawValue),
            "radius64": .uint(UInt64(radius64)),
            "rowPolicy": .string(rowPolicy.rawValue),
            "separatorPolicy": .string(separatorPolicy.rawValue)])
    }
}

private extension UIButtonMetricsV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["labelInsets64", "minimumHitWidth64", "minimumHitHeight64", "overlayRadius64"])
        return Self(labelInsets64: try UIInsets64V1.appearanceReadV2(f["labelInsets64"]!),
            minimumHitWidth64: UInt32(try f["minimumHitWidth64"]!.number(1, 65536)),
            minimumHitHeight64: UInt32(try f["minimumHitHeight64"]!.number(1, 65536)),
            overlayRadius64: UInt32(try f["overlayRadius64"]!.number(0, 65536)))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["labelInsets64": try labelInsets64.appearanceWriteV2(),
            "minimumHitWidth64": .uint(UInt64(minimumHitWidth64)),
            "minimumHitHeight64": .uint(UInt64(minimumHitHeight64)),
            "overlayRadius64": .uint(UInt64(overlayRadius64))])
    }
}

private extension UIFieldMetricsV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["insets64", "minimumContentHeight64", "minimumHitHeight64"])
        return Self(insets64: try UIInsets64V1.appearanceReadV2(f["insets64"]!),
            minimumContentHeight64: UInt32(try f["minimumContentHeight64"]!.number(1, 65536)),
            minimumHitHeight64: UInt32(try f["minimumHitHeight64"]!.number(1, 65536)))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["insets64": try insets64.appearanceWriteV2(),
            "minimumContentHeight64": .uint(UInt64(minimumContentHeight64)),
            "minimumHitHeight64": .uint(UInt64(minimumHitHeight64))])
    }
}

private extension UIToggleMetricsV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["track", "thumb", "trackWidth64", "trackHeight64", "thumbWidth64", "thumbHeight64", "trackAuthoringRadius64", "thumbAuthoringRadius64", "thumbInset64", "labelGap64", "minimumHitWidth64", "minimumHitHeight64", "checkedEnd"])
        return Self(track: try appearanceConstantV2(f["track"]!, "track63x28Continuous2", .track63x28Continuous2),
            thumb: try appearanceConstantV2(f["thumb"]!, "thumb37x24Continuous2", .thumb37x24Continuous2),
            trackWidth64: UInt32(try f["trackWidth64"]!.number(4032, 4032)),
            trackHeight64: UInt32(try f["trackHeight64"]!.number(1792, 1792)),
            thumbWidth64: UInt32(try f["thumbWidth64"]!.number(2368, 2368)),
            thumbHeight64: UInt32(try f["thumbHeight64"]!.number(1536, 1536)),
            trackAuthoringRadius64: UInt32(try f["trackAuthoringRadius64"]!.number(896, 896)),
            thumbAuthoringRadius64: UInt32(try f["thumbAuthoringRadius64"]!.number(768, 768)),
            thumbInset64: UInt32(try f["thumbInset64"]!.number(128, 128)),
            labelGap64: UInt32(try f["labelGap64"]!.number(0, 65536)),
            minimumHitWidth64: UInt32(try f["minimumHitWidth64"]!.number(1, 65536)),
            minimumHitHeight64: UInt32(try f["minimumHitHeight64"]!.number(1, 65536)),
            checkedEnd: try appearanceConstantV2(f["checkedEnd"]!, "logicalTrailing", .logicalTrailing))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["track": .string(track.rawValue),
            "thumb": .string(thumb.rawValue),
            "trackWidth64": .uint(UInt64(trackWidth64)),
            "trackHeight64": .uint(UInt64(trackHeight64)),
            "thumbWidth64": .uint(UInt64(thumbWidth64)),
            "thumbHeight64": .uint(UInt64(thumbHeight64)),
            "trackAuthoringRadius64": .uint(UInt64(trackAuthoringRadius64)),
            "thumbAuthoringRadius64": .uint(UInt64(thumbAuthoringRadius64)),
            "thumbInset64": .uint(UInt64(thumbInset64)),
            "labelGap64": .uint(UInt64(labelGap64)),
            "minimumHitWidth64": .uint(UInt64(minimumHitWidth64)),
            "minimumHitHeight64": .uint(UInt64(minimumHitHeight64)),
            "checkedEnd": .string(checkedEnd.rawValue)])
    }
}

private extension UINavigationMetricsV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["expandedRole", "compactRole", "expandedAlignment", "compactAlignment", "expandedInsets64", "compactInsets64", "minimumExpandedBar64", "minimumCompactBar64", "collapse", "titleWrap"])
        return Self(expandedRole: try appearanceConstantV2(f["expandedRole"]!, "navigationExpanded", .navigationExpanded),
            compactRole: try appearanceConstantV2(f["compactRole"]!, "headline", .headline),
            expandedAlignment: try appearanceConstantV2(f["expandedAlignment"]!, "leading", .leading),
            compactAlignment: try appearanceConstantV2(f["compactAlignment"]!, "center", .center),
            expandedInsets64: try UIInsets64V1.appearanceReadV2(f["expandedInsets64"]!),
            compactInsets64: try UIInsets64V1.appearanceReadV2(f["compactInsets64"]!),
            minimumExpandedBar64: UInt32(try f["minimumExpandedBar64"]!.number(1, 65536)),
            minimumCompactBar64: UInt32(try f["minimumCompactBar64"]!.number(1, 65536)),
            collapse: try appearanceConstantV2(f["collapse"]!, "snapAtExpandedOverflow", .snapAtExpandedOverflow),
            titleWrap: try appearanceConstantV2(f["titleWrap"]!, "growExpandedEllipsizeCompactOneLine", .growExpandedEllipsizeCompactOneLine))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["expandedRole": .string(expandedRole.rawValue),
            "compactRole": .string(compactRole.rawValue),
            "expandedAlignment": .string(expandedAlignment.rawValue),
            "compactAlignment": .string(compactAlignment.rawValue),
            "expandedInsets64": try expandedInsets64.appearanceWriteV2(),
            "compactInsets64": try compactInsets64.appearanceWriteV2(),
            "minimumExpandedBar64": .uint(UInt64(minimumExpandedBar64)),
            "minimumCompactBar64": .uint(UInt64(minimumCompactBar64)),
            "collapse": .string(collapse.rawValue),
            "titleWrap": .string(titleWrap.rawValue)])
    }
}

private extension UIThemeV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["recipe", "typography", "light", "dark", "stacks", "groupedList", "button", "field", "toggle", "navigation"])
        return Self(recipe: try appearanceConstantV2(f["recipe"]!, "measuredShared2", .measuredShared2),
            typography: try UITypographyV2.appearanceReadV2(f["typography"]!),
            light: try UIPaintsV2.appearanceReadV2(f["light"]!),
            dark: try UIPaintsV2.appearanceReadV2(f["dark"]!),
            stacks: try UIStackMetricsV2.appearanceReadV2(f["stacks"]!),
            groupedList: try UIGroupedListMetricsV2.appearanceReadV2(f["groupedList"]!),
            button: try UIButtonMetricsV2.appearanceReadV2(f["button"]!),
            field: try UIFieldMetricsV2.appearanceReadV2(f["field"]!),
            toggle: try UIToggleMetricsV2.appearanceReadV2(f["toggle"]!),
            navigation: try UINavigationMetricsV2.appearanceReadV2(f["navigation"]!))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["recipe": .string(recipe.rawValue),
            "typography": try typography.appearanceWriteV2(),
            "light": try light.appearanceWriteV2(),
            "dark": try dark.appearanceWriteV2(),
            "stacks": try stacks.appearanceWriteV2(),
            "groupedList": try groupedList.appearanceWriteV2(),
            "button": try button.appearanceWriteV2(),
            "field": try field.appearanceWriteV2(),
            "toggle": try toggle.appearanceWriteV2(),
            "navigation": try navigation.appearanceWriteV2()])
    }
}

private extension UIAppearanceResourceV1 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["id", "kind", "path", "sha256", "bytes", "provenance", "scale", "locale", "direction"])
        return Self(id: try appearanceIDV2(f["id"]!),
            kind: try appearanceEnumV2(f["kind"]!, UIResourceKindV1.self),
            path: try appearancePathV2(f["path"]!),
            sha256: try appearanceSha256V2(f["sha256"]!),
            bytes: UInt32(try f["bytes"]!.number(1, 4194304)),
            provenance: try appearancePrintableV2(f["provenance"]!),
            scale: UInt8(try f["scale"]!.number(1, 4)),
            locale: try appearanceLocaleV2(f["locale"]!),
            direction: try appearanceEnumV2(f["direction"]!, UIResourceDirectionV1.self))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["id": try appearanceStringV2(id, 128),
            "kind": .string(kind.rawValue),
            "path": try appearanceStringV2(path, 256),
            "sha256": try appearanceStringV2(sha256, 64),
            "bytes": .uint(UInt64(bytes)),
            "provenance": try appearanceStringV2(provenance, 512),
            "scale": .uint(UInt64(scale)),
            "locale": try appearanceStringV2(locale, 64),
            "direction": .string(direction.rawValue)])
    }
}

private extension UIFontFaceV1 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["resourceID", "postScriptName", "weight", "style"])
        return Self(resourceID: try appearanceIDV2(f["resourceID"]!),
            postScriptName: try appearanceTextV2(f["postScriptName"]!, 1, 128) { (33...126).contains($0) },
            weight: try appearanceWeightV2(f["weight"]!),
            style: try appearanceEnumV2(f["style"]!, UIFontStyleV1.self))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["resourceID": try appearanceStringV2(resourceID, 128),
            "postScriptName": try appearanceStringV2(postScriptName, 128),
            "weight": .uint(UInt64(weight.rawValue)),
            "style": .string(style.rawValue)])
    }
}

private extension UIInsets64V1 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["top", "leading", "bottom", "trailing"])
        return Self(top: UInt32(try f["top"]!.number(0, 65536)),
            leading: UInt32(try f["leading"]!.number(0, 65536)),
            bottom: UInt32(try f["bottom"]!.number(0, 65536)),
            trailing: UInt32(try f["trailing"]!.number(0, 65536)))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["top": .uint(UInt64(top)),
            "leading": .uint(UInt64(leading)),
            "bottom": .uint(UInt64(bottom)),
            "trailing": .uint(UInt64(trailing))])
    }
}

private extension UISharedTextMetricsV1 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let f = try value.fields(["size64", "weight"])
        return Self(size64: UInt32(try f["size64"]!.number(64, 16384)),
            weight: try appearanceWeightV2(f["weight"]!))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        .object(["size64": .uint(UInt64(size64)),
            "weight": .uint(UInt64(weight.rawValue))])
    }
}

private func appearancePathV2(_ value: AppearanceJSONV2) throws -> String {
    let path = try appearanceTextV2(value, 1, 256) {
        appearanceAlphanumericV2($0) || $0 == 95 || $0 == 46 || $0 == 45 || $0 == 47
    }
    var first = true
    for byte in path.utf8 {
        if byte == 47 {
            guard !first else { throw UIAppearanceErrorV2.shape }
            first = true
        } else {
            guard !first || byte != 46 else { throw UIAppearanceErrorV2.shape }
            first = false
        }
    }
    guard !first else { throw UIAppearanceErrorV2.shape }
    return path
}
private func appearanceLocaleV2(_ value: AppearanceJSONV2) throws -> String {
    let locale = try appearanceTextV2(value, 1, 64) { appearanceAlphanumericV2($0) || $0 == 45 }
    var first = true
    for byte in locale.utf8 {
        if byte == 45 {
            guard !first else { throw UIAppearanceErrorV2.shape }
            first = true
        } else { first = false }
    }
    guard !first else { throw UIAppearanceErrorV2.shape }
    return locale
}
private func appearanceSha256V2(_ value: AppearanceJSONV2) throws -> String {
    try appearanceTextV2(value, 64, 64) { (48...57).contains($0) || (97...102).contains($0) }
}
private func appearanceWeightV2(_ value: AppearanceJSONV2) throws -> UIFontWeightV1 {
    guard let weight = UIFontWeightV1(rawValue: UInt16(try value.number(400, 700))) else {
        throw UIAppearanceErrorV2.number
    }
    return weight
}
private extension UIRGBA8V1 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        let text = try appearanceTextV2(value, 9, 9) { $0 == 35 || (48...57).contains($0) || (65...70).contains($0) }
        let bytes = Array(text.utf8)
        guard bytes[0] == 35, !bytes.dropFirst().contains(35) else { throw UIAppearanceErrorV2.shape }
        func channel(_ offset: Int) -> UInt8 {
            func hex(_ byte: UInt8) -> UInt8 { byte <= 57 ? byte - 48 : byte - 55 }
            return hex(bytes[offset]) * 16 + hex(bytes[offset + 1])
        }
        return Self(red: channel(1), green: channel(3), blue: channel(5), alpha: channel(7))
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        let hex = Array("0123456789ABCDEF".utf8)
        var bytes: [UInt8] = [35]
        for byte in [red, green, blue, alpha] { bytes.append(hex[Int(byte >> 4)]); bytes.append(hex[Int(byte & 15)]) }
        return .string(String(decoding: bytes, as: UTF8.self))
    }
}
private extension UIFontSourceV1 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        guard case let .object(f) = value, let kind = f["kind"] else { throw UIAppearanceErrorV2.shape }
        switch try kind.text() {
        case "systemSans":
            _ = try value.fields(["kind"])
            return .systemSans
        case "bundled":
            _ = try value.fields(["kind", "faces", "fallback"])
            return .bundled(faces: try f["faces"]!.items(1, 16).map { try UIFontFaceV1.appearanceReadV2($0) },
                            fallback: try appearanceEnumV2(f["fallback"]!, UIFontFallbackV1.self))
        default: throw UIAppearanceErrorV2.shape
        }
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        switch self {
        case .systemSans: return .object(["kind": .string("systemSans")])
        case let .bundled(faces, fallback):
            guard (1...16).contains(faces.count) else { throw UIAppearanceErrorV2.fontCatalog }
            return .object(["kind": .string("bundled"), "fallback": .string(fallback.rawValue),
                            "faces": .array(try faces.map { try $0.appearanceWriteV2() })])
        }
    }
}

private extension UIAppearanceConfigurationV2 {
    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {
        guard case let .object(f) = value, let mode = f["mode"] else { throw UIAppearanceErrorV2.shape }
        let parsedMode: UIAppearanceModeV2
        switch try mode.text() {
        case "shared":
            _ = try value.fields(["format", "id", "mode", "theme", "resources"])
            parsedMode = .shared(try UIThemeV2.appearanceReadV2(f["theme"]!))
        case "platformSpecific":
            _ = try value.fields(["format", "id", "mode", "iOS", "android", "reason", "resources"])
            parsedMode = .platformSpecific(iOS: try UIThemeV2.appearanceReadV2(f["iOS"]!),
                android: try UIThemeV2.appearanceReadV2(f["android"]!), reason: try appearancePrintableV2(f["reason"]!))
        default: throw UIAppearanceErrorV2.shape
        }
        guard try f["format"]!.text() == format else { throw UIAppearanceErrorV2.shape }
        return Self(id: try appearanceIDV2(f["id"]!), mode: parsedMode,
            resources: try f["resources"]!.items(0, 64).map { try UIAppearanceResourceV1.appearanceReadV2($0) })
    }
    func appearanceWriteV2() throws -> AppearanceJSONV2 {
        guard resources.count <= 64 else { throw UIAppearanceErrorV2.resourceCatalog }
        var fields: [String: AppearanceJSONV2] = ["format": .string(Self.format),
            "id": try appearanceStringV2(id, 128), "resources": .array(try resources.map { try $0.appearanceWriteV2() })]
        switch mode {
        case let .shared(theme):
            fields["mode"] = .string("shared"); fields["theme"] = try theme.appearanceWriteV2()
        case let .platformSpecific(iOS, android, reason):
            fields["mode"] = .string("platformSpecific")
            fields["iOS"] = try iOS.appearanceWriteV2(); fields["android"] = try android.appearanceWriteV2()
            fields["reason"] = try appearanceStringV2(reason)
        }
        return .object(fields)
    }
}


private func appearanceConstantV2<T>(_ value: AppearanceJSONV2, _ expected: String, _ result: T) throws -> T {
    guard try value.text() == expected else { throw UIAppearanceErrorV2.shape }
    return result
}

private func appearanceSemanticsV2(_ value: UIAppearanceConfigurationV2) throws {
    var ids: Set<String> = [], paths: Set<String> = []
    var total: UInt64 = 0
    var fontCount = 0
    for resource in value.resources {
        guard ids.insert(resource.id).inserted,
              paths.insert(resource.path.lowercased()).inserted,
              resource.provenance.first != " ", resource.provenance.last != " " else {
            throw UIAppearanceErrorV2.resourceCatalog
        }
        let (sum, overflow) = total.addingReportingOverflow(UInt64(resource.bytes))
        guard !overflow, sum <= 16 * 1024 * 1024 else { throw UIAppearanceErrorV2.resourceCatalog }
        total = sum
        if resource.kind == .fontSFNT {
            fontCount += 1
            guard fontCount <= 16, resource.scale == 1, resource.locale == "und",
                  resource.direction == .neutral else { throw UIAppearanceErrorV2.fontCatalog }
        }
    }
    func theme(_ theme: UIThemeV2) throws {
        let p = theme.typography.profiles
        let rows = [p.xs, p.s, p.m, p.l, p.xl, p.xxl, p.xxxl, p.a1, p.a2, p.a3, p.a4, p.a5]
        for (profile, row) in zip(UISharedTextProfileV1.allCases, rows) {
            let metrics = [row.body, row.headline, row.title, row.caption, row.sectionHeader, row.navigationExpanded]
            for (role, metric) in zip(UISharedTextRoleV1.allCases, metrics) {
                guard metric == profile.metrics(for: role) else { throw UIAppearanceErrorV2.unsupportedProfile }
            }
        }
        if case let .bundled(faces, _) = theme.typography.font {
            var pairs: Set<String> = [], normals: Set<UIFontWeightV1> = []
            for face in faces {
                let pair = String(face.weight.rawValue) + ":" + face.style.rawValue
                guard pairs.insert(pair).inserted,
                      let resource = value.resources.first(where: { $0.id == face.resourceID }),
                      resource.kind == .fontSFNT else { throw UIAppearanceErrorV2.fontCatalog }
                if face.style == .normal { normals.insert(face.weight) }
            }
            guard normals.isSuperset(of: [.w400, .w600, .w700]),
                  faces.allSatisfy({ normals.contains($0.weight) }) else { throw UIAppearanceErrorV2.fontCatalog }
        }
        let f = theme.groupedList.profileFloors64
        let floors = [f.xs, f.s, f.m, f.l, f.xl, f.xxl, f.xxxl, f.a1, f.a2, f.a3, f.a4, f.a5]
        guard floors.allSatisfy({ $0 >= theme.toggle.trackHeight64 }),
              zip(floors, floors.dropFirst()).allSatisfy({ $0 <= $1 }),
              theme.navigation.minimumExpandedBar64 >= theme.navigation.minimumCompactBar64 else {
            throw UIAppearanceErrorV2.geometry
        }
        // Fixed switch sizes are already schema-checked. Widen before addition;
        // this expresses the envelope invariant without UInt32 intermediate overflow.
        let toggle = theme.toggle
        guard UInt64(toggle.thumbWidth64) + 2 * UInt64(toggle.thumbInset64) <= UInt64(toggle.trackWidth64),
              UInt64(toggle.thumbHeight64) + 2 * UInt64(toggle.thumbInset64) == UInt64(toggle.trackHeight64) else {
            throw UIAppearanceErrorV2.geometry
        }
        let clear = UIRGBA8V1(red: 0, green: 0, blue: 0, alpha: 0)
        for paint in [theme.light, theme.dark] {
            guard [paint.button.normal, paint.button.destructive, paint.button.cancel].allSatisfy({
                $0.disabled.background == clear
            }), paint.field.disabled.caret == clear, paint.field.disabled.selection == clear,
                paint.field.enabled.outline.width64 == 0, paint.field.disabled.outline.width64 == 0,
                paint.toggle.on.disabled.overlay == clear, paint.toggle.off.disabled.overlay == clear else {
                throw UIAppearanceErrorV2.shape
            }
        }
    }
    switch value.mode {
    case let .shared(shared): try theme(shared)
    case let .platformSpecific(iOS, android, reason):
        guard reason.first != " ", reason.last != " " else { throw UIAppearanceErrorV2.shape }
        try theme(iOS); try theme(android)
    }
}
