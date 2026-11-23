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

    public init(swiftSources: [String]? = nil, resourceFolders: [String]? = nil,
                localNetworkUsageDescription: String? = nil, allowsLocalNetworking: Bool? = nil) {
        self.swiftSources = swiftSources
        self.resourceFolders = resourceFolders
        self.localNetworkUsageDescription = localNetworkUsageDescription
        self.allowsLocalNetworking = allowsLocalNetworking
    }

    var sources: [String] { (swiftSources ?? []).sorted() }
    var folders: [String] { (resourceFolders ?? []).sorted() }
    var hasPlist: Bool { localNetworkUsageDescription != nil || allowsLocalNetworking != nil }
    var isEmpty: Bool { sources.isEmpty && folders.isEmpty && !hasPlist }

    func validate(appName: String) throws {
        let paths = sources + folders
        let invalidPath = MixerFailure("config.ios-native", "Declare unique Swift files and resource folders with simple paths relative to Platforms/iOS.")
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
        if let description = localNetworkUsageDescription {
            guard description.utf8.count <= 1024, !description.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
                  description.rangeOfCharacter(from: .controlCharacters) == nil,
                  !description.contains("$("), !description.contains("${") else {
                throw MixerFailure("config.ios-native", "Local network usage description must be plain, nonempty text up to 1024 UTF-8 bytes.")
            }
        }
    }

    func validateFiles(in platform: URL) throws {
        for path in sources + folders {
            let components = path.split(separator: "/")
            var item = platform
            for component in components.dropLast() {
                item.appendPathComponent(String(component))
                try Self.require(item, type: S_IFDIR)
            }
            item.appendPathComponent(String(components.last!))
            if path.hasSuffix(".swift") {
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
