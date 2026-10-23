// REVIEW-ONLY DERIVED SOURCE. Injected into a copied bridge target, never into
// production. Gates delay observation/scheduling; they grant no adapter authority.
import Foundation
import CMixerVMCapability

final class ReviewAsyncGate: @unchecked Sendable {
    private let lock = NSLock()
    private var opened = false
    private var arrivals = 0
    private var waiters: [CheckedContinuation<Void, Never>] = []
    var entered: Int { lock.lock(); defer { lock.unlock() }; return arrivals }
    func hold() async {
        await withCheckedContinuation { continuation in
            lock.lock(); arrivals += 1
            // A defective relaunch cannot turn the test seam into an unbounded
            // queue. Extra arrivals resume and the arrival assertion still fails.
            let resume = opened || waiters.count >= 16
            if !resume { waiters.append(continuation) }
            lock.unlock()
            if resume { continuation.resume() }
        }
    }
    func open() {
        lock.lock(); opened = true
        let pending = waiters; waiters.removeAll()
        lock.unlock()
        for continuation in pending { continuation.resume() }
    }
}

final class ReviewSyncGate: @unchecked Sendable {
    private let condition = NSCondition()
    private var opened = false
    private var arrivals = 0
    private var escaped = false
    var entered: Int { condition.lock(); defer { condition.unlock() }; return arrivals }
    var timedOut: Bool { condition.lock(); defer { condition.unlock() }; return escaped }
    func hold() {
        condition.lock(); arrivals += 1
        // Date is only a test-hang escape. It never supplies request authority.
        let escape = Date().addingTimeInterval(6)
        while !opened {
            if !condition.wait(until: escape) { escaped = true; break }
        }
        condition.unlock()
    }
    func open() { condition.lock(); opened = true; condition.broadcast(); condition.unlock() }
}

private final class ReviewBox<Value>: @unchecked Sendable {
    private let lock = NSLock()
    private var value: Value
    init(_ value: Value) { self.value = value }
    func use<Result>(_ body: (inout Value) -> Result) -> Result {
        lock.lock(); defer { lock.unlock() }; return body(&value)
    }
}

enum ReviewBridgeControls {
    enum StartupFault { case wrongABI, invalidI32 }
    enum CreateFault { case wrongABI, successZeroHandle, publishedErrorHandle }
    struct Options {
        var workerStart: ReviewAsyncGate?
        var acceptancePublish: ReviewAsyncGate?
        var reservedID: ReviewAsyncGate?
        var envelopeResume: ReviewSyncGate?
        var afterDrain: ReviewSyncGate?
        var afterDrainCount = 8
        var expireScans = 0
        var lateTake: ReviewSyncGate?
        var beforeWake: ReviewSyncGate?
        var beforeRemaining: ReviewSyncGate?
        var remainingOrdinal = 1
        var holdDelivery = false
        var holdExit = false
        var startupFault: StartupFault?
        var createFault: CreateFault?
        var emptyTakenPayload = false
    }
    private struct Delivery {
        let owner: NativeExitOwner
        let ticket: NativeTicket
        let bytes: Data
    }
    private struct Exit {
        let owner: NativeExitOwner
        let ticket: NativeTicket
    }
    private struct State {
        var options = Options()
        var workerStarts = 0
        var acceptancePublishes = 0
        var scans = 0
        var closeSignals = 0
        var drainHeld = false
        var takeHeld = false
        var wakeHeld = false
        var nativeCallsTaken = 0
        var remainingCalls = 0
        var startupFaultUsed = false
        var createFaultUsed = false
        var emptyTakenPayloadUsed = false
        var delivery: Delivery?
        var exit: Exit?
    }
    private static let state = ReviewBox(State())
    static func install(_ options: Options) {
        resetAndRelease()
        state.use { $0.options = options }
    }
    static func resetAndRelease() {
        let old = state.use { state -> State in let old = state; state = State(); return old }
        old.options.workerStart?.open(); old.options.acceptancePublish?.open()
        old.options.reservedID?.open(); old.options.envelopeResume?.open()
        old.options.afterDrain?.open(); old.options.lateTake?.open()
        old.options.beforeWake?.open(); old.options.beforeRemaining?.open()
        if let delivery = old.delivery { delivery.owner.delivery(delivery.bytes, ticket: delivery.ticket) }
        if let exit = old.exit { exit.owner.exited(exit.ticket) }
    }
    static var starts: Int { state.use { $0.workerStarts } }
    static var scans: Int { state.use { $0.scans } }
    static var closeSignals: Int { state.use { $0.closeSignals } }
    static var holdingDelivery: Bool { state.use { $0.delivery != nil } }
    static var holdingExit: Bool { state.use { $0.exit != nil } }
    static func beforeWorker() async {
        let gate = state.use { state -> ReviewAsyncGate? in state.workerStarts += 1; return state.options.workerStart }
        await gate?.hold()
    }
    static func beforeAcceptancePublish() async {
        let gate = state.use { state -> ReviewAsyncGate? in state.acceptancePublishes += 1; return state.options.acceptancePublish }
        await gate?.hold()
    }
    static func afterReservedID() async {
        await state.use { $0.options.reservedID }?.hold()
    }
    static func beforeEnvelopeResume() { state.use { $0.options.envelopeResume }?.hold() }
    static func transformStartup(_ report: inout MixerVmReport) {
        let fault = state.use { state -> StartupFault? in
            guard !state.startupFaultUsed else { return nil }
            state.startupFaultUsed = true; return state.options.startupFault
        }
        switch fault {
        case .wrongABI: report.abi_version = 99
        case .invalidI32: report.value_type = 1; report.value = Int64.max
        case nil: break
        }
    }
    static func transformCreate(_ status: inout UInt32, _ handle: inout UInt64, _ report: inout MixerVmReport) {
        let fault = state.use { state -> CreateFault? in
            guard !state.createFaultUsed else { return nil }
            state.createFaultUsed = true; return state.options.createFault
        }
        // The real native creation already happened. The zero-handle case
        // deliberately hides one no-I/O handle until this filtered process ends;
        // no production source/runtime state outside the test process is edited.
        switch fault {
        case .wrongABI: report.abi_version = 99
        case .successZeroHandle: handle = 0
        case .publishedErrorHandle: status = 3; report.status = 3
        case nil: break
        }
    }
    static func beforeNativeWake() {
        let gate = state.use { state -> ReviewSyncGate? in
            guard !state.wakeHeld, state.nativeCallsTaken > 0, let gate = state.options.beforeWake else { return nil }
            state.wakeHeld = true; return gate
        }
        gate?.hold()
    }
    static func beforeNativeRemaining() {
        let gate = state.use { state -> ReviewSyncGate? in
            state.remainingCalls += 1
            return state.remainingCalls == state.options.remainingOrdinal ? state.options.beforeRemaining : nil
        }
        gate?.hold()
    }
    static func transformTake(_ message: inout MixerVmCapabilityMessageV1) {
        if message.kind == 1 { state.use { $0.nativeCallsTaken += 1 } }
        let empty = state.use { state -> Bool in
            guard message.kind == 1, state.options.emptyTakenPayload, !state.emptyTakenPayloadUsed else { return false }
            state.emptyTakenPayloadUsed = true; return true
        }
        if empty { message.payload_length = 0 }
    }
    static func afterCloseSignal() { state.use { $0.closeSignals += 1 } }
    static func afterNativeTake() {
        let gate = state.use { state -> ReviewSyncGate? in
            guard !state.takeHeld else { return nil }
            state.takeHeld = true; return state.options.lateTake
        }
        gate?.hold()
    }
    static func beforeTicketScan(_ owner: NativeExitOwner, cutoff: ContinuousClock.Instant) {
        let count = owner.control.withLock { $0.tickets.compactMap { $0 }.count }
        let action = state.use { state -> (ReviewSyncGate?, Bool) in
            state.scans += 1
            let gate: ReviewSyncGate?
            if !state.drainHeld && count >= state.options.afterDrainCount {
                state.drainHeld = true; gate = state.options.afterDrain
            } else { gate = nil }
            // If eight takes need more than one batch, prevent admission until
            // all eight raw tickets are registered. No adapter is substituted.
            let waitingForDrain = state.options.afterDrain != nil && !state.drainHeld
            let configuredExpiry = count >= state.options.afterDrainCount && state.options.expireScans > 0
            let expire = waitingForDrain || configuredExpiry
            if configuredExpiry { state.options.expireScans -= 1 }
            return (gate, expire)
        }
        action.0?.hold()
        if action.1 {
            // Deliberately exceed two review batches. This is a scheduling seam,
            // not evidence about uninstrumented timing or hard real-time bounds.
            while ContinuousClock.now <= cutoff { Thread.sleep(forTimeInterval: 0.001) }
        }
    }
    static func hostDelivery(_ bytes: Data, ticket: NativeTicket, owner: NativeExitOwner) {
        let capture = state.use { state -> Bool in
            guard state.options.holdDelivery, state.delivery == nil else { return false }
            state.delivery = Delivery(owner: owner, ticket: ticket, bytes: bytes)
            return true
        }
        if !capture { owner.delivery(bytes, ticket: ticket) }
    }
    static func hostExit(_ ticket: NativeTicket, owner: NativeExitOwner) {
        let capture = state.use { state -> Bool in
            guard state.options.holdExit, state.exit == nil else { return false }
            state.exit = Exit(owner: owner, ticket: ticket); return true
        }
        if !capture { owner.exited(ticket) }
    }
    static func releaseDelivery() {
        let captured = state.use { state -> Delivery? in let value = state.delivery; state.delivery = nil; return value }
        if let captured { captured.owner.delivery(captured.bytes, ticket: captured.ticket) }
    }
    static func releaseExit() {
        let captured = state.use { state -> Exit? in let value = state.exit; state.exit = nil; return value }
        if let captured { captured.owner.exited(captured.ticket) }
    }
}
