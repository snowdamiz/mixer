import Foundation
import Testing
@testable import MixerBuild

private func inventory(_ source: Data, name: String = "Example.swift", _ body: (MigrationReport) throws -> Void) throws {
    let parent = FileManager.default.temporaryDirectory
    let root = parent.appendingPathComponent(UUID().uuidString)
    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: root) }
    let file = root.appendingPathComponent(name)
    try source.write(to: file)
    let digest = try SourceDigest.tree(root)
    let report = try MigrationInspector.inspect(root)
    #expect(report.schema == 1)
    #expect(report.authority == "advisory-only")
    #expect(report.technicalEligibility == "unverified")
    #expect(report.swiftFiles == 1)
    #expect(report.findings.allSatisfy { $0.file == name })
    try body(report)
    #expect(try Data(contentsOf: file) == source)
    #expect(try SourceDigest.tree(root) == digest)
}

@Test func commentsAndStringExamplesNoLongerProduceFindingsOrShiftCRLFLines() throws {
    let source = "// import SwiftUI UnsafeMutablePointer dlopen(\r\nlet text = \"import UIKit UnsafeMutablePointer dlopen(\"\r\nimport SwiftUI\r\nlet p: UnsafeMutablePointer<Int>? = nil\r\n"
    try inventory(Data(source.utf8)) { report in
        #expect(report.findings.map(\.line) == [3, 4])
        #expect(report.findings.map(\.message) == ["Apple SwiftUI import", "Unsafe pointer use"])
        print("CANDIDATE_REPORT=" + String(decoding: try JSONFile.data(report), as: UTF8.self))
    }
}

@Test func nestedCommentsAndAnnotatedWhitespaceImports() throws {
    let source = """
    /* import SwiftUI
       /* import AppKit UnsafeMutablePointer dlopen( */
       import UIKit */
    @preconcurrency import\t\tSwiftUI
    import/* separator /* nested */ */   UIKit
    import struct CoreLocation.CLLocationCoordinate2D
    @testable import StoreKit
    """
    try inventory(Data(source.utf8)) { report in
        #expect(report.findings.map(\.line) == [4, 5, 6, 7])
        #expect(report.findings.map(\.message) == ["Apple SwiftUI import", "UIKit import", "Native location integration", "Native store integration"])
    }
}

@Test func ordinaryRawAndMultilineContentsAreNotCode() throws {
    let source = #####"""
    let a = "import SwiftUI UnsafeMutablePointer dlopen( @objc #if #externalMacro"
    let escaped = "\" import UIKit \\ UnsafeMutablePointer"
    let raw = ##"import AppKit \(UnsafeMutablePointer<Int>.self) \#(dlopen("##
    let multi = """
    import StoreKit
    UnsafeMutablePointer dlopen( @objc #if
    """
    let rawMulti = ##"""
    import CoreLocation
    " UnsafeMutablePointer dlopen( \(import UIKit)
    """##
    """#####
    try inventory(Data(source.utf8)) { report in #expect(report.findings.isEmpty) }
}

@Test func interpolationScansActualCodeAndNestedStrings() throws {
    let source = #####"""
    let a = "text \(UnsafeMutablePointer<Int>.self) import UIKit"
    let b = ##"raw \##(dlopen ("import SwiftUI", 0)) import AppKit"##
    let c = "nested \("inner \(UnsafeMutablePointer<Int>.self)")"
    let d = """
    text
    \(dlopen(
      "UnsafeMutablePointer import UIKit", 0))
    """
    """#####
    try inventory(Data(source.utf8)) { report in
        #expect(report.findings.map(\.line) == [1, 2, 3, 6])
        #expect(report.findings.map(\.message) == ["Unsafe pointer use", "Dynamic loading", "Unsafe pointer use", "Dynamic loading"])
    }
}

@Test func unicodeAndMixedPhysicalNewlinesRetainOriginalPointers() throws {
    let source = "let café東京 = \"🧪 import UIKit\"\r\n/* é\r\nUnsafeMutablePointer */\nimport\r\n  AppKit\rlet p: UnsafeMutablePointer<Int>? = nil\n@objc class C {}\r\n#if os(iOS)\r\n#externalMacro(module: \"UIKit\", type: \"T\")\r\n#endif"
    try inventory(Data(source.utf8), name: "Écran東京.swift") { report in
        #expect(report.findings.map(\.line) == [4, 6, 7, 8, 9])
        #expect(report.findings.map(\.message) == ["macOS AppKit import", "Unsafe pointer use", "Objective-C interoperability", "Conditional compilation", "Compiler macro"])
    }
}

@Test func identifierBoundariesAndRawIdentifiers() throws {
    let source = """
    import SwiftUIExtras
    let UnsafeMutablePointerExample = 0
    let UnsafeMutablePointeré = 0
    let mydlopen = 0
    let `import SwiftUI dlopen( UnsafeMutablePointer` = 0
    let p: `UnsafeMutablePointer`<Int>? = nil
    import `UIKit`
    """
    try inventory(Data(source.utf8)) { report in
        #expect(report.findings.map(\.line) == [6, 7])
        #expect(report.findings.map(\.message) == ["Unsafe pointer use", "UIKit import"])
    }
}

@Test(arguments: ["/* unclosed import UIKit", "let x = \"unfinished UnsafeMutablePointer", "let x = #\"unfinished dlopen(\"", "let x = \"\\(UnsafeMutablePointer<Int>.self", "let x = `unfinished", "let pattern = /import SwiftUI/", "let pattern = #/UnsafeMutablePointer/#", "let quotient = 4 / 2"])
func incompleteOrUnsupportedFormsRequireCompilerReview(_ source: String) throws {
    try inventory(Data(source.utf8)) { report in
        #expect(report.findings.contains { $0.category == "compiler-review" && $0.message == "Incomplete or unsupported lexical form" })
    }
}

@Test func invalidUTF8RequiresCompilerReview() throws {
    try inventory(Data([0xFF, 0x22, 0x0A])) { report in
        #expect(report.findings.count == 1)
        #expect(report.findings.first?.category == "compiler-review")
        #expect(report.findings.first?.line == 1)
    }
}

@Test func existingSizeAndSymlinkBoundsStillReject() throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: root) }
    let file = root.appendingPathComponent("Large.swift")
    try Data(repeating: 32, count: 16 * 1_048_576 + 1).write(to: file)
    #expect(throws: MixerFailure.self) { try MigrationInspector.inspect(root) }
    try FileManager.default.removeItem(at: file)
    let target = root.appendingPathComponent("Actual.swift")
    try Data("import UIKit".utf8).write(to: target)
    try FileManager.default.createSymbolicLink(at: root.appendingPathComponent("Link.swift"), withDestinationURL: target)
    #expect(throws: MixerFailure.self) { try MigrationInspector.inspect(root) }
    #expect(try String(contentsOf: target, encoding: .utf8) == "import UIKit")
}


@Test func longRawDelimiterPayloadAndNearClosersRetainRealImport() throws {
    let hashes = String(repeating: "#", count: 16_384)
    let almost = String(hashes.dropLast())
    let payload = String(repeating: "\"" + almost + " import UIKit UnsafeMutablePointer \\" + almost + "x", count: 64)
    let source = "let text = " + hashes + "\"" + payload + "\"" + hashes + "\r\nimport SwiftUI\r\n"
    #expect(source.utf8.count > 2_000_000)
    try inventory(Data(source.utf8)) { report in
        #expect(report.findings.map(\.line) == [2])
        #expect(report.findings.map(\.message) == ["Apple SwiftUI import"])
    }
}

@Test func maximumSizeRawDelimiterFileIsInventoriedWithoutFalseFindings() throws {
    let limit = 16 * 1_048_576
    let suffix = "\r\nimport UIKit\r\n"
    let hashes = String(repeating: "#", count: (limit - suffix.utf8.count - 2) / 2)
    var source = hashes + "\"\"" + hashes + suffix
    source += String(repeating: " ", count: limit - source.utf8.count)
    #expect(source.utf8.count == limit)
    try inventory(Data(source.utf8)) { report in
        #expect(report.findings.map(\.line) == [2])
        #expect(report.findings.map(\.message) == ["UIKit import"])
    }
}

@Test func incompleteLongRawDelimiterDoesNotInventLaterImports() throws {
    let hashes = String(repeating: "#", count: 131_072)
    let source = "let text = " + hashes + "\"\"\"\nimport UIKit\n\"\"\"" + String(hashes.dropLast()) + "\nimport SwiftUI\n"
    try inventory(Data(source.utf8)) { report in
        #expect(report.findings.count == 1)
        #expect(report.findings.first?.line == 1)
        #expect(report.findings.first?.category == "compiler-review")
    }
}

@Test func hashRunsInCodeDoNotRescanOverlappingSuffixes() throws {
    // This is a lexical inventory, so invalid directive grammar is left to Swift.
    let source = String(repeating: "#", count: 1_048_576) + "if os(iOS)\nimport UIKit\n#endif\n"
    try inventory(Data(source.utf8)) { report in
        #expect(report.findings.map(\.line) == [1, 2])
        #expect(report.findings.map(\.message) == ["Conditional compilation", "UIKit import"])
    }
}

@Test func initialBOMRetainsFirstImportAtLineOne() throws {
    let source = Data("\u{FEFF}import AppKit\n".utf8)
    #expect(SourceDigest.sha256(source) == "9ad155190330482c78c43a3a5bd2b96a5ab4ae51c98dc4c9f3463b47aa96097a")
    try inventory(source) { report in
        #expect(report.findings.map(\.line) == [1])
        #expect(report.findings.map(\.message) == ["macOS AppKit import"])
        print("R756_BOM_FIRST_REPORT=" + String(decoding: try JSONFile.data(report), as: UTF8.self))
    }
}

@Test func initialBOMPreservesFollowingCRLFPhysicalLines() throws {
    let source = Data("\u{FEFF}import AppKit\r\nimport UIKit\r\nlet text = \"import StoreKit\"\r\nimport SwiftUI\r\n".utf8)
    try inventory(source) { report in
        #expect(report.findings.map(\.line) == [1, 2, 4])
        #expect(report.findings.map(\.message) == ["macOS AppKit import", "UIKit import", "Apple SwiftUI import"])
        print("R756_BOM_CRLF_REPORT=" + String(decoding: try JSONFile.data(report), as: UTF8.self))
    }
}

@Test func initialBOMBeforeLiteralPreservesInternalBOMAndSourceBytes() throws {
    let source = Data(("\u{FEFF}\"import AppKit\u{FEFF} import StoreKit\"\r\n"
        + "let UnsafeMutablePointer\u{FEFF} = 0\r\nimport UIKit\r\n").utf8)
    try inventory(source) { report in
        #expect(report.findings.map(\.line) == [3])
        #expect(report.findings.map(\.message) == ["UIKit import"])
        print("R756_BOM_LITERAL_REPORT=" + String(decoding: try JSONFile.data(report), as: UTF8.self))
    }
}
