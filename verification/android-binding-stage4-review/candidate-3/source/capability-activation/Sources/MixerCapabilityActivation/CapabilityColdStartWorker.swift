import Foundation
@_spi(GuestUIV1) import MixerGuest

/// All durable/adapter work is reached from this private non-MainActor owner.
/// The reservation's retained store worker reaches notification consumers only
/// through weak boxes; it cannot retain this actor or a concrete attempt.
actor CapabilityColdStartWorker {
    private let configuration: CapabilityRecoveryConfiguration
    private var installed: InstalledMaterial?
    private let environment: CapabilityRecoveryEnvironment
    private var admission: CapabilityRecoveryStoreAdmission?
    private let control: CapabilityColdStartControl
    private let guestUIBinding: CapabilityGuestUIPresentationBinding?
    private var store: CapabilityRecoveryStore?
    private var active: CapabilityConsumedStartup?
    private var signals: CapabilityAttemptSignals?
    private var milestones: Set<String> = []
    private var earnedHealth = false
    init(configuration: CapabilityRecoveryConfiguration, installed: InstalledMaterial,
         environment: CapabilityRecoveryEnvironment, admission: CapabilityRecoveryStoreAdmission,
         control: CapabilityColdStartControl, guestUIBinding: CapabilityGuestUIPresentationBinding? = nil) {
        self.configuration = configuration; self.installed = installed
        self.environment = environment; self.admission = admission; self.control = control; self.guestUIBinding = guestUIBinding
    }
    func open(_ op: CapabilityColdStartOperation) async throws {
        try control.requireCurrent(op)
        guard let installed, let admission else { throw coldStartError("closed") }
        self.admission = nil // One-shot input belongs to this open frame now.
        let opened = try await CapabilityRecoveryStore.open(admission: admission, installed: installed,
            configuration: configuration, environment: environment, guestUI: guestUIBinding != nil)
        store = opened
        guard control.installStore(opened) else { throw coldStartError("closed") }
        try control.requireCurrent(op)
    }
    private func currentStore(_ op: CapabilityColdStartOperation) throws -> CapabilityRecoveryStore {
        try control.requireCurrent(op)
        guard let store else { throw coldStartError("closed") }; return store
    }
    func begin(_ manifest: Data, _ assignment: Data, _ op: CapabilityColdStartOperation) async throws {
        let store = try currentStore(op)
        try await store.beginDownload(signedManifest: manifest, signedAssignment: assignment)
        try control.requireCurrent(op)
    }
    func offset(_ op: CapabilityColdStartOperation) async throws -> UInt64 {
        let result = try await currentStore(op).downloadOffset()
        try control.requireCurrent(op); return result
    }
    func append(_ bytes: Data, _ offset: UInt64, _ op: CapabilityColdStartOperation) async throws {
        try await currentStore(op).appendDownload(bytes, atOffset: offset)
        try control.requireCurrent(op)
    }
    func finishDownload(_ op: CapabilityColdStartOperation) async throws {
        try await currentStore(op).finishDownload()
        try control.requireCurrent(op)
    }
    func cancelDownload(_ op: CapabilityColdStartOperation) async throws {
        try await currentStore(op).cancelDownload()
        try control.requireCurrent(op)
    }
    private enum StartupStep {
        case live
        case fallback(CapabilityStartupSelection?, CapabilityConcreteRetirement?, CapabilityColdStartObservation?)
        case recovery(CapabilityColdStartObservation?)
    }
    func start(_ op: CapabilityColdStartOperation) async throws {
        do {
            let store = try currentStore(op)
            var selection = try await store.prepareStartupSelection()
            try control.requireCurrent(op)
            guard selection != nil else { control.setPhase(.nativeFallback); return }
            while let next = selection {
                selection = nil // The one-shot input moves into the inner helper.
                let step = try await runSelectionOwned(next, op)
                switch step {
                case .live: return
                case .recovery(let observation):
                    if let observation { try await finishObservation(observation) }
                    return
                case .fallback(let fallback, let retirement, let observation):
                    // No old concrete/group/session/construction/consumed alias
                    // survives runSelectionOwned's return before either join.
                    if let observation { try await finishObservation(observation) }
                    try control.requireCurrent(op)
                    if let retirement {
                        control.setRetirementWait(retirement)
                        let retired = await retirement.wait()
                        control.setRetirementWait(nil)
                        guard retired else { throw coldStartError("retirement_stopped") }
                    }
                    try control.requireCurrent(op)
                    if let fallback { selection = fallback }
                    else { control.setPhase(.nativeFallback); return }
                }
            }
        } catch {
            // Final close owns durable terminal persistence after this ordinary
            // tail. Keep only its consumed metadata, never concrete aliases.
            let observation = control.isClosed ? nil : abandonOwned()
            if let observation { try await finishObservation(observation) }
            throw error
        }
    }
    private func runSelectionOwned(_ selection: CapabilityStartupSelection,
                                   _ op: CapabilityColdStartOperation) async throws -> StartupStep {
        let store = try currentStore(op)
        guard let installed else { throw coldStartError("closed") }
        let exchange = try guestUIBinding.map { _ in try GuestUIExchangeV1(generation: selection.generation) }
        let signals = CapabilityAttemptSignals(generation: selection.generation, guestUI: exchange)
        try control.installObservation(signals, worker: self, candidate: selection.candidateID,
            launch: selection.launchID, op: op)
        var consumed: CapabilityConsumedStartup?
        do {
            if let guestUIBinding, let exchange {
                let presentation = try await guestUIBinding.bind(exchange)
                guard control.installPresentationLifetime(presentation, signals: signals, op: op) else {
                    exchange.stop(.closed)
                    let result = await presentation.finish() // Close raced the MainActor bind.
                    if !result.isRetired { control.reservation.quarantine() }
                    throw coldStartError("closed")
                }
                try control.requireCurrent(op)
            }
            let input = try await store.consume(selection, signals: signals)
            consumed = input; active = input; self.signals = signals; milestones.removeAll(); earnedHealth = false
            control.markConsumed(true)
            try control.requireCurrent(op)
            let attempt = try CapabilityConcreteAttempt(consumed: input, installed: installed,
                reservation: control.reservation, signals: signals)
            try control.installConcrete(attempt, signals: signals) // Before any construct await.
            try await attempt.construct()
            try requireAttempt(op, signals)
            if exchange != nil { try await attempt.startupGuestUI() }
            else { _ = try await attempt.startup() } // Effects remain disabled.
            try requireAttempt(op, signals)
            try await store.recordEffectsIntent(input, signals: signals)
            try requireAttempt(op, signals)
            try await attempt.enableEffects() // Original selected absolute cutoff.
            try requireAttempt(op, signals)
            try await store.confirmEffectsEnabled(input, signals: signals)
            try requireAttempt(op, signals)
            if let exchange {
                try exchange.confirmEffectsEnabled(generation: input.generation)
                try await store.reportMilestone(input, id: "feature_started")
                milestones.insert("feature_started")
                try requireAttempt(op, signals)
            }
            try control.armTimer(seconds: configuration.observationSeconds, signals: signals)
            control.setPhase(.provisionalGuest)
            return .live
        } catch CapabilitySelectionConsumeError.rejected {
            control.markConsumed(false); active = nil; self.signals = nil
            return .fallback(nil, nil, control.detachObservation())
        } catch CapabilitySelectionConsumeError.cleanupRequiresReopen {
            control.setPhase(.recoveryRequired); control.markConsumed(false); active = nil; self.signals = nil
            return .recovery(control.detachObservation())
        } catch {
            if control.isClosed { throw error }
            if !signals.snapshot.stopped { signals.requestStop(.closed) }
            let retirement = control.stopConcrete()
            control.setPhase(.stopping)
            guard let consumed else {
                control.setPhase(.recoveryRequired)
                return .recovery(control.detachObservation())
            }
            do {
                let disposition = try await store.failAndPrepareFallback(consumed, signals: signals,
                    allowFallback: !control.isClosed)
                active = nil; self.signals = nil; control.markConsumed(false)
                let observation = control.detachObservation()
                switch disposition {
                case .selection(let next): return .fallback(next, retirement, observation)
                case .nativeFallback: return .fallback(nil, retirement, observation)
                case .recoveryRequired: control.setPhase(.recoveryRequired); return .recovery(observation)
                }
            } catch {
                active = nil; self.signals = nil; control.markConsumed(false)
                control.setPhase(.recoveryRequired)
                return .recovery(control.detachObservation())
            }
        }
    }
    private func requireAttempt(_ op: CapabilityColdStartOperation, _ signals: CapabilityAttemptSignals) throws {
        try control.requireCurrent(op)
        guard !signals.snapshot.stopped else { throw coldStartError("terminal") }
    }
    private func finishObservation(_ observation: CapabilityColdStartObservation) async throws {
        if let result = await observation.finish(), !result.isRetired {
            control.reservation.quarantine()
            throw coldStartError("presentation_join")
        }
    }
    /// Returns before the caller joins timer/consumer continuations. All concrete
    /// aliases and this actor's unique old consumed payload leave first.
    private func abandonOwned() -> CapabilityColdStartObservation? {
        _ = control.stopConcrete()
        active = nil; signals = nil; control.markConsumed(false); milestones.removeAll()
        control.setPhase(.recoveryRequired)
        return control.detachObservation()
    }
    func reportMilestone(_ id: String, _ op: CapabilityColdStartOperation) async throws {
        let observation = try await reportMilestoneOwned(id, op)
        if let observation { try await finishObservation(observation) }
    }
    private func reportMilestoneOwned(_ id: String, _ op: CapabilityColdStartOperation) async throws -> CapabilityColdStartObservation? {
        let store = try currentStore(op)
        guard let active, let signals else { throw coldStartError("not_observing") }
        guard configuration.requiredMilestones.contains(id) else { throw coldStartError("milestone") }
        try requireAttempt(op, signals)
        try await store.reportMilestone(active, id: id)
        milestones.insert(id)
        try control.requireCurrent(op)
        return await reconcileOwned(fromConsumer: false)
    }
    nonisolated static func handleNotificationOwned(_ box: CapabilityColdStartWeakWorker, generation: UInt64) async {
        guard let worker = box.load() else { return }
        await worker.notification(generation)
        // Strong worker reference ends with this inner function, before next().
    }
    private func notification(_ generation: UInt64) async {
        guard control.beginNotification(generation) else { return }
        defer { control.finishNotification() }
        _ = await reconcileOwned(fromConsumer: true)
    }
    private func reconcileOwned(fromConsumer: Bool) async -> CapabilityColdStartObservation? {
        control.clearPendingWake()
        guard !control.isClosed, let active, let signals, let store else { return nil }
        if let exchange = signals.guestUI, !signals.snapshot.stopped,
           let receipt = exchange.snapshot().pendingPresentationReceipt {
            do {
                try await store.reportMilestone(active, id: "first_screen")
                milestones.insert("first_screen")
                exchange.consumeObservedPresentation(generation: receipt.generation, frameSerial: receipt.frameSerial)
            } catch {
                if !signals.snapshot.stopped { signals.requestStop(.closed) }
            }
        }
        if !signals.snapshot.stopped, !earnedHealth, control.timerFired,
           configuration.requiredMilestones.isSubset(of: milestones) {
            do {
                let healthy = try await store.commitHealth(active, signals: signals)
                if healthy && !signals.snapshot.stopped && !control.isClosed {
                    earnedHealth = true; control.setPhase(.healthyGuest)
                }
            } catch {
                if !signals.snapshot.stopped { signals.requestStop(.closed) }
            }
        }
        guard signals.snapshot.stopped, !control.isClosed else { return nil }
        _ = control.stopConcrete()
        control.setPhase(.recoveryRequired)
        do { _ = try await store.failAndPrepareFallback(active, signals: signals, allowFallback: false) }
        catch { /* Active linkage remains durable/poisoned; never claim health. */ }
        self.active = nil; self.signals = nil; control.markConsumed(false); milestones.removeAll()
        if fromConsumer { control.endObservationFromConsumer(); return nil }
        return control.detachObservation()
    }
    func closeStore() async -> CapabilityRecoverySnapshot {
        admission = nil // An opening-admission failure never claimed a store.
        if let store {
            if let active, let signals, !store.snapshot.requiresReopen {
                do { _ = try await store.failAndPrepareFallback(active, signals: signals, allowFallback: false) }
                catch { /* Preserve an actual/uncertain attempt for cold recovery. */ }
            }
            active = nil; signals = nil; installed = nil; milestones.removeAll(); control.markConsumed(false)
            store.requestStop(); await store.close()
            let snapshot = store.snapshot
            self.store = nil; return snapshot
        }
        installed = nil; active = nil; signals = nil; control.markConsumed(false)
        return control.recoverySnapshot
    }
}
