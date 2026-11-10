import Foundation
import Testing
import MixerUI
import MixerAndroid

private func batchSnapshot(_ revision: UInt64, title: String = "", disabled: Bool = false) throws -> UIRenderSnapshot {
    var reconciler = UIReconciler()
    try reconciler.apply(VStack("form") {
        TextField("title", "Title", value: title, action: "edit").disabled(disabled)
        Button("add", "Add", action: "add")
    }.document(revision: revision))
    return try reconciler.currentSnapshot()
}
private func batchEvent(_ snapshot: UIRenderSnapshot, _ value: String) throws -> UIEventEnvelope {
    UIEventEnvelope(revision: snapshot.document.revision, identity: try #require(snapshot.identity(for: "title")),
                    event: .textChange, value: .string(value))
}
@MainActor private class BatchLegacySource: AndroidUIPresentation {
    var value: UIRenderSnapshot
    var onRead: (@MainActor () -> Void)?
    var snapshot: UIRenderSnapshot { let captured = value; onRead?(); return captured }
    var observer: (@MainActor (UIRenderSnapshot) -> Void)?
    var singles: [UIEventEnvelope] = []
    init(_ value: UIRenderSnapshot) { self.value = value }
    func observe(_ receive: @escaping @MainActor (UIRenderSnapshot) -> Void) -> @MainActor () -> Void {
        observer = receive; return { self.observer = nil }
    }
    func send(_ event: UIEventEnvelope) throws { singles.append(event) }
    func publish(_ value: UIRenderSnapshot) { self.value = value; observer?(value) }
}
@MainActor private final class BatchSource: BatchLegacySource, AndroidUIBatchPresentation {
    var batches: [[UIEventEnvelope]] = []
    var onBatch: (@MainActor () throws -> Void)?
    func sendBatch(_ events: [UIEventEnvelope], from snapshot: UIRenderSnapshot) throws {
        try onBatch?()
        let actions = try events.map { try snapshot.route($0) }
        let final = try batchSnapshot(snapshot.document.revision + 1, title: actions.last?.value.string ?? "")
        batches.append(events); publish(final)
    }
}
@MainActor private final class BatchSurface: AndroidUINativeSurface {
    var profile = AndroidUIProfile.measuredMultilineRetirementV3
    var capabilities: AndroidUICapabilities { profile.capabilities }
    var owner: UUID?
    var frames: [AndroidUIFrame] = []
    func activate(owner: UUID) throws { self.owner = owner }
    func install(_ frame: AndroidUIFrame) throws { #expect(frame.owner == owner); frames.append(frame) }
    func revoke(owner: UUID) { self.owner = nil }
}
@MainActor private func batchHost(_ surface: BatchSurface) throws -> AndroidUIHost {
    try AndroidUIHost(surface: surface, profile: surface.profile,
        appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), scheduleDelivery: {})
}

@MainActor @Test func batchHostOrdersOriginalEnvelopesAndPublishesOneRevision() throws {
    let source = BatchSource(try batchSnapshot(9)), surface = BatchSurface(), host = try batchHost(surface)
    defer { host.close() }
    let owner = try host.replace(with: source); try host.deliverLatest()
    let events = try [batchEvent(source.value, "R"), batchEvent(source.value, "R69 🧪")]
    try host.sendBatch(owner: owner, events: events)
    #expect(source.batches == [events]); #expect(source.singles.isEmpty)
    #expect(source.value.document.revision == 10); #expect(surface.frames.count == 1)
    #expect(host.pendingFrame?.snapshot.document.revision == 10)
    #expect(throws: AndroidUIHostError.sourceChanged) { try host.sendBatch(owner: owner, events: events) }
    try host.deliverLatest()
    #expect(surface.frames.map { $0.snapshot.document.revision } == [9, 10])
    #expect(throws: UIRoutingError.staleRevision) { try host.sendBatch(owner: owner, events: events) }
    #expect(source.batches == [events])
}

@MainActor @Test func batchHostRejectsInvalidSecondMemberBeforeAppCallback() throws {
    let source = BatchSource(try batchSnapshot(1)), surface = BatchSurface(), host = try batchHost(surface)
    defer { host.close() }
    let owner = try host.replace(with: source); try host.deliverLatest()
    let first = try batchEvent(source.value, "first")
    let bad = [UIEventEnvelope(revision: 2, identity: first.identity, event: .textChange, value: .string("stale")),
               UIEventEnvelope(revision: 1, identity: UINodeIdentity(id: "title", generation: 999), event: .textChange, value: .string("forged")),
               UIEventEnvelope(revision: 1, identity: first.identity, event: .textChange, value: .bool(true)),
               UIEventEnvelope(revision: 1, identity: first.identity, event: .valueChange, value: .bool(true))]
    for second in bad {
        #expect(throws: (any Error).self) { try host.sendBatch(owner: owner, events: [first, second]) }
        #expect(source.batches.isEmpty && source.singles.isEmpty && source.value.document.revision == 1)
        #expect(surface.frames.count == 1 && host.pendingFrame == nil)
    }
    source.publish(try batchSnapshot(2, disabled: true)); try host.deliverLatest()
    #expect(throws: UIRoutingError.disabledNode) { try host.sendBatch(owner: owner, events: [batchEvent(source.value, "x")]) }
    #expect(source.batches.isEmpty)
}

@MainActor @Test func batchHostRefusesEmptyCountBytesUnsupportedAndPreservesScalar() throws {
    let source = BatchLegacySource(try batchSnapshot(1)), surface = BatchSurface(), host = try batchHost(surface)
    defer { host.close() }
    let owner = try host.replace(with: source); try host.deliverLatest()
    let event = try batchEvent(source.value, "x")
    #expect(throws: AndroidUIHostError.batchUnsupported) { try host.sendBatch(owner: owner, events: [event]) }
    try host.send(owner: owner, event: event); #expect(source.singles == [event])
    #expect(throws: AndroidUIHostError.invalidBatch) { try host.sendBatch(owner: owner, events: []) }
    #expect(throws: AndroidUIHostError.invalidBatch) { try host.sendBatch(owner: owner, events: Array(repeating: event, count: 33)) }
    let huge = try batchEvent(source.value, String(repeating: "a", count: 131_072))
    #expect(throws: AndroidUIHostError.invalidBatch) { try host.sendBatch(owner: owner, events: [huge]) }
    #expect(source.singles == [event])
}

@MainActor @Test func batchHostRejectsChangedSourceReplacementCloseAndReentrancy() throws {
    let source = BatchSource(try batchSnapshot(1)), surface = BatchSurface(), host = try batchHost(surface)
    let owner = try host.replace(with: source), event = try batchEvent(source.value, "x")
    #expect(throws: AndroidUIHostError.noInstalledFrame) { try host.sendBatch(owner: owner, events: [event]) }
    try host.deliverLatest()
    source.value = try batchSnapshot(1, title: "silent")
    #expect(throws: AndroidUIHostError.sourceChanged) { try host.sendBatch(owner: owner, events: [event]) }
    source.value = try batchSnapshot(1)
    source.onRead = { source.onRead = nil; source.publish(try! batchSnapshot(2)) }
    #expect(throws: AndroidUIHostError.sourceChanged) { try host.sendBatch(owner: owner, events: [event]) }
    try host.deliverLatest()
    let fresh = try batchEvent(source.value, "fresh")
    source.onBatch = { #expect(throws: AndroidUIHostError.busy) { try host.sendBatch(owner: owner, events: [fresh]) } }
    try host.sendBatch(owner: owner, events: [fresh])
    let next = BatchSource(try batchSnapshot(1)), successor = try host.replace(with: next)
    try host.deliverLatest()
    #expect(throws: AndroidUIHostError.staleOwner) { try host.sendBatch(owner: owner, events: [event]) }
    #expect(next.batches.isEmpty)
    surface.profile = .measuredMultilineV2
    #expect(throws: AndroidUIHostError.profileMismatch) { try host.sendBatch(owner: successor, events: [event]) }
    #expect(host.owner == nil && next.batches.isEmpty)
    host.close()
    #expect(throws: AndroidUIHostError.closed) { try host.sendBatch(owner: successor, events: [event]) }
}

@MainActor @Test func batchHostPreservesUInt64RevisionAndBusyCloseChecks() throws {
    let revision: UInt64 = 9_007_199_254_740_993
    let source = BatchSource(try batchSnapshot(revision)), surface = BatchSurface(), host = try batchHost(surface)
    defer { host.close() }
    let owner = try host.replace(with: source); try host.deliverLatest()
    let events = try [batchEvent(source.value, "one"), batchEvent(source.value, "two")]
    try host.sendBatch(owner: owner, events: events)
    #expect(source.batches[0].map(\.revision) == [revision, revision])
    #expect(source.value.document.revision == revision + 1)
}
