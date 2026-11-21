#if os(macOS) && MIXER_PRIVATE_FIELDLOG_EDITOR
import Foundation
@_spi(InstalledApplicationStorage) import MixerCapabilities
@_spi(PrivateFieldLogEditor) @_spi(GuestUIV1) @_spi(FeatureUIV3) import MixerGuest
import MixerUI

struct FieldLogEditorStorage: InstalledApplicationStorageServing {
    static let namespace = "fieldlog_editor"

    func get(_ arguments: KVGetArguments) async throws -> KVGetResponse {
        throw CapabilityFailure.permissionDenied
    }

    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        throw CapabilityFailure.permissionDenied
    }

    func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse {
        throw CapabilityFailure.permissionDenied
    }
}

/// Development-only headless renderer. The embedding captures its trusted
/// selection and revision in the commit closure, from the displayed title.
@_spi(PrivateFieldLogEditor)
@MainActor public final class FieldLogEditorPresenter {
    public typealias Capture = @MainActor @Sendable (String) throws -> InstalledGuestUICommitRead.Commit

    private struct PendingSave {
        let generation: UInt64
        let sequence: UInt64
        let revision: UInt64
        let title: String
        let commit: InstalledGuestUICommitRead.Commit
        var savingPresented = false

        func matches(_ event: InstalledGuestUICommitEvent) -> Bool {
            event.generation == generation && event.sequence == sequence && event.displayedRevision == revision
        }
    }

    nonisolated let identity = UUID()
    private let capture: Capture
    private var ownerID: UUID?
    private var exchange: GuestUIExchangeV1?
    private var router: UINativeActionRouter?
    private var rendered: UIRenderSnapshot?
    private var pending: PendingSave?
    private var lastEventResult: GuestUIEventResultV1?
    private let validator = FeatureDocumentV3(textValuePolicy: .standard).validator

    public init(capture: @escaping Capture) { self.capture = capture }
    public var snapshot: UIRenderSnapshot? { rendered }
    var eventResult: GuestUIEventResultV1? { lastEventResult }
    var exchangeSnapshot: GuestUIExchangeSnapshotV1? { exchange?.snapshot() }

    public func issue(_ envelope: UIEventEnvelope) throws -> IssuedUIAction {
        guard let router, exchange?.snapshot().stop == nil else { throw UIRoutingError.staleIdentity }
        return try router.route(envelope)
    }

    public func submit(_ issued: IssuedUIAction) -> GuestUIEventAdmissionV1 {
        guard let exchange, let rendered, exchange.snapshot().stop == nil else { return .closed }
        let generation = exchange.snapshot().generation
        guard (try? rendered.checkedEnvelope(for: issued)) != nil else { return .stale }
        guard issued.action.nodeID == "task.save" else {
            return exchange.offerFieldLogEditorAction(issued, generation: generation)
        }
        guard issued.action.actionID == "task.save", issued.action.event == .activate,
              let title = Self.field(in: rendered.document, id: "task.title")?.properties["value"]?.string,
              let responsible = Self.field(in: rendered.document, id: "task.responsible")?.properties["value"]?.string,
              responsible.isEmpty, Self.canSave(title), pending == nil else { return .invalid(.invalidValue) }
        guard let commit = try? capture(title) else { return .invalid(.invalidValue) }
        let admission = exchange.offerFieldLogEditorAction(issued, generation: generation)
        if case .accepted(let sequence) = admission {
            pending = PendingSave(generation: generation, sequence: sequence, revision: issued.action.revision,
                                  title: title, commit: commit)
        }
        return admission
    }

    private static func canSave(_ title: String) -> Bool {
        let bytes = title.utf8
        return (1...240).contains(bytes.count) && bytes.first != 32 && bytes.last != 32 &&
            bytes.allSatisfy { (32...126).contains($0) }
    }

    nonisolated var commitFacts: InstalledGuestUICommitFacts {
        let scope = FieldLogEditorStorage.namespace
        return InstalledGuestUICommitFacts(arguments: .init(namespace: scope, key: "task-save-facts"),
            nodeID: "task.save", actionID: "task.save",
            commitArguments: .init(namespace: scope, key: "task-save-commit", valueBase64: "AQ==")) { [weak self] event in
                guard let self else { throw CapabilityFailure.permissionDenied }
                return try await self.readFacts(event)
            }
    }

    private func readFacts(_ event: InstalledGuestUICommitEvent) async throws -> InstalledGuestUICommitRead {
        while event.isLive, let save = pending, save.matches(event) {
            if save.savingPresented {
                pending = nil
                return InstalledGuestUICommitRead(response: .init(found: true, valueBase64: "AQ=="), commit: save.commit)
            }
            // The scoped read may reach this actor before the renderer's wake.
            // The existing bridge deadline/cancellation owns this wait.
            try await Task.sleep(for: .milliseconds(2))
        }
        throw CapabilityFailure.permissionDenied
    }

    func claimOwner() throws -> FieldLogEditorPresentationOwner {
        guard ownerID == nil, exchange == nil else { throw coldStartError("fieldlog_editor_presenter_owned") }
        let owner = FieldLogEditorPresentationOwner(presenter: self)
        ownerID = owner.id
        lastEventResult = nil
        return owner
    }

    fileprivate func bindForStartup(_ exchange: GuestUIExchangeV1, owner: FieldLogEditorPresentationOwner) async throws -> any CapabilityObservedPresentation {
        guard ownerID == owner.id, self.exchange == nil else { throw coldStartError("presentation") }
        let reader = try exchange.deliveryWake.takeConsumer()
        let lifetime = CapabilityGuestUIPresentationLifetime(id: try .issue(), retirement: owner)
        let installation = try lifetime.installation()
        self.exchange = exchange
        lastEventResult = nil
        let task = Task { [weak self] in
            do {
                while try await reader.next() { self?.present(exchange) }
            } catch {
                exchange.recordProtocolFailure(.init(phase: .presentation, code: .presentationInvariant))
            }
        }
        guard lifetime.attach(task, exchange: exchange) else {
            exchange.stop(.closed)
            await task.value
            _ = await installation.finish()
            throw coldStartError("presentation")
        }
        return installation
    }

    private func present(_ exchange: GuestUIExchangeV1) {
        guard self.exchange === exchange, let claim = exchange.claimPresentation(generation: exchange.snapshot().generation) else { return }
        guard claim.stop == nil else {
            _ = exchange.completePresentation(claim, snapshot: nil)
            lastEventResult = claim.eventResult ?? lastEventResult
            return
        }
        let deliveredSave: PendingSave? = pending.flatMap { save in
            guard let result = claim.eventResult, result.sequence == save.sequence,
                  result.generation == save.generation, result.outcome == .delivered else { return nil }
            return save
        }
        guard let document = claim.frame?.document.document else {
            if deliveredSave != nil {
                reject(claim, on: exchange)
                return
            }
            if !exchange.completeUnchangedFieldLogEditorPresentation(claim) {
                _ = exchange.completePresentation(claim, snapshot: nil)
            }
            lastEventResult = claim.eventResult ?? lastEventResult
            return
        }
        do {
            if let save = deliveredSave {
                guard document.revision == save.revision + 1,
                      let title = Self.field(in: document, id: "task.title"),
                      title.properties["value"]?.string?.utf8.elementsEqual(save.title.utf8) == true,
                      title.properties["disabled"] == .bool(true),
                      let button = Self.field(in: document, id: "task.save"),
                      button.properties["label"]?.string == "Saving…", button.properties["disabled"] == .bool(true) else {
                    throw coldStartError("fieldlog_editor_saving_frame")
                }
            }
            if let router { try router.update(document) }
            else { router = try UINativeActionRouter(document: document, validator: validator) }
            guard let router else { throw coldStartError("presentation") }
            let snapshot = try router.snapshot
            guard let ticket = exchange.completePresentation(claim, snapshot: snapshot),
                  exchange.observePresentation(ticket) else { return }
            rendered = snapshot
            if deliveredSave != nil { pending?.savingPresented = true }
            lastEventResult = claim.eventResult ?? lastEventResult
        } catch {
            reject(claim, on: exchange)
        }
    }

    private func reject(_ claim: GuestUIPresentationClaimV1, on exchange: GuestUIExchangeV1) {
        // Stop first so completing this claim leaves the terminal event for the next delivery.
        exchange.recordProtocolFailure(.init(phase: .presentation, code: .presentationInvariant))
        _ = exchange.completePresentation(claim, snapshot: nil)
    }

    private static func field(in document: UIDocument, id: String) -> UINode? {
        var nodes = [document.root]
        while let node = nodes.popLast() {
            if node.id == id { return node }
            nodes.append(contentsOf: node.children)
        }
        return nil
    }

    fileprivate func isUnbound(owner id: UUID) -> Bool { ownerID == id && exchange == nil }

    fileprivate func release(owner id: UUID) {
        if isUnbound(owner: id) { ownerID = nil }
    }

    fileprivate func retirePresentation(owner id: UUID) -> Bool {
        guard ownerID == id else { return false }
        guard exchange?.snapshot().stop != nil else { return exchange == nil }
        pending = nil
        rendered = nil
        router = nil
        exchange = nil
        return true
    }
}

/// One owner spans open, fallback attempts, and final close. The presenter is
/// reusable after this owner's observation and store have retired.
final class FieldLogEditorPresentationOwner: CapabilityColdStartPresentation, CapabilityPresentationRetirement {
    let id = UUID()
    private let presenter: FieldLogEditorPresenter

    fileprivate init(presenter: FieldLogEditorPresenter) { self.presenter = presenter }

    func bindForStartup(_ exchange: GuestUIExchangeV1) async throws -> any CapabilityObservedPresentation {
        try await presenter.bindForStartup(exchange, owner: self)
    }

    func requestFinalClose(_ cause: CapabilityAttemptLocalStop) {
        // The stock observation stops this exchange and joins its consumer.
    }

    func finishForClose() async -> Bool { await presenter.isUnbound(owner: id) }
    func retireEmptyPresentation() async -> Bool { await presenter.retirePresentation(owner: id) }
    func release() async { await presenter.release(owner: id) }
}
#endif
