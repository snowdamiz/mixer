// Compiled only into the isolated verification copy of MixerCapabilityActivation.
@_spi(GuestUIV1) import MixerGuest
import MixerUpdates

public struct FieldLogTaskFrame {
    public let revision: UInt64
    public let title: String
    public let status: String
    public let deliveredSequence: UInt64?
}

extension GuestUIPresentation {
    public var fieldLogTaskFrame: FieldLogTaskFrame? {
        guard case let .displaying(revision) = state,
              let children = renderHost?.snapshot.document.root.children,
              let title = children.first(where: { $0.id == "task" })?.properties["text"]?.string,
              let status = children.first(where: { $0.id == "status" })?.properties["text"]?.string else { return nil }
        let delivered = lastEventResult.flatMap { $0.outcome == .delivered ? $0.sequence : nil }
        return FieldLogTaskFrame(revision: revision, title: title, status: status, deliveredSequence: delivered)
    }
}

extension CapabilityGuestUIRuntime {
    public func closeFieldLogSignedTask() async throws {
        await close()
        let deadline = ContinuousClock.now + .seconds(8)
        while true {
            let snapshot = await recoverySnapshot()
            guard snapshot.closed, !snapshot.incompleteAttempt else {
                throw UpdateError("fixture.close",
                    "Recovery store did not close cleanly (closed=\(snapshot.closed), incompleteAttempt=\(snapshot.incompleteAttempt))")
            }
            if !snapshot.activation.cleanupPending { return }
            guard ContinuousClock.now < deadline else {
                throw UpdateError("fixture.close", "Native activation retirement still pending after 8 seconds")
            }
            try await Task.sleep(for: .milliseconds(20))
        }
    }
}
