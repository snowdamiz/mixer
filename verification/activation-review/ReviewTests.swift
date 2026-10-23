import Foundation
import Dispatch
import Testing
import Crypto
import MixerRuntime
import MixerUpdates
@testable import MixerActivation

private func u32(_ value: Int) -> [UInt8] {
    var value = value, result: [UInt8] = []
    repeat { let next = UInt8(value & 127); value >>= 7; result.append(next | (value == 0 ? 0 : 128)) } while value != 0
    return result
}
private func text(_ value: String) -> [UInt8] { u32(value.utf8.count) + Array(value.utf8) }
private func section(_ id: UInt8, _ bytes: [UInt8]) -> [UInt8] { [id] + u32(bytes.count) + bytes }
private func guest(pages: Int = 1, unknownDeadFunction: Bool = false, unknownImport: Bool = false, float: Bool = false, trapStartup: Bool = false) -> Data {
    var bytes: [UInt8] = [0,97,115,109,1,0,0,0]
    bytes += section(1, [1,0x60,0,1,float ? 0x7d : 0x7f])
    if unknownImport { bytes += section(2, [1] + text("unapproved") + text("host") + [0,0]) }
    let bodies: [[UInt8]] = float ? [[0,0x43,0,0,0x80,0x3f,0x0b]] : [
        trapStartup ? [0,0,0x0b] : [0,0x23,0,0x41,1,0x6a,0x24,0,0x23,0,0x0b],
        [0,0x41,1,0x40,0,0x0b],
        [0,0,0x0b],
    ] + (unknownDeadFunction ? [[0,0xff,0x0b]] : [])
    bytes += section(3, u32(bodies.count) + Array(repeating: 0, count: bodies.count))
    bytes += section(5, [1,0] + u32(pages))
    bytes += section(6, [1,0x7f,1,0x41,0,0x0b])
    let base = unknownImport ? 1 : 0
    var exports = [UInt8(1 + (float ? 0 : 2))] + text("run") + [0] + u32(base)
    if !float { exports += text("grow") + [0] + u32(base + 1) + text("trap") + [0] + u32(base + 2) }
    bytes += section(7, exports)
    bytes += section(10, u32(bodies.count) + bodies.flatMap { u32($0.count) + $0 })
    return Data(bytes)
}
private final class Gate: @unchecked Sendable {
    private let lock = NSLock()
    private var armed = false
    private var skip = 0
    let entered = DispatchSemaphore(value: 0), release = DispatchSemaphore(value: 0)
    func arm(skipping: Int = 0) { lock.lock(); armed = true; skip = skipping; lock.unlock() }
    func hit(_ point: DurabilityFaultPoint) {
        guard point == .beforeStateWrite else { return }
        lock.lock()
        let block: Bool
        if armed && skip > 0 { skip -= 1; block = false }
        else { block = armed; armed = false }
        lock.unlock()
        if block { entered.signal(); _ = release.wait(timeout: .now() + 10) }
    }
    private func waitSynchronously() -> Bool { entered.wait(timeout: .now() + 5) == .success }
    func wait() async -> Bool { await Task.detached { self.waitSynchronously() }.value }
}
private final class ReviewClock: @unchecked Sendable {
    private let lock = NSLock()
    private var value: UInt64 = 0
    func now() -> UInt64 { lock.lock(); defer { lock.unlock() }; return value }
    func advance() { lock.lock(); value += 11_000_000_000; lock.unlock() }
}
private struct Offer { let manifest: Data, assignment: Data, payload: Data; let digest: String }
private struct Fixture {
    let key = Curve25519.Signing.PrivateKey()
    let clock = ReviewClock()
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-independent-activation-\(UUID().uuidString)")
    let now: UInt64 = 1_792_627_300
    let fingerprint = ReleaseVerifier.sha256(Data("independent-activation-installed-build".utf8))
    var scope: UpdateScope { UpdateScope(organization: "review", project: "engine", app: "app", environment: "test", platform: "ios") }
    func verifier(version: UInt64 = 1) throws -> ReleaseVerifier {
        try ReleaseVerifier(host: InstalledRuntime(scope: scope, runtime: fingerprint, protocolVersion: version,
            capabilityHashes: [:], stateVersion: 1, maxPayloadBytes: 4_194_304,
            limits: ResourceLimits(memoryBytes: 4_194_304, fuel: 1_000_000, startupMilliseconds: 60_000)),
            roots: [TrustRoot(keyID: "review", publicKey: key.publicKey.rawRepresentation, scope: scope, artifact: true, assignment: true)])
    }
    func policy(profile: VMProfile = .integerV1) throws -> InstalledExecution {
        try InstalledExecution(runtimeFingerprint: fingerprint, profile: profile, startupExport: "run", maximumStartupMilliseconds: 5_000)
    }
    func open(profile: VMProfile = .integerV1, version: UInt64 = 1, gate: Gate? = nil) throws -> ColdStartRuntime {
        try ColdStartRuntime.open(configuration: ColdStartConfiguration(directory: directory, channel: "beta", installation: "review",
            reserveDiskBytes: 0, monotonicNanoseconds: { clock.now() }, fault: { point in gate?.hit(point) }), verifier: verifier(version: version), execution: policy(profile: profile))
    }
    func offer(_ payload: Data = guest(), memory: UInt64 = 65_536, version: UInt64 = 1, startup: UInt64 = 5_000, sequence: UInt64 = 1, release: String = "candidate") throws -> Offer {
        var manifest: [String: CanonicalValue] = [
            "schema": .uint(version), "scope": .object(["organization": .text("review"), "project": .text("engine"),
                "app": .text("app"), "environment": .text("test"), "platform": .text("ios")]),
            "release_id": .text(release), "source_commit": .text(String(repeating: "b", count: 40)),
            "provenance_id": .text("independent"), "runtime": .text(fingerprint), "protocol": .uint(version),
            "guest_abi": .uint(1), "ui_schema": .uint(1), "capability_hashes": .object([:]),
            "state_min": .uint(1), "state_max": .uint(1), "payload_sha256": .text(ReleaseVerifier.sha256(payload)),
            "compressed_bytes": .uint(UInt64(payload.count)), "expanded_bytes": .uint(UInt64(payload.count)),
            "compression": .text("none"), "asset_hashes": .object([:]), "source_map_sha256": .text(ReleaseVerifier.sha256(Data())),
            "limits": .object(["memory_bytes": .uint(memory), "fuel": .uint(1_000_000), "startup_milliseconds": .uint(startup)]),
            "key_id": .text("review"), "created_at_unix": .uint(now),
        ]
        if version == 2 { manifest["capability_grants"] = .object(["schema": .uint(1),
            "schema_sha256": .text(VerifiedCapabilityGrants.descriptorSHA256), "entries": .array([])]) }
        let value = CanonicalValue.object(manifest), digest = ReleaseVerifier.sha256(try value.canonicalCBOR())
        let assignment = CanonicalValue.object(["schema": .uint(version), "scope": manifest["scope"]!,
            "channel": .text("beta"), "cohort": .text("sha256-v1"), "rollout_basis_points": .uint(10_000),
            "sequence": .uint(sequence), "release_id": .text(release), "artifact_sha256": .text(digest),
            "runtime": .text(fingerprint), "key_id": .text("review"), "created_at_unix": .uint(now)])
        func signed(_ value: CanonicalValue, field: String, domain: String) throws -> Data {
            let signature = try key.signature(for: Data(domain.utf8) + value.canonicalCBOR())
            return try JSONEncoder().encode(CanonicalValue.object([field: value, "signature": .text(signature.base64EncodedString())]))
        }
        return try Offer(manifest: signed(value, field: "manifest", domain: "mixer.artifact.v\(version)\0"),
            assignment: signed(assignment, field: "assignment", domain: "mixer.assignment.v\(version)\0"), payload: payload, digest: digest)
    }
    func stage(_ offer: Offer, on runtime: ColdStartRuntime) async throws {
        try await runtime.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment, now: now)
        try await runtime.appendDownload(offer.payload, atOffset: 0, now: now)
        try await runtime.finishDownload(now: now)
    }
    func clean() { try? FileManager.default.removeItem(at: directory) }
}
private func code(_ operation: () async throws -> Void) async -> String {
    do { try await operation(); return "accepted" }
    catch let e as UpdateError { return e.code }
    catch let e as VMFailure { return e.code }
    catch is CancellationError { return "CancellationError" }
    catch { return String(describing: type(of: error)) }
}

@Suite(.serialized) struct IndependentActivationReview {
    @Test func signedNonPageMemoryLimitDoesNotRoundUpGrowth() async throws {
        let f = Fixture(); defer { f.clean() }; let runtime = try f.open()
        try await f.stage(f.offer(memory: 131_071), on: runtime)
        #expect(try await runtime.start(now: f.now).phase == .guest)
        #expect(try await runtime.invoke("grow").value == .i32(-1))
        #expect(try await runtime.invoke("run").value == .i32(2))
        await runtime.close()
    }
    @Test func signedTwoPageLimitPermitsExactlyOneGrowth() async throws {
        let f = Fixture(); defer { f.clean() }; let runtime = try f.open()
        try await f.stage(f.offer(memory: 131_072), on: runtime)
        #expect(try await runtime.start(now: f.now).phase == .guest)
        #expect(try await runtime.invoke("grow").value == .i32(1))
        #expect(try await runtime.invoke("grow").value == .i32(-1))
        await runtime.close()
    }
    @Test func initialMemoryCannotExceedSignedRemainder() async throws {
        let f = Fixture(); defer { f.clean() }; let runtime = try f.open()
        let offer = try f.offer(guest(pages: 2), memory: 131_071)
        #expect(await code { try await f.stage(offer, on: runtime) } != "accepted")
        #expect(await runtime.recoverySnapshot().staged == nil)
        await runtime.close()
    }
    @Test func uncalledUnknownOpcodeAndUnapprovedImportFailBeforeStaging() async throws {
        for payload in [guest(unknownDeadFunction: true), guest(unknownImport: true)] {
            let f = Fixture(); defer { f.clean() }; let runtime = try f.open()
            #expect(await code { try await f.stage(f.offer(payload), on: runtime) } == "unsupported")
            #expect(await runtime.recoverySnapshot().staged == nil)
            #expect(try await runtime.start(now: f.now).phase == .nativeFallback)
            await runtime.close()
        }
    }
    @Test func installedNumericProfileIsExplicit() async throws {
        let rejected = Fixture(); defer { rejected.clean() }; let integer = try rejected.open()
        #expect(await code { try await rejected.stage(rejected.offer(guest(float: true)), on: integer) } == "unsupported")
        await integer.close()
        let accepted = Fixture(); defer { accepted.clean() }; let numeric = try accepted.open(profile: .numericV2)
        try await accepted.stage(accepted.offer(guest(float: true)), on: numeric)
        #expect(try await numeric.start(now: accepted.now).startupResult?.value == .f32Bits(0x3f800000))
        await numeric.close()
    }
    @Test func v2EmptyGrantsKeepSameSignedGrowthLimit() async throws {
        let f = Fixture(); defer { f.clean() }; let runtime = try f.open(version: 2)
        try await f.stage(f.offer(memory: 65_536, version: 2), on: runtime)
        #expect(try await runtime.start(now: f.now).phase == .guest)
        #expect(try await runtime.invoke("grow").value == .i32(-1))
        await runtime.close()
    }
    @Test func cachedPayloadMutationCannotAuthorizeNextColdStart() async throws {
        let f = Fixture(); defer { f.clean() }; var runtime = try f.open(); let offer = try f.offer()
        try await f.stage(offer, on: runtime)
        #expect(try await runtime.start(now: f.now).startupResult?.value == .i32(1))
        let path = f.directory.appendingPathComponent(offer.digest + ".payload")
        try Data(repeating: 0, count: offer.payload.count).write(to: path)
        #expect(try await runtime.invoke("run").value == .i32(2)) // active immutable instance is independent
        await runtime.close(); runtime = try f.open()
        #expect(try await runtime.start(now: f.now).phase == .nativeFallback)
        #expect(await runtime.recoverySnapshot().lastRecovery == "unknownInterruption")
        await runtime.close(); runtime = try f.open()
        #expect(try await runtime.start(now: f.now).phase == .nativeFallback)
        #expect(await runtime.recoverySnapshot().quarantine[offer.digest] == "missing_or_corrupt_payload")
        await runtime.close()
    }
    @Test func stagingOperationPreventsReentrantStartWhileUpdaterIsSuspended() async throws {
        let f = Fixture(); defer { f.clean() }; let gate = Gate(), runtime = try f.open(gate: gate); let offer = try f.offer()
        gate.arm()
        let begin = Task { try await runtime.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment, now: f.now) }
        #expect(await gate.wait()); defer { gate.release.signal() }
        #expect(await code { _ = try await runtime.start(now: f.now) } == "activation.state")
        gate.release.signal(); try await begin.value
        #expect(try await runtime.downloadOffset() == 0)
        await runtime.close()
    }
    @Test func cancelledSelectionCannotPublishSessionOrTrapEvidence() async throws {
        let f = Fixture(); defer { f.clean() }; let gate = Gate(), runtime = try f.open(gate: gate)
        let offer = try f.offer(); try await f.stage(offer, on: runtime); gate.arm()
        let start = Task { try await runtime.start(now: f.now) }
        #expect(await gate.wait()); defer { gate.release.signal() }
        start.cancel(); gate.release.signal()
        let result = try await start.value
        #expect(result.phase == .nativeFallback)
        #expect(await runtime.recoverySnapshot().failures[offer.digest] == nil)
        #expect(await runtime.recoverySnapshot().lastRecovery == "unknownInterruption")
        await runtime.close()
        for _ in 0..<20 { let s = try VMSession(module: guest(), profile: .integerV1); try s.close() }
    }
    @Test func closeDuringSelectionKeepsClosedAfterAwaitAndReopenIsUnknownInterruption() async throws {
        let f = Fixture(); defer { f.clean() }; let gate = Gate(), runtime = try f.open(gate: gate)
        let offer = try f.offer(); try await f.stage(offer, on: runtime); gate.arm()
        let start = Task { try await runtime.start(now: f.now) }
        #expect(await gate.wait()); defer { gate.release.signal() }
        let close = Task { await runtime.close() }
        while await runtime.snapshot().phase != .closed { await Task.yield() }
        gate.release.signal(); await close.value; _ = try? await start.value
        #expect(await runtime.snapshot().phase == .closed)
        let reopened = try f.open(); #expect(try await reopened.start(now: f.now).phase == .nativeFallback)
        #expect(await reopened.recoverySnapshot().lastRecovery == "unknownInterruption")
        #expect(await reopened.recoverySnapshot().failures[offer.digest] == nil)
        await reopened.close()
    }
    @Test func durableSelectionElapsedTimeConsumesSignedStartupBudget() async throws {
        let f = Fixture(); defer { f.clean() }; let gate = Gate(), runtime = try f.open(gate: gate)
        let offer = try f.offer(startup: 1); try await f.stage(offer, on: runtime); gate.arm()
        let start = Task { try await runtime.start(now: f.now) }
        #expect(await gate.wait()); defer { gate.release.signal() }
        // Deterministically hold native selection beyond the signed one-ms budget.
        // This is a deadline semantics check, not a device timing claim.
        try await Task.sleep(for: .milliseconds(10)); gate.release.signal()
        let result = try await start.value
        #expect(result.phase == .nativeFallback && result.failureCodes == ["activation.deadline"])
        #expect(await runtime.recoverySnapshot().failures[offer.digest] == nil)
        #expect(await runtime.recoverySnapshot().lastRecovery == "unknownInterruption")
        await runtime.close()
    }
    @Test func fallbackSelectionElapsedTimeConsumesItsOwnSignedStartupBudget() async throws {
        let f = Fixture(); defer { f.clean() }; var runtime = try f.open()
        let healthy = try f.offer(startup: 1_000)
        try await f.stage(healthy, on: runtime)
        #expect(try await runtime.start(now: f.now).phase == .guest)
        f.clock.advance()
        try await runtime.markHealthy(now: f.now, completedMilestones: ["feature_started", "first_screen"])
        await runtime.close()
        let gate = Gate(); runtime = try f.open(gate: gate)
        let candidate = try f.offer(guest(trapStartup: true), sequence: 2, release: "trap")
        try await f.stage(candidate, on: runtime)
        gate.arm(skipping: 1) // initial selection commit, then trap-recovery/fallback selection commit
        let start = Task { try await runtime.start(now: f.now) }
        #expect(await gate.wait()); defer { gate.release.signal() }
        try await Task.sleep(for: .milliseconds(1_100)); gate.release.signal()
        let result = try await start.value
        #expect(result.phase == .nativeFallback)
        #expect(result.failureCodes == ["unreachable", "activation.deadline"])
        let recovery = await runtime.recoverySnapshot()
        #expect(recovery.failures[candidate.digest] == 1)
        #expect(recovery.failures[healthy.digest] == nil && recovery.healthy == healthy.digest)
        await runtime.close()
    }
    @Test func capacityFailureDoesNotBecomeDeterministicTrapAndCanRetry() async throws {
        let f = Fixture(); defer { f.clean() }; var runtime = try f.open(); let offer = try f.offer()
        try await f.stage(offer, on: runtime)
        var holders: [VMSession] = []; defer { for s in holders { try? s.close() } }
        for _ in 0..<16 { holders.append(try VMSession(module: guest(), profile: .integerV1)) }
        let result = try await runtime.start(now: f.now)
        #expect(result.phase == .nativeFallback && result.failureCodes == ["session_limit"])
        #expect(await runtime.recoverySnapshot().failures[offer.digest] == nil)
        #expect(await runtime.recoverySnapshot().lastRecovery == "unknownInterruption")
        for s in holders { try s.close() }; holders.removeAll(); await runtime.close()
        runtime = try f.open(); #expect(try await runtime.start(now: f.now).phase == .guest)
        await runtime.close()
    }
    @Test func lateCancellationCannotCloseCompletedStartupLease() async throws {
        let f = Fixture(); defer { f.clean() }; let offer = try f.offer()
        let artifact = try f.verifier().verifyArtifact(signedManifest: offer.manifest, payload: offer.payload, now: f.now)
        let work = StartupWork()
        let (session, result) = try work.execute(payload: offer.payload, policy: f.policy(), artifact: artifact,
            startedAt: DispatchTime.now().uptimeNanoseconds)
        defer { try? session.close() }; #expect(result.value == .i32(1))
        work.cancel(.cancelled); work.cancel(.deadline)
        #expect(try session.invoke("run").value == .i32(2))
    }
    @Test func runtimeTrapRetiresLeaseAndCountsOnlyProvisionalGuestEvidence() async throws {
        let f = Fixture(); defer { f.clean() }; let runtime = try f.open(); let offer = try f.offer()
        try await f.stage(offer, on: runtime); _ = try await runtime.start(now: f.now)
        #expect(await code { _ = try await runtime.invoke("trap") } == "unreachable")
        #expect(await runtime.snapshot().phase == .nativeFallback)
        #expect(await runtime.recoverySnapshot().failures[offer.digest] == 1)
        #expect(await code { _ = try await runtime.invoke("run") } == "activation.inactive")
        await runtime.close()
    }
}
