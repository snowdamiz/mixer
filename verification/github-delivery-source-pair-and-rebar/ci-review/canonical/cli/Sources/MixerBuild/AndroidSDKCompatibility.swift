import Foundation

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
private struct AndroidProfileKey: CodingKey {
    var stringValue: String
    var intValue: Int? { nil }
    init(stringValue: String) { self.stringValue = stringValue }
    init?(intValue: Int) { nil }
}
private func profileKeys(_ decoder: any Decoder, _ expected: Set<String>) throws -> KeyedDecodingContainer<AndroidProfileKey> {
    let container = try decoder.container(keyedBy: AndroidProfileKey.self)
    guard Set(container.allKeys.map(\.stringValue)) == expected else {
        throw MixerFailure("android.sdk-profile-mismatch", "Android source-profile fields are unsupported. Explicitly migrate or recreate with the matching first-party CLI/SDK distribution.")
    }
    return container
}
extension AndroidSDKSourceIdentity {
    public init(from decoder: any Decoder) throws {
        let fields = try profileKeys(decoder, ["bytes", "sha256"])
        bytes = try fields.decode(Int.self, forKey: AndroidProfileKey(stringValue: "bytes"))
        sha256 = try fields.decode(String.self, forKey: AndroidProfileKey(stringValue: "sha256"))
    }
}
extension AndroidSDKProfileLock {
    public init(from decoder: any Decoder) throws {
        do {
            let fields = try profileKeys(decoder, ["id", "sdk_compatibility_sha256", "adapter_compatibility_sha256", "default_descriptor"])
            id = try fields.decode(String.self, forKey: AndroidProfileKey(stringValue: "id"))
            sdk_compatibility_sha256 = try fields.decode(String.self, forKey: AndroidProfileKey(stringValue: "sdk_compatibility_sha256"))
            adapter_compatibility_sha256 = try fields.decode(String.self, forKey: AndroidProfileKey(stringValue: "adapter_compatibility_sha256"))
            default_descriptor = try fields.decode(AndroidSDKSourceIdentity.self, forKey: AndroidProfileKey(stringValue: "default_descriptor"))
        } catch {
            throw MixerFailure("android.sdk-profile-mismatch", "Android source-profile record is unsupported. Explicitly migrate or recreate with the matching first-party CLI/SDK distribution.")
        }
    }
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
    // Selected frozen 22 + 23 map. Never infer or refresh from a selected SDK,
    // mutable lock, resource, environment, or successful local build.
    static let profile: AndroidSDKProfile = {
        try! JSONDecoder().decode(AndroidSDKProfile.self, from: Data(#"""
        {
          "adapter_compatibility_sha256": "2b001980e07e0d1c8a5139e79de6ad6ca83d8db66d386bd4f77689ab32a6325a",
          "adapter_files": {
            "Sources/MixerAndroidRuntime/DocumentSession.swift": {
              "bytes": 4128,
              "sha256": "701b3d82add793a2b425bfc9673583afa8be4112406071242099da7da252bd0c"
            },
            "Sources/MixerAndroidRuntime/SessionRegistry.swift": {
              "bytes": 7730,
              "sha256": "977bb8790cb822467c31c7a24ffebe96ea364067a3637bf90464ba4060b77b67"
            },
            "app/src/dev/mixer/android/AppearanceDescriptorV2.java": {
              "bytes": 31281,
              "sha256": "3c386184bcf2d6b6da068c9bc2cf11df0aaadb84d8c5cee4a5520d71008563f8"
            },
            "app/src/dev/mixer/android/AppearanceGeometryV2.java": {
              "bytes": 5972,
              "sha256": "a53c69fa7b07233d006a6ae72f93f05340b3c6ac7059de9eb4fa09aa86a8098c"
            },
            "app/src/dev/mixer/android/AppearanceNativePathsV2.java": {
              "bytes": 2396,
              "sha256": "afe8e7fd29d4d460fb3f457687a3334d7dfdc8eec872c3ad5a6052e224a18648"
            },
            "app/src/dev/mixer/android/AppearanceResolverV2.java": {
              "bytes": 24607,
              "sha256": "04237c1ffdcc777294fa70e0d7c7ecbdd4bee882ca19ce50fac795ef883ace9f"
            },
            "app/src/dev/mixer/android/AuthoredToggleInputV2.java": {
              "bytes": 6514,
              "sha256": "4b5f890ee7d3d7f4f4b17ba79bc8a44a8f26fa916e5ecd3c04a3c21fa98978fd"
            },
            "app/src/dev/mixer/android/InstalledAppearanceV2.java": {
              "bytes": 3183,
              "sha256": "8206e9592481b07557c8b8a0790b9f01d674ac1a19e413d1cdf581546247c8f9"
            },
            "app/src/dev/mixer/android/Json.java": {
              "bytes": 6633,
              "sha256": "9e3194dd187fecfad82e5f2162d5d0bcd40bf89fc4b82978be21940d0d2466d4"
            },
            "app/src/dev/mixer/android/MixerActivity.java": {
              "bytes": 2030,
              "sha256": "cc383f5f358714de5a55c65f205fd7e296ab8166657160c38059ca8ac7f4351c"
            },
            "app/src/dev/mixer/android/NativeAppearanceViewsV2.java": {
              "bytes": 81532,
              "sha256": "a217d0b178869f3e5c3fc2d80f30f559a22c76a303195e62bfcb73d3cce91cce"
            },
            "app/src/dev/mixer/android/NativeBridge.java": {
              "bytes": 1076,
              "sha256": "3e7faa3904fef5955426b9fa9993c77b61203fe605f675d73cd81bcf073306a3"
            },
            "app/src/dev/mixer/android/NativeCoordinatorV2.java": {
              "bytes": 13468,
              "sha256": "16597f90e5f9989404d88a94d35c531a06c964cd9a40dde94cc54c0aaaec5587"
            },
            "app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java": {
              "bytes": 14154,
              "sha256": "2f871e9813380b2d645b3ee636f67a7b3eae072f140163e14c7ec7ed60c562b2"
            },
            "app/src/dev/mixer/android/NativeEnvironmentV2.java": {
              "bytes": 15696,
              "sha256": "2cff6cc20d1c3c9ae751e217bba3192e315125f438312f29e933d0c79d339eb1"
            },
            "app/src/dev/mixer/android/NativeOwnerV2.java": {
              "bytes": 23743,
              "sha256": "056aa51d07e765b59a3859ce76090477a24211c973b63336406ff4b0d4102269"
            },
            "app/src/dev/mixer/android/NativeRenderer.java": {
              "bytes": 47378,
              "sha256": "fa523aa1c9cd2f11a77022b008a5e983c8fda697a93e2a76585c01f79f50d725"
            },
            "app/src/dev/mixer/android/OwnerLifecycleV2.java": {
              "bytes": 12473,
              "sha256": "4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6"
            },
            "app/src/dev/mixer/android/UiPacket.java": {
              "bytes": 8877,
              "sha256": "251577a7ce42c6931b694510cb5af0f418521ba9b0ef15c163da4b4bb0416c02"
            },
            "bridge/jni.c": {
              "bytes": 6072,
              "sha256": "a3d410605636074cc5fa01cc06ea65f75d9b71837752bb51506497d4634a9d80"
            },
            "bridge/mixer_android.h": {
              "bytes": 960,
              "sha256": "a9ba2ef9a84dbc619427d11f9db68d148467b362ffb75c035aed6a30aed2a18c"
            },
            "bridge/mixer_android_v2.h": {
              "bytes": 2265,
              "sha256": "0b89803de9693c4cdcfc73996e4b1ffcfc536420c98e6d575d36a934544803fc"
            },
            "contracts/android-profile-v1.json": {
              "bytes": 1899,
              "sha256": "b755b01f6969ea537e53fd8703fdf29166b1ef6f80997376e9158fcfe2398938"
            }
          },
          "default_descriptor": {
            "bytes": 9587,
            "sha256": "1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3"
          },
          "id": "mixer.android-source-pair.5",
          "schema": 1,
          "sdk_compatibility_sha256": "bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0",
          "sdk_files": {
            "Package.swift": {
              "bytes": 1334,
              "sha256": "ef1fda010474ab15208b413ffbac9723f87d3eb8ecffe752e6e578baa8cf6713"
            },
            "Sources/MixerCore/FeatureStore.swift": {
              "bytes": 4358,
              "sha256": "3fb26a1b1ce6a8863ea53d0c5751b3229ddad1113b486cb2c430d1d0dbcb385f"
            },
            "Sources/MixerCore/JSONInputGuard.swift": {
              "bytes": 8709,
              "sha256": "c01ae7ad973dcfc40d2b4ecef3fb8091d1c94484410621f28e77096e952de07c"
            },
            "Sources/MixerCore/Lifecycle.swift": {
              "bytes": 935,
              "sha256": "67d6dc636bb36ce765e5a0c4ee9db93d61ce7b17938e3d9a1a0ff84020927a91"
            },
            "Sources/MixerCore/Navigation.swift": {
              "bytes": 3101,
              "sha256": "6197c48eeb03aa6eeb94c3ca9a674c451deb83df9f662177014f70b866ef94d2"
            },
            "Sources/MixerCore/Resources.swift": {
              "bytes": 3301,
              "sha256": "2e9cd272144237f9fc76c3c7e46add88f43395a60ed83db24f5cd454ae7b7dca"
            },
            "Sources/MixerUI/AppearanceDefaultV1.swift": {
              "bytes": 2345,
              "sha256": "4ec1af1f904f427a17ae55e5937e017afbf3d8a4e6040749caee199e09bac1c9"
            },
            "Sources/MixerUI/AppearanceDefaultV2.swift": {
              "bytes": 10020,
              "sha256": "64daf8569dff496801b4886a03cce34aeb6af6fd9e5a76e3e0ea338b82dab05d"
            },
            "Sources/MixerUI/AppearanceDescriptorV1.swift": {
              "bytes": 34130,
              "sha256": "ad7f2b7c51041496197894829265bee7cfa8b8cb18d09abe5d816d9bf5259295"
            },
            "Sources/MixerUI/AppearanceDescriptorV2.swift": {
              "bytes": 51011,
              "sha256": "88683c11d8f3e22ddbb3e16601715d5761f6d677dbacc1d4dc9f66d7303512a1"
            },
            "Sources/MixerUI/AppearanceGeometryV2.swift": {
              "bytes": 8977,
              "sha256": "32d6a097e60e33393510a2d52df40b85d22afe7c5562504449c1f472e110cb72"
            },
            "Sources/MixerUI/AppearanceMetricMathV1.swift": {
              "bytes": 1508,
              "sha256": "fad0acfce796ae667bb01f6a29418298fe8197c7d79b2778d4fb3de79b348578"
            },
            "Sources/MixerUI/AppearanceResolutionV1.swift": {
              "bytes": 17046,
              "sha256": "cbaaeebad2ef3c4015ab4f917df3a35ed68541e52b8b12c8a27a3be07211fcf0"
            },
            "Sources/MixerUI/AppearanceResolutionV2.swift": {
              "bytes": 26464,
              "sha256": "4d416c443953c43ab3aab0500c392369fe369fa5ac95f086aa328da64885d50b"
            },
            "Sources/MixerUI/AppearanceValuesV1.swift": {
              "bytes": 12170,
              "sha256": "bb33ff6eb92603caf12e0cbd3166f291debc30ca8440696870ec523345fd6ccc"
            },
            "Sources/MixerUI/AppearanceValuesV2.swift": {
              "bytes": 17346,
              "sha256": "f96fe9d18ec2c2390268499c46e709e998e230d97840d02eb8e86094916ebc54"
            },
            "Sources/MixerUI/Authoring.swift": {
              "bytes": 6559,
              "sha256": "ef313b4f153199ce2b18d4cea75be7a61b82350dd4b17e7e3be84757898482c6"
            },
            "Sources/MixerUI/NativePacketV1.swift": {
              "bytes": 4703,
              "sha256": "ff099c2a1a57bd48c1cb7ed4fc6991dda7571d69457b0a3c7feb1cacb2cec18f"
            },
            "Sources/MixerUI/Protocol.swift": {
              "bytes": 9315,
              "sha256": "542c5076b4146f0229c89cec70848b42c0434637724f3ca9c42e1d45e2d55d42"
            },
            "Sources/MixerUI/Reconciliation.swift": {
              "bytes": 6561,
              "sha256": "c00a6e70b7550d0e5247b1b0bb5683f97b7fc93dbf42fe0363b4c4ceb7498403"
            },
            "Sources/MixerUI/SharedTextProfilesV1.swift": {
              "bytes": 3644,
              "sha256": "5547407727fc668e527f73d79765722009c9f38a931e23bfead20d979a763481"
            },
            "Sources/MixerUI/Validation.swift": {
              "bytes": 11627,
              "sha256": "c8b5002b0809a27a56513073c36c8b0b530f8f10678b2728ee0b308f021b6773"
            }
          },
          "wire": {
            "android_profile_id": "mixer-android-native-v1-development",
            "appearance_format": "mixer.native-appearance.2",
            "appearance_recipe": "measuredShared2",
            "document_schema": 1,
            "native_packet_schema": 1,
            "staged_C_ABI": "private-unversioned-v2-not-public-stable"
          }
        }
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
            throw MixerFailure("android.sdk-profile-required", "Android project predates source-pair admission. Explicitly migrate or create a fresh project with the matching first-party CLI/SDK distribution (\(profile.id)); local lock edits do not qualify a project.")
        }
        guard record == profile.lock else {
            throw MixerFailure("android.sdk-profile-mismatch", "Android source profile differs from \(profile.id). Explicitly migrate or create a fresh project with the matching first-party CLI/SDK distribution.")
        }
    }
    static func failure(_ detail: String) -> MixerFailure {
        MixerFailure("android.sdk-compatibility", "\(profile.id): \(detail). Install the matching first-party CLI/SDK distribution; local lock recomputation cannot authorize changed sources.")
    }
    private static func entries(_ directory: URL) throws -> [String] {
        try directoryType(directory)
        return try FileManager.default.contentsOfDirectory(atPath: directory.path)
    }
    private static func directoryType(_ url: URL) throws {
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: url.path),
              attrs[.type] as? FileAttributeType == .typeDirectory else { throw failure("Expected ordinary directory \(url.path)") }
    }
    /// Exact spelling is checked in the containing directory before touching an entry.
    private static func path(_ root: URL, _ relative: String, directory: Bool = false, identity: AndroidSDKSourceIdentity? = nil) throws -> URL {
        var current = root
        let components = relative.split(separator: "/").map(String.init)
        for (index, name) in components.enumerated() {
            guard try entries(current).contains(name) else { throw failure("Missing or case-aliased path \(relative)") }
            current.appendPathComponent(name)
            if index < components.count - 1 || directory { try directoryType(current) }
        }
        if let identity {
            guard let attrs = try? FileManager.default.attributesOfItem(atPath: current.path),
                  attrs[.type] as? FileAttributeType == .typeRegular,
                  (attrs[.size] as? NSNumber)?.intValue == identity.bytes else { throw failure("Expected ordinary pinned-size file \(relative)") }
        }
        return current
    }
    private static func closed(_ root: URL, _ relative: String, files: [String: AndroidSDKSourceIdentity]) throws {
        let directory = try path(root, relative, directory: true)
        let prefix = relative + "/"
        let expected = Set(files.keys.filter { $0.hasPrefix(prefix) }.map { String($0.dropFirst(prefix.count).split(separator: "/")[0]) })
        guard Set(try entries(directory)) == expected else { throw failure("Unexpected or missing directory inventory \(relative)") }
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
            guard name == "Package.swift" else { throw failure("Reserved SDK manifest namespace \(name)") }
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
    static func bounded(_ url: URL, _ identity: AndroidSDKSourceIdentity) throws -> Data {
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        let bytes = try handle.read(upToCount: identity.bytes + 1) ?? Data()
        guard bytes.count == identity.bytes, SourceDigest.sha256(bytes) == identity.sha256 else { throw failure("Pinned bytes differ at \(url.path)") }
        return bytes
    }
    private static func map(_ root: URL, _ files: [String: AndroidSDKSourceIdentity], input: Bool = false) throws -> String {
        var records = Data()
        for relative in files.keys.sorted() {
            let source = input && relative.hasPrefix("Sources/") ? "engine/" + relative : relative
            let identity = files[relative]!
            _ = try bounded(root.appendingPathComponent(source), identity)
            records.append(Data((relative + "\0" + identity.sha256 + "\n").utf8))
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
