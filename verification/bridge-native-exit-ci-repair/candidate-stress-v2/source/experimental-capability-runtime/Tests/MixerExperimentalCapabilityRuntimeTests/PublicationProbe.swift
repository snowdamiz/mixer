import Foundation
import Testing
@testable import MixerCapabilities
@_spi(GuestUIV1) import MixerGuest
@_spi(GuestUIV1) @_spi(CapabilityLifecycle) @testable import MixerExperimentalCapabilityRuntime

private final class PublicationWeakSession {
    weak var value: ExperimentalCapabilitySession?
    init(_ value: ExperimentalCapabilitySession?) { self.value = value }
}
private actor PublicationInvocationGate {
    private var waiting: CheckedContinuation<Void, Never>?
    private(set) var entered = false
    func hold() async { await withCheckedContinuation { entered = true; waiting = $0 } }
    func release() { waiting?.resume(); waiting = nil }
}

// Copied only into immutable diagnostic exports, never the product test target.
// Exercise actual C sessions, cross-queue construction, native dispatch source,
// timer callbacks, host completion, native acknowledgement and permit recycling.
extension ExperimentalBridgeTests {
    @Test func publicationProbeRunsActualSourceTimerAndNativeDrain() async throws {
        let policy = try bridgePolicy()
        for iteration in 0..<64 {
            let gate = PublicationInvocationGate()
            let session = try await ExperimentalCapabilitySession.prepare(module: GuestProgram.build(.unconsumed),
                startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters(
                    hooks: InstalledCapabilityExecutionHooks(beforeInvocation: { await gate.hold() }))).create()
            defer { session.close(); Task { await gate.release() } }
            _ = try await session.startup()
            try await session.enableEffects()
            _ = try await session.invoke("run")
            try await bridgeEventually {
                await gate.entered && session.status.timerTicks > 0 && session.status.retainedExits == 1 && session.status.acceptedCalls == 1
            }
            await gate.release()
            session.close()
            try await bridgeEventually { session.status.drained }
            #expect(session.status.acknowledgements == 1 && session.status.failure == nil)
            if iteration % 16 == 15 { print("PUBLICATION_PROBE drained=\(iteration + 1)") }
        }
        let empty = try CapabilityPolicy(installed: [], manifest: [])
        let permits = try (0..<16).map { _ in
            try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: empty,
                                                       adapters: InstalledCapabilityAdapters())
        }
        #expect(throws: ExperimentalCapabilityError("construction_busy")) {
            try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: empty,
                                                       adapters: InstalledCapabilityAdapters())
        }
        for permit in permits { permit.cancel() }
    }

    @Test func publicationProbeGuestUIStartupAndDeinitRetireWithoutHandoffRetention() async throws {
        let policy = try CapabilityPolicy(installed: [], manifest: [])
        for iteration in 0..<32 {
            let recorder = LifecycleRecorder()
            let group = OwnedCapabilityAdapterGroup(terminal: recorder, retirement: recorder)
            let exchange = try GuestUIExchangeV1(generation: 1)
            var session: ExperimentalCapabilitySession? = try await ExperimentalCapabilitySession.prepareOwnedGuestUIV1(
                module: GuestUIProgram.build(), configuration: .init(), policy: policy, adapterGroup: group, exchange: exchange).create()
            let weak = PublicationWeakSession(session)
            try await session!.startupGuestUIV1()
            #expect(exchange.snapshot().latestRevision == 1)
            try await bridgeEventually { session!.status.timerTicks > 0 }
            session = nil
            #expect(weak.value == nil)
            try await bridgeEventually { recorder.retired == 1 }
            #expect(recorder.failures.isEmpty && group.core.constructorTailObserved && group.core.cleanupJobCount == 1)
            if iteration % 8 == 7 { print("PUBLICATION_UI_PROBE retired=\(iteration + 1)") }
        }
    }
}
