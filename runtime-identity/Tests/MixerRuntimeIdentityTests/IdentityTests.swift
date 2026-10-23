import Foundation
import Testing
import MixerUpdates
import MixerRuntimeIdentity

private struct Vector: Decodable {
    let name: String
    let descriptor: CanonicalValue
    let canonicalCBOR: String
    let fingerprint: String
}
private func vectors() throws -> [Vector] {
    let url = try #require(Bundle.module.url(forResource: "vectors", withExtension: "json", subdirectory: "Fixtures"))
    return try JSONDecoder().decode([Vector].self, from: Data(contentsOf: url))
}
private func json(_ value: CanonicalValue) throws -> Data { try JSONEncoder().encode(value) }
private func setting(_ value: CanonicalValue, _ path: [String], _ replacement: CanonicalValue?) -> CanonicalValue {
    guard !path.isEmpty else { return replacement ?? value }
    if var object = value.object {
        let first = path[0]
        if path.count == 1 { object[first] = replacement }
        else if let child = object[first] { object[first] = setting(child, Array(path.dropFirst()), replacement) }
        return .object(object)
    }
    if case var .array(array) = value, let index = Int(path[0]), index < array.count {
        array[index] = setting(array[index], Array(path.dropFirst()), replacement)
        return .array(array)
    }
    return value
}
private func leaves(_ value: CanonicalValue, path: [String] = []) -> [([String], CanonicalValue)] {
    switch value {
    case let .object(object): return object.flatMap { leaves($0.value, path: path + [$0.key]) }
    case let .array(array): return array.enumerated().flatMap { leaves($0.element, path: path + [String($0.offset)]) }
    default: return [(path, value)]
    }
}
private func rejects(_ value: CanonicalValue) throws {
    let bytes = try json(value)
    #expect(throws: (any Error).self) { try RuntimeIdentity(json: bytes) }
}

struct RuntimeIdentityTests {
    @Test func independentCanonicalCBORAndHashVectors() throws {
        for vector in try vectors() {
            let identity = try RuntimeIdentity(json: json(vector.descriptor))
            #expect(identity.fingerprint == vector.fingerprint, "\(vector.name)")
            #expect(identity.canonicalCBOR.map { String(format: "%02x", $0) }.joined() == vector.canonicalCBOR)
            #expect(identity.installedRuntime.runtime == vector.fingerprint)
            #expect(identity.installedRuntime.scope.app == "test-app")
            #expect(identity.installedRuntime.guestABI == 1 && identity.installedRuntime.uiSchema == 1)
        }
    }

    @Test func objectOrderWhitespaceAndEscapesDoNotAlterIdentity() throws {
        let value = try #require(vectors().first).descriptor
        let expected = try RuntimeIdentity(json: json(value))
        let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let spelling = String(decoding: try encoder.encode(value), as: UTF8.self).replacingOccurrences(of: "test-app", with: "test-\\u0061pp")
        #expect(try RuntimeIdentity(json: Data((" \n" + spelling + "\t").utf8)).fingerprint == expected.fingerprint)
        #expect(expected.fingerprint != ReleaseVerifier.sha256(expected.canonicalCBOR))
        #expect(expected.fingerprint != ReleaseVerifier.sha256(Data("mixer.artifact.v1\0".utf8) + expected.canonicalCBOR))
    }

    @Test func everyDescriptorLeafAffectsIdentityOrIsRejected() throws {
        // Covers all capability grant/native/config and dependency identities as
        // well as engine, toolchain, permission, scope and execution fields.
        let vector = try #require(vectors().first { $0.name == "declared-http-capability" })
        for (path, leaf) in leaves(vector.descriptor) {
            let changed: CanonicalValue
            switch leaf {
            case let .text(text):
                changed = .text(path.last!.hasSuffix("_sha256") ? String(repeating: text == String(repeating: "a", count: 64) ? "b" : "a", count: 64) : text + "x")
            case let .uint(n): changed = .uint(n + 1)
            default: Issue.record("unexpected test leaf"); continue
            }
            do {
                let result = try RuntimeIdentity(json: json(setting(vector.descriptor, path, changed)))
                #expect(result.fingerprint != vector.fingerprint, "unchanged identity at \(path)")
            } catch { /* Invalid changes must fail before publishing identity. */ }
            try rejects(setting(vector.descriptor, path, nil))
        }
    }

    @Test func rejectsAmbiguousJSONAndUnsupportedFields() throws {
        let bytes = try json(#require(vectors().first).descriptor)
        let text = String(decoding: bytes, as: UTF8.self)
        for changed in ["{\"schema\":1," + text.dropFirst(), text.replacingOccurrences(of: "\"schema\":1", with: "\"Schema\":1"),
                        text.replacingOccurrences(of: "\"schema\":1", with: "\"schema\":1.0"),
                        text.replacingOccurrences(of: "\"schema\":1", with: "\"schema\":1e0"), text + "{}"] {
            #expect(throws: (any Error).self) { try RuntimeIdentity(json: Data(changed.utf8)) }
        }
        let value = try #require(vectors().first).descriptor
        try rejects(setting(value, ["native_extra"], .text("ignored is unsafe")))
        try rejects(setting(value, ["build", "extra"], .boolean(true)))
        try rejects(setting(value, ["build", "permissions_sha256"], .text(String(repeating: "A", count: 64))))
        try rejects(setting(value, ["application", "app"], .text("app/other")))
        try rejects(setting(value, ["execution", "startup_export"], .text("run\0other")))
        #expect(throws: (any Error).self) { try RuntimeIdentity(json: Data(repeating: 32, count: RuntimeIdentity.maximumDescriptorBytes + 1)) }
    }

    @Test func platformArchitectureAndTargetAreBoundTogether() throws {
        let value = try #require(vectors().first).descriptor
        for (key, text) in [("os", "macos"), ("architecture", "x86_64"), ("environment", "simulator"), ("minimum_os", "017.0"), ("minimum_os", "16.0"), ("minimum_os", "17"), ("target", "aarch64-unknown-linux-android28")] {
            try rejects(setting(value, ["platform", key], .text(text)))
        }
        let android = try #require(vectors().first { $0.name == "android-device" }).descriptor
        try rejects(setting(android, ["platform", "minimum_os"], .text("27")))
        try rejects(setting(android, ["platform", "minimum_os"], .text("028")))
        try rejects(setting(android, ["platform", "target"], .text("arm64-apple-ios17.0")))
    }

    @Test func duplicatesAndUnsortedNativeRecordsCannotAlias() throws {
        let value = try #require(vectors().first { $0.name == "declared-http-capability" }).descriptor
        guard case let .array(dependencies) = value.object?["dependencies"], case let .array(capabilities) = value.object?["capabilities"] else { Issue.record("fixture shape"); return }
        try rejects(setting(value, ["dependencies"], .array(Array(dependencies.reversed()))))
        try rejects(setting(value, ["dependencies"], .array(dependencies + [dependencies[0]])))
        try rejects(setting(value, ["capabilities"], .array(capabilities + capabilities)))
        try rejects(setting(value, ["dependencies"], .array(Array(repeating: dependencies[0], count: 129))))
        try rejects(setting(value, ["execution", "protocol"], .uint(1)))
    }

    @Test func executionCeilingsOnlyNarrowAndConstructExactHostPolicy() throws {
        let value = try #require(vectors().first).descriptor
        let fields: [(String, UInt64)] = [("startup_ms", 60_000), ("max_payload_bytes", 4_194_304), ("memory_bytes", 4_194_304), ("fuel", 1_000_000), ("operand_stack", 4096), ("call_depth", 64), ("host_calls", 1024), ("protocol", 2)]
        for (name, maximum) in fields {
            _ = try RuntimeIdentity(json: json(setting(value, ["execution", name], .uint(maximum))))
            try rejects(setting(value, ["execution", name], .uint(maximum + 1)))
            if name != "host_calls" { try rejects(setting(value, ["execution", name], .uint(0))) }
        }
        var narrowed = value
        for (name, n) in [("fuel", UInt64(123)), ("memory_bytes", 65536), ("startup_ms", 22), ("max_payload_bytes", 999), ("state_schema", 7), ("operand_stack", 32), ("call_depth", 4), ("host_calls", 0)] {
            narrowed = setting(narrowed, ["execution", name], .uint(n))
        }
        let identity = try RuntimeIdentity(json: json(narrowed))
        #expect(identity.installedRuntime.limits == ResourceLimits(memoryBytes: 65536, fuel: 123, startupMilliseconds: 22))
        #expect(identity.installedRuntime.maxPayloadBytes == 999 && identity.installedRuntime.stateVersion == 7)
        #expect(identity.execution.operandStack == 32 && identity.execution.callDepth == 4 && identity.execution.hostCalls == 0)
    }

    @Test func immutableIdentityOwnsItsDescriptorSnapshot() throws {
        var bytes = try json(#require(vectors().first).descriptor)
        let identity = try RuntimeIdentity(json: bytes), expected = identity.fingerprint
        bytes.resetBytes(in: bytes.startIndex..<bytes.endIndex)
        #expect(identity.fingerprint == expected)
        #expect(ReleaseVerifier.sha256(Data(RuntimeIdentity.domain.utf8) + identity.canonicalCBOR) == expected)
        var cbor = identity.canonicalCBOR; cbor.removeAll()
        #expect(!identity.canonicalCBOR.isEmpty)
    }
}
