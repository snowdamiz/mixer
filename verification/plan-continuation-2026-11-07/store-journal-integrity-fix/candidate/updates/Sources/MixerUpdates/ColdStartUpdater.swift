import Foundation

/// A durable selection/recovery store, not an interpreter or a live-code switcher.
/// The installed host supplies actual executable-profile validation. No default
/// accepting validator exists, and payload paths never grant execution authority.
public actor ColdStartUpdater {
    public typealias ExecutableValidator = @Sendable (Data, VerifiedArtifact) throws -> Void
    private let configuration: ColdStartConfiguration
    private let verifier: ReleaseVerifier
    private let healthyVerifier: ReleaseVerifier
    private let executableValidator: ExecutableValidator
    private let storage: DurableDirectory
    private var state: RecoveryState
    private var poisoned = false
    private var closed = false
    private var selectedThisSession = false
    private var monotonicStart: UInt64?

    public static func open(configuration: ColdStartConfiguration, verifier: ReleaseVerifier,
                            executableValidator: @escaping ExecutableValidator) throws -> ColdStartUpdater {
        guard recoveryIdentifier(configuration.channel), recoveryIdentifier(configuration.installation),
              (1...10).contains(configuration.failureThreshold), (1...3600).contains(configuration.observationSeconds),
              !configuration.requiredMilestones.isEmpty, configuration.requiredMilestones.count <= 16,
              configuration.requiredMilestones.allSatisfy(recoveryIdentifier) else {
            throw UpdateError("store.configuration", "Invalid installed recovery/health policy")
        }
        let storage = try DurableDirectory(url: configuration.directory, fault: configuration.fault)
        do {
            var state: RecoveryState
            if let bytes = try storage.read("state.json", maximumBytes: 1_048_576) {
                state = try StrictJSON.decode(RecoveryState.self, from: bytes)
                try validate(state, configuration: configuration, host: verifier.host)
            } else {
                guard storage.wasCreated else { throw UpdateError("store.missingState", "Existing recovery directory lost its replay state; native maintenance required") }
                state = RecoveryState(host: verifier.host, channel: configuration.channel, installation: configuration.installation)
                try storage.atomicState(encode(state))
            }
            if compact(&state) { try storage.atomicState(encode(state)) }
            var keep = Set(state.candidates.keys.map { $0 + ".payload" })
            if let candidate = state.download { keep.formUnion([candidate.digest + ".payload", candidate.digest + ".payload.part"]) }
            try storage.pruneOwnedFiles(keeping: keep)
            return try ColdStartUpdater(configuration: configuration, verifier: verifier,
                executableValidator: executableValidator, storage: storage, state: state)
        } catch { storage.close(); throw error }
    }

    private init(configuration: ColdStartConfiguration, verifier: ReleaseVerifier,
                 executableValidator: @escaping ExecutableValidator, storage: DurableDirectory, state: RecoveryState) throws {
        self.configuration = configuration; self.verifier = verifier
        healthyVerifier = try verifier.retainedHealthyAuthorityVerifier()
        self.executableValidator = executableValidator; self.storage = storage; self.state = state
    }

    public func close() { closed = true; storage.close() }

    public func snapshot() -> UpdateRecoverySnapshot {
        UpdateRecoverySnapshot(requiresReopen: closed || poisoned, acceptedSequence: state.acceptedSequence, downloading: state.download?.digest,
            staged: state.staged, healthy: state.healthy, previousHealthy: state.previousHealthy,
            attemptedArtifact: state.attempt?.digest, failures: state.failures, quarantine: state.quarantine,
            lastRecovery: state.lastRecovery, retainedCandidates: state.candidates.count)
    }

    /// Reserves the signed sequence atomically before accepting any download bytes.
    /// Cancellation and interrupted downloads never lower this durable high-water.
    public func beginDownload(signedManifest: Data, signedAssignment: Data, now: UInt64) throws {
        try available()
        guard state.attempt == nil, state.download == nil else { throw UpdateError("download.busy", "Resume/cancel current download or complete startup first") }
        let offer = try verifier.authorizeOffer(manifest: signedManifest, assignment: signedAssignment,
            channel: configuration.channel, installation: configuration.installation, lastSequence: state.acceptedSequence, now: now)
        guard state.quarantine[offer.candidate.digest] == nil, state.quarantine.count < 256, state.failures.count < 256 else {
            throw UpdateError("store.quarantine", "Artifact quarantined or quarantine capacity reached")
        }
        try reserve(offer.payloadBytes)
        state.download = offer.candidate; state.acceptedSequence = offer.candidate.sequence
        try commit()
    }

    public func downloadOffset() throws -> UInt64 {
        try available()
        guard let candidate = state.download else { throw UpdateError("download.absent", "No pending download") }
        return try storage.size(part(candidate.digest)) ?? storage.size(file(candidate.digest)) ?? 0
    }

    /// The network capability supplies explicit bounded chunks at the saved offset.
    /// No network implementation, callbacks or external mutable file path is trusted.
    public func appendDownload(_ data: Data, atOffset offset: UInt64, now: UInt64) throws {
        try available()
        guard data.count <= 1_048_576 else { throw UpdateError("download.chunk", "Download chunk exceeds 1 MiB") }
        let offer = try pendingOffer(now: now)
        try reserve(UInt64(data.count))
        try storage.append(data, to: part(offer.candidate.digest), offset: offset, maximumBytes: offer.payloadBytes)
    }

    public func finishDownload(now: UInt64) throws {
        try available()
        let offer = try pendingOffer(now: now)
        let partial = try storage.read(part(offer.candidate.digest), maximumBytes: Int(offer.payloadBytes))
        // A rename may have completed before a metadata fault. Reopening can finish
        // from that immutable verified destination without lowering the sequence.
        let payload = try partial ?? storage.read(file(offer.candidate.digest), maximumBytes: Int(offer.payloadBytes))
        guard let payload, UInt64(payload.count) == offer.payloadBytes else { throw UpdateError("download.incomplete", "Download is incomplete") }
        guard ReleaseVerifier.sha256(payload) == offer.payloadSHA256 else {
            if partial != nil { try storage.remove(part(offer.candidate.digest)) }
            throw UpdateError("payload.integrity", "Downloaded payload SHA-256 mismatch")
        }
        let artifact = try verifier.verifyArtifact(signedManifest: offer.candidate.signedManifest, payload: payload, now: now)
        _ = try verifier.verifyAssignment(signedAssignment: offer.candidate.signedAssignment, artifact: artifact,
            channel: configuration.channel, installation: configuration.installation, lastSequence: 0, now: now)
        try executableValidator(payload, artifact)
        if partial != nil {
            do { try storage.publishPayload(part(offer.candidate.digest), as: file(offer.candidate.digest)) }
            catch { poisoned = true; throw error }
        }
        state.candidates[offer.candidate.digest] = offer.candidate
        state.staged = offer.candidate.digest; state.download = nil
        Self.compact(&state)
        try commit()
        try cleanupOrPoison()
    }

    public func cancelDownload() throws {
        try available()
        guard let candidate = state.download else { return }
        state.download = nil
        try commit()
        do { try storage.remove(part(candidate.digest)); try cleanup() }
        catch { poisoned = true; throw error }
    }

    /// Call once per opened process session, before starting any feature instance.
    /// This only selects immutable bytes; the installed engine owns their execution.
    public func selectAtColdStart(now: UInt64) throws -> ColdStartSelection {
        try available()
        guard !selectedThisSession else { throw UpdateError("startup.session", "A cold-start selection already occurred in this session") }
        selectedThisSession = true
        if state.attempt != nil {
            state.attempt = nil; state.lastRecovery = StartupFailure.unknownInterruption.rawValue
            try commit()
            return fallback()
        }
        guard let digest = state.staged, let candidate = state.candidates[digest] else { return fallback() }
        guard let cached = try? checkedPayload(candidate, using: healthyVerifier, now: 0) else {
            quarantine(digest, reason: "missing_or_corrupt_payload")
            try commit(); return fallback()
        }
        do {
            _ = try verifier.verifyAssignment(signedAssignment: candidate.signedAssignment, artifact: cached.artifact,
                channel: configuration.channel, installation: configuration.installation, lastSequence: 0, now: now)
        } catch {
            quarantine(digest, reason: "signing_authority_denied")
            try commit(); return fallback()
        }
        let launch = UUID().uuidString
        state.attempt = StartupAttempt(launchID: launch, digest: digest, startedAtWallTime: now)
        try commit()
        monotonicStart = configuration.monotonicNanoseconds()
        return ColdStartSelection(source: .provisional, artifactSHA256: digest,
            payloadSHA256: cached.artifact.payloadSHA256, payload: cached.payload,
            verifiedArtifact: cached.artifact, launchID: launch)
    }

    public func markHealthy(launchID: String, now: UInt64, completedMilestones: Set<String>) throws {
        try available()
        guard let attempt = state.attempt, attempt.launchID == launchID, let started = monotonicStart else {
            throw UpdateError("health.launch", "No matching startup in this process session")
        }
        let monotonicNow = configuration.monotonicNanoseconds()
        guard monotonicNow >= started, monotonicNow - started >= configuration.observationSeconds * 1_000_000_000,
              completedMilestones.count <= 32, completedMilestones.allSatisfy(recoveryIdentifier),
              configuration.requiredMilestones.isSubset(of: completedMilestones) else {
            throw UpdateError("health.incomplete", "Monotonic observation or required startup milestones incomplete")
        }
        guard let candidate = state.candidates[attempt.digest] else { throw UpdateError("health.payload", "Startup candidate disappeared") }
        _ = try checkedPayload(candidate, using: verifier, now: now)
        if state.healthy != attempt.digest { state.previousHealthy = state.healthy }
        state.healthy = attempt.digest; state.staged = nil; state.attempt = nil
        state.failures.removeValue(forKey: attempt.digest)
        Self.compact(&state)
        try commit()
        monotonicStart = nil
        try cleanupOrPoison()
    }

    /// Classification is evidence supplied by the installed host, not guest code.
    /// Unknown kills, force-quits and native crashes never count as guest traps.
    public func reportFailure(launchID: String, reason: StartupFailure) throws -> ColdStartSelection {
        try available()
        guard let attempt = state.attempt, attempt.launchID == launchID else { throw UpdateError("startup.launch", "Unknown launch identity") }
        if reason == .deterministicTrap {
            let count = min(configuration.failureThreshold, (state.failures[attempt.digest] ?? 0) + 1)
            if state.failures[attempt.digest] != nil || state.failures.count < 256 { state.failures[attempt.digest] = count }
            else { quarantine(attempt.digest, reason: "history_capacity") }
            if count >= configuration.failureThreshold { quarantine(attempt.digest, reason: reason.rawValue) }
        }
        state.lastRecovery = reason.rawValue; state.attempt = nil
        try commit()
        monotonicStart = nil; selectedThisSession = true
        return fallback()
    }

    private func available() throws {
        guard !closed, !poisoned else { throw UpdateError("store.unavailable", "Store closed or commit uncertain; reopen before further work") }
    }

    private func quarantine(_ digest: String, reason: String) {
        if state.quarantine[digest] != nil || state.quarantine.count < 256 { state.quarantine[digest] = reason }
        // At capacity, retain the existing deny history and disable the pending
        // candidate. New offers are denied until trusted native maintenance.
        state.staged = nil
    }

    private func pendingOffer(now: UInt64) throws -> UpdateOffer {
        guard let candidate = state.download else { throw UpdateError("download.absent", "No pending download") }
        let offer = try verifier.authorizeOffer(manifest: candidate.signedManifest, assignment: candidate.signedAssignment,
            channel: configuration.channel, installation: configuration.installation, lastSequence: 0, now: now)
        guard offer.candidate.digest == candidate.digest, offer.candidate.sequence == candidate.sequence,
              candidate.sequence == state.acceptedSequence, state.quarantine[candidate.digest] == nil else { throw UpdateError("download.binding", "Saved offer does not bind replay state or is quarantined") }
        return offer
    }

    private func reserve(_ bytes: UInt64) throws {
        let free = try storage.availableBytes()
        guard free >= bytes, free - bytes >= configuration.reserveDiskBytes else { throw UpdateError("store.disk", "Recovery disk reserve would be exhausted") }
    }

    private func commit() throws {
        do { try storage.atomicState(Self.encode(state)) }
        catch { poisoned = true; throw error }
    }

    private func checkedPayload(_ candidate: StoredUpdateCandidate, using authority: ReleaseVerifier, now: UInt64) throws -> (payload: Data, artifact: VerifiedArtifact) {
        guard state.quarantine[candidate.digest] == nil, candidate.sequence > 0, candidate.sequence <= state.acceptedSequence,
              let payload = try storage.read(file(candidate.digest), maximumBytes: Int(verifier.host.maxPayloadBytes)) else {
            throw UpdateError("store.payload", "Cached payload unavailable")
        }
        let artifact = try authority.verifyArtifact(signedManifest: candidate.signedManifest, payload: payload, now: now)
        let assignment = try authority.verifyAssignment(signedAssignment: candidate.signedAssignment, artifact: artifact,
            channel: configuration.channel, installation: configuration.installation, lastSequence: 0, now: now)
        guard artifact.artifactSHA256 == candidate.digest, assignment.sequence == candidate.sequence else { throw UpdateError("store.binding", "Cached signed identity changed") }
        try executableValidator(payload, artifact)
        return (payload, artifact)
    }

    private func fallback() -> ColdStartSelection {
        for digest in [state.healthy, state.previousHealthy].compactMap({ $0 }) {
            if let candidate = state.candidates[digest], let cached = try? checkedPayload(candidate, using: healthyVerifier, now: 0) {
                return ColdStartSelection(source: .healthy, artifactSHA256: digest,
                    payloadSHA256: cached.artifact.payloadSHA256, payload: cached.payload,
                    verifiedArtifact: cached.artifact, launchID: nil)
            }
        }
        return ColdStartSelection(source: .nativeFallback, artifactSHA256: nil, payloadSHA256: nil,
            payload: nil, verifiedArtifact: nil, launchID: nil)
    }

    @discardableResult
    private static func compact(_ state: inout RecoveryState) -> Bool {
        let keep = Set([state.healthy, state.previousHealthy, state.staged, state.attempt?.digest, state.download?.digest].compactMap { $0 })
        let removed = state.candidates.keys.filter { !keep.contains($0) }
        for digest in removed { state.candidates.removeValue(forKey: digest); if state.quarantine[digest] == nil { state.failures.removeValue(forKey: digest) } }
        return !removed.isEmpty
    }

    private func cleanupOrPoison() throws {
        do { try cleanup() }
        catch { poisoned = true; throw error }
    }

    private func cleanup() throws {
        var keep = Set(state.candidates.keys.map(file))
        if let candidate = state.download { keep.formUnion([file(candidate.digest), part(candidate.digest)]) }
        try storage.pruneOwnedFiles(keeping: keep)
    }

    private func file(_ digest: String) -> String { digest + ".payload" }
    private func part(_ digest: String) -> String { digest + ".payload.part" }

    private static func encode(_ state: RecoveryState) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let data = try encoder.encode(state)
        guard data.count <= 1_048_576 else { throw UpdateError("store.size", "Recovery metadata exceeds 1 MiB") }
        return data
    }

    private static func validate(_ state: RecoveryState, configuration: ColdStartConfiguration, host: InstalledRuntime) throws {
        guard state.schemaVersion == 1, state.host == host, state.channel == configuration.channel,
              state.installation == configuration.installation, state.candidates.count <= 4,
              state.failures.count <= 256, state.quarantine.count <= 256,
              state.failures.allSatisfy({ recoveryDigest($0.key) && $0.value <= 10 }),
              state.quarantine.allSatisfy({ recoveryDigest($0.key) && recoveryIdentifier($0.value) }),
              state.lastRecovery.isEmpty || recoveryIdentifier(state.lastRecovery) else { throw UpdateError("store.state", "Recovery state/installed contract is invalid") }
        for (digest, candidate) in state.candidates {
            guard recoveryDigest(digest), digest == candidate.digest, candidate.sequence > 0,
                  candidate.sequence <= state.acceptedSequence, candidate.signedManifest.count <= 262_144,
                  candidate.signedAssignment.count <= 65_536 else { throw UpdateError("store.state", "Invalid retained candidate") }
        }
        for digest in [state.healthy, state.previousHealthy, state.staged, state.attempt?.digest].compactMap({ $0 }) {
            guard recoveryDigest(digest), state.candidates[digest] != nil else { throw UpdateError("store.state", "Recovery pointer has no candidate") }
        }
        if let candidate = state.download {
            guard recoveryDigest(candidate.digest), candidate.sequence > 0, candidate.sequence == state.acceptedSequence,
                  candidate.signedManifest.count <= 262_144, candidate.signedAssignment.count <= 65_536 else { throw UpdateError("store.state", "Invalid pending offer") }
        }
        if let attempt = state.attempt {
            guard recoveryIdentifier(attempt.launchID), state.staged == attempt.digest else { throw UpdateError("store.state", "Invalid startup attempt") }
        }
    }
}
