import Foundation
import Testing
import MixerUI
import MixerGuest

private let verticalFieldValidator = UIValidator(supportedTextFieldAxes: [.horizontal, .vertical])

private func axisFieldDocument(revision: UInt64 = 1, value: String = "First line\nCafé 🏗️",
                               axis: TextFieldAxis = .vertical) -> UIDocument {
    TextField("title", "Title", value: value, action: "title.changed", onSubmit: "save", axis: axis)
        .document(revision: revision)
}

@Test func textFieldAxisHorizontalAuthoringPreservesLegacyWire() throws {
    let implicit = TextField("title", "Title", value: "Draft", action: "title.changed", onSubmit: "save")
        .document(revision: 1)
    let explicit = axisFieldDocument(value: "Draft", axis: .horizontal)
    let legacy = UIDocument(revision: 1, root: UINode(id: "title", kind: .textField,
        properties: ["label": .string("Title"), "value": .string("Draft")],
        actions: [UIActionBinding(id: "title.changed", event: .textChange), UIActionBinding(id: "save", event: .submit)]))
    #expect(implicit == legacy && explicit == legacy)
    #expect(implicit.root.properties["axis"] == nil)
    let expected = Data(#"{"revision":1,"root":{"actions":[{"event":"textChange","id":"title.changed"},{"event":"submit","id":"save"}],"children":[],"id":"title","kind":"textField","properties":{"label":"Title","value":"Draft"}},"schemaVersion":1}"#.utf8)
    #expect(try UIValidator().encode(implicit) == expected)
    #expect(try UIValidator().encode(explicit) == expected)
    #expect(try UIDocument.decode(expected) == legacy)
}

@Test func textFieldAxisVerticalNeedsExplicitAdmissionOnValuesAndWire() throws {
    let value = "\nCafé\r\n漢字 e\u{301} 🏗️\n"
    let document = axisFieldDocument(value: value)
    #expect(document.schemaVersion == 1)
    #expect(document.root.properties["axis"] == .string("vertical"))
    #expect(document.root.properties["value"] == .string(value))
    let bytes = try verticalFieldValidator.encode(document)
    let decoded = try verticalFieldValidator.decode(bytes).document
    #expect(decoded == document)
    let decodedValue = try #require(decoded.root.properties["value"]?.string)
    #expect(Array(decodedValue.utf8) == Array(value.utf8))
    #expect(try verticalFieldValidator.encode(decoded) == bytes)
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) { try UIValidator().validate(document) }
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) { try UIValidator().encode(document) }
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) { try UIValidator().decode(bytes) }
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) { try UIDocument.decode(bytes) }
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) { try GuestUICodec().encode(document) }
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) { try GuestUICodec().decode(bytes) }
}

@Test func textFieldAxisValidationRejectsUnknownAndNonstringAxisValues() throws {
    let malformed: [UIValue] = [.string("diagonal"), .string("Vertical"), .string(""), .number(1), .bool(true), .null]
    for value in malformed {
        var node = axisFieldDocument().root
        node.properties["axis"] = value
        let document = UIDocument(revision: 1, root: node)
        let bytes = try JSONEncoder().encode(document)
        #expect(throws: UIValidationError.invalidProperty(node: "title", key: "axis")) {
            try verticalFieldValidator.validate(document)
        }
        #expect(throws: UIValidationError.invalidProperty(node: "title", key: "axis")) {
            try verticalFieldValidator.decode(bytes)
        }
    }
    var text = Text("text", "A label").uiNode
    text.properties["axis"] = .string("vertical")
    #expect(throws: UIValidationError.invalidProperty(node: "text", key: "axis")) {
        try verticalFieldValidator.validate(UIDocument(revision: 1, root: text))
    }
}

@Test func textFieldAxisCapabilityDoesNotWidenNodeStringOrActionValidation() throws {
    let verticalOnly = UIValidator(supportedTextFieldAxes: [.vertical])
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.horizontal)) {
        try verticalOnly.validate(axisFieldDocument(axis: .horizontal))
    }
    let noFields = UIValidator(supportedKinds: [.text], supportedTextFieldAxes: [.horizontal, .vertical])
    #expect(throws: UIValidationError.unsupportedNode(.textField)) { try noFields.validate(axisFieldDocument()) }
    let bounded = UIValidator(limits: UIValidationLimits(maximumStringBytes: 8),
                              supportedTextFieldAxes: [.horizontal, .vertical])
    #expect(throws: UIValidationError.limitExceeded("stringBytes")) {
        try bounded.validate(axisFieldDocument(value: "é\n漢🙂"))
    }
    let missingAction = UINode(id: "title", kind: .textField,
        properties: ["label": .string("Title"), "value": .string("Draft"), "axis": .string("vertical")])
    #expect(throws: UIValidationError.invalidAction(node: "title", event: .textChange)) {
        try verticalFieldValidator.validate(UIDocument(revision: 1, root: missingAction))
    }
}

@Test func textFieldAxisRejectedCandidatePreservesSnapshotIdentityAndRevision() throws {
    var reconciler = UIReconciler()
    let initial = axisFieldDocument(value: "Saved", axis: .horizontal)
    try reconciler.apply(initial)
    let previous = try reconciler.currentSnapshot()
    let identity = try #require(previous.identity(for: "title"))
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) {
        try reconciler.apply(axisFieldDocument(revision: 2))
    }
    let preserved = try reconciler.currentSnapshot()
    #expect(preserved.document == initial && preserved.identity(for: "title") == identity)
    #expect(try preserved.route(UIEventEnvelope(revision: 1, identity: identity, event: .submit)).actionID == "save")
    let accepted = axisFieldDocument(revision: 2, value: "Accepted", axis: .horizontal)
    try reconciler.apply(accepted)
    #expect(try reconciler.currentSnapshot().document == accepted)
    #expect(try reconciler.currentSnapshot().identity(for: "title") == identity)
}

@Test func textFieldAxisMultilineEventsKeepUnicodeAndCurrentSnapshotBindings() throws {
    var reconciler = UIReconciler(validator: verticalFieldValidator)
    try reconciler.apply(axisFieldDocument())
    let first = try reconciler.currentSnapshot()
    let identity = try #require(first.identity(for: "title"))
    let edited = "\nCafé\r\n漢字 e\u{301} 🏗️\n"
    let envelope = UIEventEnvelope(revision: 1, identity: identity, event: .textChange, value: .string(edited))
    let action = try first.route(envelope)
    #expect(action.actionID == "title.changed" && action.value == .string(edited))
    let routedValue = try #require(action.value.string)
    #expect(Array(routedValue.utf8) == Array(edited.utf8))
    #expect(try first.route(UIEventEnvelope(revision: 1, identity: identity, event: .submit)).actionID == "save")
    #expect(throws: UIRoutingError.invalidValue) {
        try first.route(UIEventEnvelope(revision: 1, identity: identity, event: .submit, value: .string(edited)))
    }
    let next = TextField("title", "Title", value: edited, action: "new.changed", onSubmit: "new.save", axis: .vertical)
        .document(revision: 2)
    let changes = try reconciler.apply(next)
    let current = try reconciler.currentSnapshot()
    #expect(changes.updated == ["title"] && changes.inserted.isEmpty && changes.replaced.isEmpty)
    #expect(current.identity(for: "title") == identity)
    #expect(throws: UIRoutingError.staleRevision) { try current.route(envelope) }
    #expect(try current.route(UIEventEnvelope(revision: 2, identity: identity, event: .textChange,
                                             value: .string(edited))).actionID == "new.changed")
    try reconciler.apply(TextField("title", "Title", value: edited, action: "new.changed", axis: .vertical)
        .disabled().document(revision: 3))
    let disabled = try reconciler.currentSnapshot()
    #expect(throws: UIRoutingError.disabledNode) {
        try disabled.route(UIEventEnvelope(revision: 3, identity: identity, event: .textChange, value: .string(edited)))
    }
}

@Test func textFieldAxisOptedInSnapshotCannotWidenPortablePacketOrAppearanceSupport() throws {
    var reconciler = UIReconciler(validator: verticalFieldValidator)
    let document = axisFieldDocument()
    try reconciler.apply(document)
    let snapshot = try reconciler.currentSnapshot()
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) { try snapshot.encodeNativePacketV1() }
    let v1 = try UIAppearanceDescriptorCodecV1.mixerDefaultV1()
    let environmentV1 = UIAppearanceEnvironmentV1(scheme: .light, direction: .leftToRight,
                                                  textScale1024: 1024, density1024: 1024)
    for platform: UIAppearancePlatformV1 in [.iOS, .android] {
        #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) {
            try UIAppearanceResolverV1.prepare(snapshot: snapshot, configuration: v1,
                                               environment: environmentV1, platform: platform)
        }
    }
    let v2 = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
    let environmentV2 = UIAppearanceEnvironmentV2(scheme: .light, direction: .leftToRight, profile: .l,
        density1024: 1024, viewport: UIAppearanceViewportV2(width64: 25728, height64: 55936),
        safeArea64: UIInsets64V1(top: 0, leading: 0, bottom: 0, trailing: 0), localeIdentifier: "en-US",
        accessibility: UIAppearanceAccessibilityV2(boldText: false, increasedContrast: false, reduceMotion: false), generation: 1)
    for platform: UIAppearancePlatformV2 in [.iOS, .android] {
        #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) {
            try UIAppearanceResolverV2.prepare(snapshot: snapshot, configuration: v2,
                                               environment: environmentV2, platform: platform)
        }
    }
    #expect(try reconciler.currentSnapshot().document == document)
    #expect(try reconciler.currentSnapshot().identity(for: "title") == snapshot.identity(for: "title"))
}
