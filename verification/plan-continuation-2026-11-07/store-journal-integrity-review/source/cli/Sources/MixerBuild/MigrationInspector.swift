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
            for (index, line) in String(decoding: data, as: UTF8.self).components(separatedBy: .newlines).enumerated() {
                for (needle, category, message, remediation) in rules where line.contains(needle) {
                    findings.append(MigrationFinding(file: relative, line: index + 1, category: category, message: message, remediation: remediation))
                }
            }
        }
        return MigrationReport(source: root.path, swiftFiles: swift.count, findings: findings)
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
