import Foundation
import FieldLogDraftIntegration
import MixerRuntimeIdentity
import MixerCapabilities
@_spi(AndroidGuestUIV1) import MixerCapabilityActivation
import MixerUpdates

enum Trial {
    static let channel = "beta"
    static let installation = "fieldlog-android-local-1"
    static let materials: [(String, CapabilityMaterialFile.Role)] = [
        ("bridge.json", .bridgePolicy),
        ("http.json", .configuration(capabilityID: CapabilitySchemas.httpID)),
        ("storage.json", .configuration(capabilityID: CapabilitySchemas.storageID)),
        ("http-grant.json", .installedGrant(capabilityID: CapabilitySchemas.httpID)),
        ("storage-grant.json", .installedGrant(capabilityID: CapabilitySchemas.storageID)),
    ]

    static func open(privateDirectory: URL, assets: URL, workspace: ObservedStorage) async throws -> CapabilityGuestUIAndroidRuntime {
        let files = try materials.map { name, role in
            CapabilityMaterialFile(role: role, bytes: try read(assets, name))
        }
        let identity = try read(assets, "identity.json")
        let runtime = try CapabilityRuntimeIdentity(json: identity).fingerprint
        let execution = try InstalledCapabilityExecution(identityJSON: identity,
            materials: files, trustRootsJSON: read(assets, "roots.json"), privateContainer: privateDirectory,
            applicationStorage: .init(runtimeFingerprint: runtime, namespace: FieldLogDraftStorage.namespace,
                service: workspace, allowsDeferredGuestUIStartup: true))
        return try await CapabilityGuestUIAndroidRuntime.open(configuration: .init(
            directory: privateDirectory.appendingPathComponent("recovery"), channel: channel,
            installation: installation, observationSeconds: 1), execution: execution)
    }

    static func read(_ assets: URL, _ name: String) throws -> Data {
        try Data(contentsOf: assets.appendingPathComponent(name))
    }
}

struct TrialError: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }

    static func detail(_ error: any Error) -> String {
        if let refusal = error as? UpdateError { return "\(refusal.code): \(refusal)" }
        return String(describing: error)
    }
}

// Count dispatches while forwarding the unchanged installed storage contract.
actor ObservedStorage: InstalledApplicationStorageServing {
    private let storage: FieldLogDraftStorage
    private(set) var calls = [0, 0, 0]

    init(_ storage: FieldLogDraftStorage) { self.storage = storage }

    func get(_ arguments: KVGetArguments) async throws -> KVGetResponse {
        calls[0] += 1
        return try await storage.get(arguments)
    }

    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        calls[1] += 1
        return try await storage.put(arguments, maximumTotalBytes: maximumTotalBytes, maximumEntries: maximumEntries)
    }

    func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse {
        calls[2] += 1
        return try await storage.delete(arguments)
    }
}
