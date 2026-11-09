import Foundation
import Testing
import MixerUI
import MixerAndroid

private let unicode = "\nCafé\r\n漢字 e\u{301} 🏗️\n"
private let allCapabilities = AndroidUICapabilities(kinds: Set(NodeKind.allCases),
    textFieldAxes: [.horizontal, .vertical], appearanceV2: true)
private enum Failure: Error, Equatable { case attachment }

private func form(_ revision: UInt64, title: String = unicode, saving: Bool = false) throws -> UIRenderSnapshot {
    var reconciler = UIReconciler(validator: UIValidator(supportedTextFieldAxes: [.horizontal, .vertical]))
    try reconciler.apply(VStack("form") {
        TextField("title", "Title", value: title, action: "title.changed", axis: .vertical).disabled(saving)
        TextField("responsible", "Responsible", value: "Zoë 👷", action: "responsible.changed").disabled(saving)
        Button("add", saving ? "Saving" : "Add", action: "add").disabled(saving)
    }.document(revision: revision))
    return try reconciler.currentSnapshot()
}

private func list(_ revision: UInt64) throws -> UIRenderSnapshot {
    var reconciler = UIReconciler()
    try reconciler.apply(Text("tasks", "Saved task").document(revision: revision))
    return try reconciler.currentSnapshot()
}

@MainActor private final class Presentation: AndroidUIPresentation {
    var snapshot: UIRenderSnapshot
    var observers: [Int: @MainActor (UIRenderSnapshot) -> Void] = [:]
    var captured: [@MainActor (UIRenderSnapshot) -> Void] = []
    var events: [UIEventEnvelope] = []
    var onEvent: (@MainActor (UIEventEnvelope) throws -> Void)?
    var cancellations = 0
    init(_ snapshot: UIRenderSnapshot) { self.snapshot = snapshot }
    func observe(_ receive: @escaping @MainActor (UIRenderSnapshot) -> Void) -> @MainActor () -> Void {
        let id = captured.count
        captured.append(receive); observers[id] = receive
        receive(snapshot)
        return { [weak self] in self?.observers[id] = nil; self?.cancellations += 1 }
    }
    func send(_ event: UIEventEnvelope) throws { events.append(event); try onEvent?(event) }
    func publish(_ snapshot: UIRenderSnapshot) {
        self.snapshot = snapshot
        for observer in Array(observers.values) { observer(snapshot) }
    }
}

/// A controlled boundary double. No Java, JNI, native view or durable repository
/// behavior is implemented here; tests observe only the public Swift host effects.
@MainActor private final class Surface: AndroidUINativeSurface {
    let profile = AndroidUIProfile.measuredMultilineV2
    var capabilities = allCapabilities
    var frames: [AndroidUIFrame] = []
    var revoked: [UUID] = []
    var activeOwner: UUID?
    var fail = false
    var duringInstall: (@MainActor () throws -> Void)?
    func activate(owner: UUID) throws {
        guard activeOwner == nil else { throw Failure.attachment }
        activeOwner = owner
    }
    func install(_ frame: AndroidUIFrame) throws {
        try duringInstall?()
        guard activeOwner == frame.owner, !revoked.contains(frame.owner), !fail else { throw Failure.attachment }
        frames.append(frame)
    }
    func revoke(owner: UUID) {
        revoked.append(owner)
        if activeOwner == owner { activeOwner = nil }
    }
}

@MainActor private func host(_ surface: Surface, schedule: @escaping @MainActor () -> Void = {}) throws -> AndroidUIHost {
    try AndroidUIHost(surface: surface, profile: surface.profile, appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(),
                      scheduleDelivery: schedule)
}

private func add(_ snapshot: UIRenderSnapshot) throws -> UIEventEnvelope {
    UIEventEnvelope(revision: snapshot.document.revision, identity: try #require(snapshot.identity(for: "add")), event: .activate)
}

@Test @MainActor func androidHostCoalescesSnapshotsAndPreservesVerticalUnicodeAppearancePacket() throws {
    let surface = Surface(); var wakes = 0
    let host = try host(surface) { wakes += 1 }
    let source = Presentation(try form(1))
    let owner = try host.replace(with: source)
    source.publish(try form(2)); source.publish(try form(3))
    #expect(wakes == 1 && surface.frames.isEmpty)
    #expect(try host.deliverLatest())
    #expect(surface.frames.count == 1 && surface.frames[0].owner == owner)
    let frame = try #require(surface.frames.last)
    #expect(frame.snapshot.document.revision == 3)
    let packet = try #require(JSONSerialization.jsonObject(with: frame.packet) as? [String: Any])
    let document = try JSONSerialization.data(withJSONObject: #require(packet["document"]))
    let decoded = try UIValidator(supportedTextFieldAxes: [.horizontal, .vertical]).decode(document).document
    #expect(decoded == source.snapshot.document)
    #expect(Array(try #require(decoded.root.children[0].properties["value"]?.string).utf8) == Array(unicode.utf8))
    #expect(decoded.root.children[0].properties["axis"] == .string("vertical"))
    #expect(decoded.root.children[1].properties["value"] == .string("Zoë 👷"))
    #expect(try UIAppearanceDescriptorCodecV2.decode(frame.appearanceDescriptorV2) == UIAppearanceDescriptorCodecV2.mixerDefaultV2())
    #expect(try !host.deliverLatest())
    host.close(); #expect(source.cancellations == 1 && source.observers.isEmpty)
}

@Test @MainActor func androidHostRoutesOriginalEnvelopeAndRejectsStaleDisabledAndForgedEvents() throws {
    let surface = Surface(); let host = try host(surface); let source = Presentation(try form(1))
    let owner = try host.replace(with: source); try host.deliverLatest()
    let event = try add(source.snapshot)
    let forged = UIEventEnvelope(revision: 1, identity: UINodeIdentity(id: "add", generation: 999), event: .activate)
    #expect(throws: UIRoutingError.staleIdentity) { try host.send(owner: owner, event: forged) }
    source.onEvent = { _ in source.publish(try form(2, saving: true)) }
    try host.send(owner: owner, event: event)
    #expect(source.events == [event])
    #expect(throws: AndroidUIHostError.sourceChanged) { try host.send(owner: owner, event: event) }
    try host.deliverLatest()
    #expect(throws: UIRoutingError.staleRevision) { try host.send(owner: owner, event: event) }
    #expect(throws: UIRoutingError.disabledNode) { try host.send(owner: owner, event: add(source.snapshot)) }
    #expect(source.events.count == 1)
    host.close()
}

@Test @MainActor func androidHostTextEventsKeepOriginalIdentityRevisionAndUnicodeBytes() throws {
    let surface = Surface(); let host = try host(surface); let source = Presentation(try form(1, title: ""))
    let owner = try host.replace(with: source); try host.deliverLatest()
    let title = UIEventEnvelope(revision: 1, identity: try #require(source.snapshot.identity(for: "title")),
                                event: .textChange, value: .string(unicode))
    source.onEvent = { _ in source.publish(try form(2)) }
    try host.send(owner: owner, event: title); try host.deliverLatest()
    source.onEvent = nil
    let responsible = UIEventEnvelope(revision: 2, identity: try #require(source.snapshot.identity(for: "responsible")),
                                      event: .textChange, value: .string("Zoë 👷"))
    try host.send(owner: owner, event: responsible)
    #expect(source.events == [title, responsible])
    #expect(Array(try #require(source.events.first?.value.string).utf8) == Array(unicode.utf8))
    let wrongValue = UIEventEnvelope(revision: 2, identity: responsible.identity, event: .textChange, value: .bool(true))
    #expect(throws: UIRoutingError.invalidValue) { try host.send(owner: owner, event: wrongValue) }
    #expect(source.events.count == 2)
    host.close()
}

@Test func androidHostAxisPacketDoesNotWidenStandardLimits() throws {
    var reconciler = UIReconciler(validator: UIValidator(limits: UIValidationLimits(maximumStringBytes: 32_768),
        supportedTextFieldAxes: [.horizontal, .vertical]))
    try reconciler.apply(TextField("title", "Title", value: String(repeating: "x", count: 16_385),
                                   action: "edit", axis: .vertical).document(revision: 1))
    let snapshot = try reconciler.currentSnapshot()
    #expect(throws: UIValidationError.limitExceeded("stringBytes")) {
        try snapshot.encodeNativePacketV1(supportedTextFieldAxes: [.horizontal, .vertical])
    }
}

@Test @MainActor func androidHostNativeFailureCannotReplayOrUndoExternalCommit() throws {
    let surface = Surface(); let host = try host(surface); let source = Presentation(try form(1))
    let owner = try host.replace(with: source); try host.deliverLatest()
    var starts = 0, completedCommits = 0
    var completion: (@MainActor () throws -> Void)?
    source.onEvent = { _ in
        starts += 1; source.publish(try form(2, saving: true))
        completion = { completedCommits += 1; source.publish(try list(3)) }
    }
    try host.send(owner: owner, event: add(source.snapshot)); try host.deliverLatest()
    #expect(completedCommits == 0 && surface.frames.last?.snapshot.document.root.children.last?.properties["label"] == .string("Saving"))
    let complete = try #require(completion)
    try complete()
    surface.fail = true
    #expect(throws: Failure.attachment) { try host.deliverLatest() }
    #expect(starts == 1 && completedCommits == 1 && source.events.count == 1)
    surface.fail = false; try host.deliverLatest()
    #expect(surface.frames.last?.snapshot.document.root.id == "tasks")
    #expect(starts == 1 && completedCommits == 1 && source.events.count == 1)
    host.close()
}

@Test @MainActor func androidHostFailureRetainsTextAndRetryUsesNewRevision() throws {
    let surface = Surface(); let host = try host(surface); let source = Presentation(try form(1))
    let owner = try host.replace(with: source); try host.deliverLatest()
    source.onEvent = { event in source.publish(try form(event.revision + 1, saving: true)) }
    try host.send(owner: owner, event: add(source.snapshot)); try host.deliverLatest()
    // Controlled failed app completion. The existing app model owns this result.
    source.publish(try form(3)); try host.deliverLatest()
    let retryFrame = try #require(surface.frames.last)
    #expect(retryFrame.snapshot.document.root.children[0].properties["value"] == .string(unicode))
    try host.send(owner: owner, event: add(source.snapshot))
    #expect(source.events.map(\.revision) == [1, 3])
    host.close()
}

@Test @MainActor func androidHostCloseDuringSaveRejectsCapturedLateCompletion() throws {
    let surface = Surface(); let host = try host(surface); let source = Presentation(try form(1))
    let owner = try host.replace(with: source); try host.deliverLatest()
    source.onEvent = { _ in source.publish(try form(2, saving: true)) }
    try host.send(owner: owner, event: add(source.snapshot)); try host.deliverLatest()
    let lateObserver = try #require(source.captured.first), installed = surface.frames.count
    host.close(); host.close()
    source.publish(try list(3)); lateObserver(try list(3))
    #expect(throws: AndroidUIHostError.closed) { try host.deliverLatest() }
    #expect(host.pendingFrame == nil && surface.frames.count == installed)
    #expect(source.cancellations == 1 && surface.revoked == [owner])
}

@Test @MainActor func androidHostReplacementRejectsOldOwnersAndPendingWake() throws {
    let surface = Surface(); var wakes = 0; let host = try host(surface) { wakes += 1 }
    let old = Presentation(try form(8)), next = Presentation(try form(1, title: "Replacement"))
    let oldOwner = try host.replace(with: old); try host.deliverLatest()
    old.publish(try form(9, saving: true))
    let newOwner = try host.replace(with: next)
    old.captured[0](try list(10))
    #expect(wakes == 2) // Initial delivery plus one pending wake spanning replacement.
    try host.deliverLatest() // May be the old queued wake; only newest owner wins.
    #expect(old.cancellations == 1 && surface.revoked == [oldOwner])
    #expect(surface.frames.last?.owner == newOwner && surface.frames.last?.snapshot.document.revision == 1)
    #expect(throws: AndroidUIHostError.staleOwner) { try host.send(owner: oldOwner, event: add(next.snapshot)) }
    #expect(next.events.isEmpty && old.events.isEmpty)
    host.close()
}

@Test @MainActor func androidHostNewSnapshotDuringInstallKeepsLatestAndRejectsOldEvents() throws {
    let surface = Surface(); let host = try host(surface); let source = Presentation(try form(1))
    let owner = try host.replace(with: source), first = source.snapshot
    surface.duringInstall = { source.publish(try form(2, title: "Later\n漢字")) }
    try host.deliverLatest()
    #expect(host.pendingFrame?.snapshot.document.revision == 2)
    #expect(throws: AndroidUIHostError.sourceChanged) { try host.send(owner: owner, event: add(first)) }
    surface.duringInstall = nil; try host.deliverLatest()
    #expect(surface.frames.map { $0.snapshot.document.revision } == [1, 2])
    #expect(source.events.isEmpty)
    host.close()
}

@Test @MainActor func androidHostSurfaceCannotBeSharedByTwoLiveHosts() throws {
    let surface = Surface(), source = Presentation(try form(1))
    let first = try host(surface), second = try host(surface)
    let owner = try first.replace(with: source)
    #expect(throws: Failure.attachment) { try second.replace(with: source) }
    #expect(surface.activeOwner == owner && source.observers.count == 1)
    try first.deliverLatest()
    first.close(); second.close()
}

@Test @MainActor func androidHostInstallSerializesAdmissionAndReentrantCloseRevokes() throws {
    let surface = Surface(); let host = try host(surface); let source = Presentation(try form(1))
    let owner = try host.replace(with: source)
    surface.duringInstall = {
        #expect(throws: AndroidUIHostError.busy) { try host.send(owner: owner, event: add(source.snapshot)) }
        #expect(throws: AndroidUIHostError.busy) { try host.replace(with: source) }
        host.close()
    }
    #expect(throws: Failure.attachment) { try host.deliverLatest() }
    #expect(surface.frames.isEmpty && source.events.isEmpty && source.cancellations == 1)
    #expect(surface.revoked == [owner])
}

@Test @MainActor func androidHostCapabilitiesFailClosedWithoutWideningLegacyEncoder() throws {
    let vertical = try form(1)
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) { try vertical.encodeNativePacketV1() }
    let surface = Surface()
    surface.capabilities = AndroidUICapabilities(kinds: Set(NodeKind.allCases), textFieldAxes: [.horizontal], appearanceV2: true)
    let host = try host(surface), source = Presentation(vertical)
    let owner = try host.replace(with: source)
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) { try host.deliverLatest() }
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) { try host.send(owner: owner, event: add(vertical)) }
    #expect(source.events.isEmpty && surface.frames.isEmpty)
    host.close()
    let absent = Surface(); absent.capabilities = AndroidUICapabilities()
    #expect(throws: AndroidUIHostError.appearanceUnsupported) { try AndroidUIHost(surface: absent, profile: absent.profile,
        appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), scheduleDelivery: {}) }
}

@Test @MainActor func androidHostRejectsSilentOrRegressingSourceThenAcceptsNewerSnapshot() throws {
    let surface = Surface(); let host = try host(surface); let source = Presentation(try form(2))
    let owner = try host.replace(with: source); try host.deliverLatest()
    let event = try add(source.snapshot)
    source.snapshot = try form(2, title: "Unnotified change")
    #expect(throws: AndroidUIHostError.sourceChanged) { try host.send(owner: owner, event: event) }
    source.publish(try form(1))
    #expect(throws: AndroidUIHostError.revisionNotIncreasing) { try host.deliverLatest() }
    #expect(source.events.isEmpty)
    source.publish(try form(3)); try host.deliverLatest()
    try host.send(owner: owner, event: add(source.snapshot))
    #expect(source.events.count == 1)
    host.close()
}

import Foundation
import Testing
import MixerUI
import MixerAndroid

private enum ReviewFailure: Error { case activation, unavailable, unknownAttachment }

private func reviewSnapshot(_ revision: UInt64, label: String = "Add") throws -> UIRenderSnapshot {
    var reconciler = UIReconciler()
    try reconciler.apply(Button("add", label, action: "save").document(revision: revision))
    return try reconciler.currentSnapshot()
}

private func reviewEvent(_ snapshot: UIRenderSnapshot) throws -> UIEventEnvelope {
    let identity = try #require(snapshot.identity(for: "add"))
    return UIEventEnvelope(revision: snapshot.document.revision, identity: identity, event: .activate)
}

@MainActor private final class ReviewSource: AndroidUIPresentation {
    var value: UIRenderSnapshot
    var reads = 0
    var onRead: (@MainActor (Int) -> Void)?
    var onObserve: (@MainActor () -> Void)?
    var onCancel: (@MainActor () -> Void)?
    var callbacks: [@MainActor (UIRenderSnapshot) -> Void] = []
    var events: [UIEventEnvelope] = []
    var cancellations = 0
    init(_ value: UIRenderSnapshot) { self.value = value }
    var snapshot: UIRenderSnapshot {
        let result = value
        reads += 1
        onRead?(reads)
        return result
    }
    func observe(_ receive: @escaping @MainActor (UIRenderSnapshot) -> Void) -> @MainActor () -> Void {
        callbacks.append(receive)
        receive(value)
        onObserve?()
        return { self.cancellations += 1; self.onCancel?() }
    }
    func publish(_ next: UIRenderSnapshot) {
        value = next
        for callback in callbacks { callback(next) }
    }
    func send(_ event: UIEventEnvelope) throws { events.append(event) }
}

@MainActor private final class ReviewSurface: AndroidUINativeSurface {
    let profile = AndroidUIProfile.measuredMultilineV2
    var capabilities = AndroidUICapabilities(kinds: Set(NodeKind.allCases),
        textFieldAxes: [.horizontal, .vertical], appearanceV2: true)
    var owner: UUID?
    var revoked: Set<UUID> = []
    var frames: [AndroidUIFrame] = []
    var installCalls = 0
    var onActivate: (@MainActor () throws -> Void)?
    var onInstall: (@MainActor () throws -> Void)?
    var onRevoke: (@MainActor () -> Void)?
    var unknown = false
    func activate(owner: UUID) throws {
        guard self.owner == nil, !revoked.contains(owner) else { throw ReviewFailure.activation }
        self.owner = owner
        try onActivate?()
    }
    func install(_ frame: AndroidUIFrame) throws {
        installCalls += 1
        try onInstall?()
        guard owner == frame.owner, !revoked.contains(frame.owner) else { throw ReviewFailure.unavailable }
        if unknown {
            revoke(owner: frame.owner)
            throw ReviewFailure.unknownAttachment
        }
        frames.append(frame)
    }
    func revoke(owner: UUID) {
        revoked.insert(owner)
        if self.owner == owner { self.owner = nil }
        onRevoke?()
    }
}

@MainActor private func reviewHost(_ surface: ReviewSurface) throws -> AndroidUIHost {
    try AndroidUIHost(surface: surface, profile: surface.profile, appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(),
                      scheduleDelivery: {})
}

// These assertions describe the desired public behavior, not the current implementation.
// The source getter is allowed to execute arbitrary synchronous MainActor adapter code.
@Test @MainActor func reviewCloseDuringAdmissionReadPreventsAppDispatch() throws {
    for readOffset in [1, 2] {
        let surface = ReviewSurface(), source = ReviewSource(try reviewSnapshot(1))
        let host = try reviewHost(surface)
        let owner = try host.replace(with: source)
        try host.deliverLatest()
        let event = try reviewEvent(source.value), target = source.reads + readOffset
        source.onRead = { if $0 == target { host.close() } }
        var rejected = false
        do { try host.send(owner: owner, event: event) } catch { rejected = true }
        #expect(rejected, "close during admission read \(readOffset) must reject")
        #expect(source.events.isEmpty, "no app effect may start after close returns")
        #expect(host.owner == nil && surface.owner == nil && source.cancellations == 1)
    }
}

@Test @MainActor func reviewNewPublicationDuringLastAdmissionReadPreventsStaleDispatch() throws {
    let surface = ReviewSurface(), source = ReviewSource(try reviewSnapshot(1))
    let host = try reviewHost(surface), next = try reviewSnapshot(2, label: "Saving")
    let owner = try host.replace(with: source)
    try host.deliverLatest()
    let event = try reviewEvent(source.value), target = source.reads + 2
    source.onRead = { if $0 == target { source.publish(next) } }
    var rejected = false
    do { try host.send(owner: owner, event: event) } catch { rejected = true }
    #expect(rejected, "a pending newer publication must gate the old event")
    #expect(source.events.isEmpty)
    #expect(host.pendingFrame?.snapshot.document.revision == 2)
    host.close()
}

@Test @MainActor func reviewCloseDuringReplaceSnapshotReadCannotReturnLiveOwner() throws {
    let surface = ReviewSurface(), source = ReviewSource(try reviewSnapshot(1))
    let host = try reviewHost(surface)
    source.onRead = { _ in host.close() }
    var returnedOwner: UUID?
    do { returnedOwner = try host.replace(with: source) } catch { }
    #expect(returnedOwner == nil, "replace must reject a reentrantly closed host")
    #expect(host.owner == nil && source.cancellations == 1 && surface.owner == nil)
}

@Test @MainActor func reviewActivationFailureRevokesPartialBindingAndAllowsReplacement() throws {
    let surface = ReviewSurface(), failed = ReviewSource(try reviewSnapshot(1))
    let host = try reviewHost(surface)
    surface.onActivate = { throw ReviewFailure.activation }
    #expect(throws: ReviewFailure.self) { try host.replace(with: failed) }
    #expect(failed.callbacks.isEmpty && host.owner == nil && surface.owner == nil)
    #expect(surface.revoked.count == 1)
    surface.onActivate = nil
    let next = ReviewSource(try reviewSnapshot(1))
    let token = try host.replace(with: next)
    try host.deliverLatest()
    #expect(surface.frames.last?.owner == token)
    host.close()
}

@Test @MainActor func reviewCloseInsideActivationAndObservationRevokesExactlyOnce() throws {
    for activation in [true, false] {
        let surface = ReviewSurface(), source = ReviewSource(try reviewSnapshot(1))
        let host = try reviewHost(surface)
        if activation { surface.onActivate = { host.close() } }
        else { source.onObserve = { host.close() } }
        #expect(throws: AndroidUIHostError.closed) { try host.replace(with: source) }
        #expect(surface.owner == nil && surface.revoked.count == 1 && host.pendingFrame == nil)
        #expect(source.cancellations == (activation ? 0 : 1))
    }
}

@Test @MainActor func reviewCancellationReentryCannotResurrectOldOwner() throws {
    let surface = ReviewSurface(), old = ReviewSource(try reviewSnapshot(5))
    let next = ReviewSource(try reviewSnapshot(1)), host = try reviewHost(surface)
    try host.replace(with: old)
    let late = try reviewSnapshot(6)
    old.onCancel = { old.publish(late); host.close() }
    #expect(throws: AndroidUIHostError.closed) { try host.replace(with: next) }
    #expect(next.callbacks.isEmpty && host.pendingFrame == nil && surface.owner == nil)
    #expect(old.cancellations == 1)
}

@Test @MainActor func reviewUnknownInstallCanBeFencedBySurfaceUntilExplicitReplacement() throws {
    let surface = ReviewSurface(), source = ReviewSource(try reviewSnapshot(1))
    let host = try reviewHost(surface), owner = try host.replace(with: source)
    surface.unknown = true
    #expect(throws: ReviewFailure.self) { try host.deliverLatest() }
    #expect(throws: AndroidUIHostError.noInstalledFrame) { try host.send(owner: owner, event: reviewEvent(source.value)) }
    surface.unknown = false
    #expect(throws: ReviewFailure.self) { try host.deliverLatest() }
    #expect(surface.frames.isEmpty && source.events.isEmpty && surface.owner == nil)
    let next = try host.replace(with: source)
    try host.deliverLatest()
    #expect(next != owner && surface.frames.last?.owner == next)
    host.close()
}

@Test @MainActor func reviewDuplicateChangedIdentityPoisonsUntilStrictlyNewerSnapshot() throws {
    let surface = ReviewSurface(), source = ReviewSource(try reviewSnapshot(2))
    let host = try reviewHost(surface), owner = try host.replace(with: source)
    try host.deliverLatest()
    var changed = UIReconciler()
    try changed.apply(Text("add", "Old kind").document(revision: 1))
    try changed.apply(source.value.document)
    let nextIdentity = try changed.currentSnapshot()
    #expect(nextIdentity.identity(for: "add") != source.value.identity(for: "add"))
    source.publish(nextIdentity)
    #expect(throws: AndroidUIHostError.revisionNotIncreasing) { try host.deliverLatest() }
    #expect(throws: AndroidUIHostError.revisionNotIncreasing) { try host.send(owner: owner, event: reviewEvent(nextIdentity)) }
    source.publish(try reviewSnapshot(3))
    try host.deliverLatest()
    try host.send(owner: owner, event: reviewEvent(source.value))
    #expect(source.events.count == 1)
    host.close()
}

@Test @MainActor func reviewKindCapabilitiesRejectAndRecoverOnNewSupportedTree() throws {
    let surface = ReviewSurface()
    surface.capabilities = AndroidUICapabilities(kinds: [.text], textFieldAxes: [.horizontal], appearanceV2: true)
    let source = ReviewSource(try reviewSnapshot(1)), host = try reviewHost(surface)
    try host.replace(with: source)
    #expect(throws: (any Error).self) { try host.deliverLatest() }
    #expect(surface.frames.isEmpty)
    var reconciler = UIReconciler()
    try reconciler.apply(Text("done", "Saved").document(revision: 2))
    source.publish(try reconciler.currentSnapshot())
    try host.deliverLatest()
    #expect(surface.frames.last?.snapshot.document.root.id == "done")
    host.close()
}

@Test @MainActor func reviewInvalidPublicationDuringInstallNeverAdmitsInput() throws {
    let surface = ReviewSurface(), source = ReviewSource(try reviewSnapshot(2))
    let host = try reviewHost(surface), owner = try host.replace(with: source)
    let stale = try reviewSnapshot(1)
    surface.onInstall = { source.publish(stale) }
    try host.deliverLatest()
    #expect(throws: AndroidUIHostError.revisionNotIncreasing) { try host.send(owner: owner, event: reviewEvent(source.value)) }
    #expect(source.events.isEmpty && host.pendingFrame == nil)
    host.close()
}

@Test @MainActor func r2CloseDuringDeliveryGetterNeverCallsInstall() throws {
    let surface = ReviewSurface(), source = ReviewSource(try reviewSnapshot(1))
    let host = try reviewHost(surface)
    let owner = try host.replace(with: source)
    source.onRead = { _ in host.close() }
    #expect(throws: AndroidUIHostError.closed) { try host.deliverLatest() }
    #expect(surface.installCalls == 0 && surface.frames.isEmpty)
    #expect(host.owner == nil && surface.owner == nil && surface.revoked == [owner])
    #expect(source.events.isEmpty && source.cancellations == 1)
}

@Test @MainActor func r2NewPublicationDuringDeliveryGetterCoalescesBeforeInstall() throws {
    let surface = ReviewSurface(), source = ReviewSource(try reviewSnapshot(1))
    let host = try reviewHost(surface), next = try reviewSnapshot(2)
    let owner = try host.replace(with: source)
    source.onRead = { _ in source.onRead = nil; source.publish(next) }
    #expect(throws: AndroidUIHostError.sourceChanged) { try host.deliverLatest() }
    #expect(surface.installCalls == 0 && host.pendingFrame?.snapshot.document.revision == 2)
    #expect(try host.deliverLatest())
    #expect(surface.frames.count == 1 && surface.frames[0].owner == owner)
    #expect(surface.frames[0].snapshot.document.revision == 2 && source.events.isEmpty)
    host.close()
}

@Test @MainActor func r2InvalidPublicationDuringDeliveryGetterNeverCallsInstall() throws {
    let surface = ReviewSurface(), source = ReviewSource(try reviewSnapshot(2))
    let host = try reviewHost(surface), stale = try reviewSnapshot(1)
    try host.replace(with: source)
    source.onRead = { _ in source.publish(stale) }
    #expect(throws: AndroidUIHostError.revisionNotIncreasing) { try host.deliverLatest() }
    #expect(surface.installCalls == 0 && host.pendingFrame == nil && source.events.isEmpty)
    host.close()
}

@Test @MainActor func r2PublicationDuringEitherAdmissionGetterRejectsOldEnvelope() throws {
    for offset in [1, 2] {
        let surface = ReviewSurface(), source = ReviewSource(try reviewSnapshot(1))
        let host = try reviewHost(surface), next = try reviewSnapshot(2)
        let owner = try host.replace(with: source)
        try host.deliverLatest()
        let event = try reviewEvent(source.value), target = source.reads + offset
        source.onRead = { if $0 == target { source.publish(next) } }
        #expect(throws: AndroidUIHostError.sourceChanged) { try host.send(owner: owner, event: event) }
        #expect(source.events.isEmpty && host.pendingFrame?.snapshot.document.revision == 2)
        source.onRead = nil
        try host.deliverLatest()
        let current = try reviewEvent(source.value)
        try host.send(owner: owner, event: current)
        #expect(source.events == [current])
        host.close()
    }
}

@Test @MainActor func r2InvalidPublicationDuringEitherAdmissionGetterRejectsDispatch() throws {
    for offset in [1, 2] {
        let surface = ReviewSurface(), source = ReviewSource(try reviewSnapshot(2))
        let host = try reviewHost(surface), stale = try reviewSnapshot(1)
        let owner = try host.replace(with: source)
        try host.deliverLatest()
        let event = try reviewEvent(source.value), target = source.reads + offset
        source.onRead = { if $0 == target { source.publish(stale) } }
        #expect(throws: AndroidUIHostError.revisionNotIncreasing) { try host.send(owner: owner, event: event) }
        #expect(source.events.isEmpty && host.pendingFrame == nil)
        host.close()
    }
}

@Test @MainActor func r2ReplacementDuringGetterCannotChangeSourceBinding() throws {
    let surface = ReviewSurface(), source = ReviewSource(try reviewSnapshot(1))
    let replacement = ReviewSource(try reviewSnapshot(1)), host = try reviewHost(surface)
    let owner = try host.replace(with: source)
    try host.deliverLatest()
    let event = try reviewEvent(source.value)
    var attempts = 0
    source.onRead = { _ in
        attempts += 1
        #expect(throws: AndroidUIHostError.busy) { try host.replace(with: replacement) }
    }
    try host.send(owner: owner, event: event)
    #expect(attempts == 2 && host.owner == owner && surface.owner == owner)
    #expect(source.events == [event] && replacement.events.isEmpty && replacement.callbacks.isEmpty)
    host.close()
}

import Foundation
import Testing
import MixerUI
import MixerAndroid

private enum R2ReviewError: Error { case retired, sink }

private func r2ReviewSnapshot(_ revision: UInt64) throws -> UIRenderSnapshot {
    var reconciler = UIReconciler()
    try reconciler.apply(Button("add", "Add", action: "save").document(revision: revision))
    return try reconciler.currentSnapshot()
}

private func r2ReviewEvent(_ snapshot: UIRenderSnapshot) throws -> UIEventEnvelope {
    UIEventEnvelope(revision: snapshot.document.revision,
        identity: try #require(snapshot.identity(for: "add")), event: .activate)
}

@MainActor private final class R2ReviewSource: AndroidUIPresentation {
    var value: UIRenderSnapshot
    var replayOnObserve = true
    var callback: (@MainActor (UIRenderSnapshot) -> Void)?
    var onRead: (@MainActor () -> Void)?
    var onSend: (@MainActor () throws -> Void)?
    var events: [UIEventEnvelope] = []
    var cancellations = 0
    init(_ value: UIRenderSnapshot) { self.value = value }
    var snapshot: UIRenderSnapshot {
        let captured = value
        onRead?()
        return captured
    }
    func observe(_ receive: @escaping @MainActor (UIRenderSnapshot) -> Void) -> @MainActor () -> Void {
        callback = receive
        if replayOnObserve { receive(value) }
        return { self.callback = nil; self.cancellations += 1 }
    }
    func publish(_ next: UIRenderSnapshot) { value = next; callback?(next) }
    func send(_ event: UIEventEnvelope) throws { events.append(event); try onSend?() }
}

@MainActor private final class R2ReviewSurface: AndroidUINativeSurface {
    let profile = AndroidUIProfile.measuredMultilineV2
    var capabilities = AndroidUICapabilities(kinds: Set(NodeKind.allCases),
        textFieldAxes: [.horizontal, .vertical], appearanceV2: true)
    var owner: UUID?
    var frames: [AndroidUIFrame] = []
    var retired: Set<UUID> = []
    func activate(owner: UUID) throws {
        guard self.owner == nil, !retired.contains(owner) else { throw R2ReviewError.retired }
        self.owner = owner
    }
    func install(_ frame: AndroidUIFrame) throws {
        guard owner == frame.owner, !retired.contains(frame.owner) else { throw R2ReviewError.retired }
        frames.append(frame)
    }
    func revoke(owner: UUID) {
        retired.insert(owner)
        if self.owner == owner { self.owner = nil }
    }
}

@MainActor private func r2ReviewHost(_ surface: R2ReviewSurface) throws -> AndroidUIHost {
    try AndroidUIHost(surface: surface, profile: surface.profile, appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(),
                      scheduleDelivery: {})
}

@Test @MainActor func r2ReviewReplacementGetterMustRetainNewerPublishedFrame() throws {
    for replay in [true, false] {
        let source = R2ReviewSource(try r2ReviewSnapshot(1)), surface = R2ReviewSurface()
        source.replayOnObserve = replay
        let host = try r2ReviewHost(surface), newer = try r2ReviewSnapshot(2)
        defer { host.close() }
        source.onRead = { source.onRead = nil; source.publish(newer) }
        let owner = try host.replace(with: source)
        #expect(host.owner == owner && surface.owner == owner)
        #expect(host.sourceFailure == nil, "a captured getter value is not a regressing publication")
        #expect(host.pendingFrame?.snapshot.document.revision == 2, "retain the valid newer publication")
        var delivered = false
        do { delivered = try host.deliverLatest() } catch { }
        #expect(delivered && surface.frames.last?.snapshot.document.revision == 2,
                "the newly bound screen must render without requiring revision 3")
        #expect(source.events.isEmpty)
        // Recovery control: a genuinely later revision recovers the poisoned host.
        source.publish(try r2ReviewSnapshot(3))
        #expect(try host.deliverLatest())
        #expect(surface.frames.last?.snapshot.document.revision == 3)
    }
}

@Test @MainActor func r2ReviewInvalidPublicationInsideReplacementGetterStaysRejected() throws {
    let source = R2ReviewSource(try r2ReviewSnapshot(2)), surface = R2ReviewSurface()
    let host = try r2ReviewHost(surface), stale = try r2ReviewSnapshot(1)
    defer { host.close() }
    source.onRead = { source.onRead = nil; source.publish(stale) }
    let owner = try host.replace(with: source)
    #expect(throws: AndroidUIHostError.revisionNotIncreasing) { try host.deliverLatest() }
    #expect(throws: AndroidUIHostError.revisionNotIncreasing) {
        try host.send(owner: owner, event: r2ReviewEvent(source.value))
    }
    #expect(surface.frames.isEmpty && source.events.isEmpty)
    source.publish(try r2ReviewSnapshot(3))
    #expect(try host.deliverLatest())
}

@Test @MainActor func r2ReviewReplacementAndDeliveryGettersRejectNestedOperations() throws {
    let source = R2ReviewSource(try r2ReviewSnapshot(1)), surface = R2ReviewSurface()
    let alternate = R2ReviewSource(try r2ReviewSnapshot(1)), host = try r2ReviewHost(surface)
    let event = try r2ReviewEvent(source.value)
    defer { host.close() }
    var calls = 0
    source.onRead = {
        calls += 1
        #expect(throws: AndroidUIHostError.busy) { try host.replace(with: alternate) }
        #expect(throws: AndroidUIHostError.busy) { try host.deliverLatest() }
        if let owner = host.owner {
            #expect(throws: AndroidUIHostError.busy) { try host.send(owner: owner, event: event) }
        }
    }
    let owner = try host.replace(with: source)
    #expect(try host.deliverLatest())
    #expect(calls == 2 && surface.frames.last?.owner == owner)
    #expect(source.events.isEmpty && alternate.callback == nil)
}

@Test @MainActor func r2ReviewIdenticalGetterReplayPreservesRepeatedValidEvents() throws {
    let source = R2ReviewSource(try r2ReviewSnapshot(1)), surface = R2ReviewSurface()
    let host = try r2ReviewHost(surface), event = try r2ReviewEvent(source.value)
    defer { host.close() }
    let owner = try host.replace(with: source)
    try host.deliverLatest()
    source.onRead = { source.publish(source.value) }
    try host.send(owner: owner, event: event)
    try host.send(owner: owner, event: event)
    #expect(source.events == [event, event] && host.pendingFrame == nil && host.sourceFailure == nil)
    #expect(surface.frames.count == 1)
}

@Test @MainActor func r2ReviewCurrentIdentityMustMatchEvenWithEqualDocument() throws {
    let source = R2ReviewSource(try r2ReviewSnapshot(2)), surface = R2ReviewSurface()
    let host = try r2ReviewHost(surface), event = try r2ReviewEvent(source.value)
    defer { host.close() }
    let owner = try host.replace(with: source)
    try host.deliverLatest()
    var reconciler = UIReconciler()
    try reconciler.apply(Text("add", "Previous kind").document(revision: 1))
    try reconciler.apply(source.value.document)
    let changed = try reconciler.currentSnapshot()
    #expect(changed.document == source.value.document && changed.identity(for: "add") != event.identity)
    // Deliberately unnotified source mutation challenges the final routing defense.
    source.onRead = { source.onRead = nil; source.value = changed }
    #expect(throws: UIRoutingError.staleIdentity) { try host.send(owner: owner, event: event) }
    #expect(source.events.isEmpty)
}

@Test @MainActor func r2ReviewSinkCloseAndThrowCannotReplayEffect() throws {
    let source = R2ReviewSource(try r2ReviewSnapshot(1)), surface = R2ReviewSurface()
    let host = try r2ReviewHost(surface), event = try r2ReviewEvent(source.value)
    let owner = try host.replace(with: source)
    try host.deliverLatest()
    source.onSend = { host.close(); throw R2ReviewError.sink }
    #expect(throws: R2ReviewError.sink) { try host.send(owner: owner, event: event) }
    #expect(throws: AndroidUIHostError.closed) { try host.deliverLatest() }
    #expect(source.events == [event] && source.cancellations == 1 && surface.owner == nil)
}

@Test @MainActor func r2ReviewCapabilitiesCannotWidenAfterHostNegotiation() throws {
    let source = R2ReviewSource(try r2ReviewSnapshot(1)), surface = R2ReviewSurface()
    surface.capabilities = AndroidUICapabilities(kinds: [.text], textFieldAxes: [.horizontal], appearanceV2: true)
    let host = try r2ReviewHost(surface)
    defer { host.close() }
    surface.capabilities = AndroidUICapabilities(kinds: Set(NodeKind.allCases),
        textFieldAxes: [.horizontal, .vertical], appearanceV2: true)
    try host.replace(with: source)
    #expect(throws: (any Error).self) { try host.deliverLatest() }
    #expect(surface.frames.isEmpty && host.pendingFrame == nil && source.events.isEmpty)
}

import Foundation
import Testing
import MixerUI
import MixerAndroid

private enum R3Failure: Error { case install }

private func r3Snapshot(_ revision: UInt64, textOnly: Bool = false) throws -> UIRenderSnapshot {
    var reconciler = UIReconciler()
    if textOnly {
        try reconciler.apply(Text("add", "Unsupported").document(revision: revision))
    } else {
        try reconciler.apply(Button("add", "Add", action: "save").document(revision: revision))
    }
    return try reconciler.currentSnapshot()
}

private func r3Event(_ snapshot: UIRenderSnapshot) throws -> UIEventEnvelope {
    UIEventEnvelope(revision: snapshot.document.revision,
        identity: try #require(snapshot.identity(for: "add")), event: .activate)
}

@MainActor private final class R3Source: AndroidUIPresentation {
    var value: UIRenderSnapshot
    var captureOverride: UIRenderSnapshot?
    var replay = true
    var callback: (@MainActor (UIRenderSnapshot) -> Void)?
    var onRead: (@MainActor () -> Void)?
    var events: [UIEventEnvelope] = []
    init(_ value: UIRenderSnapshot) { self.value = value }
    var snapshot: UIRenderSnapshot {
        let capture = captureOverride ?? value
        onRead?()
        return capture
    }
    func observe(_ receive: @escaping @MainActor (UIRenderSnapshot) -> Void) -> @MainActor () -> Void {
        callback = receive
        if replay { receive(value) }
        return { self.callback = nil }
    }
    func publish(_ value: UIRenderSnapshot) { self.value = value; callback?(value) }
    func send(_ event: UIEventEnvelope) throws { events.append(event) }
}

@MainActor private final class R3Surface: AndroidUINativeSurface {
    let profile = AndroidUIProfile.measuredMultilineV2
    let capabilities = AndroidUICapabilities(kinds: [.button], textFieldAxes: [.horizontal], appearanceV2: true)
    var owner: UUID?
    var frames: [AndroidUIFrame] = []
    var failInstall = false
    func activate(owner: UUID) throws { self.owner = owner }
    func install(_ frame: AndroidUIFrame) throws {
        guard !failInstall, owner == frame.owner else { throw R3Failure.install }
        frames.append(frame)
    }
    func revoke(owner: UUID) { if self.owner == owner { self.owner = nil } }
}

@MainActor private func r3Host(_ surface: R3Surface,
    schedule: @escaping @MainActor () -> Void = {}) throws -> AndroidUIHost {
    try AndroidUIHost(surface: surface, profile: surface.profile, appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(),
                      scheduleDelivery: schedule)
}

@Test @MainActor func r3BootstrapPublicationBurstKeepsLatestAndRejectsOldEvent() throws {
    for replay in [false, true] {
        let first = try r3Snapshot(1), second = try r3Snapshot(2), third = try r3Snapshot(3)
        let source = R3Source(first), surface = R3Surface()
        var wakes = 0
        let host = try r3Host(surface) { wakes += 1 }
        defer { host.close() }
        source.replay = replay
        source.onRead = {
            source.onRead = nil
            source.publish(second); source.publish(third); source.publish(third)
        }
        let owner = try host.replace(with: source)
        #expect(host.sourceFailure == nil && host.pendingFrame?.snapshot.document.revision == 3)
        #expect(wakes == 1 && source.events.isEmpty)
        #expect(try host.deliverLatest())
        #expect(surface.frames.map { $0.snapshot.document.revision } == [3])
        #expect(throws: (any Error).self) { try host.send(owner: owner, event: r3Event(first)) }
        let event = try r3Event(third)
        try host.send(owner: owner, event: event)
        #expect(source.events == [event])
    }
}

@Test @MainActor func r3ActualRegressionAfterNewerBootstrapPublicationRemainsFailure() throws {
    for replay in [false, true] {
        let source = R3Source(try r3Snapshot(1)), surface = R3Surface(), host = try r3Host(surface)
        defer { host.close() }
        source.replay = replay
        let second = try r3Snapshot(2), third = try r3Snapshot(3)
        source.onRead = {
            source.onRead = nil
            source.publish(third); source.publish(second)
        }
        let owner = try host.replace(with: source)
        #expect(throws: AndroidUIHostError.revisionNotIncreasing) { try host.deliverLatest() }
        #expect(host.pendingFrame == nil && surface.frames.isEmpty)
        source.publish(third)
        #expect(throws: AndroidUIHostError.revisionNotIncreasing) { try host.deliverLatest() }
        #expect(throws: AndroidUIHostError.revisionNotIncreasing) {
            try host.send(owner: owner, event: r3Event(third))
        }
        source.publish(try r3Snapshot(4))
        #expect(try host.deliverLatest())
        #expect(surface.frames.map { $0.snapshot.document.revision } == [4] && source.events.isEmpty)
    }
}

@Test @MainActor func r3InvalidCapabilityPublicationCannotBeHealedByCapturedValue() throws {
    let source = R3Source(try r3Snapshot(1)), surface = R3Surface(), host = try r3Host(surface)
    defer { host.close() }
    let second = try r3Snapshot(2), invalid = try r3Snapshot(3, textOnly: true)
    source.onRead = { source.onRead = nil; source.publish(second); source.publish(invalid) }
    try host.replace(with: source)
    #expect(host.sourceFailure != nil && host.pendingFrame == nil)
    #expect(throws: (any Error).self) { try host.deliverLatest() }
    #expect(surface.frames.isEmpty && source.events.isEmpty)
    source.publish(try r3Snapshot(4))
    #expect(try host.deliverLatest())
    #expect(surface.frames.last?.snapshot.document.revision == 4)
}

@Test @MainActor func r3UnjustifiedStaleGetterStillFailsClosed() throws {
    let source = R3Source(try r3Snapshot(2)), surface = R3Surface(), host = try r3Host(surface)
    defer { host.close() }
    // Deliberately violate the source contract without an intervening callback.
    source.captureOverride = try r3Snapshot(1)
    try host.replace(with: source)
    #expect(throws: AndroidUIHostError.revisionNotIncreasing) { try host.deliverLatest() }
    #expect(host.pendingFrame == nil && surface.frames.isEmpty && source.events.isEmpty)
}

@Test @MainActor func r3BootstrapWithoutPublicationStillValidatesCapture() throws {
    let source = R3Source(try r3Snapshot(1, textOnly: true)), surface = R3Surface()
    let host = try r3Host(surface)
    defer { host.close() }
    source.replay = false
    try host.replace(with: source)
    #expect(host.sourceFailure != nil && host.pendingFrame == nil)
    #expect(throws: (any Error).self) { try host.deliverLatest() }
    #expect(surface.frames.isEmpty && source.events.isEmpty)
}

@Test @MainActor func r3RetiredObserverCannotOvertakeNewOwnerBootstrap() throws {
    let old = R3Source(try r3Snapshot(1)), source = R3Source(try r3Snapshot(2))
    let surface = R3Surface(), host = try r3Host(surface)
    defer { host.close() }
    let oldOwner = try host.replace(with: old)
    try host.deliverLatest()
    let late = try #require(old.callback), obsolete = try r3Snapshot(99)
    source.replay = false
    source.onRead = { source.onRead = nil; late(obsolete) }
    let owner = try host.replace(with: source)
    #expect(owner != oldOwner && host.sourceFailure == nil)
    #expect(host.pendingFrame?.snapshot.document.revision == 2)
    #expect(try host.deliverLatest())
    #expect(surface.frames.last?.owner == owner && surface.frames.last?.snapshot.document.revision == 2)
    #expect(old.events.isEmpty && source.events.isEmpty)
}

@Test @MainActor func r3CloseAfterBootstrapPublicationCannotReturnLiveOwner() throws {
    let source = R3Source(try r3Snapshot(1)), surface = R3Surface(), host = try r3Host(surface)
    let second = try r3Snapshot(2)
    source.onRead = { source.onRead = nil; source.publish(second); host.close() }
    #expect(throws: AndroidUIHostError.closed) { try host.replace(with: source) }
    #expect(host.owner == nil && host.pendingFrame == nil && surface.owner == nil)
    #expect(throws: AndroidUIHostError.closed) { try host.deliverLatest() }
    #expect(surface.frames.isEmpty && source.events.isEmpty)
}

@Test @MainActor func r3RetryOfOvertakenBootstrapInstallsWithoutReplayingEffect() throws {
    let source = R3Source(try r3Snapshot(1)), surface = R3Surface(), host = try r3Host(surface)
    defer { host.close() }
    let second = try r3Snapshot(2)
    source.onRead = { source.onRead = nil; source.publish(second) }
    let owner = try host.replace(with: source)
    surface.failInstall = true
    #expect(throws: R3Failure.install) { try host.deliverLatest() }
    #expect(host.pendingFrame?.snapshot.document.revision == 2 && source.events.isEmpty)
    surface.failInstall = false
    #expect(try host.deliverLatest())
    let event = try r3Event(second)
    try host.send(owner: owner, event: event)
    #expect(try !host.deliverLatest())
    #expect(source.events == [event] && surface.frames.count == 1)
}

@Test @MainActor func r3NewerPublicationAfterInvalidBootstrapCallbackCanRecover() throws {
    let source = R3Source(try r3Snapshot(2)), surface = R3Surface(), host = try r3Host(surface)
    defer { host.close() }
    let stale = try r3Snapshot(1), third = try r3Snapshot(3)
    source.onRead = { source.onRead = nil; source.publish(stale); source.publish(third) }
    try host.replace(with: source)
    #expect(host.sourceFailure == nil && host.pendingFrame?.snapshot.document.revision == 3)
    #expect(try host.deliverLatest())
    #expect(surface.frames.last?.snapshot.document.revision == 3 && source.events.isEmpty)
}
