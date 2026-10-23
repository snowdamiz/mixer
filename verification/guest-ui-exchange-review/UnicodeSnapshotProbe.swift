import Foundation
import MixerUI
@_spi(GuestUIV1) import MixerGuest

@main struct UnicodeSnapshotProbe {
    static func main() throws {
        let originalID = "caf\u{00e9}"
        let changedID = "cafe\u{0301}"
        let originalAction = "save.\u{00e9}"
        let changedAction = "save.e\u{0301}"
        func document(_ id: String, _ action: String) -> UIDocument {
            UIDocument(revision: 1, root: UINode(id: id, kind: .button,
                properties: ["label": .string("Save")],
                actions: [UIActionBinding(id: action, event: .activate)]))
        }
        let exchange = try GuestUIExchangeV1(generation: 1)
        let startup = try exchange.claimStartup()
        try exchange.finishTurn(startup, documentBytes: GuestUICodec().encode(document(originalID, originalAction)))
        try exchange.enterEffectsIntent(generation: 1)
        try exchange.confirmEffectsEnabled(generation: 1)
        let claim = exchange.claimPresentation(generation: 1)!
        var reconciler = UIReconciler()
        try reconciler.apply(document(changedID, changedAction))
        let snapshot = try reconciler.currentSnapshot()
        let accepted = exchange.completePresentation(claim, snapshot: snapshot) != nil
        let envelope = UIEventEnvelope(revision: 1, identity: snapshot.identity(for: changedID)!, event: .activate)
        let admission = exchange.offer(envelope, generation: 1)
        var emitted: [String: [UInt8]] = [:]
        if let turn = try? exchange.claimNextTurn(ready: false), case .event(_, let bytes) = turn.kind {
            let event = try GuestUIEventCodecV1.decode(bytes)
            emitted = ["node": Array(event.nodeID.utf8), "action": Array(event.actionID.utf8)]
        }
        let result: [String: Any] = [
            "original_node_utf8": Array(originalID.utf8),
            "changed_node_utf8": Array(changedID.utf8),
            "original_action_utf8": Array(originalAction.utf8),
            "changed_action_utf8": Array(changedAction.utf8),
            "swift_string_equality": originalID == changedID,
            "snapshot_accepted": accepted,
            "admission": String(describing: admission),
            "emitted_utf8": emitted,
            "stop": String(describing: exchange.snapshot().stop)
        ]
        print(String(decoding: try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]), as: UTF8.self))
    }
}
