import Darwin
import Foundation

public struct MigrationSwiftPackage: Codable, Sendable {
    public var basis = "supplied-swiftpm-description"
    public var moduleGraph = "advisory"
    public var explanation = "Target membership and dependency edges come from the supplied SwiftPM description. The importer checks file associations but cannot establish graph provenance, freshness, or platform conditions. Causes follow described edges between associated Swift targets to the nearest finding of each class. Import locations are lexical hints. Product dependencies and other target kinds are outside this traversal."
    public let modules: [MigrationModule]
    public let unassignedSwiftFiles: [String]
}

public struct MigrationModule: Codable, Sendable {
    public enum Classification: String, Codable, Sendable, CaseIterable {
        case unsupported
        case platformSpecific = "platform-specific"
        case nativePluginReview = "native-plugin-review"
        case sharedAfterAPIAdaptation = "shared-after-api-adaptation"
        case compilerReview = "compiler-review"
        case noSourceHints = "no-source-hints"

        fileprivate init(category: String) {
            switch category {
            case "unsupported-mobile", "unsupported-guest": self = .unsupported
            case "platform-specific": self = .platformSpecific
            case "native-capability", "native-only-review": self = .nativePluginReview
            case "adaptation-required": self = .sharedAfterAPIAdaptation
            default: self = .compilerReview
            }
        }
    }

    public enum SourceAssociation: String, Codable, Sendable {
        case associated
        case unsupportedTarget = "unsupported-target"
        case unverifiedSources = "unverified-sources"
    }

    public struct Dependency: Codable, Sendable {
        public let module: String
        public let importSpelling: String?
        public let file: String?
        public let line: Int?
    }

    public struct Cause: Codable, Sendable {
        public let classification: Classification
        public let via: Dependency
        public let dependencyDepth: Int
        public let originModule: String
        public let finding: MigrationFinding
    }

    public let name: String
    public let c99name: String
    public let sourceAssociation: SourceAssociation
    public let swiftFiles: [String]
    public let sourceClassification: Classification?
    public let findings: [MigrationFinding]
    public let localDependencies: [Dependency]
    public let dependencyCauses: [Cause]
}

private struct SwiftPackageDescription: Decodable {
    struct Target: Decodable {
        let name: String
        let c99name: String
        let moduleType: String
        let type: String
        let path: String
        let sources: [String]
        let targetDependencies: [String]?

        var dependencies: [String] { targetDependencies ?? [] }
        var isOrdinarySwift: Bool { moduleType == "SwiftTarget" && ["library", "executable", "test"].contains(type) }
    }

    let path: String
    let targets: [Target]

    static func read(_ file: URL) throws -> Self {
        let limit = 4 * 1_048_576
        let fd = open(file.path, O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw failure("Cannot open the SwiftPM description.") }
        defer { close(fd) }
        var info = stat()
        guard fstat(fd, &info) == 0, info.st_mode & S_IFMT == S_IFREG, info.st_size <= limit else {
            throw failure("The SwiftPM description must be a regular file of at most 4 MiB.")
        }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: false)
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        guard let data = try? handle.read(upToCount: limit + 1), data.count <= limit,
              let description = try? decoder.decode(Self.self, from: data) else {
            throw failure("Expected JSON from swift package describe --type json, at most 4 MiB.")
        }
        guard description.targets.count <= 1_024,
              description.targets.reduce(0, { $0 + $1.sources.count }) <= 16_384,
              description.targets.reduce(0, { $0 + $1.dependencies.count }) <= 16_384 else {
            throw failure("The SwiftPM description exceeds the target, source, or dependency limit.")
        }
        return description
    }

    static func failure(_ message: String) -> MixerFailure { MixerFailure("import.swiftpm-description", message) }

    static func validText(_ text: String, limit: Int) -> Bool {
        !text.isEmpty && text.utf8.count <= limit && !text.utf8.contains { $0 < 32 || $0 == 127 }
    }

    static func relativePath(_ path: String) -> Bool {
        validText(path, limit: 4_096) && path.split(separator: "/", omittingEmptySubsequences: false)
            .allSatisfy { !$0.isEmpty && $0 != "." && $0 != ".." }
    }

    static func canonicalPath(_ path: String) -> Data? {
        guard let resolved = realpath(path, nil) else { return nil }
        defer { free(resolved) }
        return Data(bytes: resolved, count: strlen(resolved))
    }
}

struct SwiftPackageInventory {
    private typealias Description = SwiftPackageDescription
    private typealias Target = Description.Target

    private struct Module {
        let target: Target
        let association: MigrationModule.SourceAssociation
        let files: [String]
    }

    private let modules: [String: Module]
    private let targetByFile: [Data: String]
    private let unassigned: [String]
    private let sourceDependencies: [String: [String]]
    private let importTargetsByModule: [String: [Data: String]]
    private var importsByModule: [String: [String: MigrationModule.Dependency]] = [:]

    init(description: URL, root: URL, swiftFiles: [URL], relativePaths: [String]) throws {
        let graph = try Description.read(description)
        guard graph.path.hasPrefix("/"), Description.validText(graph.path, limit: 4_096),
              let rootPath = Description.canonicalPath(root.path), Description.canonicalPath(graph.path) == rootPath else {
            throw Description.failure("The SwiftPM description root does not match the import directory.")
        }
        let rootFD = open(root.path, O_RDONLY | O_DIRECTORY | O_CLOEXEC)
        guard rootFD >= 0 else { throw Description.failure("Cannot open the import directory.") }
        defer { close(rootFD) }

        var rootPrefix = rootPath
        if rootPrefix.last != 47 { rootPrefix.append(47) }
        var inspectedPaths: [Data: String] = [:]
        for (file, relative) in zip(swiftFiles, relativePaths) {
            if let path = Description.canonicalPath(file.path) { inspectedPaths[path] = relative }
        }
        let names = Set(graph.targets.map(\.name))
        guard names.count == graph.targets.count else { throw Description.failure("Duplicate SwiftPM target name.") }

        var modules: [String: Module] = [:]
        var targetByFile: [Data: String] = [:]
        var claimedFiles: Set<Data> = []
        for target in graph.targets {
            let dependencies = Set(target.dependencies)
            guard [target.name, target.c99name, target.type, target.moduleType].allSatisfy({ Description.validText($0, limit: 1_024) }),
                  target.path == "." || Description.relativePath(target.path),
                  target.sources.allSatisfy(Description.relativePath),
                  dependencies.count == target.dependencies.count, !dependencies.contains(target.name),
                  dependencies.allSatisfy({ Description.validText($0, limit: 1_024) && names.contains($0) }) else {
                throw Description.failure("Invalid SwiftPM target, relative path, or local dependency.")
            }
            guard target.isOrdinarySwift else {
                modules[target.name] = Module(target: target, association: .unsupportedTarget, files: [])
                continue
            }
            let paths = try target.sources.compactMap { source -> String? in
                let relative = target.path == "." ? source : target.path + "/" + source
                guard Description.validText(relative, limit: 4_096) else {
                    throw Description.failure("SwiftPM source path exceeds the path limit.")
                }
                // Use the filesystem's spelling so APFS aliases match the inspected path.
                var info = stat()
                guard fstatat(rootFD, relative, &info, AT_SYMLINK_NOFOLLOW_ANY) == 0,
                      info.st_mode & S_IFMT == S_IFREG,
                      let path = Description.canonicalPath(root.path + "/" + relative),
                      path.starts(with: rootPrefix), let inspected = inspectedPaths[path] else { return nil }
                guard claimedFiles.insert(Data(inspected.utf8)).inserted else {
                    throw Description.failure("SwiftPM source has duplicate target membership.")
                }
                return inspected
            }
            guard paths.count == target.sources.count, !paths.isEmpty else {
                modules[target.name] = Module(target: target, association: .unverifiedSources, files: [])
                continue
            }
            for path in paths { targetByFile[Data(path.utf8)] = target.name }
            modules[target.name] = Module(target: target, association: .associated, files: paths.sorted())
        }
        let bySpelling = Dictionary(grouping: graph.targets, by: { Data($0.c99name.utf8) })
        var sourceDependencies: [String: [String]] = [:]
        var importTargetsByModule: [String: [Data: String]] = [:]
        for (name, module) in modules where module.association == .associated {
            let dependencies = module.target.dependencies.filter { modules[$0]?.association == .associated }.sorted()
            sourceDependencies[name] = dependencies
            for dependency in dependencies {
                guard let spelling = modules[dependency]?.target.c99name else { continue }
                let key = Data(spelling.utf8)
                if bySpelling[key]?.count == 1 { importTargetsByModule[name, default: [:]][key] = dependency }
            }
        }
        self.modules = modules
        self.targetByFile = targetByFile
        self.sourceDependencies = sourceDependencies
        self.importTargetsByModule = importTargetsByModule
        unassigned = relativePaths.filter { targetByFile[Data($0.utf8)] == nil }
    }

    func target(for file: String) -> String? { targetByFile[Data(file.utf8)] }

    func importTargets(for name: String) -> [Data: String]? { importTargetsByModule[name] }

    mutating func recordImports(_ imports: [String: Int], file: String, target: String) {
        for (dependency, line) in imports where importsByModule[target]?[dependency] == nil {
            guard let spelling = modules[dependency]?.target.c99name else { continue }
            importsByModule[target, default: [:]][dependency] = .init(
                module: dependency, importSpelling: spelling.utf8.elementsEqual(dependency.utf8) ? nil : spelling,
                file: file, line: line
            )
        }
    }

    func report(findings: [MigrationFinding]) -> MigrationSwiftPackage {
        typealias Classification = MigrationModule.Classification
        let names = modules.keys.sorted()
        var findingsByModule: [String: [MigrationFinding]] = [:]
        for finding in findings {
            if let target = target(for: finding.file) { findingsByModule[target, default: []].append(finding) }
        }
        var incoming: [String: [(dependent: String, edge: MigrationModule.Dependency)]] = [:]
        for name in names {
            for dependency in sourceDependencies[name, default: []] {
                let edge = importsByModule[name]?[dependency] ?? .init(module: dependency, importSpelling: nil, file: nil, line: nil)
                incoming[dependency, default: []].append((name, edge))
            }
        }

        var classes: [String: Classification] = [:]
        var causes: [String: [MigrationModule.Cause]] = [:]
        for classification in Classification.allCases where classification != .noSourceHints {
            // Walk backward from each origin once per class to keep the shortest witness.
            var queue: [(name: String, origin: String, finding: MigrationFinding, depth: Int)] = []
            for name in names {
                if let finding = findingsByModule[name, default: []].first(where: { Classification(category: $0.category) == classification }) {
                    queue.append((name, name, finding, 0))
                    if classes[name] == nil { classes[name] = classification }
                }
            }
            var visited = Set(queue.map(\.name))
            var next = 0
            while next < queue.count {
                let entry = queue[next]
                next += 1
                for (dependent, edge) in incoming[entry.name, default: []] where visited.insert(dependent).inserted {
                    let depth = entry.depth + 1
                    causes[dependent, default: []].append(.init(classification: classification, via: edge,
                                                               dependencyDepth: depth, originModule: entry.origin, finding: entry.finding))
                    queue.append((dependent, entry.origin, entry.finding, depth))
                }
            }
        }

        let reports = names.compactMap { name -> MigrationModule? in
            guard let module = modules[name] else { return nil }
            let dependencies = module.target.dependencies.sorted().map {
                importsByModule[name]?[$0] ?? .init(module: $0, importSpelling: nil, file: nil, line: nil)
            }
            return MigrationModule(name: name, c99name: module.target.c99name, sourceAssociation: module.association,
                                   swiftFiles: module.files,
                                   sourceClassification: module.association == .associated ? classes[name, default: .noSourceHints] : nil,
                                   findings: findingsByModule[name, default: []], localDependencies: dependencies,
                                   dependencyCauses: causes[name, default: []])
        }
        return MigrationSwiftPackage(modules: reports, unassignedSwiftFiles: unassigned)
    }
}
