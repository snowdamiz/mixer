import Foundation

public struct MigrationFinding: Codable, Sendable {
    public var file: String
    public var line: Int
    public var category: String
    public var message: String
    public var remediation: String
}

public struct MigrationReport: Codable, Sendable {
    public var schema = 1
    public var source: String
    public var swiftFiles: Int
    public var findings: [MigrationFinding]
    public var authority = "advisory-only"
    public var technicalEligibility = "unverified"
    public var explanation = "Read-only lexical inventory. This does not type-check source, resolve dependencies, certify sharing, or authorize OTA. Macros and conditional compilation require compiler analysis."
}

public enum MigrationInspector {
    public static func inspect(_ root: URL) throws -> MigrationReport {
        let root = root.resolvingSymlinksInPath().standardizedFileURL
        var findings: [MigrationFinding] = []
        let swift = try SourceDigest.files(in: root).filter { $0.pathExtension == "swift" }
        let rules: [(String, String, String, String)] = [
            ("import SwiftUI", "adaptation-required", "Apple SwiftUI import", "Migrate selected screens to MixerUI; preserve native screens behind explicit adapters."),
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
        for file in swift {
            let data = try Data(contentsOf: file)
            guard data.count <= 16 * 1_048_576 else { throw MixerFailure("import.size", "Swift file exceeds inventory limit: \(file.path)") }
            let relative = String(file.path.dropFirst(root.standardizedFileURL.path.count + 1))
            var inventory = SwiftInventory(data)
            let matches = inventory.scan()
            for match in matches {
                let (_, category, message, remediation) = rules[match.rule]
                findings.append(MigrationFinding(file: relative, line: match.line, category: category, message: message, remediation: remediation))
            }
            if let line = inventory.reviewLine {
                findings.append(MigrationFinding(file: relative, line: line, category: "compiler-review", message: "Incomplete or unsupported lexical form", remediation: "Compile the original source with its target toolchain; this lexical inventory may be incomplete."))
            }
        }
        return MigrationReport(source: root.path, swiftFiles: swift.count, findings: findings)
    }
}

// A bounded inventory scanner, not a Swift parser. Regex literals deliberately
// stop inventory with compiler review because slash/operator disambiguation
// requires grammar context. Conditional branches are inventoried, not evaluated.
private struct SwiftInventory {
    struct Match: Hashable { let rule: Int; let line: Int }
    private struct Token { let text: String; let line: Int; var raw = false }
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
    private var stack: [Context] = [.code(depth: 0, start: 1)]
    private var previous: [Token] = []
    private var matches: Set<Match> = []
    private(set) var reviewLine: Int?

    init(_ data: Data) {
        bytes = Array(data)
        if bytes.starts(with: [0xEF, 0xBB, 0xBF]) { index = 3 }
        if String(data: data, encoding: .utf8) == nil { reviewLine = 1 }
    }

    private func has(_ pattern: [UInt8], at offset: Int? = nil) -> Bool {
        let start = offset ?? index
        return start + pattern.count <= bytes.count && bytes[start..<(start + pattern.count)].elementsEqual(pattern)
    }

    private mutating func advance(_ count: Int = 1) {
        for _ in 0..<count where index < bytes.count {
            if bytes[index] == 13 || (bytes[index] == 10 && (index == 0 || bytes[index - 1] != 13)) { line += 1 }
            index += 1
        }
    }

    private func word(_ byte: UInt8) -> Bool {
        byte >= 128 || (65...90).contains(byte) || (97...122).contains(byte) || (48...57).contains(byte) || byte == 95 || byte == 36
    }

    private mutating func emit(_ token: Token) {
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
            else if kinds.contains(last.text), !last.raw, previous.count == 2, previous[0].text == "import", !previous[0].raw { importToken = previous[0] }
            else { importToken = nil }
            if let importToken, let rule = ["SwiftUI": 0, "UIKit": 1, "AppKit": 2, "StoreKit": 3, "CoreLocation": 4][token.text] {
                matches.insert(Match(rule: rule, line: importToken.line))
            }
        }
        previous.append(token)
        if previous.count > 2 { previous.removeFirst() }
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
                    stack.append(.string(StringContext(hashes: hashes, quotes: quotes, start: line)))
                    previous.removeAll(); advance(hashes + quotes); continue
                }
                // Bare and extended regex literals, as well as ambiguous slash
                // operators, retain an explicit incomplete-inventory warning.
                if byte == 47 || (hashes > 0 && has([47], at: index + hashes)) { reviewLine = line; continue }
                if hashes > 0 {
                    // Only the final hash can precede an inventoried directive.
                    // Consume the run once instead of rescanning each suffix.
                    emit(Token(text: "#", line: line)); advance(hashes); continue
                }
                if byte == 96 {
                    let begin = index; let tokenLine = line
                    advance()
                    while index < bytes.count && ![96, 10, 13].contains(bytes[index]) { advance() }
                    guard index < bytes.count && bytes[index] == 96 else { reviewLine = tokenLine; continue }
                    emit(Token(text: String(decoding: bytes[(begin + 1)..<index], as: UTF8.self), line: tokenLine, raw: true))
                    advance(); continue
                }
                if word(byte) {
                    let begin = index; let tokenLine = line
                    while index < bytes.count && word(bytes[index]) { advance() }
                    emit(Token(text: String(decoding: bytes[begin..<index], as: UTF8.self), line: tokenLine)); continue
                }
                if depth > 0 {
                    if byte == 40 { stack[stack.count - 1] = .code(depth: depth + 1, start: start) }
                    if byte == 41 {
                        if depth == 1 { stack.removeLast(); previous.removeAll(); advance(); continue }
                        stack[stack.count - 1] = .code(depth: depth - 1, start: start)
                    }
                }
                emit(Token(text: String(decoding: [byte], as: UTF8.self), line: line)); advance()
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
        return matches.sorted { $0.line == $1.line ? $0.rule < $1.rule : $0.line < $1.line }
    }
}

public struct ReleaseAssessment: Codable, Sendable {
    public var schema = 1
    public var application: String
    public var platforms: [String]
    public var sourceDigest: String
    public var sdkDigest: String
    public var technicalEligibility = "blocked"
    public var policyAssessment = "pending-project-review"
    public var publicationAllowed = false
    public var blockers = [
        "Native and full Swift guest outputs have not been compiled and qualified for both targets.",
        "Transitive compiler/capability/UI/state compatibility inventory is not complete.",
        "Signed per-platform artifacts and installed-runtime receipts are required.",
        "Fallback and previous-healthy state compatibility tests are required."
    ]
    public static func inspect(_ root: URL) throws -> Self {
        let config = try ApplicationConfiguration.load(root)
        let lock = try ProjectBuild.verifyLock(root: root)
        return Self(application: config.application, platforms: config.targets, sourceDigest: try SourceDigest.tree(root), sdkDigest: lock.sdkDigest)
    }
}
