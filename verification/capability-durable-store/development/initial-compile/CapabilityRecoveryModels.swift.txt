import Foundation
import MixerUpdates

struct CapabilityRecoveryConfiguration: Sendable {
    let directory: URL
    let channel: String
    let installation: String
    var failureThreshold: UInt64 = 2
    var observationSeconds: UInt64 = 10
    var requiredMilestones: Set<String> = ["feature_started", "first_screen"]
    var reserveDiskBytes: UInt64 = 16 * 1_048_576
}

/// Test controls cannot accept executable content. Production uses actual clocks
/// and the concrete native validator, never a caller-supplied validation closure.
struct CapabilityRecoveryEnvironment: Sendable {
    var wall: @Sendable () -> UInt64 = { UInt64(max(0, Date().timeIntervalSince1970)) }
    var monotonic: @Sendable () -> UInt64 = { DispatchTime.now().uptimeNanoseconds }
    var fault: (@Sendable (CapabilityDurabilityFaultPoint) throws -> Void)?
    var beforeValidation: (@Sendable () async -> Void)?
    var afterValidation: (@Sendable () async -> Void)?
}

struct CapabilityRecoverySnapshot: Sendable, Equatable {
    var requiresReopen = false
    var closed = false
    var busy = false
    var acceptedSequence: UInt64 = 0
    var downloading: String?
    var staged: String?
    var healthy: String?
    var previousHealthy: String?
    var retainedCandidates = 0
    var incompleteAttempt = false
}

struct CapabilityRecoveryCandidate: Codable, Sendable {
    let candidateID: String
    let artifactSHA256: String
    let payloadSHA256: String
    let payloadBytes: UInt64
    let sequence: UInt64
    let signedManifest: Data
    let signedAssignment: Data

    static func id(artifact: String, sequence: UInt64, manifest: Data, assignment: Data) throws -> String {
        let record = CanonicalValue.object(["artifact_sha256": .text(artifact), "sequence": .uint(sequence),
            "manifest_raw_sha256": .text(ReleaseVerifier.sha256(manifest)),
            "assignment_raw_sha256": .text(ReleaseVerifier.sha256(assignment))])
        return ReleaseVerifier.sha256(Data("mixer.capability.candidate.v1\0".utf8) + (try record.canonicalCBOR()))
    }
    init(artifact: String, payloadHash: String, payloadBytes: UInt64, sequence: UInt64, manifest: Data, assignment: Data) throws {
        candidateID = try Self.id(artifact: artifact, sequence: sequence, manifest: manifest, assignment: assignment)
        artifactSHA256 = artifact; payloadSHA256 = payloadHash; self.payloadBytes = payloadBytes; self.sequence = sequence
        signedManifest = manifest; signedAssignment = assignment
    }
    enum CodingKeys: String, CodingKey, CaseIterable {
        case candidateID, artifactSHA256, payloadSHA256, payloadBytes, sequence, signedManifest, signedAssignment
    }
    init(from decoder: any Decoder) throws {
        try capabilityClosed(decoder, Set(CodingKeys.allCases.map(\.stringValue)))
        let f = try decoder.container(keyedBy: CodingKeys.self)
        candidateID = try f.decode(String.self, forKey: .candidateID)
        artifactSHA256 = try f.decode(String.self, forKey: .artifactSHA256)
        payloadSHA256 = try f.decode(String.self, forKey: .payloadSHA256)
        payloadBytes = try f.decode(UInt64.self, forKey: .payloadBytes); sequence = try f.decode(UInt64.self, forKey: .sequence)
        signedManifest = try Self.document(f.decode(String.self, forKey: .signedManifest))
        signedAssignment = try Self.document(f.decode(String.self, forKey: .signedAssignment))
    }
    private static func document(_ text: String) throws -> Data {
        guard text.utf8.prefix(87_385).count <= 87_384,
              let bytes = Data(base64Encoded: text), bytes.count <= 65_536,
              bytes.base64EncodedString() == text else { throw capabilityRecoveryError("state") }
        return bytes
    }
}

/// Persisted health/attempt structure only. This slice exposes no API to create
/// health, publish a selection or execute a stored candidate.
struct CapabilityStoredHealth: Codable, Sendable {
    let candidateID: String
    let launchID: String
    let committedAtWallTime: UInt64
    let observationSeconds: UInt64
    let completedMilestones: Set<String>
    enum CodingKeys: String, CodingKey, CaseIterable { case candidateID, launchID, committedAtWallTime, observationSeconds, completedMilestones }
    init(from decoder: any Decoder) throws {
        try capabilityClosed(decoder, Set(CodingKeys.allCases.map(\.stringValue)))
        let f = try decoder.container(keyedBy: CodingKeys.self)
        candidateID = try f.decode(String.self, forKey: .candidateID); launchID = try f.decode(String.self, forKey: .launchID)
        committedAtWallTime = try f.decode(UInt64.self, forKey: .committedAtWallTime)
        observationSeconds = try f.decode(UInt64.self, forKey: .observationSeconds)
        let ids = try f.decode([String].self, forKey: .completedMilestones)
        guard ids.count <= 16, Set(ids).count == ids.count else { throw capabilityRecoveryError("state") }
        completedMilestones = Set(ids)
    }
}
struct CapabilityStoredAttempt: Codable, Sendable {
    let launchID: String
    let candidateID: String
    let source: String
    let startedAtWallTime: UInt64
    let effectsMayHaveOpened: Bool
    enum CodingKeys: String, CodingKey, CaseIterable { case launchID, candidateID, source, startedAtWallTime, effectsMayHaveOpened }
    init(from decoder: any Decoder) throws {
        try capabilityClosed(decoder, Set(CodingKeys.allCases.map(\.stringValue)))
        let f = try decoder.container(keyedBy: CodingKeys.self)
        launchID = try f.decode(String.self, forKey: .launchID); candidateID = try f.decode(String.self, forKey: .candidateID)
        source = try f.decode(String.self, forKey: .source); startedAtWallTime = try f.decode(UInt64.self, forKey: .startedAtWallTime)
        effectsMayHaveOpened = try f.decode(Bool.self, forKey: .effectsMayHaveOpened)
    }
}
struct CapabilityRecoveryState: Codable, Sendable {
    var kind = "mixer-capability-cold-start-v1"
    var schemaVersion: UInt64 = 3
    let fingerprint: String
    let host: InstalledRuntime
    let channel: String
    let installation: String
    var acceptedSequence: UInt64 = 0
    var pending: CapabilityRecoveryCandidate?
    var candidates: [String: CapabilityRecoveryCandidate] = [:]
    var staged: String?
    var healthy: CapabilityStoredHealth?
    var previousHealthy: CapabilityStoredHealth?
    var attempt: CapabilityStoredAttempt?
    var failures: [String: UInt64] = [:]
    var quarantine: [String: String] = [:]
    var lastRecovery = ""
    init(installed: InstalledMaterial, configuration: CapabilityRecoveryConfiguration) {
        fingerprint = installed.identity.fingerprint; host = installed.identity.installedRuntime
        channel = configuration.channel; installation = configuration.installation
    }
    enum CodingKeys: String, CodingKey, CaseIterable {
        case kind, schemaVersion, fingerprint, host, channel, installation, acceptedSequence, pending, candidates
        case staged, healthy, previousHealthy, attempt, failures, quarantine, lastRecovery
    }
    init(from decoder: any Decoder) throws {
        try capabilityClosed(decoder, Set(CodingKeys.allCases.map(\.stringValue)))
        let f = try decoder.container(keyedBy: CodingKeys.self)
        kind = try f.decode(String.self, forKey: .kind); schemaVersion = try f.decode(UInt64.self, forKey: .schemaVersion)
        fingerprint = try f.decode(String.self, forKey: .fingerprint); host = try f.decode(InstalledRuntime.self, forKey: .host)
        channel = try f.decode(String.self, forKey: .channel); installation = try f.decode(String.self, forKey: .installation)
        acceptedSequence = try f.decode(UInt64.self, forKey: .acceptedSequence)
        pending = try f.decodeIfPresent(CapabilityRecoveryCandidate.self, forKey: .pending)
        candidates = try f.decode([String: CapabilityRecoveryCandidate].self, forKey: .candidates)
        staged = try f.decodeIfPresent(String.self, forKey: .staged)
        healthy = try f.decodeIfPresent(CapabilityStoredHealth.self, forKey: .healthy)
        previousHealthy = try f.decodeIfPresent(CapabilityStoredHealth.self, forKey: .previousHealthy)
        attempt = try f.decodeIfPresent(CapabilityStoredAttempt.self, forKey: .attempt)
        failures = try f.decode([String: UInt64].self, forKey: .failures)
        quarantine = try f.decode([String: String].self, forKey: .quarantine)
        lastRecovery = try f.decode(String.self, forKey: .lastRecovery)
    }
    func encode(to encoder: any Encoder) throws {
        var f = encoder.container(keyedBy: CodingKeys.self)
        try f.encode(kind, forKey: .kind); try f.encode(schemaVersion, forKey: .schemaVersion)
        try f.encode(fingerprint, forKey: .fingerprint); try f.encode(host, forKey: .host)
        try f.encode(channel, forKey: .channel); try f.encode(installation, forKey: .installation)
        try f.encode(acceptedSequence, forKey: .acceptedSequence); try f.encode(pending, forKey: .pending)
        try f.encode(candidates, forKey: .candidates); try f.encode(staged, forKey: .staged)
        try f.encode(healthy, forKey: .healthy); try f.encode(previousHealthy, forKey: .previousHealthy)
        try f.encode(attempt, forKey: .attempt); try f.encode(failures, forKey: .failures)
        try f.encode(quarantine, forKey: .quarantine); try f.encode(lastRecovery, forKey: .lastRecovery)
    }
}

func capabilityRecoveryIdentifier(_ value: String) -> Bool {
    let bytes = value.utf8.prefix(129)
    return !bytes.isEmpty && bytes.count <= 128 && bytes.allSatisfy {
        (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || [45,46,95].contains($0)
    }
}
func capabilityRecoveryDigest(_ value: String) -> Bool {
    let bytes = value.utf8.prefix(65)
    return bytes.count == 64 && bytes.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
}
func capabilityRecoveryError(_ code: String) -> UpdateError { UpdateError("capability.store.\(code)", "Private capability recovery rejected") }
private struct CapabilityRecoveryKey: CodingKey {
    let stringValue: String; var intValue: Int? { nil }
    init?(stringValue: String) { self.stringValue = stringValue }
    init?(intValue: Int) { return nil }
}
private func capabilityClosed(_ decoder: any Decoder, _ expected: Set<String>) throws {
    let f = try decoder.container(keyedBy: CapabilityRecoveryKey.self)
    guard Set(f.allKeys.map(\.stringValue)) == expected else { throw capabilityRecoveryError("fields") }
}
