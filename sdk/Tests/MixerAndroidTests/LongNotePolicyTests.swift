import Foundation
import Testing
import MixerUI
import MixerCore
import MixerAndroid

private let axes: Set<TextFieldAxis> = [.horizontal, .vertical]
private let policyValidator = UIValidator(supportedTextFieldAxes: [.horizontal, .vertical], textValuePolicy: .longNoteV1)
private func note(_ value: String, axis: TextFieldAxis = .vertical, label: String = "Notes", id: String = "note", revision: UInt64 = 1) -> UIDocument {
    MixerUI.TextField(id, label, value: value, action: "note.changed", axis: axis).document(revision: revision)
}
private func snapshot(_ value: String = "", revision: UInt64 = 1) throws -> UIRenderSnapshot {
    var r = UIReconciler(validator: policyValidator)
    try r.apply(note(value, revision: revision))
    return try r.currentSnapshot()
}
@Test func longNoteFullByteCasesThroughActualCodecPacketAndEvents() throws {
    let cases = [("ascii", String(repeating: "a", count: 100_000)),
                 ("accent", String(repeating: "é", count: 50_000)),
                 ("emoji", String(repeating: "🌱", count: 25_000)),
                 ("decomposed", String(repeating: "e\u{301}", count: 33_333) + "x"),
                 ("control", String(repeating: "\u{1}", count: 100_000)),
                 ("newline", String(repeating: "\n", count: 100_000))]
    for (name, value) in cases {
        #expect(value.utf8.count == 100_000)
        #expect(throws: (any Error).self) { try UIValidator(supportedTextFieldAxes: axes).validate(note(value)) }
        let bytes = try policyValidator.encode(note(value))
        let decoded = try UIDocument.decode(bytes, validator: policyValidator)
        #expect(Array(decoded.root.properties["value"]!.string!.utf8) == Array(value.utf8))
        let s = try snapshot(value)
        #expect(throws: (any Error).self) { try s.encodeNativePacketV1(supportedTextFieldAxes: axes) }
        let packet = try s.encodeNativePacketV1(supportedTextFieldAxes: axes, textValuePolicy: .longNoteV1)
        #expect(packet.count <= 1_048_576)
        if name == "control" { #expect(packet.count > 600_000) }
        let event = UIEventEnvelope(revision: 1, identity: s.identity(for: "note")!, event: .textChange, value: .string(value))
        let eventBytes = try JSONEncoder().encode(event)
        try JSONInputGuard.validate(eventBytes, limits: JSONInputLimits(maximumDepth: 8, maximumValues: 64, maximumStringBytes: 100_000))
        let restored = try JSONDecoder().decode(UIEventEnvelope.self, from: eventBytes)
        #expect(Array(try s.route(restored).value.string!.utf8) == Array(value.utf8))
        #expect(throws: (any Error).self) { try policyValidator.validate(note(value + "x")) }
        #expect(throws: UIRoutingError.invalidValue) {
            try s.route(UIEventEnvelope(revision: 1, identity: event.identity, event: .textChange, value: .string(value + "x")))
        }
    }
}

@Test func longNoteCannotUpgradeLabelIDHorizontalOrStaleEvent() throws {
    let long = String(repeating: "a", count: 100_000)
    for doc in [note("", label: long), note("", id: long), note(long, axis: .horizontal),
                MixerUI.Text("text", long).document(revision: 1)] {
        #expect(throws: (any Error).self) { try policyValidator.validate(doc) }
        let raw = try JSONEncoder().encode(doc)
        #expect(throws: (any Error).self) { try UIDocument.decode(raw, validator: policyValidator) }
    }
    #expect(throws: UIValidationError.limitExceeded("stringBytes")) {
        try UIValidator(supportedTextFieldAxes: axes).validate(note(String(repeating: "a", count: 16_385)))
    }
    let s = try snapshot(long)
    #expect(throws: UIRoutingError.staleRevision) { try s.route(UIEventEnvelope(revision: 2, identity: s.identity(for: "note")!, event: .textChange, value: .string(long))) }
    #expect(throws: UIRoutingError.staleIdentity) { try s.route(UIEventEnvelope(revision: 1, identity: UINodeIdentity(id: "note", generation: 999), event: .textChange, value: .string(long))) }
}

@MainActor private final class NoteSource: AndroidUIBatchPresentation {
    var snapshot: UIRenderSnapshot
    var sent: [UIEventEnvelope] = []
    init(standard: Bool = false) throws {
        if standard {
            var r = UIReconciler(validator: UIValidator(supportedTextFieldAxes: axes))
            try r.apply(note("")); snapshot = try r.currentSnapshot()
        } else { snapshot = try R199Snapshot() }
    }
    func observe(_ receive: @escaping @MainActor (UIRenderSnapshot) -> Void) -> @MainActor () -> Void { {} }
    func send(_ event: UIEventEnvelope) throws { _ = try snapshot.route(event); sent.append(event) }
    func sendBatch(_ events: [UIEventEnvelope], from captured: UIRenderSnapshot) throws {
        for event in events { _ = try captured.route(event) }; sent += events
    }
}
private func R199Snapshot() throws -> UIRenderSnapshot { try snapshot() }
@MainActor private final class NoteSurface: AndroidUINativeSurface {
    var profile: AndroidUIProfile
    var capabilities: AndroidUICapabilities { profile.capabilities }
    var installed: AndroidUIFrame?
    init(_ profile: AndroidUIProfile = .measuredMultilineLongNotesV4) { self.profile = profile }
    func activate(owner: UUID) throws {}
    func install(_ frame: AndroidUIFrame) throws { installed = frame }
    func revoke(owner: UUID) { installed = nil }
}
@MainActor @Test func longNoteActualHostScalarBatchOwnerAndWrongProfile() throws {
    let source = try NoteSource(), surface = NoteSurface()
    let host = try AndroidUIHost(surface: surface, profile: .measuredMultilineLongNotesV4,
        appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), scheduleDelivery: {})
    defer { host.close() }
    let legacySurface = NoteSurface(.measuredMultilineRetirementV3)
    let legacyHost = try AndroidUIHost(surface: legacySurface, profile: .measuredMultilineRetirementV3,
        appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), scheduleDelivery: {})
    defer { legacyHost.close() }
    try legacyHost.replace(with: source)
    #expect(throws: AndroidUIHostError.profileMismatch) { try legacyHost.deliverLatest() }
    let owner = try host.replace(with: source); try host.deliverLatest()
    let text = String(repeating: "\u{1}", count: 100_000)
    let event = UIEventEnvelope(revision: 1, identity: source.snapshot.identity(for: "note")!, event: .textChange, value: .string(text))
    try host.send(owner: owner, event: event)
    try host.sendBatch(owner: owner, events: [event])
    #expect(source.sent == [event, event])
    #expect(throws: AndroidUIHostError.invalidBatch) { try host.sendBatch(owner: owner, events: [event, event]) }
    #expect(throws: AndroidUIHostError.staleOwner) { try host.send(owner: UUID(), event: event) }
    surface.profile = .measuredMultilineRetirementV3
    #expect(throws: AndroidUIHostError.profileMismatch) { try host.send(owner: owner, event: event) }
    #expect(source.sent.count == 2)
    #expect(throws: AndroidUIHostError.profileMismatch) {
        try AndroidUIHost(surface: surface, profile: .measuredMultilineLongNotesV4,
            appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), scheduleDelivery: {})
    }
}


@MainActor @Test func longNoteActualHostExactAggregateAndCountBoundaries() throws {
    var rows: [[String: Any]] = []
    for (profile, standard, maximum) in [(AndroidUIProfile.measuredMultilineLongNotesV4, false, 1_048_576),
                                       (.measuredMultilineRetirementV3, true, 131_072)] {
        let source = try NoteSource(standard: standard), surface = NoteSurface(profile)
        let host = try AndroidUIHost(surface: surface, profile: profile,
            appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), scheduleDelivery: {})
        defer { host.close() }
        let owner = try host.replace(with: source); try host.deliverLatest()
        let identity = source.snapshot.identity(for: "note")!
        func event(_ value: String) -> UIEventEnvelope {
            UIEventEnvelope(revision: 1, identity: identity, event: .textChange, value: .string(value))
        }
        let tiny = event("")
        try host.sendBatch(owner: owner, events: Array(repeating: tiny, count: 32))
        #expect(source.sent.count == 32)
        #expect(throws: AndroidUIHostError.invalidBatch) { try host.sendBatch(owner: owner, events: Array(repeating: tiny, count: 33)) }
        #expect(throws: AndroidUIHostError.invalidBatch) { try host.sendBatch(owner: owner, events: []) }
        let width = standard ? 16_384 : 100_000
        let fullCount = (maximum - 4_096) / width
        var batch = Array(repeating: event(String(repeating: "a", count: width)), count: fullCount)
        batch.append(event(""))
        let overhead = try JSONEncoder().encode(batch).count
        let tail = maximum - overhead
        #expect(tail >= 0 && tail <= width)
        batch[batch.count - 1] = event(String(repeating: "a", count: tail))
        #expect(try JSONEncoder().encode(batch).count == maximum)
        try host.sendBatch(owner: owner, events: batch)
        let accepted = source.sent.count
        batch[batch.count - 1] = event(String(repeating: "a", count: tail + 1))
        #expect(try JSONEncoder().encode(batch).count == maximum + 1)
        #expect(throws: AndroidUIHostError.invalidBatch) { try host.sendBatch(owner: owner, events: batch) }
        #expect(source.sent.count == accepted)
        rows.append(["profile": profile.rawValue, "exactBytesAccepted": maximum,
                     "oneOverRefused": maximum + 1, "eventsAccepted": 32, "eventsRefused": 33])
    }
    #expect(AndroidUIHost.maximumBatchBytes == 131_072)
    #expect(AndroidUIHost.maximumBatchEvents == 32)
    var r = UIReconciler(validator: UIValidator(supportedTextFieldAxes: axes))
    try r.apply(note("", axis: .horizontal))
}
