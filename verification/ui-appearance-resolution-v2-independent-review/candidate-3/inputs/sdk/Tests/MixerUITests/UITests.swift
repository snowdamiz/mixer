import Foundation
import Testing
import MixerUI
import MixerGuest

private func frame(_ root: UINode, _ revision: UInt64 = 1) -> UIDocument { UIDocument(revision: revision, root: root) }

@Test func authoringBuildsFieldLogEditorAndGuestCodecOnlyRoundTripsValues() throws {
    let tasks = [("task.1", "Inspect roof"), ("task.2", "Check access")]
    let showQueue = true
    let view = Navigation("root", title: "FieldLog") {
        List("project.list") {
            Section("project.tasks", title: "Tasks") {
                for (id, title) in tasks { Text(id, title) }
            }
            TextField("entry.notes", "Notes", value: "Café 🏗️", action: "entry.notes.changed", onSubmit: "entry.save")
                .accessibilityLabel("Inspection notes")
            Toggle("task.complete", "Complete", value: false, action: "task.complete.changed")
            if showQueue { Button("queue.retry", "Retry uploads", action: "queue.retry") }
        }
    }
    let document = view.document(revision: 17)
    let codec = GuestUICodec()
    let encoded = try codec.encode(document)
    let decoded = try codec.decode(encoded)
    #expect(decoded.document == document)
    #expect(decoded.nodeCount == 8)
    #expect(try codec.encode(decoded.document) == encoded)
}

@Test func validationRejectsDuplicateUnsupportedAndMalformedControls() throws {
    let duplicate = VStack("root") { Text("same", "A"); Text("same", "B") }.document(revision: 1)
    #expect(throws: UIValidationError.duplicateIdentity("same")) { try UIValidator().validate(duplicate) }
    let unsupported = UIValidator(supportedKinds: [.vStack])
    #expect(throws: UIValidationError.unsupportedNode(.text)) {
        try unsupported.validate(VStack("root") { Text("text", "A") }.document(revision: 1))
    }
    #expect(throws: UIValidationError.invalidProperty(node: "text", key: "script")) {
        try UIValidator().validate(frame(UINode(id: "text", kind: .text, properties: ["text": .string("Hi"), "script": .string("execute")])))
    }
    #expect(throws: UIValidationError.invalidAction(node: "button", event: .activate)) {
        try UIValidator().validate(frame(UINode(id: "button", kind: .button, properties: ["label": .string("Save")])))
    }
    let duplicateEvent = UINode(id: "button", kind: .button, properties: ["label": .string("Save")],
                                actions: [UIActionBinding(id: "a", event: .activate), UIActionBinding(id: "b", event: .activate)])
    #expect(throws: UIValidationError.invalidAction(node: "button", event: .activate)) { try UIValidator().validate(frame(duplicateEvent)) }
    #expect(throws: UIValidationError.invalidChildren("text")) {
        try UIValidator().validate(frame(UINode(id: "text", kind: .text, properties: ["text": .string("Hi")], children: [Text("child", "No").uiNode])))
    }
    #expect(throws: UIValidationError.invalidChildren("nav")) { try UIValidator().validate(Navigation("nav") {}.document(revision: 1)) }
    #expect(throws: UIValidationError.invalidIdentifier("")) { try UIValidator().validate(Text("", "No").document(revision: 1)) }
}

@Test func hostileWireMessagesFailClosed() throws {
    let validator = UIValidator()
    let unknownKind = Data(#"{"schemaVersion":1,"revision":1,"root":{"id":"x","kind":"webView","properties":{},"children":[],"actions":[]}}"#.utf8)
    #expect(throws: (any Error).self) { try validator.decode(unknownKind) }
    let unknownField = Data(#"{"schemaVersion":1,"revision":1,"root":{"id":"x","kind":"text","properties":{"text":"A"},"children":[],"actions":[],"nativeSelector":"run:"}}"#.utf8)
    #expect(throws: UIValidationError.unsupportedField("nativeSelector")) { try validator.decode(unknownField) }
    let unknownVersion = Data(#"{"schemaVersion":9,"revision":1,"root":null}"#.utf8)
    #expect(throws: UIValidationError.unsupportedSchema(9)) { try validator.decode(unknownVersion) }
    let objectProperty = Data(#"{"schemaVersion":1,"revision":1,"root":{"id":"x","kind":"text","properties":{"text":{"object":"bad"}},"children":[],"actions":[]}}"#.utf8)
    #expect(throws: (any Error).self) { try validator.decode(objectProperty) }
    #expect(throws: (any Error).self) { try validator.decode(Data(unknownField.dropLast(4))) }
    let exactLimit = UIValidator(limits: UIValidationLimits(maximumMessageBytes: 128))
    #expect(throws: UIValidationError.limitExceeded("messageBytes")) { try exactLimit.decode(Data(repeating: 0x20, count: 129)) }
}

@Test func boundsApplyToDecodedAndInMemoryTrees() throws {
    var node = Text("leaf", "value").uiNode
    for index in 0..<8 { node = UINode(id: "level.\(index)", kind: .vStack, children: [node]) }
    let deep = frame(node)
    let encoded = try UIValidator().encode(deep)
    let depthValidator = UIValidator(limits: UIValidationLimits(maximumDepth: 4))
    #expect(throws: UIValidationError.limitExceeded("depth")) { try depthValidator.validate(deep) }
    #expect(throws: UIValidationError.limitExceeded("depth")) { try depthValidator.decode(encoded) }
    let wide = VStack("root") { for index in 0..<5 { Text("n.\(index)", "Text") } }.document(revision: 1)
    let nodeValidator = UIValidator(limits: UIValidationLimits(maximumNodes: 3))
    #expect(throws: UIValidationError.limitExceeded("nodes")) { try nodeValidator.validate(wide) }
    #expect(throws: UIValidationError.limitExceeded("nodes")) { try nodeValidator.decode(UIValidator().encode(wide)) }
    let childValidator = UIValidator(limits: UIValidationLimits(maximumChildrenPerNode: 2))
    #expect(throws: UIValidationError.limitExceeded("children")) { try childValidator.validate(wide) }
    #expect(throws: UIValidationError.limitExceeded("children")) { try childValidator.decode(UIValidator().encode(wide)) }
    let stringValidator = UIValidator(limits: UIValidationLimits(maximumStringBytes: 3))
    #expect(throws: UIValidationError.limitExceeded("stringBytes")) { try stringValidator.validate(Text("emoji", "🏗").document(revision: 1)) }
    #expect(throws: UIValidationError.invalidProperty(node: "root", key: "spacing")) {
        try UIValidator().validate(VStack("root", spacing: .infinity) {}.document(revision: 1))
    }
}

@Test func thousandRowReorderRetainsIdentityAndSeparatesPropertyUpdates() throws {
    func document(_ rows: [Int], revision: UInt64, changed: Int? = nil) -> UIDocument {
        List("queue") {
            for row in rows { Text("row.\(row)", changed == row ? "Retried" : "Pending \(row)") }
        }.document(revision: revision)
    }
    var reconciler = UIReconciler()
    let initial = try reconciler.apply(document(Array(0..<1000), revision: 1))
    #expect(initial.inserted.count == 1001)
    let first = try reconciler.currentSnapshot()
    let reversed = Array((0..<1000).reversed())
    let reordered = try reconciler.apply(document(reversed, revision: 2))
    let second = try reconciler.currentSnapshot()
    #expect(reordered.inserted.isEmpty && reordered.removed.isEmpty && reordered.updated.isEmpty)
    #expect(reordered.moved.count == 1000)
    for row in 0..<1000 { #expect(first.identity(for: "row.\(row)") == second.identity(for: "row.\(row)")) }
    let updated = try reconciler.apply(document(reversed, revision: 3, changed: 700))
    #expect(updated.updated == ["row.700"])
    #expect(updated.moved.isEmpty)
}

@Test func eventOwnershipRejectsStaleReplacedDisabledAndForgedValues() throws {
    var reconciler = UIReconciler()
    try reconciler.apply(Button("save", "Save", action: "entry.save").document(revision: 1))
    let original = try reconciler.currentSnapshot()
    let oldID = try #require(original.identity(for: "save"))
    let action = try original.route(UIEventEnvelope(revision: 1, identity: oldID, event: .activate))
    #expect(action.actionID == "entry.save" && action.nodeID == "save")
    #expect(throws: UIRoutingError.invalidValue) {
        try original.route(UIEventEnvelope(revision: 1, identity: oldID, event: .activate, value: .string("spoof")))
    }
    #expect(throws: UIRoutingError.unboundEvent) {
        try original.route(UIEventEnvelope(revision: 1, identity: oldID, event: .valueChange, value: .bool(true)))
    }
    try reconciler.apply(Text("empty", "No editor").document(revision: 2))
    try reconciler.apply(Button("save", "Delete", action: "entry.delete").document(revision: 3))
    let current = try reconciler.currentSnapshot()
    #expect(current.identity(for: "save") != oldID)
    #expect(throws: UIRoutingError.staleRevision) { try current.route(UIEventEnvelope(revision: 1, identity: oldID, event: .activate)) }
    #expect(throws: UIRoutingError.staleIdentity) { try current.route(UIEventEnvelope(revision: 3, identity: oldID, event: .activate)) }
    try reconciler.apply(VStack("disabled") { Button("save", "Save", action: "entry.save") }.disabled().document(revision: 4))
    let disabled = try reconciler.currentSnapshot()
    #expect(throws: UIRoutingError.disabledNode) {
        try disabled.route(UIEventEnvelope(revision: 4, identity: #require(disabled.identity(for: "save")), event: .activate))
    }
}

@Test func typedTextToggleBindingsAndAtomicFailure() throws {
    var reconciler = UIReconciler(validator: UIValidator(limits: UIValidationLimits(maximumStringBytes: 10)))
    try reconciler.apply(VStack("root") {
        TextField("notes", "Notes", value: "", action: "edit")
        Toggle("done", "Done", value: false, action: "complete")
    }.document(revision: 1))
    let snapshot = try reconciler.currentSnapshot()
    let notes = try #require(snapshot.identity(for: "notes"))
    let done = try #require(snapshot.identity(for: "done"))
    #expect(try snapshot.route(UIEventEnvelope(revision: 1, identity: notes, event: .textChange, value: .string("hello"))).value == .string("hello"))
    #expect(try snapshot.route(UIEventEnvelope(revision: 1, identity: done, event: .valueChange, value: .bool(true))).actionID == "complete")
    #expect(throws: UIRoutingError.invalidValue) { try snapshot.route(UIEventEnvelope(revision: 1, identity: done, event: .valueChange, value: .string("yes"))) }
    #expect(throws: UIRoutingError.invalidValue) { try snapshot.route(UIEventEnvelope(revision: 1, identity: notes, event: .textChange, value: .string("far too much text"))) }
    let bad = VStack("root") { Text("duplicate", "A"); Text("duplicate", "B") }.document(revision: 2)
    #expect(throws: UIValidationError.duplicateIdentity("duplicate")) { try reconciler.apply(bad) }
    #expect(try reconciler.currentSnapshot().document == snapshot.document)
    #expect(throws: UIReconciliationError.revisionNotIncreasing) { try reconciler.apply(snapshot.document) }
    let replacement = try reconciler.apply(Button("notes", "Save", action: "save").document(revision: 3))
    #expect(replacement.replaced == ["notes"])
    #expect(try reconciler.currentSnapshot().identity(for: "notes") != notes)
}
