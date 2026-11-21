#if canImport(SwiftUI) && canImport(MixerApple)
import Foundation
import XCTest
import MixerCapabilities
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

private struct UnusedHydrationRepository: InstalledApplicationStorageServing {
    func get(_ arguments: KVGetArguments) async throws -> KVGetResponse {
        XCTFail("Invalid hydration selection reached the repository")
        throw CapabilityFailure.unavailable
    }
    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        XCTFail("Invalid hydration selection reached the repository")
        throw CapabilityFailure.unavailable
    }
    func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse {
        XCTFail("Invalid hydration selection reached the repository")
        throw CapabilityFailure.unavailable
    }
}

// The startup and hydrate signatures are tested at signed ingress before
// these fixtures could execute. All functions and memory are defined in Wasm.
private enum SignedHydrationModule {
    static func make(hookIndex: UInt8?) -> Data {
        func section(_ section: UInt8, _ bytes: [UInt8]) -> [UInt8] {
            precondition(bytes.count < 128)
            return [section, UInt8(bytes.count)] + bytes
        }
        var exports: [(String, UInt8)] = [
            ("mixer_guest_ui_start_v1", 0), ("mixer_guest_ui_event_v1", 1),
            ("mixer_guest_capability_ready_v1", 2),
        ]
        if let hookIndex { exports.append(("mixer_guest_ui_hydrate_v1", hookIndex)) }
        var table = [UInt8(exports.count)]
        for (name, index) in exports { table += [UInt8(name.utf8.count)] + name.utf8 + [0, index] }
        var module: [UInt8] = [0, 97, 115, 109, 1, 0, 0, 0]
        module += section(1, [3, 0x60, 0, 1, 0x7f, 0x60, 1, 0x7f, 1, 0x7f, 0x60, 0, 0])
        module += section(3, [3, 0, 1, 2]) + section(5, [1, 1, 1, 1])
        module += section(7, table) + section(10, [3, 4, 0, 0x41, 0, 0x0b, 4, 0, 0x41, 0, 0x0b, 2, 0, 0x0b])
        return Data(module)
    }
}

final class DeferredSignedGrantTests: XCTestCase, @unchecked Sendable {
    func testDeferredStartupRequiresBoundInstalledMaterialAndEffectiveSignedGrant() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-hydration-grant-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        let service = UnusedHydrationRepository()
        let fixture = try GuestUISignedFixture(root: root, storageService: service, deferredStartup: true)
        XCTAssertThrowsError(try GuestUISignedFixture(root: root, storageService: service, deferredStartup: true, boundNamespace: "other"))
        XCTAssertThrowsError(try GuestUISignedFixture(root: root, storageService: service, deferredStartup: true, boundFingerprint: "wrong"))
        let runtime = try await CapabilityGuestUIRuntime.openOwned(configuration: fixture.configuration,
            installed: fixture.execution.installed, environment: .init(wall: { 1000 }))
        do {
            for (index, hook) in [nil, UInt8(2)].enumerated() {
                let payload = SignedHydrationModule.make(hookIndex: hook)
                let (manifest, assignment) = try fixture.documents(payload, sequence: UInt64(index + 1), storage: true)
                try await runtime.beginDownload(signedManifest: manifest, signedAssignment: assignment)
                try await runtime.appendDownload(payload, atOffset: 0)
                do {
                    try await runtime.finishDownload()
                    XCTFail("Signed payload with an invalid hydrate export staged")
                } catch {
                    XCTAssertEqual(error as? GuestUIProtocolFailureV1, .init(phase: .validation, code: .requiredExport))
                }
                let snapshot = await runtime.recoverySnapshot()
                XCTAssertNil(snapshot.staged)
            }
            let payload = SignedHydrationModule.make(hookIndex: 0)
            let (manifest, assignment) = try fixture.documents(payload, sequence: 3, storage: false)
            try await runtime.beginDownload(signedManifest: manifest, signedAssignment: assignment)
            try await runtime.appendDownload(payload, atOffset: 0)
            try await runtime.finishDownload()
            let result = try await runtime.start()
            XCTAssertEqual(result.phase, .nativeFallback)
            XCTAssertFalse(result.effectsMayHaveOpened)
        } catch {
            await runtime.close()
            throw error
        }
        await runtime.close()
        XCTAssertTrue(runtime.ownerRetired)
        if runtime.ownerRetired { try FileManager.default.removeItem(at: root) }
    }
}
#endif
