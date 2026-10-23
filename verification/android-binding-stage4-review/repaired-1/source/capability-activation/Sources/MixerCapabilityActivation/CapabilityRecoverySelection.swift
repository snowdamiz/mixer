import Foundation
import MixerExperimentalCapabilityRuntime
@_spi(CapabilityDurableV3) import MixerUpdates

/// Same-context enclosing evidence only. Retained provenance is established by
/// this private store's real committed record, never supplied by the coordinator.
enum CapabilitySelectionEvidence: Sendable {
    case fresh(VerifiedArtifactV3)
    case retained(RetainedHealthyEvidenceV3)
}
enum CapabilitySelectionSource: Sendable { case fresh, retained }

/// Opaque reference-backed one-shot handle. Its issuer key is constructible only
/// in the private store file; no public initializer/decoder or payload getter.
final class CapabilityStartupSelection: @unchecked Sendable {
    let source: CapabilitySelectionSource
    let candidateID: String
    let launchID: String
    let generation: UInt64
    let startupBeganUptimeNanoseconds: UInt64
    let startupCutoffUptimeNanoseconds: UInt64
    private let key: CapabilityRecoverySelectionKey
    private var input: CapabilityConsumedStartup?
    private let lock = NSLock()
    private var consumed = false
    init(key: CapabilityRecoverySelectionKey, input: CapabilityConsumedStartup) {
        self.key = key; self.input = input
        source = input.source; candidateID = input.candidateID; launchID = input.launchID
        generation = input.generation; startupBeganUptimeNanoseconds = input.startupBeganUptimeNanoseconds
        startupCutoffUptimeNanoseconds = input.startupCutoffUptimeNanoseconds
    }
    func inspect(for key: CapabilityRecoverySelectionKey) throws -> CapabilityConsumedStartup {
        lock.lock(); defer { lock.unlock() }
        guard self.key === key, !consumed, let input else { throw capabilityRecoveryError("selection_consumed") }
        return input
    }
    func take(for key: CapabilityRecoverySelectionKey) throws -> CapabilityConsumedStartup {
        lock.lock(); defer { lock.unlock() }
        guard self.key === key, !consumed, let input else { throw capabilityRecoveryError("selection_consumed") }
        consumed = true; self.input = nil; return input
    }
    func invalidate(for key: CapabilityRecoverySelectionKey) {
        lock.lock(); defer { lock.unlock() }
        if self.key === key { consumed = true; input = nil }
    }
}

/// Private coordinator construction inputs after the one-shot store consume.
/// This type is not accepted by any public development or OTA entrypoint.
final class CapabilityConsumedStartup: Sendable {
    let module: Data
    let startupExport: String
    let policy: CapabilityExecutionPolicy
    let evidence: CapabilitySelectionEvidence
    let source: CapabilitySelectionSource
    let candidateID: String
    let launchID: String
    let generation: UInt64
    let startupBeganUptimeNanoseconds: UInt64
    let startupCutoffUptimeNanoseconds: UInt64
    private let key: CapabilityRecoverySelectionKey
    init(key: CapabilityRecoverySelectionKey, module: Data, startupExport: String,
         policy: CapabilityExecutionPolicy, evidence: CapabilitySelectionEvidence,
         source: CapabilitySelectionSource, candidateID: String, launchID: String,
         generation: UInt64, began: UInt64, cutoff: UInt64) {
        self.key = key; self.module = module; self.startupExport = startupExport
        self.policy = policy; self.evidence = evidence; self.source = source
        self.candidateID = candidateID; self.launchID = launchID; self.generation = generation
        startupBeganUptimeNanoseconds = began; startupCutoffUptimeNanoseconds = cutoff
    }
    func wasIssued(by key: CapabilityRecoverySelectionKey) -> Bool { self.key === key }
}

/// Only .rejected establishes a safely discarded unconsumed attempt. Other
/// errors do not authorize a coordinator to launch a local native fallback.
enum CapabilitySelectionConsumeError: Error { case rejected, cleanupRequiresReopen }

enum CapabilityRecoveryDisposition: Sendable {
    case selection(CapabilityStartupSelection)
    case nativeFallback
    case recoveryRequired
}
enum CapabilityRecoveryFailure: String, Sendable {
    case deterministicTrap = "deterministic_trap"
    case cancelled, deadline, closed
    case nativePanic = "native_panic"
    case unknownInterruption = "unknown_interruption"

    static func classify(_ snapshot: CapabilityAttemptSignalSnapshot) -> Self {
        switch snapshot.firstCause {
        case .local(.cancelled): return .cancelled
        case .local(.deadline): return .deadline
        case .local(.closed): return .closed
        case .bridge(let failure):
            if case .panicOrQuarantine = failure.kind { return .nativePanic }
            if case .cancelled = failure.kind { return .cancelled }
            if case .deadlineExceeded = failure.kind { return .deadline }
            guard [.startup, .invocation, .wake].contains(failure.operation), failure.nativeStatus == 2 else { return .unknownInterruption }
            let expected: String?
            switch failure.kind {
            case .guestTrap(.unreachable): expected = "unreachable"
            case .guestTrap(.integerDivideByZero): expected = "integer_divide_by_zero"
            case .guestTrap(.integerOverflow): expected = "integer_overflow"
            case .guestTrap(.invalidConversionToInteger): expected = "invalid_conversion_to_integer"
            case .guestTrap(.memoryOutOfBounds): expected = "memory_out_of_bounds"
            case .guestTrap(.tableOutOfBounds): expected = "table_out_of_bounds"
            case .guestTrap(.indirectCallNull): expected = "indirect_call_null"
            case .guestTrap(.indirectCallTypeMismatch): expected = "indirect_call_type_mismatch"
            case .guestTrap(.hostAbort): expected = "host_abort"
            case .resource(.fuel): expected = "fuel_exhausted"
            case .resource(.hostCalls): expected = "host_call_limit"
            case .resource(.callDepth): expected = "call_depth_exceeded"
            case .resource(.operandStack): expected = "operand_stack_exceeded"
            default: expected = nil
            }
            return expected == failure.code ? .deterministicTrap : .unknownInterruption
        case nil: return .unknownInterruption
        }
    }
}
