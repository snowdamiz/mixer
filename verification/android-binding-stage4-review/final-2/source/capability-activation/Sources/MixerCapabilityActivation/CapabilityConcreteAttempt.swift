import Foundation
import Dispatch
import MixerCapabilities
@_spi(CapabilityLifecycle) import MixerExperimentalCapabilityRuntime
@_spi(GuestUIV1) import MixerExperimentalCapabilityRuntime
@_spi(GuestUIV1) import MixerGuest
import MixerUpdates

/// Private concrete owner, never an evidence ingress or public execution API.
/// Initialization reserves its adapter obligation before any I/O/actor work.
/// The coordinator must store this object before calling construct(). Neither
/// this object nor its resources are retained by reservation.adapterOwner.
final class CapabilityConcreteAttempt: Sendable {
    private let control: CapabilityConcreteControl
    private let setup: CapabilityConcreteSetup
    let retirement: CapabilityConcreteRetirement
    init(consumed: CapabilityConsumedStartup, installed: InstalledMaterial,
         reservation: CapabilityAttemptReservation, signals: CapabilityAttemptSignals) throws {
        guard consumed.generation == signals.generation else { throw concreteAttemptError("generation") }
        let obligation = try reservation.reserveAdapterGroup()
        let retirement = CapabilityConcreteRetirement(obligation: obligation)
        let control = CapabilityConcreteControl(consumed: consumed, installed: installed, signals: signals, retirement: retirement)
        self.retirement = retirement; self.control = control; setup = CapabilityConcreteSetup(control: control)
    }
    func construct() async throws {
        try control.beginConstruction() // A duplicate call cannot stop the first.
        do {
            try await withTaskCancellationHandler {
                try await setup.constructOwned()
                try control.requireOpen(deadline: true)
            } onCancel: { control.stop(.cancelled) }
            try control.constructionDidReturn()
            retirement.setupDidReturn()
        } catch {
            control.stop(nil)
            // The helper's input/KV/group/create frame has returned. Local
            // resource aliases in stop() also return before this logical tail.
            retirement.setupDidReturn(); throw error
        }
    }
    func startup() async throws -> ExperimentalCapabilityInvocation {
        try control.beginMethod()
        do {
            let result = try await withTaskCancellationHandler {
                try await Self.startupOwned(control)
            } onCancel: { control.stop(.cancelled) }
            control.methodDidReturn(); return result
        } catch { control.stop(nil); control.methodDidReturn(); throw error }
    }
    func startupGuestUI() async throws {
        guard control.signals.guestUI != nil else { throw concreteAttemptError("installed_mode") }
        try control.beginMethod()
        do {
            try await withTaskCancellationHandler {
                try await Self.startupGuestUIOwned(control)
            } onCancel: { control.stop(.cancelled) }
            control.methodDidReturn()
        } catch { control.stop(nil); control.methodDidReturn(); throw error }
    }
    func enableEffects() async throws {
        try control.beginMethod()
        do {
            try await withTaskCancellationHandler {
                try await Self.enableOwned(control)
            } onCancel: { control.stop(.cancelled) }
            control.methodDidReturn()
        } catch { control.stop(nil); control.methodDidReturn(); throw error }
    }
    /// Internal development of the eventual facade uses this fixed export call;
    /// it grants no selection/evidence/health authority and accepts no service.
    func invoke(_ export: String) async throws -> ExperimentalCapabilityInvocation {
        guard !export.isEmpty, export.utf8.prefix(4097).count <= 4096 else { throw concreteAttemptError("export") }
        try control.beginMethod()
        do {
            let result = try await withTaskCancellationHandler {
                try await Self.invokeOwned(control, export: export)
            } onCancel: { control.stop(.cancelled) }
            control.methodDidReturn(); return result
        } catch { control.stop(nil); control.methodDidReturn(); throw error }
    }
    @discardableResult func stop(cause: CapabilityAttemptLocalStop = .closed) -> CapabilityConcreteRetirement {
        control.stop(cause); return retirement
    }
    deinit { control.stop(.closed) }

    // Only the inner frames retain a session across its async method. They
    // return before methodDidReturn may retire the outer adapter obligation.
    private static func startupOwned(_ c: CapabilityConcreteControl) async throws -> ExperimentalCapabilityInvocation {
        try c.requireOpen(deadline: true)
        let session = try c.sessionForMethod()
        let result = try await session.startup()
        try c.requireOpen(deadline: true); return result
    }
    private static func enableOwned(_ c: CapabilityConcreteControl) async throws {
        try c.requireOpen(deadline: true)
        let session = try c.sessionForMethod()
        try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: c.cutoff)
        try c.requireOpen(deadline: true)
    }
    private static func startupGuestUIOwned(_ c: CapabilityConcreteControl) async throws {
        try c.requireOpen(deadline: true)
        let session = try c.sessionForMethod()
        try await session.startupGuestUIV1()
        try c.requireOpen(deadline: true)
    }
    private static func invokeOwned(_ c: CapabilityConcreteControl, export: String) async throws -> ExperimentalCapabilityInvocation {
        try c.requireOpen(deadline: false)
        let session = try c.sessionForMethod()
        let result = try await session.invoke(export)
        try c.requireOpen(deadline: false); return result
    }
}

private final class CapabilityConcreteControl: @unchecked Sendable {
    struct Input: Sendable { let consumed: CapabilityConsumedStartup; let installed: InstalledMaterial }
    private struct State {
        var input: Input?
        var invokedConstruction = false
        var startedConstruction = false
        var constructionReady = false
        var stopped = false
        var methodBusy = false
        var group: OwnedCapabilityAdapterGroup?
        var construction: ExperimentalCapabilityConstruction?
        var session: ExperimentalCapabilitySession?
    }
    private struct StoppedResources {
        let input: Input?
        let group: OwnedCapabilityAdapterGroup?
        let construction: ExperimentalCapabilityConstruction?
        let session: ExperimentalCapabilitySession?
        let unusedSetup: Bool
    }
    private let lock = NSLock()
    private var state: State
    let signals: CapabilityAttemptSignals
    let retirement: CapabilityConcreteRetirement
    let cutoff: UInt64
    init(consumed: CapabilityConsumedStartup, installed: InstalledMaterial,
         signals: CapabilityAttemptSignals, retirement: CapabilityConcreteRetirement) {
        state = State(input: Input(consumed: consumed, installed: installed))
        self.signals = signals; self.retirement = retirement; cutoff = consumed.startupCutoffUptimeNanoseconds
    }
    func beginConstruction() throws {
        try locked { s in
            guard !s.invokedConstruction else { throw concreteAttemptError("construction_consumed") }
            s.invokedConstruction = true
            guard !s.stopped else { throw concreteAttemptError("stopped") }
            s.startedConstruction = true
        }
    }
    func takeInput() throws -> Input {
        try locked { s in
            guard !s.stopped, let input = s.input else { throw concreteAttemptError("stopped") }
            s.input = nil; return input
        }
    }
    func constructionDidReturn() throws {
        try locked { s in
            guard !s.stopped, !signals.snapshot.stopped, s.session != nil else { throw concreteAttemptError("stopped") }
            s.constructionReady = true
        }
    }
    func installGroup(_ group: OwnedCapabilityAdapterGroup) -> Bool {
        locked { s in guard !s.stopped else { return false }; s.group = group; return true }
    }
    func installConstruction(_ construction: ExperimentalCapabilityConstruction) -> Bool {
        locked { s in guard !s.stopped else { return false }; s.construction = construction; return true }
    }
    func installSession(_ session: ExperimentalCapabilitySession) -> Bool {
        locked { s in guard !s.stopped else { return false }; s.session = session; return true }
    }
    func beginMethod() throws {
        try locked { s in
            guard !s.stopped, !signals.snapshot.stopped, s.constructionReady, s.session != nil else { throw concreteAttemptError("stopped") }
            guard !s.methodBusy else { throw concreteAttemptError("busy") }
            try retirement.beginMethod(); s.methodBusy = true
        }
    }
    func methodDidReturn() {
        locked { $0.methodBusy = false }; retirement.methodDidReturn()
    }
    func sessionForMethod() throws -> ExperimentalCapabilitySession {
        try locked { s in guard !s.stopped, let session = s.session else { throw concreteAttemptError("stopped") }; return session }
    }
    func requireOpen(deadline: Bool) throws {
        guard !locked({ $0.stopped }), !signals.snapshot.stopped else { throw concreteAttemptError("stopped") }
        if deadline && DispatchTime.now().uptimeNanoseconds >= cutoff {
            signals.requestStop(.deadline); throw concreteAttemptError("deadline")
        }
        try Task.checkCancellation()
    }
    func stop(_ cause: CapabilityAttemptLocalStop?) {
        if let cause { signals.requestStop(cause) } // Before any bridge cancellation.
        let unused = stopOwned()
        if unused { retirement.setupDidReturn() }
    }
    // Resource destruction and all SDK calls occur outside the control lock.
    // This inner frame returns before an unused setup or method can retire.
    private func stopOwned() -> Bool {
        let resources = locked { s in
            let resources = StoppedResources(input: s.input, group: s.group, construction: s.construction,
                session: s.session, unusedSetup: !s.startedConstruction)
            s.stopped = true; s.input = nil; s.group = nil; s.construction = nil; s.session = nil
            return resources
        }
        resources.construction?.cancel(); resources.session?.close(); resources.group?.closeIfUntransferred()
        withExtendedLifetime(resources.input) {}
        return resources.unusedSetup
    }
    private func locked<T>(_ body: (inout State) throws -> T) rethrows -> T {
        lock.lock(); defer { lock.unlock() }; return try body(&state)
    }
}

/// No Task, dispatch job or terminal consumer is created here. Synchronous
/// filesystem adapter initialization runs only on this private non-MainActor.
private actor CapabilityConcreteSetup {
    private let control: CapabilityConcreteControl
    init(control: CapabilityConcreteControl) { self.control = control }
    func constructOwned() async throws {
        let input = try control.takeInput()
        var storage: AppPrivateKeyValueStore?
        var group: OwnedCapabilityAdapterGroup?
        do {
            try control.requireOpen(deadline: true)
            if let policy = input.consumed.policy.storage {
                storage = try AppPrivateKeyValueStore(directory: input.installed.privateContainer.appendingPathComponent(policy.directoryComponent, isDirectory: true),
                    namespaces: policy.namespaces, maximumTotalBytes: policy.maximumTotalBytes, maximumEntries: policy.maximumEntries)
            }
            try control.requireOpen(deadline: true)
            let http = try input.consumed.policy.http.map { try URLSessionHTTPTransport(maximumConcurrentRequests: Int($0.maximumConcurrentRequests)) }
            control.retirement.expectGroup()
            let createdGroup = OwnedCapabilityAdapterGroup(http: http, storage: storage,
                terminal: control.signals, retirement: control.retirement)
            group = createdGroup
            guard control.installGroup(createdGroup) else { createdGroup.closeIfUntransferred(); throw concreteAttemptError("stopped") }
            try control.requireOpen(deadline: true)
            let construction: ExperimentalCapabilityConstruction
            if let exchange = control.signals.guestUI {
                construction = try ExperimentalCapabilitySession.prepareOwnedGuestUIV1(module: input.consumed.module,
                    configuration: input.consumed.policy.native, policy: input.consumed.policy.policy,
                    adapterGroup: createdGroup, exchange: exchange)
            } else {
                construction = try ExperimentalCapabilitySession.prepareOwned(module: input.consumed.module,
                    startupExport: input.consumed.startupExport, configuration: input.consumed.policy.native,
                    policy: input.consumed.policy.policy, adapterGroup: createdGroup)
            }
            guard control.installConstruction(construction) else { construction.cancel(); throw concreteAttemptError("stopped") }
            let session = try await construction.create()
            guard control.installSession(session) else { session.close(); throw concreteAttemptError("stopped") }
            try control.requireOpen(deadline: true)
        } catch {
            if let group { group.closeIfUntransferred() }
            else if let storage { await storage.close() } // Before group, no cleanup Task exists.
            throw error
        }
    }
}

func concreteAttemptError(_ code: String) -> UpdateError {
    UpdateError("capability.concrete.\(code)", "Capability concrete attempt rejected")
}
