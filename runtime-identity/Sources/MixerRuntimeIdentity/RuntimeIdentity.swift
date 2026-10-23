import Foundation
import MixerUpdates

/// Validated description of trusted native build inputs. This is deliberately
/// not a verified release, signature, build attestation or executable VM token.
public struct RuntimeIdentity: Sendable {
    public static let maximumDescriptorBytes = 131_072
    public static let domain = "mixer.runtime.identity.v1\0"
    public let fingerprint: String
    public let canonicalCBOR: Data
    public let descriptor: CanonicalValue
    public let installedRuntime: InstalledRuntime
    public let execution: ExecutionPolicy

    public struct ExecutionPolicy: Sendable {
        public let profile: String
        public let startupExport: String
        public let operandStack: UInt32
        public let callDepth: UInt32
        public let hostCalls: UInt64
    }

    public init(json: Data) throws {
        let value = try StrictJSON.decode(CanonicalValue.self, from: json, maximumBytes: Self.maximumDescriptorBytes)
        let root = try Fields(value, keys: ["schema", "application", "platform", "engine", "toolchain", "dependencies", "capabilities", "build", "execution"])
        guard try root.number("schema", 1...1) == 1 else { throw identityError("schema") }

        let app = try Fields(root.value("application"), keys: ["organization", "project", "app", "environment", "bundle_id"])
        let organization = try app.identifier("organization"), project = try app.identifier("project")
        let appID = try app.identifier("app"), environment = try app.identifier("environment")
        _ = try app.identifier("bundle_id")

        let platform = try Fields(root.value("platform"), keys: ["os", "architecture", "environment", "minimum_os", "target"])
        let os = try platform.oneOf("os", ["ios", "android"])
        let architecture = try platform.oneOf("architecture", ["arm64", "x86_64"])
        let deployment = try platform.oneOf("environment", ["device", "simulator"])
        let minimumOS = try platform.identifier("minimum_os")
        let target = try platform.identifier("target")
        try Self.checkPlatform(os: os, architecture: architecture, environment: deployment, minimumOS: minimumOS, target: target)

        let engine = try Fields(root.value("engine"), keys: ["version", "source_sha256", "artifact_sha256", "profile", "guest_abi", "ui_schema", "ui_contract_sha256", "capability_contract_sha256"])
        _ = try engine.label("version")
        try engine.digests(["source_sha256", "artifact_sha256", "ui_contract_sha256", "capability_contract_sha256"])
        let profile = try engine.oneOf("profile", ["mixer-integer-v1", "mixer-numeric-v2", "mixer-table-memory-v3"])
        let guestABI = try engine.number("guest_abi", 1...1), uiSchema = try engine.number("ui_schema", 1...1)

        let toolchain = try Fields(root.value("toolchain"), keys: ["compiler_version", "compiler_sha256", "sdk_version", "sdk_sha256", "build_tools_sha256"])
        _ = try toolchain.label("compiler_version"); _ = try toolchain.label("sdk_version")
        try toolchain.digests(["compiler_sha256", "sdk_sha256", "build_tools_sha256"])

        var previousDependency: String?
        for entry in try root.list("dependencies", maximum: 128) {
            let dependency = try Fields(entry, keys: ["id", "version", "artifact_sha256"])
            let id = try dependency.identifier("id")
            try Self.next(id, previous: &previousDependency)
            _ = try dependency.label("version"); try dependency.digests(["artifact_sha256"])
        }
        var capabilityHashes: [String: String] = [:]
        var previousCapability: String?
        for entry in try root.list("capabilities", maximum: 128) {
            let capability = try Fields(entry, keys: ["id", "schema_sha256", "native_sha256", "configuration_sha256", "grants_sha256"])
            let id = try capability.identifier("id")
            try Self.next(id, previous: &previousCapability)
            try capability.digests(["schema_sha256", "native_sha256", "configuration_sha256", "grants_sha256"])
            capabilityHashes[id] = try capability.label("schema_sha256")
        }

        let build = try Fields(root.value("build"), keys: ["configuration", "settings_sha256", "generated_bridge_sha256", "link_inputs_sha256", "native_fallback_sha256", "permissions_sha256", "entitlements_sha256", "trust_roots_sha256", "resource_policy_sha256"])
        _ = try build.oneOf("configuration", ["debug", "release"])
        try build.digests(["settings_sha256", "generated_bridge_sha256", "link_inputs_sha256", "native_fallback_sha256", "permissions_sha256", "entitlements_sha256", "trust_roots_sha256", "resource_policy_sha256"])

        let policy = try Fields(root.value("execution"), keys: ["startup_export", "startup_ms", "max_payload_bytes", "memory_bytes", "fuel", "operand_stack", "call_depth", "host_calls", "state_schema", "protocol"])
        let startup = try policy.exportName("startup_export")
        let startupMS = try policy.number("startup_ms", 1...60_000)
        let payload = try policy.number("max_payload_bytes", 1...4_194_304)
        let memory = try policy.number("memory_bytes", 1...4_194_304)
        let fuel = try policy.number("fuel", 1...1_000_000)
        let operands = try policy.number("operand_stack", 1...4096)
        let depth = try policy.number("call_depth", 1...64)
        let hostCalls = try policy.number("host_calls", 0...1024)
        let state = try policy.number("state_schema", 0...UInt64.max)
        let protocolVersion = try policy.number("protocol", 1...2)
        guard protocolVersion == 2 || capabilityHashes.isEmpty else { throw identityError("capability_protocol") }

        let cbor = try value.canonicalCBOR()
        guard cbor.count <= Self.maximumDescriptorBytes else { throw identityError("size") }
        let fingerprint = ReleaseVerifier.sha256(Data(Self.domain.utf8) + cbor)
        self.fingerprint = fingerprint; canonicalCBOR = cbor; descriptor = value
        installedRuntime = InstalledRuntime(
            scope: UpdateScope(organization: organization, project: project, app: appID, environment: environment, platform: os),
            runtime: fingerprint, protocolVersion: protocolVersion, guestABI: guestABI, uiSchema: uiSchema,
            capabilityHashes: capabilityHashes, stateVersion: state, maxPayloadBytes: payload,
            limits: ResourceLimits(memoryBytes: memory, fuel: fuel, startupMilliseconds: startupMS))
        execution = ExecutionPolicy(profile: profile, startupExport: startup, operandStack: UInt32(operands), callDepth: UInt32(depth), hostCalls: hostCalls)
    }

    private static func next(_ id: String, previous: inout String?) throws {
        guard previous.map({ $0.utf8.lexicographicallyPrecedes(id.utf8) }) ?? true else { throw identityError("order") }
        previous = id
    }

    private static func checkPlatform(os: String, architecture: String, environment: String, minimumOS: String, target: String) throws {
        if os == "ios" {
            let parts = minimumOS.split(separator: ".", omittingEmptySubsequences: false)
            guard (2...3).contains(parts.count), parts.allSatisfy({ part in
                guard let n = UInt16(part) else { return false }
                return String(n) == part
            }), let major = UInt16(parts[0]), major >= 17,
            environment == "simulator" || architecture == "arm64" else { throw identityError("platform") }
            let suffix = environment == "simulator" ? "-simulator" : ""
            guard target == "\(architecture)-apple-ios\(minimumOS)\(suffix)" else { throw identityError("target") }
        } else {
            guard let api = UInt16(minimumOS), api >= 28, String(api) == minimumOS,
                  environment == "device" || environment == "simulator" else { throw identityError("platform") }
            let arch = architecture == "arm64" ? "aarch64" : "x86_64"
            guard target == "\(arch)-unknown-linux-android\(minimumOS)" else { throw identityError("target") }
        }
    }
}

private func identityError(_ code: String) -> UpdateError { UpdateError("identity.\(code)", "Invalid installed runtime identity: \(code)") }

private struct Fields {
    let fields: [String: CanonicalValue]
    init(_ value: CanonicalValue, keys: Set<String>) throws {
        guard let fields = value.object, Set(fields.keys) == keys else { throw identityError("fields") }
        self.fields = fields
    }
    func value(_ key: String) throws -> CanonicalValue {
        guard let value = fields[key] else { throw identityError("missing") }; return value
    }
    func label(_ key: String) throws -> String {
        guard let text = try value(key).text, !text.isEmpty, text.utf8.count <= 256,
              text.utf8.allSatisfy({ (32...126).contains($0) }), text.first != " ", text.last != " " else { throw identityError("text") }
        return text
    }
    func identifier(_ key: String) throws -> String {
        let text = try label(key)
        guard text.utf8.count <= 128, text.utf8.allSatisfy({ (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || [45, 46, 95].contains($0) }) else { throw identityError("identifier") }
        return text
    }
    func exportName(_ key: String) throws -> String {
        // Original Wasm export names may be Unicode. Preserve exact UTF-8 without
        // normalizing spelling; native linker/source inputs are separately hashed.
        guard let text = try value(key).text, !text.isEmpty, text.utf8.count <= 4096,
              !text.unicodeScalars.contains(where: { $0.value < 32 || $0.value == 127 }) else { throw identityError("export") }
        return text
    }
    func oneOf(_ key: String, _ choices: Set<String>) throws -> String {
        let text = try label(key); guard choices.contains(text) else { throw identityError("version") }; return text
    }
    func number(_ key: String, _ bounds: ClosedRange<UInt64>) throws -> UInt64 {
        guard let n = try value(key).uint, bounds.contains(n) else { throw identityError("number") }; return n
    }
    func digests(_ keys: [String]) throws {
        for key in keys {
            let text = try label(key)
            guard text.utf8.count == 64, text.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else { throw identityError("digest") }
        }
    }
    func list(_ key: String, maximum: Int) throws -> [CanonicalValue] {
        guard case let .array(values) = try value(key), values.count <= maximum else { throw identityError("collection") }; return values
    }
}
