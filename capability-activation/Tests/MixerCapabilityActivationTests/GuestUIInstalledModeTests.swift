import Foundation
import XCTest
import MixerCapabilities
import MixerRuntimeIdentity
import MixerUpdates
@testable import MixerCapabilityActivation

final class GuestUIInstalledModeTests: XCTestCase, @unchecked Sendable {
    private static let milestones: Set<String> = ["feature_started", "first_screen"]
    private static let contract = "mixer.guest-ui-event-v1"
    private static let header = "mixer.guest-ui-native-header-v1"
    private static let contractHash = "34180d46e20e403c9cd3f3aa1584a7b6d0e67e94900267c7aa51c87116566024"
    private static let headerHash = "d8d8217b900662e77787a8729f5c1cfe096b0df25ffe39e289f89d69fc156ab5"

    private func resource(_ name: String) throws -> Data {
        try Data(contentsOf: XCTUnwrap(Bundle.module.url(forResource: name, withExtension: nil, subdirectory: "Fixtures")))
    }
    private func descriptor(startup: String = "start", contract: (String, String)? = nil,
                            header: (String, String)? = nil, unrelated: Bool = false) throws -> Data {
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: resource("identity.json")) as? [String: Any])
        var execution = try XCTUnwrap(object["execution"] as? [String: Any])
        execution["startup_export"] = startup; object["execution"] = execution
        var dependencies = try XCTUnwrap(object["dependencies"] as? [[String: Any]])
        if let contract {
            dependencies.append(["id": Self.contract, "version": contract.0, "artifact_sha256": contract.1])
        }
        if let header {
            dependencies.append(["id": Self.header, "version": header.0, "artifact_sha256": header.1])
        }
        if unrelated {
            dependencies.append(["id": Self.contract + ".other", "version": "9", "artifact_sha256": String(repeating: "a", count: 64)])
        }
        object["dependencies"] = dependencies.sorted { ($0["id"] as! String) < ($1["id"] as! String) }
        return try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys, .withoutEscapingSlashes])
    }
    private func rejected(_ operation: () throws -> Void, file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertThrowsError(try operation(), file: file, line: line) { error in
            XCTAssertEqual((error as? UpdateError)?.code, "capability.runtime.installed_mode", file: file, line: line)
        }
    }

    func testReservedStartupAndEveryMarkerCombinationSelectOnlyExactUIMode() throws {
        for uiStartup in [false, true] {
            for hasContract in [false, true] {
                for hasHeader in [false, true] {
                    let bytes = try descriptor(startup: uiStartup ? "mixer_guest_ui_start_v1" : "start",
                        contract: hasContract ? ("1", Self.contractHash) : nil,
                        header: hasHeader ? ("1", Self.headerHash) : nil)
                    let identity = try CapabilityRuntimeIdentity(json: bytes)
                    if uiStartup || hasContract || hasHeader {
                        rejected { try CapabilityInstalledExecutionMode.requireCapabilityOnly(identity) }
                    } else { try CapabilityInstalledExecutionMode.requireCapabilityOnly(identity) }
                    if uiStartup && hasContract && hasHeader {
                        try CapabilityInstalledExecutionMode.requireGuestUI(identity, milestones: Self.milestones)
                    } else {
                        rejected { try CapabilityInstalledExecutionMode.requireGuestUI(identity, milestones: Self.milestones) }
                    }
                }
            }
        }
    }

    func testWrongMarkerVersionsAndHashesRejectBothModesWithoutNamespacePrefixMatching() throws {
        for position in 0..<2 {
            for invalid in [("2", position == 0 ? Self.contractHash : Self.headerHash), ("1", String(repeating: "a", count: 64))] {
                let bytes = try descriptor(startup: "mixer_guest_ui_start_v1",
                    contract: position == 0 ? invalid : ("1", Self.contractHash),
                    header: position == 1 ? invalid : ("1", Self.headerHash))
                let identity = try CapabilityRuntimeIdentity(json: bytes)
                rejected { try CapabilityInstalledExecutionMode.requireCapabilityOnly(identity) }
                rejected { try CapabilityInstalledExecutionMode.requireGuestUI(identity, milestones: Self.milestones) }
            }
        }
        let unrelated = try CapabilityRuntimeIdentity(json: descriptor(unrelated: true))
        try CapabilityInstalledExecutionMode.requireCapabilityOnly(unrelated)
        rejected { try CapabilityInstalledExecutionMode.requireGuestUI(unrelated, milestones: Self.milestones) }
    }

    func testExactUIMilestonesAndIdentityFingerprintBinding() throws {
        let plain = try CapabilityRuntimeIdentity(json: descriptor())
        let exact = try CapabilityRuntimeIdentity(json: descriptor(startup: "mixer_guest_ui_start_v1",
            contract: ("1", Self.contractHash), header: ("1", Self.headerHash)))
        XCTAssertNotEqual(plain.fingerprint, exact.fingerprint)
        let other = try CapabilityRuntimeIdentity(json: descriptor(startup: "mixer_guest_ui_start_v1",
            contract: ("1", String(repeating: "b", count: 64)), header: ("1", Self.headerHash)))
        XCTAssertNotEqual(exact.fingerprint, other.fingerprint)
        for milestones: Set<String> in [[], ["feature_started"], ["first_screen"], ["feature_started", "first_screen", "caller_report"]] {
            rejected { try CapabilityInstalledExecutionMode.requireGuestUI(exact, milestones: milestones) }
        }
        try CapabilityInstalledExecutionMode.requireGuestUI(exact, milestones: Self.milestones)
    }

    func testPublicCapabilityFacadeRejectsReservedModesBeforePoolAndFilesystem() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-ui-mode-" + UUID().uuidString)
        let materials: [CapabilityMaterialFile] = [
            .init(role: .bridgePolicy, bytes: try resource("bridge.json")),
            .init(role: .configuration(capabilityID: CapabilitySchemas.httpID), bytes: try resource("http.json")),
            .init(role: .configuration(capabilityID: CapabilitySchemas.storageID), bytes: try resource("storage.json")),
            .init(role: .installedGrant(capabilityID: CapabilitySchemas.httpID), bytes: try resource("http-grant.json")),
            .init(role: .installedGrant(capabilityID: CapabilitySchemas.storageID), bytes: try resource("storage-grant.json"))]
        let before = CapabilityAttemptReservation.occupiedSlots
        let reservations = try (before..<16).map { _ in try CapabilityAttemptReservation.acquire() }
        defer { for reservation in reservations { reservation.beginClosing() } }
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, 16)
        let variants = [
            try descriptor(startup: "mixer_guest_ui_start_v1"),
            try descriptor(contract: ("2", String(repeating: "a", count: 64))),
            try descriptor(header: ("2", String(repeating: "a", count: 64))),
            try descriptor(startup: "mixer_guest_ui_start_v1", contract: ("1", Self.contractHash), header: ("1", Self.headerHash))]
        for bytes in variants {
            let execution = try InstalledCapabilityExecution(identityJSON: bytes, materials: materials,
                trustRootsJSON: resource("roots.json"), privateContainer: root)
            let configuration = CapabilityColdStartConfiguration(directory: root.appendingPathComponent("recovery"), channel: "beta", installation: "ui-mode")
            do {
                let runtime = try await CapabilityColdStartRuntime.open(configuration: configuration, execution: execution)
                await runtime.close(); XCTFail("Capability facade accepted reserved UI mode")
            } catch { XCTAssertEqual((error as? UpdateError)?.code, "capability.runtime.installed_mode") }
            XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, 16)
            XCTAssertFalse(FileManager.default.fileExists(atPath: root.path))
        }
    }
}
