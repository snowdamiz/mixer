import MixerUI

fileprivate final class FeatureMount: Sendable {}

package struct FrameToken: Equatable, Sendable {
    fileprivate let mount: FeatureMount
    package let ordinal: UInt64

    package static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.mount === rhs.mount && lhs.ordinal == rhs.ordinal
    }
}

package struct FramePresentation: Sendable {
    package let token: FrameToken
    package let snapshot: UIRenderSnapshot
}

package struct PreparedFrame: Sendable {
    package let presentation: FramePresentation
    package let changes: UIChangeSet
}

package enum PresentationOutcome: Equatable, Sendable {
    case drawnAndInputReady
    case canceled
    case failed
}

package enum DispatchOutcome: Equatable, Sendable {
    case rejected
    case handled(superseded: FrameToken?)
    case invalidState(FeatureError, superseded: FrameToken?)
}

package enum FeatureError: Error, Equatable, Sendable {
    case wrongExecutor
    case detached
    case reentrant
    case exhaustedFrameOrdinals
    case exhaustedNodeIDs
    case limitExceeded(String)
    case unsupportedView
    case customMirror
    case invalidRoot
    case unsupportedState
    case unsupportedEnvironment
    case unboundControl
    case reusedState
    case stateWriteDuringBuild
    case unsupportedRowKey
    case duplicateRowKey
    case unsupportedAccessibilityTarget
    case duplicateAccessibilityProperty(String)
}

/// The installed host owns one session per mount and runs it in synchronous
/// turns on its declared serial executor.
package final class FeatureSession {
    private struct Frame {
        let presentation: FramePresentation
        let reconciler: UIReconciler
        let identities: NodeIdentities
        let handlers: [String: StateHandler]
        let access: StateAccess
        let environment: EnvironmentValues
    }

    private struct Candidate {
        let frame: Frame
        let cells: StateCells
    }

    private let mount = FeatureMount()
    private let executor: FeatureExecutor
    private let validator: UIValidator
    private var ordinal: UInt64 = 0
    private var accepted: Frame?
    private var pending: Candidate?
    private var busy = false
    private var detached = false

    package init(executor: FeatureExecutor, validator: UIValidator = UIValidator()) {
        self.executor = executor
        self.validator = validator
    }

    package var acceptedPresentation: FramePresentation? {
        guard executor.isCurrent() else { return nil }
        return accepted?.presentation
    }

    /// Supersedes the previous candidate even if building its replacement fails.
    /// Changes are calculated relative to the last accepted presentation.
    package func prepare<Root: View>(
        environment: UIAppearanceEnvironmentV2? = nil, _ root: () -> Root
    ) throws -> PreparedFrame {
        guard executor.isCurrent() else { throw FeatureError.wrongExecutor }
        guard !busy else { throw FeatureError.reentrant }
        guard !detached else { throw FeatureError.detached }
        return try withTurn {
            pending = nil
            guard ordinal < .max else { throw FeatureError.exhaustedFrameOrdinals }
            ordinal += 1
            let token = FrameToken(mount: mount, ordinal: ordinal)
            let access = StateAccess()
            let values = environment.map(EnvironmentValues.init(resolved:)) ?? EnvironmentValues()
            return try StateTurn.run(access, executor: executor, phase: .build, environment: values) { turn in
                let rootView = root()
                try turn.checkWrites()
                let evaluation = ViewEvaluation(
                    limits: validator.limits,
                    cells: accepted?.access.acceptedCells ?? [:],
                    identities: accepted?.identities ?? NodeIdentities(),
                    turn: turn
                )
                let document = try evaluation.document(from: rootView, revision: token.ordinal)
                var reconciler = accepted?.reconciler ?? UIReconciler(validator: validator)
                let changes = try reconciler.apply(document)
                let presentation = FramePresentation(token: token, snapshot: try reconciler.currentSnapshot())
                let frame = Frame(presentation: presentation, reconciler: reconciler,
                                  identities: evaluation.identities, handlers: evaluation.handlers, access: access,
                                  environment: values)
                pending = Candidate(frame: frame, cells: turn.cells)
                return PreparedFrame(presentation: presentation, changes: changes)
            }
        }
    }

    /// Returns true when the receipt consumed the current candidate.
    @discardableResult
    package func finish(_ token: FrameToken, outcome: PresentationOutcome) -> Bool {
        guard executor.isCurrent(), !busy, let pending, pending.frame.presentation.token == token else { return false }
        return withTurn {
            if outcome == .drawnAndInputReady {
                accepted?.access.retire()
                pending.frame.access.publish(pending.cells)
                accepted = pending.frame
            }
            self.pending = nil
            return true
        }
    }

    package func dispatch(_ token: FrameToken, _ event: UIEventEnvelope) -> DispatchOutcome {
        guard executor.isCurrent(), !busy, let accepted, accepted.presentation.token == token,
              let routed = try? accepted.presentation.snapshot.route(event),
              let handler = accepted.handlers[routed.actionID],
              let operation = handler.action.operation(for: routed) else {
            return .rejected
        }
        return withTurn {
            let superseded = pending?.frame.presentation.token
            pending = nil
            let access = accepted.access
            return StateTurn.run(
                access, executor: executor, phase: .event, environment: accepted.environment,
                cells: access.acceptedCells, scope: handler.scope
            ) { turn in
                operation()
                do throws(FeatureError) {
                    try turn.checkWrites()
                    access.publish(turn.cells)
                    return .handled(superseded: superseded)
                } catch {
                    return .invalidState(error, superseded: superseded)
                }
            }
        }
    }

    @discardableResult
    package func detach() -> Bool {
        guard executor.isCurrent(), !busy, !detached else { return false }
        return withTurn {
            detached = true
            pending = nil
            accepted?.access.retire()
            accepted = nil
            return true
        }
    }

    private func withTurn<Result>(_ operation: () throws -> Result) rethrows -> Result {
        busy = true
        defer { busy = false }
        return try operation()
    }
}
