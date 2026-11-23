#if canImport(Darwin)
import Darwin
#elseif canImport(Android)
import Android
#else
import Glibc
#endif
import Foundation

public struct AppleNativeConfiguration: Codable, Equatable, Sendable {
    public var swiftSources: [String]?
    public var resourceFolders: [String]?
    public var localNetworkUsageDescription: String?
    public var allowsLocalNetworking: Bool?
    public var simulatorArchive: String?
    public var simulatorArchiveSHA256: String?

    public init(swiftSources: [String]? = nil, resourceFolders: [String]? = nil,
                localNetworkUsageDescription: String? = nil, allowsLocalNetworking: Bool? = nil,
                simulatorArchive: String? = nil, simulatorArchiveSHA256: String? = nil) {
        self.swiftSources = swiftSources
        self.resourceFolders = resourceFolders
        self.localNetworkUsageDescription = localNetworkUsageDescription
        self.allowsLocalNetworking = allowsLocalNetworking
        self.simulatorArchive = simulatorArchive
        self.simulatorArchiveSHA256 = simulatorArchiveSHA256
    }

    var sources: [String] { (swiftSources ?? []).sorted() }
    var folders: [String] { (resourceFolders ?? []).sorted() }
    var hasPlist: Bool { localNetworkUsageDescription != nil || allowsLocalNetworking != nil }
    private var hasArchiveDeclaration: Bool { simulatorArchive != nil || simulatorArchiveSHA256 != nil }
    private var paths: [String] { sources + folders + (simulatorArchive.map { [$0] } ?? []) }
    var isEmpty: Bool { sources.isEmpty && folders.isEmpty && !hasPlist && !hasArchiveDeclaration }

    func validate(appName: String) throws {
        let paths = self.paths
        let invalidPath = MixerFailure("config.ios-native", "Declare unique native inputs with simple paths relative to Platforms/iOS.")
        guard paths.count <= 256, Set(paths.map { $0.lowercased() }).count == paths.count else { throw invalidPath }
        for path in paths {
            guard path.utf8.count <= 512,
                  path.range(of: #"\A[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*(?:/[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)*\z"#,
                             options: .regularExpression) != nil,
                  !path.lowercased().hasPrefix("\(appName.lowercased()).xcodeproj/") else { throw invalidPath }
        }
        let sourceNames = sources.map { String($0.split(separator: "/").last!).lowercased() }
        guard sources.allSatisfy({ $0.hasSuffix(".swift") }),
              Set(sourceNames).count == sources.count,
              !sourceNames.contains("\(appName.lowercased())app.swift") else { throw invalidPath }
        let reservedBundleNames: Set<String> = [appName.lowercased(), "pkginfo", "_codesignature",
            "frameworks", "plugins", "watch", "appclips", "sc_info", "meta-inf"]
        let bundleNames = folders.map { String($0.split(separator: "/").last!).lowercased() }
        guard Set(bundleNames).count == folders.count,
              bundleNames.allSatisfy({ !$0.contains(".") && !reservedBundleNames.contains($0) }) else { throw invalidPath }
        if hasArchiveDeclaration {
            guard let archive = simulatorArchive, archive.hasSuffix(".a"),
                  let digest = simulatorArchiveSHA256,
                  digest.range(of: #"\A[0-9a-f]{64}\z"#, options: .regularExpression) != nil else {
                throw MixerFailure("config.ios-native-archive", "Declare an iOS Simulator static archive and its lowercase SHA-256 together.")
            }
            let archivePath = archive.lowercased()
            guard !folders.contains(where: { archivePath.hasPrefix($0.lowercased() + "/") }) else {
                throw MixerFailure("config.ios-native-archive", "Keep the Simulator static archive outside declared resource folders.")
            }
        }
        if let description = localNetworkUsageDescription {
            guard description.utf8.count <= 1024, !description.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
                  description.rangeOfCharacter(from: .controlCharacters) == nil,
                  !description.contains("$("), !description.contains("${") else {
                throw MixerFailure("config.ios-native", "Local network usage description must be plain, nonempty text up to 1024 UTF-8 bytes.")
            }
        }
    }

    func validateFiles(in platform: URL) throws {
        for path in paths {
            let components = path.split(separator: "/")
            var item = platform
            for component in components.dropLast() {
                item.appendPathComponent(String(component))
                try Self.require(item, type: S_IFDIR)
            }
            item.appendPathComponent(String(components.last!))
            if path == simulatorArchive {
                try Self.require(item, type: S_IFREG)
                let bytes = try Data(contentsOf: item, options: .mappedIfSafe)
                guard bytes.starts(with: Data("!<arch>\n".utf8)), SourceDigest.sha256(bytes) == simulatorArchiveSHA256 else {
                    throw MixerFailure("generate.ios-native-archive", "Simulator static archive differs from its declared format or SHA-256.")
                }
            } else if path.hasSuffix(".swift") {
                try Self.require(item, type: S_IFREG)
            } else {
                try Self.validateResourceFolder(item)
            }
        }
    }

    private static func validateResourceFolder(_ folder: URL) throws {
        try require(folder, type: S_IFDIR)
        for name in try FileManager.default.contentsOfDirectory(atPath: folder.path) {
            let item = folder.appendingPathComponent(name)
            guard !name.hasPrefix("."), !["pem", "key", "p12", "pfx", "mobileprovision", "keystore", "jks"]
                .contains(item.pathExtension.lowercased()) else {
                throw MixerFailure("generate.ios-native-path", "Unsupported resource entry: \(item.path)")
            }
            if try fileType(item) == S_IFDIR {
                try validateResourceFolder(item)
            } else {
                try require(item, type: S_IFREG)
            }
        }
    }

    static func fileType(_ item: URL) throws -> mode_t? {
        var info = stat()
        if lstat(item.path, &info) == 0 { return info.st_mode & S_IFMT }
        if errno == ENOENT { return nil }
        throw MixerFailure("generate.ios-native-path", "Cannot inspect native path: \(item.path)")
    }

    static func require(_ item: URL, type: mode_t, allowMissing: Bool = false) throws {
        let actual = try fileType(item)
        guard actual == type || (actual == nil && allowMissing) else {
            throw MixerFailure("generate.ios-native-path", "Expected an in-project directory or regular file without symlinks: \(item.path)")
        }
    }

    func plist() throws -> Data? {
        guard hasPlist else { return nil }
        var entries: [String: Any] = [:]
        if let localNetworkUsageDescription { entries["NSLocalNetworkUsageDescription"] = localNetworkUsageDescription }
        if let allowsLocalNetworking { entries["NSAppTransportSecurity"] = ["NSAllowsLocalNetworking": allowsLocalNetworking] }
        return try PropertyListSerialization.data(fromPropertyList: entries, format: .xml, options: 0)
    }
}
