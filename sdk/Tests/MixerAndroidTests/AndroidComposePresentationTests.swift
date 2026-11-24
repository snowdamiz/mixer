import Foundation
import MixerUI
import Testing
@_spi(ComposeHost) import MixerAndroid

@Suite @MainActor
struct AndroidComposePresentationTests {
    private static let title = "Café / e\u{301} 🏗️"

    @Test func canceledSameRenderKeepsTheDrawnEditorAndSaveHandler() throws {
        var reconciler = UIReconciler()
        try reconciler.apply(UIDocument(revision: 40, root: UINode(id: "prior", kind: .text,
                                                                 properties: ["text": .string("Prior")])))
        let shown = try snapshot(&reconciler, revision: 41)
        let candidate = try snapshot(&reconciler, revision: 42)
        let bridge = makeBridge(returning: Void.self)
        var draft = Self.title
        var saved: [String] = []
        var candidateEffects = 0
        let drawn = try bridge.prepare(owner: bridge.owner, snapshot: shown) { envelope, action in
            #expect(envelope.revision == 41)
            #expect(action.revision == 41)
            if case .string(let title) = action.value, action.actionID == "title.changed" { draft = title }
            if action.actionID == "editor.save" { saved.append(draft) }
        }
        let save = try event(drawn, node: "save", kind: .activate)
        #expect(throws: AndroidComposePresentationError.staleReceipt) {
            try bridge.dispatch(save, from: drawn.receipt)
        }
        #expect(bridge.acknowledgeDraw(drawn.receipt))

        let failed = try bridge.prepare(owner: bridge.owner, snapshot: candidate) { _, _ in candidateEffects += 1 }
        #expect(drawn.receipt.owner == bridge.owner && drawn.receipt.sequence == 1)
        #expect(drawn.receipt.documentRevision == 41 && failed.receipt.documentRevision == 42)
        #expect(failed.receipt.sequence == 2 && failed.receipt.opaqueID != drawn.receipt.opaqueID)
        #expect(drawn.snapshot.isSameRender(as: shown))
        #expect(drawn.snapshot.document.root == failed.snapshot.document.root)
        #expect(drawn.snapshot.identity(for: "title") == failed.snapshot.identity(for: "title"))
        var fresh = UIReconciler()
        try fresh.apply(shown.document)
        #expect(drawn.snapshot.identity(for: "title") != fresh.snapshot?.identity(for: "title"))
        let decoded = try UIDocument.decode(drawn.documentUTF8)
        #expect(decoded == shown.document)
        #expect(drawn.documentUTF8 == (try UIValidator().encode(shown.document)))
        let encodedTitle = try #require(decoded.root.children.first?.properties["value"]?.string)
        #expect(Array(encodedTitle.utf8) == Array(Self.title.utf8))

        let provisionalSave = try event(failed, node: "save", kind: .activate)
        #expect(throws: AndroidComposePresentationError.staleReceipt) {
            try bridge.dispatch(provisionalSave, from: failed.receipt)
        }
        #expect(bridge.cancel(failed.receipt))
        #expect(!bridge.acknowledgeDraw(failed.receipt) && !bridge.cancel(failed.receipt))

        let edited = "更新 / e\u{301} 👷"
        let change = try event(drawn, node: "title", kind: .textChange, value: .string(edited))
        let received = try JSONDecoder().decode(UIEventEnvelope.self, from: JSONEncoder().encode(change))
        try bridge.dispatch(received, from: drawn.receipt)
        try bridge.dispatch(save, from: drawn.receipt)
        #expect(saved.map { Array($0.utf8) } == [Array(edited.utf8)])
        #expect(candidateEffects == 0)
    }

    @Test func acknowledgmentsAndEventsRequireEveryReceiptField() throws {
        var reconciler = UIReconciler()
        let bridge = makeBridge(returning: String.self)
        let frame = try bridge.prepare(owner: bridge.owner, snapshot: snapshot(&reconciler, revision: .max)) { _, action in
            action.actionID
        }
        let receipt = frame.receipt
        let exactEcho = AndroidComposePrepareReceipt(owner: receipt.owner, sequence: receipt.sequence,
                                                    documentRevision: receipt.documentRevision, opaqueID: receipt.opaqueID)
        let wrongReceipts = [
            AndroidComposePrepareReceipt(owner: UUID(), sequence: receipt.sequence,
                                         documentRevision: receipt.documentRevision, opaqueID: receipt.opaqueID),
            AndroidComposePrepareReceipt(owner: receipt.owner, sequence: 2,
                                         documentRevision: receipt.documentRevision, opaqueID: receipt.opaqueID),
            AndroidComposePrepareReceipt(owner: receipt.owner, sequence: receipt.sequence,
                                         documentRevision: .max - 1, opaqueID: receipt.opaqueID),
            AndroidComposePrepareReceipt(owner: receipt.owner, sequence: receipt.sequence,
                                         documentRevision: receipt.documentRevision, opaqueID: UUID()),
        ]
        #expect(try UIDocument.decode(frame.documentUTF8).revision == .max)
        for wrong in wrongReceipts {
            #expect(!bridge.acknowledgeDraw(wrong) && !bridge.cancel(wrong))
        }
        #expect(bridge.acknowledgeDraw(exactEcho))
        #expect(!bridge.acknowledgeDraw(exactEcho) && !bridge.cancel(exactEcho))
        let save = try event(frame, node: "save", kind: .activate)
        for wrong in wrongReceipts {
            let error: AndroidComposePresentationError = wrong.owner == receipt.owner ? .staleReceipt : .staleOwner
            #expect(throws: error) { try bridge.dispatch(save, from: wrong) }
        }
        #expect(try bridge.dispatch(save, from: exactEcho) == "editor.save")
    }

    @Test func routingRejectsStaleDisabledUnboundAndMalformedEvents() throws {
        var reconciler = UIReconciler()
        let bridge = makeBridge(returning: Void.self)
        var effects = 0
        let first = try bridge.prepare(owner: bridge.owner, snapshot: snapshot(&reconciler, revision: 1)) { _, _ in effects += 1 }
        #expect(bridge.acknowledgeDraw(first.receipt))
        let next = try bridge.prepare(owner: bridge.owner, snapshot: snapshot(&reconciler, revision: 2, disabled: true)) { _, _ in
            effects += 1
        }
        let save = try event(first, node: "save", kind: .activate)
        let staleRevision = UIEventEnvelope(revision: 0, identity: save.identity, event: .activate)
        let staleIdentity = UIEventEnvelope(revision: 1, identity: UINodeIdentity(id: "save", generation: .max), event: .activate)
        let unbound = UIEventEnvelope(revision: 1, identity: save.identity, event: .submit)
        let malformed = UIEventEnvelope(revision: 1, identity: save.identity, event: .activate, value: .bool(true))
        let refusals: [(UIEventEnvelope, UIRoutingError)] = [
            (staleRevision, .staleRevision), (staleIdentity, .staleIdentity), (unbound, .unboundEvent), (malformed, .invalidValue),
        ]
        for (event, error) in refusals {
            #expect(throws: error) { try bridge.dispatch(event, from: first.receipt) }
        }
        #expect(bridge.acknowledgeDraw(next.receipt))
        let disabled = try event(next, node: "save", kind: .activate)
        #expect(throws: UIRoutingError.disabledNode) { try bridge.dispatch(disabled, from: next.receipt) }
        #expect(throws: AndroidComposePresentationError.staleReceipt) { try bridge.dispatch(save, from: first.receipt) }
        #expect(effects == 0)
    }

    @Test func admittedSaveSupersedesPendingAndRejectsReentry() throws {
        var reconciler = UIReconciler()
        let first = try snapshot(&reconciler, revision: 1)
        let second = try snapshot(&reconciler, revision: 2)
        let third = try snapshot(&reconciler, revision: 3)
        let bridge = makeBridge(returning: Void.self)
        defer { bridge.retire(owner: bridge.owner) }

        var acceptedReceipt: AndroidComposePrepareReceipt?
        var pendingReceipt: AndroidComposePrepareReceipt?
        var handled = 0
        let drawn = try bridge.prepare(owner: bridge.owner, snapshot: first) { event, _ in
            handled += 1
            let accepted = try #require(acceptedReceipt)
            let pending = try #require(pendingReceipt)
            #expect(throws: AndroidComposePresentationError.reentrant) { try bridge.dispatch(event, from: accepted) }
            #expect(throws: AndroidComposePresentationError.reentrant) { try bridge.dispatch(event, from: pending) }
            #expect(throws: AndroidComposePresentationError.reentrant) {
                try bridge.prepare(owner: bridge.owner, snapshot: third) { _, _ in }
            }
            #expect(!bridge.acknowledgeDraw(pending) && !bridge.cancel(pending))
            #expect(!bridge.retire(owner: bridge.owner))
        }
        acceptedReceipt = drawn.receipt
        #expect(bridge.acknowledgeDraw(drawn.receipt))
        let pending = try bridge.prepare(owner: bridge.owner, snapshot: second) { _, _ in Issue.record("Pending handler ran") }
        pendingReceipt = pending.receipt
        try bridge.dispatch(event(drawn, node: "save", kind: .activate), from: drawn.receipt)
        #expect(handled == 1)
        #expect(!bridge.acknowledgeDraw(pending.receipt))
        let next = try bridge.prepare(owner: bridge.owner, snapshot: third) { _, _ in handled += 1 }
        #expect(bridge.acknowledgeDraw(next.receipt))
        try bridge.dispatch(event(next, node: "save", kind: .activate), from: next.receipt)
        #expect(handled == 2)
    }

    @Test func failedEncodingAndRetirementCannotLendAuthority() throws {
        var reconciler = UIReconciler()
        let first = try snapshot(&reconciler, revision: 1)
        let bridge = makeBridge(returning: String.self)
        let accepted = try bridge.prepare(owner: bridge.owner, snapshot: first) { _, _ in "drawn" }
        #expect(bridge.acknowledgeDraw(accepted.receipt))
        let pending = try bridge.prepare(owner: bridge.owner, snapshot: snapshot(&reconciler, revision: 2)) { _, _ in "pending" }
        var vertical = UIReconciler(validator: UIValidator(supportedTextFieldAxes: [.vertical]))
        let invalid = try snapshot(&vertical, revision: 3, axis: "vertical")
        #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) {
            try bridge.prepare(owner: bridge.owner, snapshot: invalid) { _, _ in "invalid" }
        }
        #expect(!bridge.acknowledgeDraw(pending.receipt))
        #expect(throws: AndroidComposePresentationError.revisionNotIncreasing) {
            try bridge.prepare(owner: bridge.owner, snapshot: first) { _, _ in "replay" }
        }
        let save = try event(accepted, node: "save", kind: .activate)
        #expect(try bridge.dispatch(save, from: accepted.receipt) == "drawn")

        let neverDrawn = try bridge.prepare(owner: bridge.owner, snapshot: snapshot(&reconciler, revision: 4)) { _, _ in "never" }
        #expect(!bridge.retire(owner: UUID()) && bridge.retire(owner: bridge.owner))
        #expect(!bridge.acknowledgeDraw(neverDrawn.receipt) && !bridge.cancel(neverDrawn.receipt))
        #expect(throws: AndroidComposePresentationError.staleOwner) { try bridge.dispatch(save, from: accepted.receipt) }
        #expect(throws: AndroidComposePresentationError.staleOwner) {
            try bridge.prepare(owner: bridge.owner, snapshot: first) { _, _ in "retired" }
        }

        let replacement = makeBridge(returning: String.self)
        let sameRender = try replacement.prepare(owner: replacement.owner, snapshot: first) { _, _ in "replacement" }
        #expect(replacement.acknowledgeDraw(sameRender.receipt))
        #expect(sameRender.receipt.sequence == accepted.receipt.sequence)
        #expect(throws: AndroidComposePresentationError.staleOwner) { try replacement.dispatch(save, from: accepted.receipt) }
        #expect(try replacement.dispatch(save, from: sameRender.receipt) == "replacement")
    }

    @Test func wrongExecutorRefusesPreparation() throws {
        var reconciler = UIReconciler()
        let shown = try snapshot(&reconciler, revision: 1)
        let bridge = AndroidComposePresentation<Void>(isOnExecutor: { false })
        #expect(throws: AndroidComposePresentationError.wrongExecutor) {
            try bridge.prepare(owner: bridge.owner, snapshot: shown) { _, _ in }
        }
        #expect(!bridge.retire(owner: bridge.owner))
    }

    private func makeBridge<Result>(returning: Result.Type) -> AndroidComposePresentation<Result> {
        AndroidComposePresentation(isOnExecutor: { Thread.isMainThread })
    }

    private func snapshot(_ reconciler: inout UIReconciler, revision: UInt64, disabled: Bool = false,
                          axis: String? = nil) throws -> UIRenderSnapshot {
        var fieldProperties: [String: UIValue] = ["label": .string("Title"), "value": .string(Self.title)]
        if let axis { fieldProperties["axis"] = .string(axis) }
        let title = UINode(id: "title", kind: .textField, properties: fieldProperties,
                           actions: [UIActionBinding(id: "title.changed", event: .textChange)])
        let save = UINode(id: "save", kind: .button, properties: ["label": .string("Save")],
                          actions: [UIActionBinding(id: "editor.save", event: .activate)])
        let root = UINode(id: "form", kind: .vStack, properties: ["disabled": .bool(disabled)], children: [title, save])
        try reconciler.apply(UIDocument(revision: revision, root: root))
        return try reconciler.currentSnapshot()
    }

    private func event(_ frame: AndroidComposeFrame, node: String, kind: UIEventKind, value: UIValue = .null) throws -> UIEventEnvelope {
        UIEventEnvelope(revision: frame.snapshot.document.revision, identity: try #require(frame.snapshot.identity(for: node)),
                        event: kind, value: value)
    }
}
