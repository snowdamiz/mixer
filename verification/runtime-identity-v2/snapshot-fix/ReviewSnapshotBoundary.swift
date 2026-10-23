import Foundation
import Testing
import MixerRuntimeIdentity

struct ReviewSnapshotBoundary {
    @Test func scanAndDecodeMustUseTheSameOwnedBytes() throws {
        let url = try #require(Bundle.module.url(forResource: "vectors-v2", withExtension: "json", subdirectory: "Fixtures"))
        let vectors = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [[String: Any]])
        var descriptor = try #require(vectors.first?["descriptor"] as? [String: Any])
        let clean = try JSONSerialization.data(withJSONObject: descriptor, options: [.sortedKeys])
        var execution = try #require(descriptor["execution"] as? [String: Any])
        execution["fuel"] = 777777; descriptor["execution"] = execution
        let changed = try JSONSerialization.data(withJSONObject: descriptor, options: [.sortedKeys])
        let duplicate = Data(("{\"schema\":2," + String(decoding: changed, as: UTF8.self).dropFirst()).utf8)
        let count = max(clean.count, duplicate.count) + 16
        let original = clean + Data(repeating: 32, count: count-clean.count)
        let replacement = duplicate + Data(repeating: 32, count: count-duplicate.count)
        let pointer = UnsafeMutableRawPointer.allocate(byteCount: count, alignment: 1)
        defer { pointer.deallocate() }
        original.withUnsafeBytes { pointer.copyMemory(from: $0.baseAddress!, byteCount: count) }
        let borrowed = Data(bytesNoCopy: pointer, count: count, deallocator: .none)
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: directory) }
        let path = directory.appendingPathComponent("replacement.json")
        try replacement.write(to: path)
        setenv("MIXER_IDENTITY_REVIEW_ADDRESS", String(UInt(bitPattern: pointer)), 1)
        setenv("MIXER_IDENTITY_REVIEW_REPLACEMENT", path.path, 1)
        defer { unsetenv("MIXER_IDENTITY_REVIEW_ADDRESS"); unsetenv("MIXER_IDENTITY_REVIEW_REPLACEMENT") }
        let identity = try CapabilityRuntimeIdentity(json: borrowed)
        unsetenv("MIXER_IDENTITY_REVIEW_ADDRESS"); unsetenv("MIXER_IDENTITY_REVIEW_REPLACEMENT")
        let expected = try #require(UInt64(ProcessInfo.processInfo.environment["MIXER_IDENTITY_REVIEW_EXPECTED_FUEL"] ?? ""))
        #expect(identity.installedRuntime.limits.fuel == expected)
        #expect(borrowed == replacement)
        #expect(throws: (any Error).self) { try CapabilityRuntimeIdentity(json: borrowed) }
        print("SCANNER_BOUNDARY observed_fuel=\(identity.installedRuntime.limits.fuel) expected=\(expected); raw duplicate replacement rejects when scanned")
    }
}
