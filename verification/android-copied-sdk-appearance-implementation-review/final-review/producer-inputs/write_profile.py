import json, pathlib
root=pathlib.Path(__file__).resolve().parents[2]
p=json.loads((root/'verification/android-copied-sdk-appearance-contract/proposed-profile-observation.json').read_text())
p['id']='mixer.android-source-pair.1'
# Deliberate initial implementation from the selected frozen observation. This is
# not invoked by any product build and cannot refresh the committed policy.
head='''import Foundation

/// Exact first-party development source pair; no version range or stable ABI claim.
public struct AndroidSDKProfileLock: Codable, Equatable, Sendable {
    public var id: String
    public var sdk_compatibility_sha256: String
    public var adapter_compatibility_sha256: String
    public var default_descriptor: AndroidSDKSourceIdentity
}
public struct AndroidSDKSourceIdentity: Codable, Equatable, Sendable {
    public var bytes: Int
    public var sha256: String
}
struct AndroidSDKProfile: Codable, Sendable {
    var schema: Int
    var id: String
    var sdk_compatibility_sha256: String
    var adapter_compatibility_sha256: String
    var default_descriptor: AndroidSDKSourceIdentity
    var sdk_files: [String: AndroidSDKSourceIdentity]
    var adapter_files: [String: AndroidSDKSourceIdentity]
    var wire: Wire
    struct Wire: Codable, Sendable {
        var android_profile_id: String
        var appearance_format: String
        var appearance_recipe: String
        var document_schema: Int
        var native_packet_schema: Int
        var staged_C_ABI: String
    }
    var lock: AndroidSDKProfileLock {
        AndroidSDKProfileLock(id: id, sdk_compatibility_sha256: sdk_compatibility_sha256,
            adapter_compatibility_sha256: adapter_compatibility_sha256, default_descriptor: default_descriptor)
    }
}

enum AndroidSDKCompatibility {
    // Selected frozen 22 + 20 map. Never infer or refresh from a selected SDK,
    // mutable lock, resource, environment, or successful local build.
    static let profile: AndroidSDKProfile = {
        try! JSONDecoder().decode(AndroidSDKProfile.self, from: Data(#"""
'''
tail='''
        """#.utf8))
    }()
    static let marker = "__MIXER_ANDROID_SOURCE_PROFILE_HEX__"

    static func renderDriver(_ template: String) throws -> String {
        guard template.components(separatedBy: marker).count == 2 else {
            throw MixerFailure("android.driver-profile", "The installed Android driver must contain exactly one source-profile marker. Reinstall the matching CLI distribution.")
        }
        let hex = try JSONFile.data(profile).map { String(format: "%02x", $0) }.joined()
        let result = template.replacingOccurrences(of: marker, with: hex)
        guard !result.contains(marker) else { throw failure("Unrendered Android driver profile") }
        return result
    }

    static func require(_ record: AndroidSDKProfileLock?) throws {
        guard let record else {
            throw MixerFailure("android.sdk-profile-required", "Android project predates source-pair admission. Explicitly migrate or create a fresh project with the matching first-party CLI/SDK distribution (\\(profile.id)); local lock edits do not qualify a project.")
        }
        guard record == profile.lock else {
            throw MixerFailure("android.sdk-profile-mismatch", "Android source profile differs from \\(profile.id). Explicitly migrate or create a fresh project with the matching first-party CLI/SDK distribution.")
        }
    }
    static func failure(_ detail: String) -> MixerFailure {
        MixerFailure("android.sdk-compatibility", "\\(profile.id): \\(detail). Install the matching first-party CLI/SDK distribution; local lock recomputation cannot authorize changed sources.")
    }
    private static func entries(_ directory: URL) throws -> [String] {
        try directoryType(directory)
        return try FileManager.default.contentsOfDirectory(atPath: directory.path)
    }
    private static func directoryType(_ url: URL) throws {
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: url.path),
              attrs[.type] as? FileAttributeType == .typeDirectory else { throw failure("Expected ordinary directory \\(url.path)") }
    }
    /// Exact spelling is checked in the containing directory before touching an entry.
    private static func path(_ root: URL, _ relative: String, directory: Bool = false, identity: AndroidSDKSourceIdentity? = nil) throws -> URL {
        var current = root
        let components = relative.split(separator: "/").map(String.init)
        for (index, name) in components.enumerated() {
            guard try entries(current).contains(name) else { throw failure("Missing or case-aliased path \\(relative)") }
            current.appendPathComponent(name)
            if index < components.count - 1 || directory { try directoryType(current) }
        }
        if let identity {
            guard let attrs = try? FileManager.default.attributesOfItem(atPath: current.path),
                  attrs[.type] as? FileAttributeType == .typeRegular,
                  (attrs[.size] as? NSNumber)?.intValue == identity.bytes else { throw failure("Expected ordinary pinned-size file \\(relative)") }
        }
        return current
    }
    private static func closed(_ root: URL, _ relative: String, files: [String: AndroidSDKSourceIdentity]) throws {
        let directory = try path(root, relative, directory: true)
        let prefix = relative + "/"
        let expected = Set(files.keys.filter { $0.hasPrefix(prefix) }.map { String($0.dropFirst(prefix.count).split(separator: "/")[0]) })
        guard Set(try entries(directory)) == expected else { throw failure("Unexpected or missing directory inventory \\(relative)") }
        for name in expected.sorted() {
            let item = relative + "/" + name
            if let identity = files[item] { _ = try path(root, item, identity: identity) }
            else { try closed(root, item, files: files) }
        }
    }
    private static func sdkLayout(_ root: URL) throws {
        let names = try entries(root)
        // Reject all non-ASCII names BEFORE any case transformation/classification,
        // entry following, copying or hashing (including unrelated Unicode names).
        guard names.allSatisfy({ $0.utf8.allSatisfy { $0 < 128 } }) else { throw failure("Non-ASCII SDK-root entry name") }
        for name in names where name.lowercased().hasPrefix("package") {
            guard name == "Package.swift" else { throw failure("Reserved SDK manifest namespace \\(name)") }
        }
        _ = try path(root, "Package.swift", identity: profile.sdk_files["Package.swift"]!)
        for target in ["Sources/MixerCore", "Sources/MixerUI"] { try closed(root, target, files: profile.sdk_files) }
    }
    private static func adapterLayout(_ root: URL, input: Bool) throws {
        let files = Dictionary(uniqueKeysWithValues: profile.adapter_files.map { key, value in
            (input && key.hasPrefix("Sources/") ? "engine/" + key : key, value)
        })
        for (relative, identity) in files { _ = try path(root, relative, identity: identity) }
        try closed(root, input ? "engine/Sources/MixerAndroidRuntime" : "Sources/MixerAndroidRuntime", files: files)
        if !input {
            for relative in ["app/src", "bridge", "contracts"] { try closed(root, relative, files: files) }
        }
    }
    private static func bounded(_ url: URL, _ identity: AndroidSDKSourceIdentity) throws -> Data {
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        let bytes = try handle.read(upToCount: identity.bytes + 1) ?? Data()
        guard bytes.count == identity.bytes, SourceDigest.sha256(bytes) == identity.sha256 else { throw failure("Pinned bytes differ at \\(url.path)") }
        return bytes
    }
    private static func map(_ root: URL, _ files: [String: AndroidSDKSourceIdentity], input: Bool = false) throws -> String {
        var records = Data()
        for relative in files.keys.sorted() {
            let source = input && relative.hasPrefix("Sources/") ? "engine/" + relative : relative
            let identity = files[relative]!
            _ = try bounded(root.appendingPathComponent(source), identity)
            records.append(Data((relative + "\\0" + identity.sha256 + "\\n").utf8))
        }
        return SourceDigest.sha256(records)
    }
    static func admitSDK(_ root: URL) throws {
        try sdkLayout(root)
        guard try map(root, profile.sdk_files) == profile.sdk_compatibility_sha256 else { throw failure("SDK projection digest") }
    }
    static func admitInput(sdk: URL, adapter: URL) throws {
        // Finish both layouts, including sizes, before required-source content reads.
        try sdkLayout(sdk); try adapterLayout(adapter, input: true)
        guard try map(sdk, profile.sdk_files) == profile.sdk_compatibility_sha256,
              try map(adapter, profile.adapter_files, input: true) == profile.adapter_compatibility_sha256 else { throw failure("Input source-pair digest") }
    }
    static func admitAdapterInput(_ adapter: URL) throws {
        try adapterLayout(adapter, input: true)
        guard try map(adapter, profile.adapter_files, input: true) == profile.adapter_compatibility_sha256 else { throw failure("Adapter projection digest") }
    }
    private static func appearanceLayout(_ adapter: URL) throws -> URL {
        try directoryType(adapter.deletingLastPathComponent())
        for relative in ["app", "app/assets", "app/assets/MixerAppearanceV2"] { _ = try path(adapter, relative, directory: true) }
        guard Set(try entries(adapter.appendingPathComponent("app/assets"))) == ["MixerAppearanceV2"],
              Set(try entries(adapter.appendingPathComponent("app/assets/MixerAppearanceV2"))) == ["descriptor.json"] else { throw failure("Android appearance closed asset inventory") }
        return try path(adapter, "app/assets/MixerAppearanceV2/descriptor.json", identity: profile.default_descriptor)
    }
    static func admitAdapter(_ adapter: URL) throws {
        let descriptor = try appearanceLayout(adapter)
        try adapterLayout(adapter, input: false)
        _ = try bounded(descriptor, profile.default_descriptor)
        guard try map(adapter, profile.adapter_files) == profile.adapter_compatibility_sha256 else { throw failure("Adapter projection digest") }
    }
    static func admitProject(_ root: URL) throws {
        let generated = try path(root, "Generated", directory: true)
        let adapter = try path(generated, "MixerAndroid", directory: true)
        let descriptor = try appearanceLayout(adapter)
        let sdk = try path(generated, "MixerSDK", directory: true)
        try sdkLayout(sdk); try adapterLayout(adapter, input: false)
        _ = try bounded(descriptor, profile.default_descriptor)
        guard try map(sdk, profile.sdk_files) == profile.sdk_compatibility_sha256,
              try map(adapter, profile.adapter_files) == profile.adapter_compatibility_sha256 else { throw failure("Project source-pair digest") }
    }
    static func admitDefault(_ bytes: Data) throws {
        guard bytes.count == profile.default_descriptor.bytes,
              SourceDigest.sha256(bytes) == profile.default_descriptor.sha256 else { throw failure("CLI-linked typed default differs from selected profile") }
    }
}
'''
(root/'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').write_text(head+'\n'.join('        '+line for line in json.dumps(p,indent=2,sort_keys=True).splitlines())+'\n'+tail)
