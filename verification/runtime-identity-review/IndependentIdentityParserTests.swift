import Foundation
import Testing
import MixerUpdates
import MixerRuntimeIdentity

private struct IdentityReviewVector: Decodable { let descriptor: CanonicalValue }
private func reviewDescriptor() throws -> CanonicalValue {
    let path = try #require(Bundle.module.url(forResource: "vectors", withExtension: "json", subdirectory: "Fixtures"))
    return try #require(JSONDecoder().decode([IdentityReviewVector].self, from: Data(contentsOf: path)).first).descriptor
}
private func reviewJSON(_ value: CanonicalValue) throws -> Data {
    let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
    return try encoder.encode(value)
}
private func reviewSet(_ value: CanonicalValue, _ path: [String], _ replacement: CanonicalValue) -> CanonicalValue {
    if path.isEmpty { return replacement }
    if var object = value.object {
        object[path[0]] = path.count == 1 ? replacement : reviewSet(object[path[0]]!, Array(path.dropFirst()), replacement)
        return .object(object)
    }
    if case var .array(array) = value, let index = Int(path[0]) {
        array[index] = reviewSet(array[index], Array(path.dropFirst()), replacement)
        return .array(array)
    }
    return value
}
private func reviewIdentityRejects(_ value: CanonicalValue) throws {
    let data = try reviewJSON(value)
    #expect(throws: (any Error).self) { try RuntimeIdentity(json: data) }
}
private func reviewRawRejects(_ data: Data) { #expect(throws: (any Error).self) { try RuntimeIdentity(json: data) } }

struct IndependentIdentityParserTests {
    @Test func escapedDuplicatesAtRootAndNestedObjectsAreRejected() throws {
        let text = String(decoding: try reviewJSON(reviewDescriptor()), as: UTF8.self)
        for (literal, escaped) in [("schema", "\\u0073chema"), ("application", "\\u0061pplication"),
                                   ("app", "\\u0061pp"), ("compiler_version", "compiler_\\u0076ersion"),
                                   ("startup_export", "startup_\\u0065xport"), ("artifact_sha256", "artifact_\\u0073ha256")] {
            let prefix = "\"" + literal + "\":"
            let raw = text.replacingOccurrences(of: prefix, with: "\"" + escaped + "\":null," + prefix)
            #expect(raw != text)
            reviewRawRejects(Data(raw.utf8))
        }
        reviewRawRejects(Data([0xef, 0xbb, 0xbf]) + Data(text.utf8))
        reviewRawRejects(Data((text + " {}").utf8))
    }

    @Test func invalidUTF8SurrogatesAndControlCharactersCannotAliasExports() throws {
        let base = reviewSet(try reviewDescriptor(), ["execution", "startup_export"], .text("REVIEW_EXPORT"))
        let text = String(decoding: try reviewJSON(base), as: UTF8.self)
        let parts = text.components(separatedBy: "REVIEW_EXPORT")
        #expect(parts.count == 2)
        for bytes: [UInt8] in [[0xff], [0xc0, 0xaf], [0xed, 0xa0, 0x80], [0xe2, 0x82], [0], [10], [127]] {
            reviewRawRejects(Data(parts[0].utf8) + Data(bytes) + Data(parts[1].utf8))
        }
        for spelling in ["\\ud800", "\\udc00", "\\ud800\\u0061", "\\u0000", "\\u001f", "\\u007f"] {
            reviewRawRejects(Data(text.replacingOccurrences(of: "REVIEW_EXPORT", with: spelling).utf8))
        }
        let literal = try RuntimeIdentity(json: reviewJSON(reviewSet(base, ["execution", "startup_export"], .text("😀"))))
        let escaped = try RuntimeIdentity(json: Data(text.replacingOccurrences(of: "REVIEW_EXPORT", with: "\\ud83d\\ude00").utf8))
        #expect(literal.fingerprint == escaped.fingerprint)
        let composed = try RuntimeIdentity(json: reviewJSON(reviewSet(base, ["execution", "startup_export"], .text("é"))))
        let decomposed = try RuntimeIdentity(json: reviewJSON(reviewSet(base, ["execution", "startup_export"], .text("e\u{301}"))))
        #expect(composed.fingerprint != decomposed.fingerprint)
        #expect(Array(composed.execution.startupExport.utf8) != Array(decomposed.execution.startupExport.utf8))
    }

    @Test func rawNumericSpellingsNeverCoerceAndUint64MaximumIsExact() throws {
        let base = try reviewDescriptor()
        let text = String(decoding: try reviewJSON(base), as: UTF8.self)
        for token in ["-0", "-1", "+1", "01", "1.0", "1e0", "1E0", "0x1", "NaN", "Infinity", "true", "null", "\"1\"", "18446744073709551616"] {
            let raw = text.replacingOccurrences(of: "\"state_schema\":1", with: "\"state_schema\":" + token)
            #expect(raw != text)
            reviewRawRejects(Data(raw.utf8))
        }
        let maximum = try RuntimeIdentity(json: reviewJSON(reviewSet(base, ["execution", "state_schema"], .uint(UInt64.max))))
        #expect(maximum.installedRuntime.stateVersion == UInt64.max)
        for path in [["schema"], ["engine", "guest_abi"], ["engine", "ui_schema"], ["execution", "fuel"], ["execution", "host_calls"]] {
            for replacement in [CanonicalValue.boolean(true), .text("1"), .array([]), .object([:])] {
                try reviewIdentityRejects(reviewSet(base, path, replacement))
            }
        }
    }

    @Test func byteDepthAndNodeCeilingsAreEnforcedBeforeDecoding() throws {
        let bytes = try reviewJSON(reviewDescriptor())
        let identity = try RuntimeIdentity(json: bytes)
        var exact = bytes
        exact.append(Data(repeating: 32, count: RuntimeIdentity.maximumDescriptorBytes - exact.count))
        #expect(try RuntimeIdentity(json: exact).fingerprint == identity.fingerprint)
        exact.append(32); reviewRawRejects(exact)
        for raw in [String(repeating: "[", count: 34) + "0" + String(repeating: "]", count: 34),
                    "{\"x\":[" + Array(repeating: "0", count: 20001).joined(separator: ",") + "]}"] {
            do { _ = try RuntimeIdentity(json: Data(raw.utf8)); Issue.record("missing scanner resource rejection") }
            catch let error as UpdateError { #expect(error.code == "json.limit") }
        }
    }

    @Test func closedObjectsAndASCIIStringBoundsRejectHiddenPolicyFields() throws {
        let base = try reviewDescriptor()
        for path in [[], ["application"], ["platform"], ["engine"], ["toolchain"], ["build"], ["execution"], ["dependencies", "0"]] {
            try reviewIdentityRejects(reviewSet(base, path + ["hidden_policy"], .boolean(true)))
        }
        for key in ["organization", "project", "app", "environment", "bundle_id"] {
            _ = try RuntimeIdentity(json: reviewJSON(reviewSet(base, ["application", key], .text(String(repeating: "a", count: 128)))))
            for text in ["", " a", "a ", "a/b", "a\\b", "é", String(repeating: "a", count: 129)] {
                try reviewIdentityRejects(reviewSet(base, ["application", key], .text(text)))
            }
        }
        _ = try RuntimeIdentity(json: reviewJSON(reviewSet(base, ["toolchain", "sdk_version"], .text(String(repeating: "a", count: 256)))))
        try reviewIdentityRejects(reviewSet(base, ["toolchain", "sdk_version"], .text(String(repeating: "a", count: 257))))
        _ = try RuntimeIdentity(json: reviewJSON(reviewSet(base, ["execution", "startup_export"], .text(String(repeating: "é", count: 2048)))))
        try reviewIdentityRejects(reviewSet(base, ["execution", "startup_export"], .text(String(repeating: "é", count: 2048) + "a")))
    }

    @Test func nativeInventoriesHaveExactLimitsUniqueIDsAndByteOrdering() throws {
        let base = try reviewDescriptor(), digest = String(repeating: "a", count: 64)
        let dependencies: [CanonicalValue] = (0..<128).map { .object(["id": .text(String(format: "dep%03d", $0)), "version": .text("1"), "artifact_sha256": .text(digest)]) }
        let capabilities: [CanonicalValue] = (0..<128).map { .object(["id": .text(String(format: "cap%03d", $0)), "schema_sha256": .text(digest), "native_sha256": .text(digest), "configuration_sha256": .text(digest), "grants_sha256": .text(digest)]) }
        let combined = reviewSet(reviewSet(base, ["dependencies"], .array(dependencies)), ["capabilities"], .array(capabilities))
        #expect(try RuntimeIdentity(json: reviewJSON(combined)).installedRuntime.capabilityHashes.count == 128)
        try reviewIdentityRejects(reviewSet(combined, ["capabilities"], .array(capabilities + [capabilities[0]])))
        try reviewIdentityRejects(reviewSet(combined, ["dependencies"], .array(dependencies + [dependencies[0]])))
        try reviewIdentityRejects(reviewSet(combined, ["capabilities", "0", "extra"], .text("ignored grant")))
        try reviewIdentityRejects(reviewSet(combined, ["capabilities"], .array(Array(capabilities.reversed()))))
        try reviewIdentityRejects(reviewSet(combined, ["execution", "protocol"], .uint(1)))
        var first = dependencies[0].object!; first["id"] = .text("Z")
        var second = dependencies[1].object!; second["id"] = .text("a")
        _ = try RuntimeIdentity(json: reviewJSON(reviewSet(base, ["dependencies"], .array([.object(first), .object(second)]))))
        try reviewIdentityRejects(reviewSet(base, ["dependencies"], .array([.object(second), .object(first)])))
    }

    @Test func platformAndHostPolicyFactoryUseTheEntireValidatedDescriptor() throws {
        let base = try reviewDescriptor()
        for (os, arch, environment, minimum, target) in [
            ("ios", "x86_64", "simulator", "17.0.1", "x86_64-apple-ios17.0.1-simulator"),
            ("android", "x86_64", "device", "28", "x86_64-unknown-linux-android28"),
            ("android", "arm64", "simulator", "28", "aarch64-unknown-linux-android28")] {
            let value = reviewSet(base, ["platform"], .object(["os": .text(os), "architecture": .text(arch), "environment": .text(environment), "minimum_os": .text(minimum), "target": .text(target)]))
            #expect(try RuntimeIdentity(json: reviewJSON(value)).installedRuntime.scope.platform == os)
            try reviewIdentityRejects(reviewSet(value, ["platform", "target"], .text(target + ".extra")))
        }
        let value = reviewSet(base, ["execution", "memory_bytes"], .uint(65535))
        let identity = try RuntimeIdentity(json: reviewJSON(value))
        #expect(identity.installedRuntime.limits.memoryBytes == 65535)
        #expect(identity.fingerprint == ReleaseVerifier.sha256(Data("mixer.runtime.identity.v1\0".utf8) + identity.canonicalCBOR))
        #expect(identity.fingerprint != ReleaseVerifier.sha256(Data("mixer.runtime.identity.v1\\0".utf8) + identity.canonicalCBOR))
        #expect(identity.fingerprint != ReleaseVerifier.sha256(identity.canonicalCBOR))
    }
}
