import Foundation
@_spi(S5SignedCompose) import MixerCapabilityActivation
import MixerCapabilities
import MixerUpdates

struct JourneyError: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}

enum SignedStage: String, Sendable {
    case prior, candidate, rollback

    var sequence: UInt64 {
        switch self {
        case .prior: 1
        case .candidate: 2
        case .rollback: 3
        }
    }

    var payload: String { self == .rollback ? "prior" : rawValue }
}

actor SignedJourney {
    private let assets: URL
    private let directory: URL
    private var owner: CapabilityColdStartRuntime?
    private var previous: CapabilityColdStartRecoverySnapshot?
    private var lastStage: SignedStage?
    private let key = KVGetArguments(namespace: "material_test", key: "s5-title")

    init(assets: URL, directory: URL) {
        self.assets = assets
        self.directory = directory
    }

    private func load(_ name: String) throws -> Data {
        try Data(contentsOf: assets.appendingPathComponent(name))
    }

    func activate(_ stage: SignedStage, presentation: S5SignedPresentation,
                  provisional: @Sendable () -> Void) async throws -> String {
        if let lastStage, stage.sequence != lastStage.sequence + 1 { throw JourneyError("Wrong fixture sequence") }
        if lastStage == nil, stage != .prior { throw JourneyError("Missing prior release") }
        previous = try await closeOwner()
        let execution = try InstalledCapabilityExecution(identityJSON: load("identity.json"), materials: [
            .init(role: .bridgePolicy, bytes: try load("bridge.json")),
            .init(role: .configuration(capabilityID: CapabilitySchemas.storageID), bytes: try load("storage.json")),
            .init(role: .installedGrant(capabilityID: CapabilitySchemas.storageID), bytes: try load("storage-grant.json")),
        ], trustRootsJSON: load("roots.json"), privateContainer: directory)
        let configuration = CapabilityColdStartConfiguration(directory: directory.appendingPathComponent("recovery"),
            channel: "beta", installation: "s5-local", observationSeconds: 1)
        if stage == .prior {
            do {
                let unexpected = try await CapabilityColdStartRuntime.open(configuration: configuration, execution: execution)
                await unexpected.close()
                throw JourneyError("Ordinary admission accepted the development editor")
            } catch let error as UpdateError where error.code == "capability.runtime.installed_mode" {}
        }
        let runtime = try await CapabilityColdStartRuntime.openS5SignedCompose(configuration: configuration,
            execution: execution, presentation: presentation)
        owner = runtime
        let manifest = try load(stage.rawValue + ".manifest")
        let assignment = try load(stage.rawValue + ".assignment")
        let bytes = try load(stage.payload + ".wasm")
        if stage == .rollback {
            try await requireRefusedInstall(runtime, manifest: manifest, assignment: assignment)
        }
        try await runtime.beginDownload(signedManifest: manifest, signedAssignment: assignment)
        try await runtime.appendDownload(bytes, atOffset: 0)
        try await runtime.finishDownload()
        let activation = try await runtime.start()
        guard activation.phase == .provisionalGuest, let candidate = activation.candidateID else {
            throw JourneyError("Startup phase \(activation.phase) bridge \(String(describing: activation.firstBridgeFailure))")
        }
        provisional()
        let deadline = ContinuousClock.now + .seconds(10)
        while ContinuousClock.now < deadline {
            let state = await runtime.recoverySnapshot()
            if state.activation.phase == .healthyGuest {
                guard state.healthy == candidate, state.acceptedSequence == stage.sequence,
                      state.previousHealthy == previous?.healthy else {
                    throw JourneyError("Unexpected healthy candidate or assignment")
                }
                if stage == .rollback { try checkRollback(candidate, manifest: manifest, bytes: bytes) }
                lastStage = stage
                return candidate
            }
            guard state.activation.phase == .provisionalGuest else {
                throw JourneyError("Presentation stopped in \(state.activation.phase)")
            }
            try await Task.sleep(for: .milliseconds(20))
        }
        throw JourneyError("Timed out waiting for exact presentation and health")
    }

    private func requireRefusedInstall(_ runtime: CapabilityColdStartRuntime, manifest: Data, assignment: Data) async throws {
        let before = await runtime.recoverySnapshot()
        let signed = try StrictJSON.decode(CanonicalValue.self, from: manifest)
        guard var fields = signed.object, let signature = fields["signature"]?.text,
              var tampered = Data(base64Encoded: signature), tampered.count == 64 else {
            throw JourneyError("Invalid signed fixture")
        }
        tampered[0] ^= 1
        fields["signature"] = .text(tampered.base64EncodedString())
        do {
            try await runtime.beginDownload(signedManifest: JSONEncoder().encode(CanonicalValue.object(fields)),
                                            signedAssignment: assignment)
            throw JourneyError("Tampered artifact signature was admitted")
        } catch let error as UpdateError where error.code == "v3.signature.invalid" {}
        let after = await runtime.recoverySnapshot()
        guard before.acceptedSequence == 2, after.acceptedSequence == before.acceptedSequence,
              before.healthy != nil, after.healthy == before.healthy, after.staged == nil, after.downloading == nil else {
            throw JourneyError("Rejected install changed durable selection")
        }
    }

    private func checkRollback(_ candidate: String, manifest: Data, bytes: Data) throws {
        struct Record: Decodable {
            struct Candidate: Decodable {
                let signedManifest: Data
                let payloadSHA256: String
                let sequence: UInt64
            }
            let candidates: [String: Candidate]
        }
        let record = try JSONDecoder().decode(Record.self,
            from: Data(contentsOf: directory.appendingPathComponent("recovery/state.json")))
        guard let selected = record.candidates[candidate], selected.sequence == 3,
              selected.signedManifest == manifest, selected.payloadSHA256 == ReleaseVerifier.sha256(bytes),
              manifest == (try load("prior.manifest")) else {
            throw JourneyError("Rollback changed the original signed artifact or payload")
        }
    }

    private func closeOwner() async throws -> CapabilityColdStartRecoverySnapshot? {
        guard let owner else { return nil }
        let snapshot = await owner.recoverySnapshot()
        guard await owner.closeS5SignedCompose() else { throw JourneyError("Owner did not retire") }
        self.owner = nil
        return snapshot
    }

    func finish() async throws -> Data {
        _ = try await closeOwner()
        let store = try AppPrivateKeyValueStore(directory: directory.appendingPathComponent("material_test"),
                                                namespaces: ["material_test"])
        do {
            let value = try await store.get(key)
            await store.close()
            guard value.found, let bytes = Data(base64Encoded: value.valueBase64) else {
                throw JourneyError("Missing persisted title")
            }
            return bytes
        } catch {
            await store.close()
            throw error
        }
    }

    func abort() async {
        _ = try? await closeOwner()
    }
}
