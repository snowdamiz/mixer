import Foundation
import CryptoKit
import MixerCore

public struct MixerFailure: Error, CustomStringConvertible, Sendable {
    public let code: String
    public let description: String
    public init(_ code: String, _ description: String) { self.code = code; self.description = description }
}

public enum AndroidApplicationHost: String, Codable, Sendable {
    case legacyV1 = "legacy-v1"
    case publicV3 = "public-v3"
    case publicV4 = "public-v4"
    var isPublic: Bool { self == .publicV3 || self == .publicV4 }
}

public struct ApplicationConfiguration: Codable, Equatable, Sendable {
    public var schema: Int = 1
    public var application: String
    public var name: String
    public var language: String = "swift"
    public var applicationIdentifiers: [String: String]?
    public var targets: [String] = ["ios", "android"]
    public var toolchainLock: String = "mixer.lock"
    public var capabilities: [String] = ["storage.files"]
    public var androidHost: AndroidApplicationHost? = nil
    public var updates = UpdateConfiguration()
    public init(name: String, application: String) { self.name = name; self.application = application }
    package func applicationIdentifier(for platform: String) -> String {
        applicationIdentifiers?[platform] ?? application
    }
    public func validate() throws {
        guard schema == 1, language == "swift" else { throw MixerFailure("config.schema", "Only schema 1 and language swift are supported.") }
        guard name.range(of: "^[A-Za-z][A-Za-z0-9_]{0,63}$", options: .regularExpression) != nil else {
            throw MixerFailure("config.name", "Name must be a Swift identifier starting with a letter (maximum 64 characters).")
        }
        let identifiers = applicationIdentifiers ?? [:]
        guard Set(identifiers.keys).isSubset(of: targets),
              ([application] + identifiers.values).allSatisfy({
                  $0.range(of: #"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$"#, options: .regularExpression) != nil
              }) else {
            throw MixerFailure("config.application", "Application identifiers must be reverse-DNS identifiers for configured targets.")
        }
        guard Set(targets).count == targets.count, !targets.isEmpty, Set(targets).isSubset(of: ["ios", "android"]) else { throw MixerFailure("config.targets", "Targets must be unique ios/android entries.") }
        if let androidHost {
            guard targets.contains("android") else { throw MixerFailure("config.android-host", "androidHost requires an android target.") }
            if androidHost.isPublic {
                let reserved: Set<String> = ["abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class", "const", "continue", "default", "do", "double", "else", "enum", "extends", "final", "finally", "float", "for", "goto", "if", "implements", "import", "instanceof", "int", "interface", "long", "native", "new", "package", "private", "protected", "public", "return", "short", "static", "strictfp", "super", "switch", "synchronized", "this", "throw", "throws", "transient", "try", "void", "volatile", "while", "true", "false", "null", "_"]
                guard application != "dev.mixer.android", !application.hasPrefix("dev.mixer.android."),
                      application.split(separator: ".").allSatisfy({ !reserved.contains(String($0)) }) else {
                    throw MixerFailure("config.android-host", "The public Android host requires an app-owned Java package outside dev.mixer.android, with no Java keyword segments.")
                }
            }
        }
        guard toolchainLock == "mixer.lock" else { throw MixerFailure("config.lock", "The current schema requires mixer.lock beside mixer.yml.") }
        guard updates.activation == "cold-start", updates.compatibility == "exact-runtime-fingerprint", updates.requireArtifactSignature, updates.requireAssignmentSignature else { throw MixerFailure("config.updates", "Cold-start activation, exact runtime identity, and both signatures are required.") }
        guard Set(capabilities).count == capabilities.count, capabilities.allSatisfy({ $0.range(of: "^[a-z][a-z0-9.-]{1,95}$", options: .regularExpression) != nil }) else { throw MixerFailure("config.capabilities", "Capabilities must be unique bounded identifiers.") }
    }
    public static func load(_ root: URL) throws -> Self {
        let url = root.appendingPathComponent("mixer.yml")
        let data = try Data(contentsOf: url)
        guard data.count <= 1_048_576 else { throw MixerFailure("config.size", "mixer.yml exceeds 1 MiB.") }
        do {
            try JSONInputGuard.validate(data, limits: JSONInputLimits(maximumDepth: 32, maximumValues: 4096))
        } catch let error as JSONInputError {
            throw MixerFailure("config.encoding", "Invalid or ambiguous configuration JSON (\(error.reason.rawValue) at byte \(error.offset)). The current format is the JSON subset of YAML 1.2.")
        }
        let raw: Any
        do { raw = try JSONSerialization.jsonObject(with: data) }
        catch { throw MixerFailure("config.encoding", "This preview reads the JSON subset of YAML 1.2 in mixer.yml. Use the generated configuration; block-style YAML support is not yet implemented.") }
        guard let fields = raw as? [String: Any] else { throw MixerFailure("config.shape", "mixer.yml must be an object.") }
        let known: Set<String> = ["schema", "application", "name", "language", "targets", "toolchainLock", "capabilities", "updates", "androidHost", "applicationIdentifiers"]
        let unknown = Set(fields.keys).subtracting(known)
        guard unknown.isEmpty else { throw MixerFailure("config.unknown", "Unknown configuration keys: \(unknown.sorted().joined(separator: ", ")).") }
        if let updateFields = fields["updates"] as? [String: Any] {
            let allowed: Set<String> = ["activation", "compatibility", "requireArtifactSignature", "requireAssignmentSignature"]
            guard Set(updateFields.keys).isSubset(of: allowed) else { throw MixerFailure("config.unknown", "Unknown update configuration key.") }
        }
        let config = try JSONDecoder().decode(Self.self, from: data)
        try config.validate()
        return config
    }
}

public struct UpdateConfiguration: Codable, Equatable, Sendable {
    public var activation = "cold-start"
    public var compatibility = "exact-runtime-fingerprint"
    public var requireArtifactSignature = true
    public var requireAssignmentSignature = true
    public init() {}
}

public struct ToolchainLock: Codable, Sendable {
    public var schema = 1
    public var sdkDigest: String
    public var sdkDistribution: String
    public var swiftVersion: String
    public var generatedBy = "mixer 0.1.0-dev"
    public var qualification = "local-development-only"
    public var android: AndroidToolchainLock?
    public init(sdkDigest: String, swiftVersion: String) {
        self.sdkDigest = sdkDigest; self.swiftVersion = swiftVersion; sdkDistribution = "bundled-source-snapshot"
    }
}

public enum JSONFile {
    public static func data<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        return try encoder.encode(value) + Data([10])
    }
    public static func write<T: Encodable>(_ value: T, to url: URL) throws { try data(value).write(to: url, options: .atomic) }
}

public enum SourceDigest {
    private static let skipped = Set([".build", ".git", ".swiftpm", "node_modules", ".gradle", ".mixer", "target", ".DS_Store"])

    private static func excludesItem(_ url: URL) -> Bool {
        let name = url.lastPathComponent.lowercased()
        return name == ".env" || (name.hasPrefix(".env.") && name != ".env.example")
            || ["pem", "key", "p12", "pfx", "mobileprovision", "keystore", "jks"].contains(url.pathExtension.lowercased())
    }

    public static func files(in root: URL) throws -> [URL] {
        let root = root.resolvingSymlinksInPath().standardizedFileURL
        guard let enumerator = FileManager.default.enumerator(atPath: root.path) else { throw MixerFailure("files.read", "Cannot enumerate \(root.path)") }
        var result: [URL] = []
        for case let relative as String in enumerator {
            let url = root.appendingPathComponent(relative)
            if skipped.contains(url.lastPathComponent) { enumerator.skipDescendants(); continue }
            if excludesItem(url) { continue }
            let info = try url.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey])
            if info.isSymbolicLink == true { throw MixerFailure("files.symlink", "Source snapshots reject symlinks: \(url.path)") }
            if info.isRegularFile == true { result.append(url) }
        }
        return result.sorted { $0.path < $1.path }
    }

    // List each directory explicitly so a traversal error cannot yield a partial export.
    static func exportEntries(in root: URL) throws -> [(relative: String, directory: Bool)] {
        let keys: Set<URLResourceKey> = [.isDirectoryKey, .isRegularFileKey, .isSymbolicLinkKey]
        var pending = [""]
        var result: [(String, Bool)] = []
        while let parent = pending.popLast() {
            let directory = root.appendingPathComponent(parent, isDirectory: true)
            let names: [String]
            do {
                names = try FileManager.default.contentsOfDirectory(atPath: directory.path)
            } catch {
                throw MixerFailure("files.read", "Cannot enumerate \(directory.path): \(error.localizedDescription)")
            }
            for name in names where !skipped.contains(name) {
                let relative = parent.isEmpty ? name : parent + "/" + name
                let url = root.appendingPathComponent(relative)
                let info = try url.resourceValues(forKeys: keys)
                let excluded = excludesItem(url)
                if info.isSymbolicLink == true {
                    if excluded { continue }
                    throw MixerFailure("files.symlink", "Source snapshots reject symlinks: \(url.path)")
                }
                if info.isDirectory == true { pending.append(relative) }
                if !excluded && (info.isDirectory == true || info.isRegularFile == true) {
                    result.append((relative, info.isDirectory == true))
                }
            }
        }
        return result
    }

    static func exportFingerprint(_ root: URL) throws -> String {
        var hash = SHA256()
        let entries = try exportEntries(in: root).sorted {
            $0.relative.utf8.lexicographicallyPrecedes($1.relative.utf8)
        }
        for entry in entries {
            hash.update(data: Data(entry.relative.utf8))
            hash.update(data: Data([0, entry.directory ? 1 : 0]))
            if !entry.directory {
                let bytes = try Data(contentsOf: root.appendingPathComponent(entry.relative))
                hash.update(data: Data(SHA256.hash(data: bytes)))
            }
        }
        return hash.finalize().map { String(format: "%02x", $0) }.joined()
    }

    public static func sha256(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
    public static func tree(_ root: URL) throws -> String {
        let root = root.resolvingSymlinksInPath().standardizedFileURL
        var hash = SHA256()
        for file in try files(in: root) {
            let relative = String(file.path.dropFirst(root.path.count + 1))
            hash.update(data: Data(relative.utf8)); hash.update(data: Data([0]))
            hash.update(data: Data(sha256(try Data(contentsOf: file)).utf8)); hash.update(data: Data([10]))
        }
        return hash.finalize().map { String(format: "%02x", $0) }.joined()
    }
}
