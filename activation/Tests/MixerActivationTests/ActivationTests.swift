import Foundation
import Dispatch
import Testing
import Crypto
import MixerRuntime
import MixerUpdates
@testable import MixerActivation

private final class Clock: @unchecked Sendable {
    private let lock = NSLock()
    private var value: UInt64 = 1_000
    func now() -> UInt64 { lock.lock(); defer { lock.unlock() }; return value }
    func advance() { lock.lock(); value += 10_000_000_000; lock.unlock() }
}

private struct Offer {
    let manifest: Data
    let assignment: Data
    let payload: Data
    let digest: String
}

private struct Fixture {
    let protocolVersion: UInt64
    init(protocolVersion: UInt64 = 1) { self.protocolVersion = protocolVersion }
    // Originally authored guest counter, with retained mutable global/memory.
    static let counter = Data([0,97,115,109,1,0,0,0,
        1,5,1,96,0,1,127,3,2,1,0,5,4,1,1,1,1,
        6,6,1,127,1,65,0,11,7,7,1,3,114,117,110,0,0,
        10,20,1,18,0,35,0,65,1,106,36,0,65,0,35,0,54,2,0,35,0,11])
    static let trap = Data([0,97,115,109,1,0,0,0,1,5,1,96,0,1,127,
        3,2,1,0,7,7,1,3,114,117,110,0,0,10,5,1,3,0,0,11])
    let key = Curve25519.Signing.PrivateKey() // ephemeral, never persisted
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-activation-\(UUID().uuidString)")
    let clock = Clock()
    let now: UInt64 = 1_792_627_300
    let fingerprint = ReleaseVerifier.sha256(Data("owned-VM-test-installed-build-v1".utf8))
    let scope = UpdateScope(organization: "test-org", project: "test-project", app: "test-app", environment: "development", platform: "ios")
    var scopeValue: CanonicalValue { .object(["organization": .text(scope.organization), "project": .text(scope.project),
        "app": .text(scope.app), "environment": .text(scope.environment), "platform": .text(scope.platform)]) }
    var host: InstalledRuntime { InstalledRuntime(scope: scope, runtime: fingerprint, protocolVersion: protocolVersion, capabilityHashes: [:],
        stateVersion: 1, maxPayloadBytes: 4_194_304,
        limits: ResourceLimits(memoryBytes: 4_194_304, fuel: 1_000_000, startupMilliseconds: 60_000)) }
    func verifier(host: InstalledRuntime? = nil) throws -> ReleaseVerifier {
        try ReleaseVerifier(host: host ?? self.host, roots: [TrustRoot(keyID: "test-key", publicKey: key.publicKey.rawRepresentation,
            scope: scope, artifact: true, assignment: true)])
    }
    func policy(limits: VMLimits = VMLimits()) throws -> InstalledExecution {
        try InstalledExecution(runtimeFingerprint: fingerprint, profile: .integerV1, limits: limits,
            startupExport: "run", maximumStartupMilliseconds: 5_000)
    }
    func open(policy: InstalledExecution? = nil) throws -> ColdStartRuntime {
        try ColdStartRuntime.open(configuration: ColdStartConfiguration(directory: directory, channel: "beta",
            installation: "test-installation", reserveDiskBytes: 0, monotonicNanoseconds: { clock.now() }),
            verifier: verifier(), execution: policy ?? self.policy())
    }
    func clean() { try? FileManager.default.removeItem(at: directory) }
    func offer(sequence: UInt64 = 1, release: String = "first", payload: Data = Self.counter,
               memory: UInt64 = 65_536, fuel: UInt64 = 100, startup: UInt64 = 5_000) throws -> Offer {
        var fields: [String: CanonicalValue] = [
            "schema": .uint(protocolVersion), "scope": scopeValue, "release_id": .text(release),
            "source_commit": .text(String(repeating: "a", count: 40)), "provenance_id": .text("local-test"),
            "runtime": .text(fingerprint), "protocol": .uint(protocolVersion), "guest_abi": .uint(1), "ui_schema": .uint(1),
            "capability_hashes": .object([:]), "state_min": .uint(1), "state_max": .uint(1),
            "payload_sha256": .text(ReleaseVerifier.sha256(payload)), "compressed_bytes": .uint(UInt64(payload.count)),
            "expanded_bytes": .uint(UInt64(payload.count)), "compression": .text("none"), "asset_hashes": .object([:]),
            "source_map_sha256": .text(ReleaseVerifier.sha256(Data())), "key_id": .text("test-key"),
            "created_at_unix": .uint(now), "limits": .object(["memory_bytes": .uint(memory), "fuel": .uint(fuel), "startup_milliseconds": .uint(startup)]),
        ]
        if protocolVersion == 2 {
            fields["capability_grants"] = .object(["schema": .uint(1),
                "schema_sha256": .text(VerifiedCapabilityGrants.descriptorSHA256), "entries": .array([])])
        }
        let manifest = CanonicalValue.object(fields)
        let digest = ReleaseVerifier.sha256(try manifest.canonicalCBOR())
        let assignment = CanonicalValue.object([
            "schema": .uint(protocolVersion), "scope": scopeValue, "channel": .text("beta"), "cohort": .text("sha256-v1"),
            "rollout_basis_points": .uint(10_000), "sequence": .uint(sequence), "release_id": .text(release),
            "artifact_sha256": .text(digest), "runtime": .text(fingerprint), "key_id": .text("test-key"), "created_at_unix": .uint(now),
        ])
        func sign(_ value: CanonicalValue, field: String, domain: String) throws -> Data {
            let signature = try key.signature(for: Data(domain.utf8) + value.canonicalCBOR())
            return try JSONEncoder().encode(CanonicalValue.object([field: value, "signature": .text(signature.base64EncodedString())]))
        }
        return try Offer(manifest: sign(manifest, field: "manifest", domain: "mixer.artifact.v\(protocolVersion)\0"),
            assignment: sign(assignment, field: "assignment", domain: "mixer.assignment.v\(protocolVersion)\0"), payload: payload, digest: digest)
    }
    func stage(_ offer: Offer, on runtime: ColdStartRuntime) async throws {
        try await runtime.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment, now: now)
        try await runtime.appendDownload(offer.payload, atOffset: 0, now: now)
        try await runtime.finishDownload(now: now)
    }
    func earnHealth(_ runtime: ColdStartRuntime) async throws {
        clock.advance()
        try await runtime.markHealthy(now: now, completedMilestones: ["feature_started", "first_screen"])
    }
}

private func rejects(_ code: String? = nil, _ operation: () async throws -> Void) async {
    do { try await operation(); Issue.record("Expected rejection") }
    catch let error as UpdateError { if let code { #expect(error.code == code) } }
    catch let error as VMFailure { if let code { #expect(error.code == code) } }
    catch { if code != nil { Issue.record("Unexpected error: \(error)") } }
}

@Suite(.serialized)
struct ActivationTests {
    @Test func emptyStoreSelectsRealNativeFallbackAndCannotExecuteGuest() async throws {
        let f = Fixture(); defer { f.clean() }; let runtime = try f.open()
        let status = try await runtime.start(now: f.now)
        #expect(status.phase == .nativeFallback && status.source == .nativeFallback)
        #expect(status.startupResult == nil && status.artifactSHA256 == nil)
        await rejects("activation.inactive") { _ = try await runtime.invoke("run") }
        await rejects("activation.state") { _ = try await runtime.start(now: f.now) }
        await runtime.close(); #expect(await runtime.snapshot().phase == .closed)
    }

    @Test(arguments: [UInt64(1), 2]) func verifiedColdStartRunsOwnedCounterRetainsStateAndReopensHealthyOffline(version: UInt64) async throws {
        let f = Fixture(protocolVersion: version); defer { f.clean() }; let offer = try f.offer()
        var runtime = try f.open(); try await f.stage(offer, on: runtime)
        let started = try await runtime.start(now: f.now)
        #expect(started.phase == .guest && started.source == .provisional && started.artifactSHA256 == offer.digest)
        #expect(started.startupResult?.value == .i32(1))
        #expect(try await runtime.invoke("run").value == .i32(2))
        await rejects("health.incomplete") { try await runtime.markHealthy(now: f.now, completedMilestones: ["feature_started", "first_screen"]) }
        try await f.earnHealth(runtime)
        #expect(await runtime.recoverySnapshot().healthy == offer.digest)
        await runtime.close(); runtime = try f.open()
        let healthy = try await runtime.start(now: UInt64.max)
        #expect(healthy.source == .healthy && healthy.startupResult?.value == .i32(1))
        #expect(try await runtime.invoke("run").value == .i32(2))
        await runtime.close()
    }

    @Test func trapRecoveryUsesHealthyGuestThenQuarantinesWithoutTouchingAppData() async throws {
        let f = Fixture(); defer { f.clean() }; let healthy = try f.offer()
        var runtime = try f.open(); try await f.stage(healthy, on: runtime)
        _ = try await runtime.start(now: f.now); try await f.earnHealth(runtime); await runtime.close()
        let draft = f.directory.deletingLastPathComponent().appendingPathComponent("draft-\(UUID().uuidString)")
        defer { try? FileManager.default.removeItem(at: draft) }
        let text = Data("Unsynced\n  exact draft 🌍".utf8); try text.write(to: draft)
        let candidate = try f.offer(sequence: 2, release: "trap", payload: Fixture.trap)
        for attempt in 1...2 {
            runtime = try f.open()
            if attempt == 1 { try await f.stage(candidate, on: runtime) }
            let active = try await runtime.start(now: f.now)
            #expect(active.phase == .guest && active.source == .healthy && active.artifactSHA256 == healthy.digest)
            #expect(active.failureCodes == ["unreachable"] && active.startupResult?.value == .i32(1))
            #expect(await runtime.recoverySnapshot().failures[candidate.digest] == UInt64(attempt))
            await runtime.close()
        }
        runtime = try f.open()
        #expect(await runtime.recoverySnapshot().quarantine[candidate.digest] == "deterministicTrap")
        #expect(try await runtime.start(now: f.now).artifactSHA256 == healthy.digest)
        #expect(try Data(contentsOf: draft) == text)
        await runtime.close()
    }

    @Test func signedLimitsReachActualVMValidationAndExecution() async throws {
        let f = Fixture(); defer { f.clean() }; var runtime = try f.open()
        let tooSmall = try f.offer(memory: 65_535)
        try await runtime.beginDownload(signedManifest: tooSmall.manifest, signedAssignment: tooSmall.assignment, now: f.now)
        try await runtime.appendDownload(tooSmall.payload, atOffset: 0, now: f.now)
        await rejects { try await runtime.finishDownload(now: f.now) }
        #expect(await runtime.recoverySnapshot().staged == nil)
        try await runtime.cancelDownload(); await runtime.close()
        runtime = try f.open(); let lowFuel = try f.offer(sequence: 2, release: "fuel", fuel: 8)
        try await f.stage(lowFuel, on: runtime)
        let status = try await runtime.start(now: f.now)
        #expect(status.phase == .nativeFallback && status.failureCodes == ["fuel_exhausted"])
        #expect(await runtime.recoverySnapshot().failures[lowFuel.digest] == 1)
        await runtime.close()
    }

    @Test func nativeLimitsCanOnlyNarrowSignedLimits() async throws {
        let f = Fixture(); defer { f.clean() }
        let runtime = try f.open(policy: f.policy(limits: VMLimits(fuel: 8)))
        try await f.stage(f.offer(fuel: 100), on: runtime)
        #expect(try await runtime.start(now: f.now).failureCodes == ["fuel_exhausted"])
        await runtime.close()
    }

    @Test func payloadCorruptionAndWrongInstalledPolicyCannotActivate() async throws {
        let f = Fixture(); defer { f.clean() }
        let wrong = try InstalledExecution(runtimeFingerprint: String(repeating: "0", count: 64), profile: .integerV1, startupExport: "run")
        await rejects("activation.compatibility") { _ = try f.open(policy: wrong) }
        let unsupported = InstalledRuntime(scope: f.scope, runtime: f.fingerprint,
            capabilityHashes: ["storage.kv.v1": String(repeating: "a", count: 64)],
            stateVersion: 1, maxPayloadBytes: 4_194_304, limits: f.host.limits)
        await rejects("activation.compatibility") {
            _ = try ColdStartRuntime.open(configuration: ColdStartConfiguration(directory: f.directory, channel: "beta",
                installation: "test-installation"), verifier: f.verifier(host: unsupported), execution: f.policy())
        }
        #expect(!FileManager.default.fileExists(atPath: f.directory.path))
        let runtime = try f.open(); let offer = try f.offer()
        try await runtime.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment, now: f.now)
        try await runtime.appendDownload(Data(repeating: 0, count: offer.payload.count), atOffset: 0, now: f.now)
        await rejects("payload.integrity") { try await runtime.finishDownload(now: f.now) }
        #expect(try await runtime.downloadOffset() == 0)
        #expect(try await runtime.start(now: f.now).phase == .nativeFallback)
        await runtime.close()
    }

    @Test func nativeArgumentMistakesDoNotBecomeGuestTrapEvidence() async throws {
        let f = Fixture(); defer { f.clean() }; let runtime = try f.open(); let offer = try f.offer()
        try await f.stage(offer, on: runtime); _ = try await runtime.start(now: f.now)
        await rejects("invalid_arguments") { _ = try await runtime.invoke("run", arguments: [.i32(1)]) }
        #expect(await runtime.snapshot().phase == .nativeFallback)
        #expect(await runtime.recoverySnapshot().failures[offer.digest] == nil)
        #expect(await runtime.recoverySnapshot().lastRecovery == "unknownInterruption")
        await runtime.close()
    }

    @Test func startupDeadlineAndCancelBeforePublishDoNotExecuteOrClaimHealth() async throws {
        let f = Fixture(); defer { f.clean() }; let offer = try f.offer()
        let artifact = try f.verifier().verifyArtifact(signedManifest: offer.manifest, payload: offer.payload, now: f.now)
        let expired = StartupWork()
        await rejects("activation.deadline") {
            _ = try expired.execute(payload: offer.payload, policy: f.policy(), artifact: artifact, startedAt: 0)
        }
        let cancelled = StartupWork(); cancelled.cancel(.cancelled)
        await rejects("activation.cancelled") {
            _ = try cancelled.execute(payload: offer.payload, policy: f.policy(), artifact: artifact,
                startedAt: DispatchTime.now().uptimeNanoseconds)
        }
        // Repeated retirement does not leak the 16 native session slots.
        for _ in 0..<24 {
            let instance = try VMSession(module: offer.payload, profile: .integerV1)
            #expect(try instance.invoke("run").value == .i32(1)); try instance.close()
        }
    }

    @Test func closeRacingStartupCannotPublishNewGuestOwnership() async throws {
        let f = Fixture(); defer { f.clean() }
        for sequence in 1...20 {
            let runtime = try f.open()
            if sequence == 1 { try await f.stage(f.offer(), on: runtime) }
            let task = Task { try await runtime.start(now: f.now) }
            await runtime.close()
            _ = try? await task.value
            #expect(await runtime.snapshot().phase == .closed)
            await rejects("activation.inactive") { _ = try await runtime.invoke("run") }
        }
    }

    @Test func cancelledStartupCallerCannotActivateOrQuarantineGuest() async throws {
        let f = Fixture(); defer { f.clean() }; let runtime = try f.open(); let offer = try f.offer()
        try await f.stage(offer, on: runtime)
        let task = Task { try await runtime.start(now: f.now) }
        task.cancel()
        let snapshot = try await task.value
        #expect(snapshot.phase == .nativeFallback && snapshot.startupResult == nil)
        #expect(snapshot.failureCodes == ["activation.cancelled"])
        let recovery = await runtime.recoverySnapshot()
        #expect(recovery.failures[offer.digest] == nil && recovery.quarantine[offer.digest] == nil && recovery.healthy == nil)
        await runtime.close()
    }
}
