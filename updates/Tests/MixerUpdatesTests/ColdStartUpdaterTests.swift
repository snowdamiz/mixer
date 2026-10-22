import Foundation
import Testing
import Crypto
@testable import MixerUpdates

private final class StoreClock: @unchecked Sendable {
    private let lock = NSLock()
    private var value: UInt64 = 1_000
    func now() -> UInt64 { lock.lock(); defer { lock.unlock() }; return value }
    func set(_ value: UInt64) { lock.lock(); self.value = value; lock.unlock() }
    func advance() { lock.lock(); value += 10_000_000_000; lock.unlock() }
}

private final class StoreFault: @unchecked Sendable {
    private let lock = NSLock()
    private var point: DurabilityFaultPoint?
    func arm(_ point: DurabilityFaultPoint?) { lock.lock(); self.point = point; lock.unlock() }
    func check(_ point: DurabilityFaultPoint) throws {
        lock.lock(); let hit = self.point == point; lock.unlock()
        if hit { throw UpdateError("test.interruption", point.rawValue) }
    }
}

private struct StoreVector: Decodable {
    let host: InstalledRuntime
    let signed_manifest: CanonicalValue
    let signed_assignment: CanonicalValue
    let installation: String
}

private struct StoreOffer {
    let manifest: Data
    let assignment: Data
    let payload: Data
    let digest: String
}

private struct StoreFixture {
    let vector: StoreVector
    // Ephemeral process-only test signing material, never persisted or logged.
    let key = Curve25519.Signing.PrivateKey()
    let directory: URL
    let clock = StoreClock()
    let fault = StoreFault()
    let now: UInt64 = 1_792_627_300

    init() throws {
        let url = try #require(Bundle.module.url(forResource: "signed-release-v1", withExtension: "json", subdirectory: "Fixtures"))
        vector = try StrictJSON.decode(StoreVector.self, from: Data(contentsOf: url))
        directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-store-\(UUID().uuidString)")
    }
    func remove() { try? FileManager.default.removeItem(at: directory) }
    func root(revoked: Bool = false, replaced: Bool = false, notAfter: UInt64 = 0) -> TrustRoot {
        TrustRoot(keyID: "store.test", publicKey: replaced ? Curve25519.Signing.PrivateKey().publicKey.rawRepresentation : key.publicKey.rawRepresentation,
                  scope: vector.host.scope, artifact: true, assignment: true, revoked: revoked, notAfterUnix: notAfter)
    }
    func verifier(revoked: Bool = false, replaced: Bool = false, notAfter: UInt64 = 0) throws -> ReleaseVerifier {
        try ReleaseVerifier(host: vector.host, roots: [root(revoked: revoked, replaced: replaced, notAfter: notAfter)])
    }
    func configuration(reserve: UInt64 = 0) -> ColdStartConfiguration {
        ColdStartConfiguration(directory: directory, channel: "beta", installation: vector.installation,
            reserveDiskBytes: reserve, monotonicNanoseconds: { clock.now() }, fault: { try fault.check($0) })
    }
    func open(revoked: Bool = false, replaced: Bool = false, notAfter: UInt64 = 0,
              validator: @escaping ColdStartUpdater.ExecutableValidator = { payload, _ in
                  // Explicit store-test fixture validation, not a Wasm/Swift engine claim.
                  guard payload.starts(with: Data("store-fixture-".utf8)) else { throw UpdateError("test.profile", "Fixture denied") }
              }) throws -> ColdStartUpdater {
        try ColdStartUpdater.open(configuration: configuration(), verifier: verifier(revoked: revoked, replaced: replaced, notAfter: notAfter), executableValidator: validator)
    }
    func offer(_ sequence: UInt64, release: UInt64? = nil) throws -> StoreOffer {
        let release = release ?? sequence
        let payload = Data("store-fixture-\(release)".utf8)
        var manifest = try #require(vector.signed_manifest.object?["manifest"]?.object)
        manifest["key_id"] = .text("store.test"); manifest["release_id"] = .text("store-release-\(release)")
        manifest["payload_sha256"] = .text(ReleaseVerifier.sha256(payload))
        manifest["compressed_bytes"] = .uint(UInt64(payload.count)); manifest["expanded_bytes"] = .uint(UInt64(payload.count))
        let value = CanonicalValue.object(manifest)
        let digest = ReleaseVerifier.sha256(try value.canonicalCBOR())
        var assignment = try #require(vector.signed_assignment.object?["assignment"]?.object)
        assignment["key_id"] = .text("store.test"); assignment["release_id"] = .text("store-release-\(release)")
        assignment["artifact_sha256"] = .text(digest); assignment["sequence"] = .uint(sequence)
        func sign(_ value: CanonicalValue, field: String, domain: String) throws -> Data {
            let signature = try key.signature(for: Data(domain.utf8) + value.canonicalCBOR())
            return try JSONEncoder().encode(CanonicalValue.object([field: value, "signature": .text(signature.base64EncodedString())]))
        }
        return try StoreOffer(manifest: sign(value, field: "manifest", domain: "mixer.artifact.v1\0"),
            assignment: sign(.object(assignment), field: "assignment", domain: "mixer.assignment.v1\0"), payload: payload, digest: digest)
    }
    func stage(_ offer: StoreOffer, on store: ColdStartUpdater) async throws {
        try await store.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment, now: now)
        try await store.appendDownload(offer.payload, atOffset: 0, now: now)
        try await store.finishDownload(now: now)
    }
    func earnHealth(_ store: ColdStartUpdater) async throws -> ColdStartSelection {
        let selected = try await store.selectAtColdStart(now: now)
        clock.advance()
        try await store.markHealthy(launchID: #require(selected.launchID), now: now, completedMilestones: ["feature_started", "first_screen"])
        return selected
    }
}

private func storeRejects(_ code: String? = nil, _ operation: () async throws -> Void) async {
    do { try await operation(); Issue.record("Expected store rejection") }
    catch let error as UpdateError { if let code { #expect(error.code == code) } }
    catch { if code != nil { Issue.record("Unexpected store error: \(error)") } }
}

@Test func coldStartHealthRequiresThisProcessMonotonicTimeAndMilestones() async throws {
    let f = try StoreFixture(); defer { f.remove() }
    let store = try f.open(); let offer = try f.offer(1)
    try await f.stage(offer, on: store)
    let selected = try await store.selectAtColdStart(now: f.now)
    #expect(selected.source == .provisional && selected.payload == offer.payload)
    let launch = try #require(selected.launchID)
    await storeRejects("startup.session") { _ = try await store.selectAtColdStart(now: f.now) }
    await storeRejects("health.incomplete") { try await store.markHealthy(launchID: launch, now: UInt64.max, completedMilestones: ["feature_started", "first_screen"]) }
    f.clock.set(0)
    await storeRejects("health.incomplete") { try await store.markHealthy(launchID: launch, now: f.now - 100, completedMilestones: ["feature_started", "first_screen"]) }
    f.clock.set(10_000_001_000)
    await storeRejects("health.incomplete") { try await store.markHealthy(launchID: launch, now: f.now, completedMilestones: ["feature_started"]) }
    try await store.markHealthy(launchID: launch, now: f.now - 100, completedMilestones: ["feature_started", "first_screen"])
    #expect(await store.snapshot().healthy == offer.digest)
    await store.close()
    let reopened = try f.open()
    let healthy = try await reopened.selectAtColdStart(now: UInt64.max)
    #expect(healthy.source == .healthy && healthy.payload == offer.payload && healthy.launchID == nil)
    await reopened.close()
}

@Test func downloadResumesAtExactOffsetAndCancellationPreservesReplayHighWater() async throws {
    let f = try StoreFixture(); defer { f.remove() }; let offer = try f.offer(1)
    var store = try f.open()
    try await store.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment, now: f.now)
    try await store.appendDownload(offer.payload.prefix(4), atOffset: 0, now: f.now)
    await store.close(); store = try f.open()
    #expect(try await store.downloadOffset() == 4)
    await storeRejects("download.offset") { try await store.appendDownload(Data([1]), atOffset: 3, now: f.now) }
    await storeRejects("download.offset") { try await store.appendDownload(offer.payload, atOffset: 4, now: f.now) }
    await storeRejects("download.chunk") { try await store.appendDownload(Data(repeating: 0, count: 1_048_577), atOffset: 4, now: f.now) }
    await storeRejects("download.incomplete") { try await store.finishDownload(now: f.now) }
    try await store.appendDownload(offer.payload.dropFirst(4), atOffset: 4, now: f.now)
    try await store.finishDownload(now: f.now)
    let second = try f.offer(2)
    try await store.beginDownload(signedManifest: second.manifest, signedAssignment: second.assignment, now: f.now)
    try await store.cancelDownload(); await store.close(); store = try f.open()
    #expect(await store.snapshot().acceptedSequence == 2)
    await storeRejects("assignment.replay") { try await store.beginDownload(signedManifest: second.manifest, signedAssignment: second.assignment, now: f.now) }
    await store.close()
}

@Test func integrityAndInstalledExecutablePolicyFailBeforeStaging() async throws {
    let f = try StoreFixture(); defer { f.remove() }; let offer = try f.offer(1)
    let store = try f.open(validator: { _, _ in throw UpdateError("test.profile", "Denied installed profile") })
    try await store.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment, now: f.now)
    try await store.appendDownload(Data(repeating: 0, count: offer.payload.count), atOffset: 0, now: f.now)
    await storeRejects("payload.integrity") { try await store.finishDownload(now: f.now) }
    #expect(try await store.downloadOffset() == 0)
    try await store.appendDownload(offer.payload, atOffset: 0, now: f.now)
    await storeRejects("test.profile") { try await store.finishDownload(now: f.now) }
    #expect(await store.snapshot().staged == nil)
    #expect(try await store.selectAtColdStart(now: f.now).source == .nativeFallback)
    await store.close()
}

@Test func deterministicTrapsQuarantineButUnknownKillsAndNativeFailuresDoNot() async throws {
    let f = try StoreFixture(); defer { f.remove() }; let a = try f.offer(1); let b = try f.offer(2)
    var store = try f.open(); try await f.stage(a, on: store); _ = try await f.earnHealth(store); await store.close()
    store = try f.open(); try await f.stage(b, on: store)
    _ = try await store.selectAtColdStart(now: f.now); await store.close()
    store = try f.open()
    #expect(try await store.selectAtColdStart(now: f.now).artifactSHA256 == a.digest)
    #expect(await store.snapshot().failures[b.digest] == nil)
    #expect(await store.snapshot().lastRecovery == StartupFailure.unknownInterruption.rawValue)
    await store.close()
    for reason in [StartupFailure.nativeCrash, .userQuit, .unknownInterruption, .deterministicTrap, .deterministicTrap] {
        store = try f.open(); let attempt = try await store.selectAtColdStart(now: f.now)
        let fallback = try await store.reportFailure(launchID: #require(attempt.launchID), reason: reason)
        #expect(fallback.artifactSHA256 == a.digest)
        await store.close()
    }
    store = try f.open(); let status = await store.snapshot()
    #expect(status.failures[b.digest] == 2 && status.quarantine[b.digest] == "deterministicTrap" && status.staged == nil)
    let retry = try f.offer(3, release: 2)
    await storeRejects("store.quarantine") { try await store.beginDownload(signedManifest: retry.manifest, signedAssignment: retry.assignment, now: f.now) }
    #expect(try await store.selectAtColdStart(now: f.now).artifactSHA256 == a.digest)
    await store.close()
}

@Test func earnedHealthyOfflineAuthorityRetainsSignatureKeysScopeAndCompatibility() async throws {
    let f = try StoreFixture(); defer { f.remove() }; let a = try f.offer(1); let b = try f.offer(2)
    var store = try f.open(); try await f.stage(a, on: store); _ = try await f.earnHealth(store); await store.close()
    store = try f.open(); try await f.stage(b, on: store); await store.close()
    store = try f.open(revoked: true, notAfter: 1)
    #expect(try await store.selectAtColdStart(now: f.now).artifactSHA256 == a.digest)
    #expect(await store.snapshot().quarantine[b.digest] == "signing_authority_denied")
    await store.close(); store = try f.open(replaced: true)
    #expect(try await store.selectAtColdStart(now: f.now).source == .nativeFallback)
    await store.close()
}

@Test(arguments: [DurabilityFaultPoint.beforeStateWrite, .beforeStateFileSync, .beforeStateRename, .afterStateRename, .afterStateDirectorySync])
func sequenceReservationInterruptionNeverAuthorizesUnverifiedPayload(_ point: DurabilityFaultPoint) async throws {
    let f = try StoreFixture(); defer { f.remove() }; let offer = try f.offer(1)
    var store = try f.open(); f.fault.arm(point)
    await storeRejects("test.interruption") { try await store.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment, now: f.now) }
    await storeRejects("store.unavailable") { _ = try await store.downloadOffset() }
    await store.close(); f.fault.arm(nil); store = try f.open()
    let committed = [.afterStateRename, .afterStateDirectorySync].contains(point)
    #expect(await store.snapshot().acceptedSequence == (committed ? 1 : 0))
    if committed {
        try await store.cancelDownload()
        await storeRejects("assignment.replay") { try await store.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment, now: f.now) }
    }
    #expect(try await store.selectAtColdStart(now: f.now).source == .nativeFallback)
    await store.close()
}

@Test(arguments: [DurabilityFaultPoint.beforePayloadWrite, .beforePayloadSync, .beforePayloadRename, .afterPayloadRename, .afterPayloadDirectorySync])
func payloadInterruptionResumesWithoutLosingReplayState(_ point: DurabilityFaultPoint) async throws {
    let f = try StoreFixture(); defer { f.remove() }; let offer = try f.offer(1); var store = try f.open()
    try await store.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment, now: f.now)
    if [.beforePayloadWrite, .beforePayloadSync].contains(point) {
        f.fault.arm(point)
        await storeRejects("test.interruption") { try await store.appendDownload(offer.payload, atOffset: 0, now: f.now) }
    } else {
        try await store.appendDownload(offer.payload, atOffset: 0, now: f.now); f.fault.arm(point)
        await storeRejects("test.interruption") { try await store.finishDownload(now: f.now) }
    }
    await store.close(); f.fault.arm(nil); store = try f.open()
    let status = await store.snapshot()
    #expect(status.acceptedSequence == 1 && status.staged == nil)
    let offset = try await store.downloadOffset()
    if [.afterPayloadRename, .afterPayloadDirectorySync].contains(point) { #expect(offset == UInt64(offer.payload.count)) }
    let final = f.directory.appendingPathComponent(offer.digest + ".payload")
    if !FileManager.default.fileExists(atPath: final.path) && offset < UInt64(offer.payload.count) {
        try await store.appendDownload(offer.payload.dropFirst(Int(offset)), atOffset: offset, now: f.now)
    }
    try await store.finishDownload(now: f.now)
    #expect(try await store.selectAtColdStart(now: f.now).payload == offer.payload)
    await store.close()
}

@Test func retainedPayloadRenamedBeforeMetadataCommitCanFinishAfterReopen() async throws {
    let f = try StoreFixture(); defer { f.remove() }; let offer = try f.offer(1); var store = try f.open()
    try await store.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment, now: f.now)
    try await store.appendDownload(offer.payload, atOffset: 0, now: f.now); f.fault.arm(.beforeStateRename)
    await storeRejects("test.interruption") { try await store.finishDownload(now: f.now) }
    #expect(await store.snapshot().requiresReopen)
    await store.close(); f.fault.arm(nil); store = try f.open()
    #expect(try await store.downloadOffset() == UInt64(offer.payload.count))
    try await store.finishDownload(now: f.now)
    #expect(try await store.selectAtColdStart(now: f.now).payload == offer.payload)
    await store.close()
}

@Test func currentSigningExpiryStillPreventsEarningHealthyAuthority() async throws {
    let f = try StoreFixture(); defer { f.remove() }; let offer = try f.offer(1)
    let store = try f.open(notAfter: f.now + 1)
    try await f.stage(offer, on: store); let selected = try await store.selectAtColdStart(now: f.now); f.clock.advance()
    await storeRejects("signature.authority") {
        try await store.markHealthy(launchID: #require(selected.launchID), now: f.now + 1, completedMilestones: ["feature_started", "first_screen"])
    }
    #expect(await store.snapshot().healthy == nil)
    await store.close()
}

@Test func nativeHistoryCapacityNeverWritesAnUnopenableState() async throws {
    let f = try StoreFixture(); defer { f.remove() }; let offer = try f.offer(1); var store = try f.open()
    try await f.stage(offer, on: store); await store.close()
    let stateURL = f.directory.appendingPathComponent("state.json")
    var state = try StrictJSON.decode(RecoveryState.self, from: Data(contentsOf: stateURL))
    for index in 0..<256 {
        let digest = ReleaseVerifier.sha256(Data("history-\(index)".utf8))
        state.quarantine[digest] = "deterministicTrap"; state.failures[digest] = 2
    }
    try JSONEncoder().encode(state).write(to: stateURL)
    store = try f.open(); let selected = try await store.selectAtColdStart(now: f.now)
    _ = try await store.reportFailure(launchID: #require(selected.launchID), reason: .deterministicTrap)
    #expect(await store.snapshot().staged == nil)
    await store.close(); store = try f.open()
    let status = await store.snapshot()
    #expect(status.quarantine.count == 256 && status.failures.count == 256)
    let next = try f.offer(2)
    await storeRejects("store.quarantine") { try await store.beginDownload(signedManifest: next.manifest, signedAssignment: next.assignment, now: f.now) }
    await store.close()
}

@Test func symlinkCacheNeverGrantsAuthorityAndOrphanCleanupPreservesUnknownFiles() async throws {
    let f = try StoreFixture(); defer { f.remove() }; let offer = try f.offer(1); var store = try f.open()
    try await f.stage(offer, on: store); await store.close()
    let cached = f.directory.appendingPathComponent(offer.digest + ".payload")
    let outside = f.directory.appendingPathComponent("native-owned-preserved")
    try offer.payload.write(to: outside); try FileManager.default.removeItem(at: cached)
    try FileManager.default.createSymbolicLink(at: cached, withDestinationURL: outside)
    let orphan = f.directory.appendingPathComponent(String(repeating: "f", count: 64) + ".payload.part")
    try Data([1]).write(to: orphan)
    store = try f.open()
    #expect(!FileManager.default.fileExists(atPath: orphan.path))
    #expect(try await store.selectAtColdStart(now: f.now).source == .nativeFallback)
    #expect(try Data(contentsOf: outside) == offer.payload)
    await store.close()
}

@Test(arguments: [DurabilityFaultPoint.beforeStateWrite, .beforeStateFileSync, .beforeStateRename, .afterStateRename, .afterStateDirectorySync])
func interruptedHealthyWriteEitherRecoversOldStateOrCompleteHealthyState(_ point: DurabilityFaultPoint) async throws {
    let f = try StoreFixture(); defer { f.remove() }; let offer = try f.offer(1); var store = try f.open()
    try await f.stage(offer, on: store); let selected = try await store.selectAtColdStart(now: f.now); f.clock.advance(); f.fault.arm(point)
    await storeRejects("test.interruption") {
        try await store.markHealthy(launchID: #require(selected.launchID), now: f.now, completedMilestones: ["feature_started", "first_screen"])
    }
    await store.close(); f.fault.arm(nil); store = try f.open()
    let recovered = try await store.selectAtColdStart(now: f.now)
    #expect(recovered.source == ([.afterStateRename, .afterStateDirectorySync].contains(point) ? .healthy : .nativeFallback))
    #expect(await store.snapshot().failures.isEmpty)
    await storeRejects("health.launch") { try await store.markHealthy(launchID: #require(selected.launchID), now: f.now, completedMilestones: ["feature_started", "first_screen"]) }
    await store.close()
}

@Test func selectedPayloadIsAnImmutableVerifiedSnapshotAndCorruptCacheFallsBack() async throws {
    let f = try StoreFixture(); defer { f.remove() }; let offer = try f.offer(1)
    var store = try f.open(); try await f.stage(offer, on: store); await store.close()
    let cached = f.directory.appendingPathComponent(offer.digest + ".payload")
    store = try f.open(validator: { payload, _ in
        guard payload == offer.payload else { throw UpdateError("test.profile", "Wrong bytes") }
        try Data("replaced-after-check".utf8).write(to: cached)
    })
    let selected = try await store.selectAtColdStart(now: f.now)
    #expect(selected.source == .provisional && selected.payload == offer.payload)
    f.clock.advance()
    await storeRejects("payload.integrity") { try await store.markHealthy(launchID: #require(selected.launchID), now: f.now, completedMilestones: ["feature_started", "first_screen"]) }
    await store.close(); store = try f.open()
    #expect(try await store.selectAtColdStart(now: f.now).source == .nativeFallback)
    await store.close(); store = try f.open()
    #expect(try await store.selectAtColdStart(now: f.now).source == .nativeFallback)
    #expect(await store.snapshot().quarantine[offer.digest] == "missing_or_corrupt_payload")
    await store.close()
}

@Test func cacheKeepsTwoHealthyGenerationsAndFallsBackAcrossMissingFiles() async throws {
    let f = try StoreFixture(); defer { f.remove() }; var store = try f.open()
    for sequence in UInt64(1)...5 {
        try await f.stage(f.offer(sequence), on: store); _ = try await f.earnHealth(store)
        #expect(await store.snapshot().retainedCandidates <= 2)
        await store.close(); store = try f.open()
    }
    let a = try f.offer(4); let b = try f.offer(5)
    let files = try FileManager.default.contentsOfDirectory(atPath: f.directory.path).filter { $0.hasSuffix(".payload") }
    #expect(files.count == 2)
    try FileManager.default.removeItem(at: f.directory.appendingPathComponent(b.digest + ".payload"))
    #expect(try await store.selectAtColdStart(now: f.now).artifactSHA256 == a.digest)
    await store.close(); store = try f.open()
    try Data([1]).write(to: f.directory.appendingPathComponent(a.digest + ".payload"))
    #expect(try await store.selectAtColdStart(now: f.now).source == .nativeFallback)
    await store.close()
}

@Test func reopenCompactsInterruptedRetirementBeforeAnotherCandidateCanBeStaged() async throws {
    let f = try StoreFixture(); defer { f.remove() }; var store = try f.open()
    for sequence in UInt64(1)...3 {
        try await f.stage(f.offer(sequence), on: store); _ = try await f.earnHealth(store)
        await store.close(); store = try f.open()
    }
    try await f.stage(f.offer(4), on: store); await store.close()
    // Model a historical transaction that left an unreferenced metadata entry
    // before file retirement. Compaction must precede accepting another offer.
    let stateURL = f.directory.appendingPathComponent("state.json")
    var state = try StrictJSON.decode(RecoveryState.self, from: Data(contentsOf: stateURL))
    let retired = try f.offer(1)
    state.candidates[retired.digest] = StoredUpdateCandidate(digest: retired.digest, sequence: 1,
        signedManifest: retired.manifest, signedAssignment: retired.assignment)
    try JSONEncoder().encode(state).write(to: stateURL)
    let retiredFile = f.directory.appendingPathComponent(retired.digest + ".payload")
    try retired.payload.write(to: retiredFile)
    store = try f.open()
    #expect(await store.snapshot().retainedCandidates == 3)
    #expect(!FileManager.default.fileExists(atPath: retiredFile.path))
    try await f.stage(f.offer(5), on: store); await store.close(); store = try f.open()
    #expect(await store.snapshot().retainedCandidates == 3)
    #expect(try await store.selectAtColdStart(now: f.now).payload == f.offer(5).payload)
    await store.close()
}

@Test func storeLockMissingReplayStateDiskReserveAndMalformedMetadataFailClosed() async throws {
    let f = try StoreFixture(); defer { f.remove() }; let store = try f.open()
    #expect(throws: UpdateError.self) { try f.open() }
    await store.close()
    let constrained = try ColdStartUpdater.open(configuration: f.configuration(reserve: UInt64.max), verifier: f.verifier(), executableValidator: { _, _ in })
    let offer = try f.offer(1)
    await storeRejects("store.disk") { try await constrained.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment, now: f.now) }
    #expect(await constrained.snapshot().acceptedSequence == 0)
    await constrained.close()
    let state = f.directory.appendingPathComponent("state.json"); let original = try Data(contentsOf: state)
    for bytes in [Data("{\"schemaVersion\":1,\"schemaVersion\":1}".utf8), Data(repeating: 32, count: 1_048_577), Data("{\"unknown\":1}".utf8)] {
        try bytes.write(to: state); #expect(throws: (any Error).self) { try f.open() }
    }
    try original.write(to: state)
    let reopened = try f.open(); await reopened.close()
    try FileManager.default.removeItem(at: state)
    #expect(throws: UpdateError.self) { try f.open() }
}
