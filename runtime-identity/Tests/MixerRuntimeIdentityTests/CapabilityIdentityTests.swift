import Foundation
import Testing
import MixerUpdates
import MixerRuntimeIdentity

private struct CapabilityVector: Decodable {
    let name: String
    let descriptor: CanonicalValue
    let canonicalCBOR: String
    let fingerprint: String
}
private func capabilityVectors() throws -> [CapabilityVector] {
    let url = try #require(Bundle.module.url(forResource: "vectors-v2", withExtension: "json", subdirectory: "Fixtures"))
    return try JSONDecoder().decode([CapabilityVector].self, from: Data(contentsOf: url))
}
private func jsonV2(_ value: CanonicalValue) throws -> Data { try JSONEncoder().encode(value) }
private func settingV2(_ value: CanonicalValue, _ path: [String], _ replacement: CanonicalValue?) -> CanonicalValue {
    guard !path.isEmpty else { return replacement ?? value }
    if var object = value.object {
        let first = path[0]
        if path.count == 1 { object[first] = replacement }
        else if let child = object[first] { object[first] = settingV2(child, Array(path.dropFirst()), replacement) }
        return .object(object)
    }
    if case var .array(array) = value, let index = Int(path[0]), index < array.count {
        array[index] = settingV2(array[index], Array(path.dropFirst()), replacement)
        return .array(array)
    }
    return value
}
private func leavesV2(_ value: CanonicalValue, path: [String] = []) -> [([String], CanonicalValue)] {
    switch value {
    case let .object(object): return object.flatMap { leavesV2($0.value, path: path + [$0.key]) }
    case let .array(array): return array.enumerated().flatMap { leavesV2($0.element, path: path + [String($0.offset)]) }
    default: return [(path, value)]
    }
}
private func rejectsV2(_ value: CanonicalValue) throws {
    let bytes = try jsonV2(value)
    #expect(throws: (any Error).self) { try CapabilityRuntimeIdentity(json: bytes) }
}

struct CapabilityRuntimeIdentityTests {
    @Test func externalNoCopyInputDoesNotRetainBorrowedBacking() throws {
        let bytes = try jsonV2(#require(capabilityVectors().first).descriptor)
        let pointer = UnsafeMutableRawPointer.allocate(byteCount: bytes.count, alignment: 1)
        defer { pointer.deallocate() }
        bytes.withUnsafeBytes { raw in pointer.copyMemory(from: raw.baseAddress!, byteCount: raw.count) }
        let borrowed = Data(bytesNoCopy: pointer, count: bytes.count, deallocator: .none)
        let identity = try CapabilityRuntimeIdentity(json: borrowed)
        let expected = identity.fingerprint
        pointer.initializeMemory(as: UInt8.self, repeating: 32, count: bytes.count)
        #expect(identity.fingerprint == expected)
        #expect(ReleaseVerifier.sha256(Data(CapabilityRuntimeIdentity.domain.utf8) + identity.canonicalCBOR) == expected)
        #expect(throws: (any Error).self) { try CapabilityRuntimeIdentity(json: borrowed) }
    }

    @Test func explicitVersionsCannotDowngradeOrAuthorize() throws {
        let value = try #require(capabilityVectors().first).descriptor
        let identity = try CapabilityRuntimeIdentity(json: jsonV2(value))
        #expect(identity.installedRuntime.protocolVersion == 3)
        #expect(throws: (any Error).self) { try RuntimeIdentity(json: jsonV2(value)) }
        #expect(throws: (any Error).self) { try ReleaseVerifier(host: identity.installedRuntime, roots: []) }
        let legacyURL = try #require(Bundle.module.url(forResource: "vectors", withExtension: "json", subdirectory: "Fixtures"))
        let legacy = try JSONDecoder().decode([CapabilityVector].self, from: Data(contentsOf: legacyURL))
        for vector in legacy { try rejectsV2(vector.descriptor) }
    }

    @Test func exactContractBindingsAndNewResourceBoundaries() throws {
        let value = try #require(capabilityVectors().first).descriptor
        for key in ["contract_sha256", "transport_sha256", "native_header_sha256"] {
            try rejectsV2(settingV2(value, ["capability_execution", key], .text(String(repeating: "a", count: 64))))
        }
        let bounds: [(String, UInt64)] = [("maximum_requests", 8), ("reservation_bytes", 8388608), ("timeout_milliseconds", 30000), ("turn_milliseconds", 50)]
        for (key, upper) in bounds {
            for n in [UInt64(1), upper] { _ = try CapabilityRuntimeIdentity(json: jsonV2(settingV2(value, ["capability_execution", key], .uint(n)))) }
            for n in [UInt64(0), upper+1] { try rejectsV2(settingV2(value, ["capability_execution", key], .uint(n))) }
        }
        for n in [UInt64(1),65535,65536,65537,4194304] {
            let identity = try CapabilityRuntimeIdentity(json: jsonV2(settingV2(value, ["execution", "memory_bytes"], .uint(n))))
            #expect(identity.execution.maximumMemoryPages == UInt32(n/65536))
            #expect(identity.installedRuntime.limits.memoryBytes == n)
        }
        try rejectsV2(settingV2(value, ["engine", "profile"], .text("mixer-integer-v1")))
        try rejectsV2(settingV2(value, ["engine", "guest_abi"], .uint(1)))
        try rejectsV2(settingV2(value, ["execution", "protocol"], .uint(2)))
        let both = try #require(capabilityVectors().first { $0.name == "both" }).descriptor
        try rejectsV2(settingV2(both, ["capabilities", "0", "schema_sha256"], .text(CapabilityRuntimeIdentity.capabilitySchemas["storage.keyValue.v1"]!)))
        try rejectsV2(settingV2(both, ["capabilities", "0", "id"], .text("native.other.v1")))
    }

    @Test func independentCanonicalCBORAndHashCapabilityVectors() throws {
        for vector in try capabilityVectors() {
            let identity = try CapabilityRuntimeIdentity(json: jsonV2(vector.descriptor))
            #expect(identity.fingerprint == vector.fingerprint, "\(vector.name)")
            #expect(identity.canonicalCBOR.map { String(format: "%02x", $0) }.joined() == vector.canonicalCBOR)
            #expect(identity.installedRuntime.runtime == vector.fingerprint)
            #expect(identity.installedRuntime.scope.app == "test-app")
            #expect(identity.installedRuntime.guestABI == 2 && identity.installedRuntime.uiSchema == 1)
        }
    }

    @Test func objectOrderWhitespaceAndEscapesDoNotAlterIdentity() throws {
        let value = try #require(capabilityVectors().first).descriptor
        let expected = try CapabilityRuntimeIdentity(json: jsonV2(value))
        let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let spelling = String(decoding: try encoder.encode(value), as: UTF8.self).replacingOccurrences(of: "test-app", with: "test-\\u0061pp")
        #expect(try CapabilityRuntimeIdentity(json: Data((" \n" + spelling + "\t").utf8)).fingerprint == expected.fingerprint)
        #expect(expected.fingerprint != ReleaseVerifier.sha256(expected.canonicalCBOR))
        #expect(expected.fingerprint != ReleaseVerifier.sha256(Data("mixer.runtime.identity.v1\0".utf8) + expected.canonicalCBOR))
    }

    @Test func everyDescriptorLeafAffectsIdentityOrIsRejected() throws {
        // Covers all capability grant/native/config and dependency identities as
        // well as engine, toolchain, permission, scope and execution fields.
        let vector = try #require(capabilityVectors().first { $0.name == "both" })
        for (path, leaf) in leavesV2(vector.descriptor) {
            let changed: CanonicalValue
            switch leaf {
            case let .text(text):
                changed = .text(path.last!.hasSuffix("_sha256") ? String(repeating: text == String(repeating: "a", count: 64) ? "b" : "a", count: 64) : text + "x")
            case let .uint(n): changed = .uint(n + 1)
            default: Issue.record("unexpected test leaf"); continue
            }
            do {
                let result = try CapabilityRuntimeIdentity(json: jsonV2(settingV2(vector.descriptor, path, changed)))
                #expect(result.fingerprint != vector.fingerprint, "unchanged identity at \(path)")
            } catch { /* Invalid changes must fail before publishing identity. */ }
            try rejectsV2(settingV2(vector.descriptor, path, nil))
        }
    }

    @Test func rejectsAmbiguousJSONAndUnsupportedFields() throws {
        let bytes = try jsonV2(#require(capabilityVectors().first).descriptor)
        let text = String(decoding: bytes, as: UTF8.self)
        for changed in ["{\"schema\":2," + text.dropFirst(), text.replacingOccurrences(of: "\"schema\":2", with: "\"Schema\":2"),
                        text.replacingOccurrences(of: "\"schema\":2", with: "\"schema\":2.0"),
                        text.replacingOccurrences(of: "\"schema\":2", with: "\"schema\":2e0"), text + "{}"] {
            #expect(throws: (any Error).self) { try CapabilityRuntimeIdentity(json: Data(changed.utf8)) }
        }
        let value = try #require(capabilityVectors().first).descriptor
        try rejectsV2(settingV2(value, ["native_extra"], .text("ignored is unsafe")))
        try rejectsV2(settingV2(value, ["build", "extra"], .boolean(true)))
        try rejectsV2(settingV2(value, ["build", "permissions_sha256"], .text(String(repeating: "A", count: 64))))
        try rejectsV2(settingV2(value, ["application", "app"], .text("app/other")))
        try rejectsV2(settingV2(value, ["execution", "startup_export"], .text("run\0other")))
        #expect(throws: (any Error).self) { try CapabilityRuntimeIdentity(json: Data(repeating: 32, count: CapabilityRuntimeIdentity.maximumDescriptorBytes + 1)) }
    }

    @Test func platformArchitectureAndTargetAreBoundTogether() throws {
        let value = try #require(capabilityVectors().first).descriptor
        for (key, text) in [("os", "macos"), ("architecture", "x86_64"), ("environment", "simulator"), ("minimum_os", "017.0"), ("minimum_os", "16.0"), ("minimum_os", "17"), ("target", "aarch64-unknown-linux-android28")] {
            try rejectsV2(settingV2(value, ["platform", key], .text(text)))
        }
        let android = try #require(capabilityVectors().first { $0.name == "android-device" }).descriptor
        try rejectsV2(settingV2(android, ["platform", "minimum_os"], .text("27")))
        try rejectsV2(settingV2(android, ["platform", "minimum_os"], .text("028")))
        try rejectsV2(settingV2(android, ["platform", "target"], .text("arm64-apple-ios17.0")))
    }

    @Test func duplicatesAndUnsortedNativeRecordsCannotAlias() throws {
        let value = try #require(capabilityVectors().first { $0.name == "both" }).descriptor
        guard case let .array(dependencies) = value.object?["dependencies"], case let .array(capabilities) = value.object?["capabilities"] else { Issue.record("fixture shape"); return }
        try rejectsV2(settingV2(value, ["dependencies"], .array(Array(dependencies.reversed()))))
        try rejectsV2(settingV2(value, ["dependencies"], .array(dependencies + [dependencies[0]])))
        try rejectsV2(settingV2(value, ["capabilities"], .array(capabilities + capabilities)))
        try rejectsV2(settingV2(value, ["dependencies"], .array(Array(repeating: dependencies[0], count: 129))))
        try rejectsV2(settingV2(value, ["execution", "protocol"], .uint(1)))
    }

    @Test func executionCeilingsOnlyNarrowAndConstructExactHostPolicy() throws {
        let value = try #require(capabilityVectors().first).descriptor
        let fields: [(String, UInt64)] = [("startup_ms", 60_000), ("max_payload_bytes", 4_194_304), ("memory_bytes", 4_194_304), ("fuel", 1_000_000), ("operand_stack", 4096), ("call_depth", 64), ("host_calls", 1024), ("protocol", 3)]
        for (name, maximum) in fields {
            _ = try CapabilityRuntimeIdentity(json: jsonV2(settingV2(value, ["execution", name], .uint(maximum))))
            try rejectsV2(settingV2(value, ["execution", name], .uint(maximum + 1)))
            if name != "host_calls" { try rejectsV2(settingV2(value, ["execution", name], .uint(0))) }
        }
        var narrowed = value
        for (name, n) in [("fuel", UInt64(123)), ("memory_bytes", 65536), ("startup_ms", 22), ("max_payload_bytes", 999), ("state_schema", 7), ("operand_stack", 32), ("call_depth", 4), ("host_calls", 0)] {
            narrowed = settingV2(narrowed, ["execution", name], .uint(n))
        }
        let identity = try CapabilityRuntimeIdentity(json: jsonV2(narrowed))
        #expect(identity.installedRuntime.limits == ResourceLimits(memoryBytes: 65536, fuel: 123, startupMilliseconds: 22))
        #expect(identity.installedRuntime.maxPayloadBytes == 999 && identity.installedRuntime.stateVersion == 7)
        #expect(identity.execution.operandStack == 32 && identity.execution.callDepth == 4 && identity.execution.hostCalls == 0)
    }

    @Test func immutableIdentityOwnsItsDescriptorSnapshot() throws {
        var bytes = try jsonV2(#require(capabilityVectors().first).descriptor)
        let identity = try CapabilityRuntimeIdentity(json: bytes), expected = identity.fingerprint
        bytes.resetBytes(in: bytes.startIndex..<bytes.endIndex)
        #expect(identity.fingerprint == expected)
        #expect(ReleaseVerifier.sha256(Data(CapabilityRuntimeIdentity.domain.utf8) + identity.canonicalCBOR) == expected)
        var cbor = identity.canonicalCBOR; cbor.removeAll()
        #expect(!identity.canonicalCBOR.isEmpty)
    }
}
