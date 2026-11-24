import Foundation
import Testing
@testable import MixerBuild

private struct DescriptionTarget: Encodable {
    let name: String
    let c99name: String
    let path: String
    let sources: [String]
    let target_dependencies: [String]
    var module_type = "SwiftTarget"
    var type = "library"
}

private func withDescription(
    files: [String: String],
    _ body: (URL, URL) throws -> Void
) throws {
    let fm = FileManager.default
    let directory = fm.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    let root = directory.appendingPathComponent("Package")
    try fm.createDirectory(at: root, withIntermediateDirectories: true)
    defer { try? fm.removeItem(at: directory) }
    for (relative, source) in files {
        let file = root.appendingPathComponent(relative)
        try fm.createDirectory(at: file.deletingLastPathComponent(), withIntermediateDirectories: true)
        try Data(source.utf8).write(to: file)
    }
    try body(root, directory.appendingPathComponent("description.json"))
}

private func writeDescription(_ file: URL, root: URL, targets: [DescriptionTarget]) throws {
    struct Description: Encodable {
        let path: String
        let targets: [DescriptionTarget]
    }
    try JSONFile.write(Description(path: root.path, targets: targets), to: file)
}

@Test func swiftPMDescriptionUsesExplicitEdgesAndOnlyAssociatedCompileSources() throws {
    try withDescription(files: [
        "Sources/Desktop/Compiled.swift": "import AppKit",
        "Sources/Desktop/Templates/Resource.swift": "import StoreKit",
        "Sources/Desktop_Kit/Decoy.swift": "import UIKit",
        "Sources/Front/Front.swift": "// import Desktop_Kit\nimport struct Desktop_Kit.Widget",
        "Run/main.swift": "print(\"entry\")",
        "Solo/Solo.swift": "#if false\nimport Desktop_Kit\n#endif",
        "Package.swift": "#error(\"never execute this manifest\")",
    ]) { root, description in
        try writeDescription(description, root: root, targets: [
            .init(name: "Desktop-Kit", c99name: "Desktop_Kit", path: "Sources/Desktop", sources: ["Compiled.swift"], target_dependencies: []),
            .init(name: "Front", c99name: "Front", path: "Sources/Front", sources: ["Front.swift"], target_dependencies: ["Desktop-Kit"]),
            .init(name: "Entry", c99name: "Entry", path: ".", sources: ["Run/main.swift"], target_dependencies: ["Front"]),
            .init(name: "Solo", c99name: "Solo", path: ".", sources: ["Solo/Solo.swift"], target_dependencies: []),
        ])
        let legacy = try MigrationInspector.inspect(root)
        let report = try MigrationInspector.inspect(root, swiftPMDescription: description)
        let package = try #require(report.swiftPackage)
        let modules = Dictionary(uniqueKeysWithValues: package.modules.map { ($0.name, $0) })
        let desktop = try #require(modules["Desktop-Kit"])
        let front = try #require(modules["Front"])
        let entry = try #require(modules["Entry"])

        #expect(try JSONFile.data(legacy).range(of: Data("\"swiftPackage\"".utf8)) == nil)
        #expect(try JSONFile.data(legacy.findings) == JSONFile.data(report.findings))
        #expect(report.authority == "advisory-only")
        #expect(report.technicalEligibility == "unverified")
        #expect(package.unassignedSwiftFiles == ["Package.swift", "Sources/Desktop/Templates/Resource.swift", "Sources/Desktop_Kit/Decoy.swift"])
        #expect(desktop.swiftFiles == ["Sources/Desktop/Compiled.swift"])
        #expect(desktop.sourceClassification == .unsupported)
        #expect(front.localDependencies.first?.importSpelling == "Desktop_Kit")
        #expect(front.localDependencies.first?.line == 2)
        #expect(front.dependencyCauses.first?.dependencyDepth == 1)
        #expect(entry.dependencyCauses.count == 1)
        #expect(entry.dependencyCauses.first?.via.module == "Front")
        #expect(entry.dependencyCauses.first?.via.line == nil)
        #expect(entry.dependencyCauses.first?.dependencyDepth == 2)
        #expect(entry.dependencyCauses.first?.originModule == "Desktop-Kit")
        #expect(entry.dependencyCauses.first?.finding.file == "Sources/Desktop/Compiled.swift")
        #expect(modules["Solo"]?.localDependencies.isEmpty == true)
        #expect(modules["Solo"]?.dependencyCauses.isEmpty == true)
    }
}

@Test func swiftPMDescriptionDoesNotAssociatePartialOrSkippedSources() throws {
    try withDescription(files: ["Good.swift": "import AppKit", "Front.swift": "import Desktop", ".build/Skipped.swift": "import UIKit"]) { root, description in
        // The legacy scan skips this directory. A graph path cannot use it to borrow an inspected file.
        try FileManager.default.createSymbolicLink(
            at: root.appendingPathComponent(".build/Link.swift"), withDestinationURL: root.appendingPathComponent("Good.swift")
        )
        for missing in ["Missing.swift", ".build/Skipped.swift", ".build/Link.swift"] {
            try writeDescription(description, root: root, targets: [
                .init(name: "Desktop", c99name: "Desktop", path: ".", sources: ["Good.swift", missing], target_dependencies: []),
                .init(name: "Front", c99name: "Front", path: ".", sources: ["Front.swift"], target_dependencies: ["Desktop"]),
            ])
            let report = try MigrationInspector.inspect(root, swiftPMDescription: description)
            let package = try #require(report.swiftPackage)
            let desktop = try #require(package.modules.first)
            let front = try #require(package.modules.last)
            #expect(desktop.sourceAssociation == .unverifiedSources)
            #expect(desktop.sourceClassification == nil)
            #expect(desktop.swiftFiles.isEmpty)
            #expect(desktop.findings.isEmpty)
            #expect(front.localDependencies.first?.line == nil)
            #expect(front.dependencyCauses.isEmpty)
            #expect(package.unassignedSwiftFiles == ["Good.swift"])
        }
    }
}

@Test func swiftPMDescriptionRejectsInvalidRootsPathsEdgesAndInputSize() throws {
    try withDescription(files: ["Good.swift": "import AppKit"]) { root, description in
        let good = DescriptionTarget(name: "Good", c99name: "Good", path: ".", sources: ["Good.swift"], target_dependencies: [])
        let invalidTargets = [
            [good, good],
            [good, .init(name: "Other", c99name: "Other", path: ".", sources: ["Good.swift"], target_dependencies: [])],
            [.init(name: "Good", c99name: "Good", path: ".", sources: ["../Good.swift"], target_dependencies: [])],
            [.init(name: "Good", c99name: "Good", path: "/outside", sources: ["Good.swift"], target_dependencies: [])],
            [.init(name: "Good", c99name: "Good", path: ".", sources: ["Good.swift"], target_dependencies: ["Missing"])],
            [.init(name: "Good", c99name: "Good", path: ".", sources: ["Good.swift"], target_dependencies: ["Good"])],
        ]
        func rejectsDescription() {
            #expect(throws: MixerFailure.self) { try MigrationInspector.inspect(root, swiftPMDescription: description) }
        }
        for targets in invalidTargets {
            try writeDescription(description, root: root, targets: targets)
            rejectsDescription()
        }
        try writeDescription(description, root: root.deletingLastPathComponent(), targets: [good])
        rejectsDescription()
        try Data("{}".utf8).write(to: description)
        rejectsDescription()
        try Data(repeating: 32, count: 4 * 1_048_576 + 1).write(to: description)
        rejectsDescription()
        #expect(throws: MixerFailure.self) { try MigrationInspector.inspect(root, swiftPMDescription: root) }
    }
}

@Test func swiftPMDescriptionMarksFrameworkSpellingSharedWithDeclaredDependency() throws {
    try withDescription(files: [
        "Local.swift": "public struct Widget {}",
        "Bridge.swift": """
        import AppKit; import UIKit
        import struct
            AppKit.Widget
        """,
        "Desktop.swift": "import AppKit",
        "Copied.swift": "import AppKit",
    ]) { root, description in
        let bridge = DescriptionTarget(name: "Bridge", c99name: "Bridge", path: ".", sources: ["Bridge.swift"], target_dependencies: ["Local-Desktop"])
        let desktop = DescriptionTarget(name: "Desktop", c99name: "Desktop", path: ".", sources: ["Desktop.swift"], target_dependencies: [])
        let alias = DescriptionTarget(name: "Local-Desktop", c99name: "AppKit", path: ".", sources: ["Local.swift"], target_dependencies: [])
        let unverified = DescriptionTarget(name: "Local-Desktop", c99name: "AppKit", path: ".", sources: ["Local.swift", "Missing.swift"], target_dependencies: [])
        let duplicate = DescriptionTarget(name: "Other", c99name: "AppKit", path: ".", sources: ["Other.swift"], target_dependencies: [])
        let plain = try MigrationInspector.inspect(root)
        #expect(plain.findings.filter { $0.file == "Bridge.swift" && $0.category == "unsupported-mobile" }.map(\.line) == [1, 2])

        for (targets, located) in [([alias], true), ([unverified], false), ([alias, duplicate], false)] {
            try writeDescription(description, root: root, targets: [bridge, desktop] + targets)
            let report = try MigrationInspector.inspect(root, swiftPMDescription: description)
            let package = try #require(report.swiftPackage)
            let bridge = try #require(package.modules.first { $0.name == "Bridge" })
            let edge = try #require(bridge.localDependencies.first)
            #expect(edge.module == "Local-Desktop")
            #expect(edge.importSpelling == (located ? "AppKit" : nil))
            #expect(edge.line == (located ? 1 : nil))
            #expect(bridge.sourceClassification == .platformSpecific)
            #expect(bridge.findings.filter { $0.category == "compiler-review" }.map(\.line) == [1, 2])
            #expect(bridge.findings.filter { $0.category == "compiler-review" }.allSatisfy { $0.message.contains("AppKit") })
            #expect(bridge.findings.count == 3)
            #expect(report.findings.filter { $0.category == "unsupported-mobile" }.map(\.file) == ["Copied.swift", "Desktop.swift"])
        }
    }
}

@Test func swiftPMDescriptionFindsDistinctPositiveDepthWitnessThroughCyclesAndTies() throws {
    let graph = [
        "AOrigin": ["Join"],
        "Entry": ["Right", "Left"],
        "IsolatedOrigin": ["Relay"],
        "Join": ["AOrigin", "ZOrigin", "YOrigin"],
        "Left": ["Join"],
        "Relay": ["IsolatedOrigin"],
        "Right": ["Join"],
        "YOrigin": [],
        "ZOrigin": [],
    ]
    let originNames: Set<String> = ["AOrigin", "IsolatedOrigin", "YOrigin", "ZOrigin"]
    let files = Dictionary(uniqueKeysWithValues: graph.keys.map { name in
        ("\(name).swift", originNames.contains(name) ? "import AppKit" : "import Foundation")
    })
    try withDescription(files: files) { root, description in
        let targets = graph.keys.sorted().reversed().map {
            DescriptionTarget(name: $0, c99name: $0, path: ".", sources: ["\($0).swift"], target_dependencies: graph[$0, default: []])
        }
        try writeDescription(description, root: root, targets: targets)
        let report = try MigrationInspector.inspect(root, swiftPMDescription: description)
        let package = try #require(report.swiftPackage)
        let modules = Dictionary(uniqueKeysWithValues: package.modules.map { ($0.name, $0) })
        let origin = try #require(modules["AOrigin"])
        #expect(origin.sourceClassification == .unsupported)
        #expect(origin.findings.count == 1)
        #expect(origin.dependencyCauses.map(\.originModule) == ["YOrigin"])
        #expect(origin.dependencyCauses.first?.dependencyDepth == 2)
        #expect(origin.dependencyCauses.first?.via.module == "Join")
        #expect(modules["IsolatedOrigin"]?.dependencyCauses.isEmpty == true)
        #expect(modules["Relay"]?.dependencyCauses.first?.originModule == "IsolatedOrigin")
        #expect(modules["Entry"]?.sourceClassification == .noSourceHints)
        #expect(modules["Entry"]?.dependencyCauses.map(\.originModule) == ["AOrigin"])
        #expect(modules["Entry"]?.dependencyCauses.first?.dependencyDepth == 3)
        #expect(modules["Entry"]?.dependencyCauses.first?.via.module == "Left")
    }
}

@Test func scopedSwiftUIImportsRemainAmbiguousForLocalModuleSpellings() throws {
    try withDescription(files: [
        "Local.swift": "import struct SwiftUI.ScrollView",
        "Shared.swift": "import struct SwiftUI.ScrollView",
    ]) { root, description in
        try writeDescription(description, root: root, targets: [
            .init(name: "Local", c99name: "SwiftUI", path: ".", sources: ["Local.swift"], target_dependencies: []),
            .init(name: "Shared", c99name: "Shared", path: ".", sources: ["Shared.swift"], target_dependencies: ["Local"]),
        ])
        let report = try MigrationInspector.inspect(root, swiftPMDescription: description)
        #expect(report.swiftUISubset?.scopedImportCounts == [:])
        #expect(report.findings.map(\.category) == ["compiler-review", "compiler-review"])
        #expect(report.findings.last?.message.contains("Ambiguous SwiftUI import") == true)
    }
}
