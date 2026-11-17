#if canImport(Crypto)
import Foundation
import MixerUI

@_spi(FeatureUIV3) public enum SwiftFeatureExecutionProfile: UInt32, Sendable { case development256 = 1 }
@_spi(FeatureUIV3) public struct ReviewedDevelopmentGrant: Sendable {
    public let artifactSHA256: String
    public let executionProfile: SwiftFeatureExecutionProfile
    public let surfaceKinds: Set<NodeKind>
    public init(artifactSHA256: String, surfaceKinds: Set<NodeKind>, executionProfile: SwiftFeatureExecutionProfile) {
        self.artifactSHA256 = artifactSHA256; self.surfaceKinds = surfaceKinds; self.executionProfile = executionProfile
    }
    public static let identity = "mixer.swift-wasi-ui-v1"
    public static let schema = "FeatureDocumentV3/MUI3"
    public static let initializer = "_initialize"
}
@_spi(FeatureUIV3) public enum SwiftFeatureError: Error, Equatable {
    case grant, closed, vm(String), input, presentation, invalidLedger, overloaded
}
@_spi(FeatureUIV3) @MainActor public protocol SwiftFeatureNativePresenter: AnyObject {
    func present(_ request: NativePresentationRequest) async throws -> NativeDisplayAcknowledgement
}
@_spi(FeatureUIV3) public struct SwiftFeatureRuntimeRequest: Sendable {
    public let packet: Data
    public let profile: SwiftFeatureExecutionProfile
    internal init(packet: Data, profile: SwiftFeatureExecutionProfile) { self.packet = packet; self.profile = profile }
}
@_spi(FeatureUIV3) @MainActor public protocol SwiftFeatureRuntimeFactory: AnyObject {
    func acquire(_ request: SwiftFeatureRuntimeRequest) -> SwiftFeatureAcquisition
}
@_spi(FeatureUIV3) @MainActor public enum SwiftFeatureAcquisition {
    case refused(any Error)
    case ready(any SwiftFeatureRuntimeOwner)
    case failedOwned(any SwiftFeatureRuntimeOwner, cause: any Error)
}
@_spi(FeatureUIV3) @MainActor public protocol SwiftFeatureCleanupAuthority: AnyObject {}
@_spi(FeatureUIV3) @MainActor public protocol SwiftFeatureRuntimeOwner: SwiftFeatureCleanupAuthority {
    func frame() throws -> Data
    func event(_ bytes: Data) throws
    func consume() -> SwiftFeatureConsumption
}
@_spi(FeatureUIV3) public struct SwiftFeatureLedgerObservation: Sendable {
    public let currents: [UInt64]
    public let tickets: UInt64
    public let invariant: UInt64
    public init(currents: [UInt64], tickets: UInt64, invariant: UInt64) {
        self.currents = currents; self.tickets = tickets; self.invariant = invariant
    }
}
@_spi(FeatureUIV3) @MainActor public enum SwiftFeatureConsumption {
    case reportedClosed(SwiftFeatureLedgerObservation)
    case retained(any SwiftFeatureCleanupAuthority, cause: any Error)
}
@_spi(FeatureUIV3) public struct SwiftFeatureClosedLedger: Sendable {
    public let currents: [UInt64]
    public let tickets: UInt64
    public let invariant: UInt64
    internal init(_ report: SwiftFeatureLedgerObservation) throws {
        guard report.currents.count == 14, report.currents.allSatisfy({ $0 == 0 }), report.tickets == 0, report.invariant == 0 else { throw SwiftFeatureError.invalidLedger }
        currents = report.currents; tickets = report.tickets; invariant = report.invariant
    }
    public func requireFourteenZeroCurrentsAndNoTicketsOrInvariant() throws {
        guard currents.count == 14, currents.allSatisfy({ $0 == 0 }), tickets == 0, invariant == 0 else { throw SwiftFeatureError.invalidLedger }
    }
}
@_spi(FeatureUIV3) @MainActor public final class SwiftFeatureRetainedCleanup {
    public let cause: any Error
    private let owner: any SwiftFeatureRuntimeOwner
    private let dependentAuthority: (any SwiftFeatureCleanupAuthority)?
    internal init(owner: any SwiftFeatureRuntimeOwner, authority: (any SwiftFeatureCleanupAuthority)? = nil, cause: any Error) {
        self.owner = owner; dependentAuthority = authority; self.cause = cause
    }
    // Retains both authorities. No destructor, retry or conversion to a clean report.
}
@_spi(FeatureUIV3) public enum SwiftFeatureCloseOutcome: Sendable {
    case clean(SwiftFeatureClosedLedger), notAcquired, retained(SwiftFeatureRetainedCleanup)
}
@_spi(FeatureUIV3) public struct SwiftFeatureFailure: Error {
    public let cause: any Error
    public let close: SwiftFeatureCloseOutcome
}

@MainActor internal final class SwiftFeatureLease {
    private var owner: (any SwiftFeatureRuntimeOwner)?
    private var close: SwiftFeatureCloseOutcome?
    init(_ owner: any SwiftFeatureRuntimeOwner) { self.owner = owner }
    func frame() throws -> Data { guard let owner else { throw SwiftFeatureError.closed }; return try owner.frame() }
    func event(_ bytes: Data) throws { guard let owner else { throw SwiftFeatureError.closed }; try owner.event(bytes) }
    func consume() -> SwiftFeatureCloseOutcome {
        if let close { return close }
        guard let owner else { return .notAcquired }
        let outcome: SwiftFeatureCloseOutcome
        switch owner.consume() {
        case .reportedClosed(let report):
            do { outcome = .clean(try SwiftFeatureClosedLedger(report)) }
            catch { outcome = .retained(SwiftFeatureRetainedCleanup(owner: owner, cause: error)) }
        case .retained(let authority, let cause):
            outcome = .retained(SwiftFeatureRetainedCleanup(owner: owner, authority: authority, cause: cause))
        }
        close = outcome; self.owner = nil
        return outcome
    }
}
#endif
