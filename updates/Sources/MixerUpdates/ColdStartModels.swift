import Foundation
import Dispatch

public struct ColdStartConfiguration: Sendable {
    public let directory: URL
    public let channel: String
    public let installation: String
    public let failureThreshold: UInt64
    public let observationSeconds: UInt64
    public let requiredMilestones: Set<String>
    public let reserveDiskBytes: UInt64
    public let monotonicNanoseconds: @Sendable () -> UInt64
    public let fault: (@Sendable (DurabilityFaultPoint) throws -> Void)?

    public init(directory: URL, channel: String, installation: String, failureThreshold: UInt64 = 2,
                observationSeconds: UInt64 = 10, requiredMilestones: Set<String> = ["feature_started", "first_screen"],
                reserveDiskBytes: UInt64 = 16 * 1_048_576,
                monotonicNanoseconds: @escaping @Sendable () -> UInt64 = { DispatchTime.now().uptimeNanoseconds },
                fault: (@Sendable (DurabilityFaultPoint) throws -> Void)? = nil) {
        self.directory = directory; self.channel = channel; self.installation = installation
        self.failureThreshold = failureThreshold; self.observationSeconds = observationSeconds
        self.requiredMilestones = requiredMilestones; self.reserveDiskBytes = reserveDiskBytes
        self.monotonicNanoseconds = monotonicNanoseconds; self.fault = fault
    }
}

public enum StartupFailure: String, Codable, Sendable {
    case deterministicTrap, unknownInterruption, nativeCrash, userQuit
}

public struct ColdStartSelection: Sendable {
    public enum Source: String, Equatable, Sendable { case nativeFallback, healthy, provisional }
    public let source: Source
    public let artifactSHA256: String?
    public let payloadSHA256: String?
    /// The exact private-file snapshot verified before selection. Paths never grant
    /// authority. The caller executes these values only through its installed engine.
    public let payload: Data?
    public let launchID: String?
}

public struct UpdateRecoverySnapshot: Equatable, Sendable {
    /// An uncertain commit may leave in-memory values newer than durable values.
    /// Close and reopen before treating sequence/pointer diagnostics as durable.
    public let requiresReopen: Bool
    public let acceptedSequence: UInt64
    public let downloading: String?
    public let staged: String?
    public let healthy: String?
    public let previousHealthy: String?
    public let attemptedArtifact: String?
    public let failures: [String: UInt64]
    public let quarantine: [String: String]
    public let lastRecovery: String
    public let retainedCandidates: Int
}

struct StoredUpdateCandidate: Codable, Sendable {
    let digest: String
    let sequence: UInt64
    let signedManifest: Data
    let signedAssignment: Data
    init(digest: String, sequence: UInt64, signedManifest: Data, signedAssignment: Data) {
        self.digest = digest; self.sequence = sequence; self.signedManifest = signedManifest; self.signedAssignment = signedAssignment
    }
    enum CodingKeys: String, CodingKey, CaseIterable { case digest, sequence, signedManifest, signedAssignment }
    init(from decoder: any Decoder) throws {
        try requireConfigurationFields(decoder, Set(CodingKeys.allCases.map(\.stringValue)))
        let fields = try decoder.container(keyedBy: CodingKeys.self)
        digest = try fields.decode(String.self, forKey: .digest); sequence = try fields.decode(UInt64.self, forKey: .sequence)
        signedManifest = try fields.decode(Data.self, forKey: .signedManifest)
        signedAssignment = try fields.decode(Data.self, forKey: .signedAssignment)
    }
}

struct UpdateOffer: Sendable {
    let candidate: StoredUpdateCandidate
    let payloadBytes: UInt64
    let payloadSHA256: String
}

struct StartupAttempt: Codable, Sendable {
    let launchID: String
    let digest: String
    let startedAtWallTime: UInt64
    init(launchID: String, digest: String, startedAtWallTime: UInt64) {
        self.launchID = launchID; self.digest = digest; self.startedAtWallTime = startedAtWallTime
    }
    enum CodingKeys: String, CodingKey, CaseIterable { case launchID, digest, startedAtWallTime }
    init(from decoder: any Decoder) throws {
        try requireConfigurationFields(decoder, Set(CodingKeys.allCases.map(\.stringValue)))
        let fields = try decoder.container(keyedBy: CodingKeys.self)
        launchID = try fields.decode(String.self, forKey: .launchID); digest = try fields.decode(String.self, forKey: .digest)
        startedAtWallTime = try fields.decode(UInt64.self, forKey: .startedAtWallTime)
    }
}

struct RecoveryState: Codable, Sendable {
    var schemaVersion = 1
    let host: InstalledRuntime
    let channel: String
    let installation: String
    var acceptedSequence: UInt64 = 0
    var download: StoredUpdateCandidate?
    var candidates: [String: StoredUpdateCandidate] = [:]
    var staged: String?
    var healthy: String?
    var previousHealthy: String?
    var attempt: StartupAttempt?
    var failures: [String: UInt64] = [:]
    var quarantine: [String: String] = [:]
    var lastRecovery = ""

    init(host: InstalledRuntime, channel: String, installation: String) {
        self.host = host; self.channel = channel; self.installation = installation
    }

    enum CodingKeys: String, CodingKey, CaseIterable {
        case schemaVersion, host, channel, installation, acceptedSequence, download, candidates
        case staged, healthy, previousHealthy, attempt, failures, quarantine, lastRecovery
    }

    init(from decoder: any Decoder) throws {
        try requireConfigurationFields(decoder, Set(CodingKeys.allCases.map(\.stringValue)))
        let fields = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try fields.decode(Int.self, forKey: .schemaVersion)
        host = try fields.decode(InstalledRuntime.self, forKey: .host)
        channel = try fields.decode(String.self, forKey: .channel)
        installation = try fields.decode(String.self, forKey: .installation)
        acceptedSequence = try fields.decode(UInt64.self, forKey: .acceptedSequence)
        download = try fields.decodeIfPresent(StoredUpdateCandidate.self, forKey: .download)
        candidates = try fields.decode([String: StoredUpdateCandidate].self, forKey: .candidates)
        staged = try fields.decodeIfPresent(String.self, forKey: .staged)
        healthy = try fields.decodeIfPresent(String.self, forKey: .healthy)
        previousHealthy = try fields.decodeIfPresent(String.self, forKey: .previousHealthy)
        attempt = try fields.decodeIfPresent(StartupAttempt.self, forKey: .attempt)
        failures = try fields.decode([String: UInt64].self, forKey: .failures)
        quarantine = try fields.decode([String: String].self, forKey: .quarantine)
        lastRecovery = try fields.decode(String.self, forKey: .lastRecovery)
    }

    func encode(to encoder: any Encoder) throws {
        var fields = encoder.container(keyedBy: CodingKeys.self)
        try fields.encode(schemaVersion, forKey: .schemaVersion); try fields.encode(host, forKey: .host)
        try fields.encode(channel, forKey: .channel); try fields.encode(installation, forKey: .installation)
        try fields.encode(acceptedSequence, forKey: .acceptedSequence); try fields.encode(download, forKey: .download)
        try fields.encode(candidates, forKey: .candidates); try fields.encode(staged, forKey: .staged)
        try fields.encode(healthy, forKey: .healthy); try fields.encode(previousHealthy, forKey: .previousHealthy)
        try fields.encode(attempt, forKey: .attempt); try fields.encode(failures, forKey: .failures)
        try fields.encode(quarantine, forKey: .quarantine); try fields.encode(lastRecovery, forKey: .lastRecovery)
    }
}

func recoveryIdentifier(_ value: String) -> Bool {
    !value.isEmpty && value.utf8.count <= 128 && value.utf8.allSatisfy {
        (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || [45, 46, 95].contains($0)
    }
}

func recoveryDigest(_ value: String) -> Bool {
    value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
}
