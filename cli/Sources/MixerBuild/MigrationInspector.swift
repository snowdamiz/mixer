import Foundation

public struct MigrationFinding: Codable, Sendable {
    public var file: String
    public var line: Int
    public var category: String
    public var message: String
    public var remediation: String
    public var column: Int?
    public var symbol: String?
}

public struct MigrationReport: Codable, Sendable {
    public var schema = 1
    public var source: String
    public var swiftFiles: Int
    public var findings: [MigrationFinding]
    public var authority = "advisory-only"
    public var technicalEligibility = "unverified"
    public var swiftPackage: MigrationSwiftPackage?
    public var swiftUISubset: MigrationSwiftUISubset?
    public var explanation = "Read-only lexical inventory. This does not type-check source, resolve dependencies, certify sharing, or authorize OTA. Macros and conditional compilation require compiler analysis."
}

public struct MigrationSwiftUISubset: Codable, Sendable {
    public let scopedImportCounts: [String: Int]
    public var explanation = "Counts cover explicit scoped import declarations for compiler-checked gaps in MixerSwiftUI across inspected Swift files. Locations point to the module token using physical lines and UTF-8 byte columns. The counts exclude incomplete scans, files with conditional compilation or UIKit or AppKit import hints, and known SwiftUI module ambiguities. Expression uses, overloads, and target portability require compiler review."
}

public enum MigrationInspector {
    public static func inspect(_ root: URL) throws -> MigrationReport {
        try inspect(root, swiftPMDescription: nil)
    }

    public static func inspect(_ root: URL, swiftPMDescription: URL?) throws -> MigrationReport {
        let root = root.resolvingSymlinksInPath().standardizedFileURL
        var findings: [MigrationFinding] = []
        var scopedImportCounts: [String: Int] = [:]
        var sawSwiftUI = false
        let swift = try SourceDigest.files(in: root).filter { $0.pathExtension == "swift" }
        let relativePaths = swift.map { String($0.path.dropFirst(root.path.count + 1)) }
        var package = try swiftPMDescription.map {
            try SwiftPackageInventory(description: $0, root: root, swiftFiles: swift, relativePaths: relativePaths)
        }
        let rules: [(String, String, String, String)] = [
            ("import SwiftUI", "compiler-review", "SwiftUI import", "Type-check the shared feature against MixerSwiftUI and Apple SwiftUI. Keep Apple-only screens in the Apple target."),
            ("import UIKit", "platform-specific", "UIKit import", "Keep UIKit code in an Apple host capability with an Android implementation."),
            ("import AppKit", "unsupported-mobile", "macOS AppKit import", "Replace desktop UI with a supported mobile surface."),
            ("import StoreKit", "native-capability", "Native store integration", "Use a versioned purchases capability; new native code requires a store build."),
            ("import CoreLocation", "native-capability", "Native location integration", "Declare foreground location capability and platform permission metadata."),
            ("UnsafeMutablePointer", "native-only-review", "Unsafe pointer use", "Keep pointers within the host; exchange bounded values or opaque generation-checked handles."),
            ("dlopen(", "unsupported-guest", "Dynamic loading", "Remove dynamic loading from guest code; use an installed host capability."),
            ("@objc", "native-only-review", "Objective-C interoperability", "Keep Objective-C interaction in the Apple adapter."),
            ("#if", "compiler-review", "Conditional compilation", "Compile and compare each target's complete dependency graph."),
            ("#externalMacro", "compiler-review", "Compiler macro", "Inventory expanded output and type-check each native and guest target.")
        ]
        for (file, relative) in zip(swift, relativePaths) {
            let data = try Data(contentsOf: file)
            guard data.count <= 16 * 1_048_576 else { throw MixerFailure("import.size", "Swift file exceeds inventory limit: \(file.path)") }
            let target = package?.target(for: relative)
            let isDescribedSwiftUIModule = target.flatMap { package?.moduleSpelling(for: $0) } == "SwiftUI"
            var inventory = SwiftInventory(data, importTargets: target.flatMap { package?.importTargets(for: $0) })
            let matches = inventory.scan()
            sawSwiftUI = sawSwiftUI || matches.contains { $0.rule == 0 }
            if let target { package?.recordImports(inventory.localImports, file: relative, target: target) }
            var fileFindings: [MigrationFinding] = []
            for match in matches {
                var (_, category, message, remediation) = rules[match.rule]
                if let spelling = inventory.ambiguousImports[match] {
                    category = "compiler-review"
                    message = "Ambiguous \(spelling) import matches a declared local dependency and a framework"
                    remediation = "Verify which module the original target toolchain imports before choosing a migration."
                } else if match.rule == 0 && isDescribedSwiftUIModule {
                    message = "SwiftUI import in a target with the same module spelling"
                    remediation = "Verify which module the original target toolchain imports before choosing a migration."
                }
                fileFindings.append(MigrationFinding(file: relative, line: match.line, category: category, message: message, remediation: remediation))
            }
            if let line = inventory.reviewLine {
                fileFindings.append(MigrationFinding(file: relative, line: line, category: "compiler-review", message: "Incomplete or unsupported lexical form", remediation: "Compile the original source with its target toolchain; this lexical inventory may be incomplete."))
            }
            if !inventory.swiftUIGapImports.isEmpty, inventory.reviewLine == nil,
               !matches.contains(where: { $0.rule == 1 || $0.rule == 2 || $0.rule == 8 }),
               !inventory.ambiguousImports.values.contains("SwiftUI"),
               !isDescribedSwiftUIModule {
                for scopedImport in inventory.swiftUIGapImports {
                    let symbol = "SwiftUI.\(scopedImport.symbol.rawValue)"
                    scopedImportCounts[symbol, default: 0] += 1
                    fileFindings.append(MigrationFinding(
                        file: relative, line: scopedImport.line, category: "swiftui-subset-gap",
                        message: "\(symbol) is missing from the MixerSwiftUI subset",
                        remediation: "Replace this scoped import and its uses when sharing the feature, or keep the feature in the Apple target.",
                        column: scopedImport.column, symbol: symbol
                    ))
                }
                fileFindings.sort {
                    ($0.line, $0.column ?? 0) < ($1.line, $1.column ?? 0)
                }
            }
            findings.append(contentsOf: fileFindings)
        }
        return MigrationReport(source: root.path, swiftFiles: swift.count, findings: findings,
                               swiftPackage: package?.report(findings: findings),
                               swiftUISubset: sawSwiftUI ? MigrationSwiftUISubset(scopedImportCounts: scopedImportCounts) : nil)
    }
}

// Selective imports in this inventory compile with Apple SwiftUI but fail at
// the imported declaration with the MixerSwiftUI alias in test_swiftui_import.py.
enum SwiftUISubsetGap: String, CaseIterable {
    case navigationStack = "NavigationStack"
    case scrollView = "ScrollView"
}

// A bounded inventory scanner, not a Swift parser. Regex literals deliberately
// stop inventory with compiler review because slash/operator disambiguation
// requires grammar context. Conditional branches are inventoried, not evaluated.
private struct SwiftInventory {
    struct Match: Hashable { let rule: Int; let line: Int }
    struct ScopedImport {
        let symbol: SwiftUISubsetGap
        let line: Int
        let column: Int
    }
    private struct Token {
        let text: String
        let line: Int
        let column: Int
        let raw: Bool
        let startsFileScopeImport: Bool
    }
    // Immutable reference ownership avoids copying delimiter storage when the
    // context is inspected or suspended around interpolation. Each delimiter is
    // allocated once at the opening string, then released with its context.
    private final class StringContext {
        let close: [UInt8]
        let escape: [UInt8]
        let quotes: Int
        let start: Int

        init(hashes: Int, quotes: Int, start: Int) {
            close = Array(repeating: 34, count: quotes) + Array(repeating: 35, count: hashes)
            escape = [92] + Array(repeating: 35, count: hashes)
            self.quotes = quotes
            self.start = start
        }
    }
    private enum Context {
        case code(depth: Int, start: Int)
        case string(StringContext)
        case block(depth: Int, start: Int)
        case comment
    }
    private let bytes: [UInt8]
    private var index = 0
    private var line = 1
    private var lineStart = 0
    private var braces = 0
    private var stack: [Context] = [.code(depth: 0, start: 1)]
    private var previous: [Token] = []
    private var matches: Set<Match> = []
    private let importTargets: [Data: SwiftPackageInventory.ImportTarget]?
    private(set) var localImports: [String: Int] = [:]
    private(set) var ambiguousImports: [Match: String] = [:]
    private(set) var reviewLine: Int?
    private(set) var swiftUIGapImports: [ScopedImport] = []

    init(_ data: Data, importTargets: [Data: SwiftPackageInventory.ImportTarget]? = nil) {
        bytes = Array(data)
        self.importTargets = importTargets
        if bytes.starts(with: [0xEF, 0xBB, 0xBF]) { index = 3 }
        if String(data: data, encoding: .utf8) == nil { reviewLine = 1 }
    }

    private func has(_ pattern: [UInt8], at offset: Int? = nil) -> Bool {
        let start = offset ?? index
        return start + pattern.count <= bytes.count && bytes[start..<(start + pattern.count)].elementsEqual(pattern)
    }

    private mutating func advance(_ count: Int = 1) {
        for _ in 0..<count where index < bytes.count {
            if bytes[index] == 13 || bytes[index] == 10 {
                if bytes[index] == 13 || index == 0 || bytes[index - 1] != 13 { line += 1 }
                lineStart = index + 1
            }
            index += 1
        }
    }

    private func word(_ byte: UInt8) -> Bool {
        byte >= 128 || (65...90).contains(byte) || (97...122).contains(byte) || (48...57).contains(byte) || byte == 95 || byte == 36
    }

    private mutating func finishSwiftUIGapImport(before next: Token? = nil) {
        guard previous.count == 5, previous[0].startsFileScopeImport,
              previous[1].text == "struct", !previous[1].raw,
              previous[2].text == "SwiftUI", previous[3].text == ".", !previous[3].raw,
              let symbol = SwiftUISubsetGap(rawValue: previous[4].text) else { return }
        let declaration = previous[4]
        if let next {
            let endsWithSemicolon = !next.raw && next.text == ";"
            let nextLineStartsStatement = next.line > declaration.line && (next.raw || next.text != ".")
            guard endsWithSemicolon || nextLineStartsStatement else { return }
        }
        let module = previous[2]
        swiftUIGapImports.append(ScopedImport(symbol: symbol, line: module.line, column: module.column))
    }

    private mutating func emit(_ text: String, raw: Bool = false, from start: Int? = nil) {
        let startsFileScopeImport = text == "import" && !raw && stack.count == 1 && braces == 0 && previous.last?.text != "."
        let token = Token(text: text, line: line, column: (start ?? index) - lineStart + 1,
                          raw: raw, startsFileScopeImport: startsFileScopeImport)
        finishSwiftUIGapImport(before: token)
        if token.text == "UnsafeMutablePointer" { matches.insert(Match(rule: 5, line: token.line)) }
        if let last = previous.last {
            if token.text == "(", last.text == "dlopen" { matches.insert(Match(rule: 6, line: last.line)) }
            if last.text == "@", token.text == "objc", !token.raw { matches.insert(Match(rule: 7, line: last.line)) }
            if last.text == "#", !token.raw {
                if token.text == "if" { matches.insert(Match(rule: 8, line: last.line)) }
                if token.text == "externalMacro" { matches.insert(Match(rule: 9, line: last.line)) }
            }
            let kinds: Set<String> = ["typealias", "struct", "class", "enum", "protocol", "let", "var", "func"]
            let importToken: Token?
            if last.text == "import", !last.raw { importToken = last }
            else if kinds.contains(last.text), !last.raw, let keyword = previous.dropLast().last,
                    keyword.text == "import", !keyword.raw { importToken = keyword }
            else { importToken = nil }
            if let importToken {
                let startsScopedImport = last.text == "import" && !token.raw && kinds.contains(token.text)
                let target = stack.count == 1 && !startsScopedImport ? importTargets?[Data(token.text.utf8)] : nil
                if let rule = ["SwiftUI": 0, "UIKit": 1, "AppKit": 2, "StoreKit": 3, "CoreLocation": 4][token.text] {
                    let match = Match(rule: rule, line: importToken.line)
                    matches.insert(match)
                    if target != nil { ambiguousImports[match] = token.text }
                }
                if case let .locatable(module)? = target, localImports[module] == nil {
                    localImports[module] = importToken.line
                }
            }
        }
        if stack.count == 1 && !raw {
            if text == "{" { braces += 1 }
            if text == "}" { braces -= 1 }
        }
        previous.append(token)
        if previous.count > 5 { previous.removeFirst() }
    }

    mutating func scan() -> [Match] {
        while index < bytes.count && reviewLine == nil {
            guard stack.count <= 256 else { reviewLine = line; break }
            switch stack[stack.count - 1] {
            case .comment:
                if bytes[index] == 10 || bytes[index] == 13 { stack.removeLast() }
                else { advance() }
            case .block(let depth, let start):
                if has([47, 42]) {
                    guard depth < 256 else { reviewLine = start; break }
                    stack[stack.count - 1] = .block(depth: depth + 1, start: start); advance(2)
                } else if has([42, 47]) {
                    if depth == 1 { stack.removeLast() }
                    else { stack[stack.count - 1] = .block(depth: depth - 1, start: start) }
                    advance(2)
                } else { advance() }
            case .string(let context):
                if bytes[index] == 34 && has(context.close) {
                    advance(context.close.count); stack.removeLast(); previous.removeAll()
                } else if bytes[index] == 92 && has(context.escape) {
                    advance(context.escape.count)
                    if has([40]) {
                        advance(); previous.removeAll(); stack.append(.code(depth: 1, start: line))
                    } else { advance() }
                } else if context.quotes == 1 && (bytes[index] == 10 || bytes[index] == 13) {
                    reviewLine = context.start
                } else { advance() }
            case .code(let depth, let start):
                let byte = bytes[index]
                if [0, 9, 10, 11, 12, 13, 32].contains(byte) { advance(); continue }
                if has([47, 47]) { stack.append(.comment); advance(2); continue }
                if has([47, 42]) { stack.append(.block(depth: 1, start: line)); advance(2); continue }
                if has([42, 47]) { reviewLine = line; continue }
                var hashes = 0
                if byte == 35 {
                    while index + hashes < bytes.count && bytes[index + hashes] == 35 { hashes += 1 }
                }
                if has([34], at: index + hashes) {
                    let quotes = has([34, 34, 34], at: index + hashes) ? 3 : 1
                    if line > (previous.last?.line ?? line) { finishSwiftUIGapImport() }
                    stack.append(.string(StringContext(hashes: hashes, quotes: quotes, start: line)))
                    previous.removeAll(); advance(hashes + quotes); continue
                }
                // Bare and extended regex literals, as well as ambiguous slash
                // operators, retain an explicit incomplete-inventory warning.
                if byte == 47 || (hashes > 0 && has([47], at: index + hashes)) { reviewLine = line; continue }
                if hashes > 0 {
                    // Only the final hash can precede an inventoried directive.
                    // Consume the run once instead of rescanning each suffix.
                    emit("#"); advance(hashes); continue
                }
                if byte == 96 {
                    let begin = index; let tokenLine = line
                    advance()
                    while index < bytes.count && ![96, 10, 13].contains(bytes[index]) { advance() }
                    guard index < bytes.count && bytes[index] == 96 else { reviewLine = tokenLine; continue }
                    emit(String(decoding: bytes[(begin + 1)..<index], as: UTF8.self), raw: true, from: begin)
                    advance(); continue
                }
                if word(byte) {
                    let begin = index
                    while index < bytes.count && word(bytes[index]) { advance() }
                    emit(String(decoding: bytes[begin..<index], as: UTF8.self), from: begin); continue
                }
                if depth > 0 {
                    if byte == 40 { stack[stack.count - 1] = .code(depth: depth + 1, start: start) }
                    if byte == 41 {
                        if depth == 1 { stack.removeLast(); previous.removeAll(); advance(); continue }
                        stack[stack.count - 1] = .code(depth: depth - 1, start: start)
                    }
                }
                emit(String(decoding: [byte], as: UTF8.self)); advance()
            }
        }
        if reviewLine == nil {
            for context in stack.reversed() {
                switch context {
                case .string(let context): reviewLine = context.start
                case .block(_, let start): reviewLine = start
                case .code(let depth, let start) where depth > 0: reviewLine = start
                default: continue
                }
                break
            }
        }
        finishSwiftUIGapImport()
        return matches.sorted { $0.line == $1.line ? $0.rule < $1.rule : $0.line < $1.line }
    }
}
