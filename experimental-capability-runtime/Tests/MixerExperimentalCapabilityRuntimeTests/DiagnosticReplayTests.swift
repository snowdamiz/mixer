import Foundation
import Testing
import MixerCapabilities
@_spi(GuestUIV1) import MixerGuest
@_spi(GuestUIV1) @_spi(CapabilityLifecycle) import MixerExperimentalCapabilityRuntime

private final class DiagnosticObserver: CapabilityBridgeTerminalObserver, CapabilityBridgeRetirementObserver, @unchecked Sendable {
    private let lock = NSLock()
    private var failures: [ExperimentalCapabilityFailure] = []
    private var retirements = 0
    func recordTerminalFailure(_ failure: ExperimentalCapabilityFailure) { lock.withLock { failures.append(failure) } }
    func recordRetired() { lock.withLock { retirements += 1 } }
    var details: [ExperimentalCapabilityFailure] { lock.withLock { failures } }
    var retired: Bool { lock.withLock { retirements == 1 } }
}

extension ExperimentalBridgeTests {
    @Test(.enabled(if: ProcessInfo.processInfo.environment["L03_GUEST_FIXTURES"] != nil))
    func originalSwiftFaultsThroughInstalledGuestUI() async throws {
        let directory = try #require(ProcessInfo.processInfo.environment["L03_GUEST_FIXTURES"])
        let variants: [(name: String, mapped: Bool, fuel: UInt64)] = [
            ("baseline-compact", false, 1_000_000),
            ("fault-osize", true, 1_000_000),
            ("fault-opt", true, 1_000_000),
            ("fault", false, 1_000_000),
            ("fault-malformed", false, 1_000_000),
            ("fault-unsupported", false, 1_000_000),
            ("fault-duplicate", false, 1_000_000),
            ("fault-oversized", false, 1_000_000),
            ("fault-external", false, 1_000_000),
            ("fault-osize", false, 1),
        ]
        var compactTrap: ExperimentalCapabilityNativeLocation?
        for variant in variants {
            let bytes = try Data(contentsOf: URL(fileURLWithPath: directory).appendingPathComponent(variant.name + ".wasm"))
            let config = ExperimentalCapabilityConfiguration(fuel: variant.fuel)
            try await ExperimentalCapabilityValidator.prepareGuestUIV1(module: bytes, configuration: config).validate()
            let exchange = try GuestUIExchangeV1(generation: 1)
            let observer = DiagnosticObserver()
            let construction = try ExperimentalCapabilitySession.prepareOwnedGuestUIV1(
                module: bytes, configuration: config, policy: CapabilityPolicy(installed: [], manifest: []),
                adapterGroup: OwnedCapabilityAdapterGroup(terminal: observer, retirement: observer), exchange: exchange)
            let session = try await construction.create()
            var detail: ExperimentalCapabilityFailure?
            do {
                try await session.startupGuestUIV1()
                #expect(variant.name.hasPrefix("baseline"))
                session.close()
                print("L03 \(variant.name): startup succeeded")
            } catch let error as ExperimentalCapabilityError {
                detail = error.failure
                #expect(error.nativeStatus == 2)
                #expect(error.failure.operation == .startup)
                #expect(error.failure.kind == (variant.fuel == 1 ? .resource(.fuel) : .guestTrap(.unreachable)))
                let location = try #require(error.failure.location)
                let function = try #require(location.functionIndex)
                #expect(location.byteOffset > 0 && location.byteOffset < bytes.count)
                #expect(!variant.name.hasPrefix("baseline"))
                #expect(error.code == (variant.fuel == 1 ? "fuel_exhausted" : "unreachable"))
                if variant.name == "fault-osize", variant.fuel != 1 {
                    compactTrap = location
                }
                if variant.name != "fault-opt", variant.fuel != 1 {
                    let expected = try #require(compactTrap)
                    #expect(function == expected.functionIndex)
                    #expect(location.byteOffset == expected.byteOffset)
                }
                if variant.mapped {
                    let source = try #require(location.source)
                    #expect(source.file == "DiagnosticGuest.swift" && source.line == 16 && source.column == 5)
                    #expect(error.description == "DiagnosticGuest.swift:16:5: unreachable")
                } else {
                    #expect(location.source == nil)
                    #expect(error.description == error.code)
                }
                print("L03 \(variant.name) fuel=\(variant.fuel) status=\(error.nativeStatus!) function=\(function) offset=\(location.byteOffset) \(error.description)")
            }
            try await bridgeEventually { session.status.drained && observer.retired }
            #expect(session.status.closed)
            #expect(session.status.retainedExits == 0)
            #expect(session.status.failure == (detail == nil ? nil : variant.fuel == 1 ? "fuel_exhausted" : "unreachable"))
            #expect(session.status.failureDetail == detail)
            #expect(observer.details == (detail.map { [$0] } ?? []))
            print("L03 \(variant.name) retired and drained")
        }
    }
}
