import Foundation
import Dispatch
import MixerCapabilities

final class Locked<Value>: @unchecked Sendable {
    private let lock = NSLock()
    private var value: Value
    init(_ value: Value) { self.value = value }
    func withLock<Result>(_ body: (inout Value) throws -> Result) rethrows -> Result {
        lock.lock(); defer { lock.unlock() }; return try body(&value)
    }
}

final class ConstructionPermit: @unchecked Sendable {
    private static let count = Locked(0)
    private static let quarantined = Locked<[ConstructionPermit]>([])
    private let released = Locked(false)
    static func acquire() throws -> ConstructionPermit {
        try count.withLock { value in
            guard value < 16 else { throw ExperimentalCapabilityError("construction_busy") }
            value += 1
        }
        return ConstructionPermit()
    }
    func release() {
        let first = released.withLock { value in if value { return false }; value = true; return true }
        if first { Self.count.withLock { $0 -= 1 } }
    }
    /// At most sixteen permits can reach this fixed process-lifetime quarantine.
    /// No module, host, callback or scheduler source is retained here.
    func quarantine() { Self.quarantined.withLock { $0.append(self) } }
    deinit { release() }
}

/// Exactly one fixed entry per guest slot. The observer can outlive the public
/// session. All state is protected; no external work executes under this lock.
final class NativeTicket: @unchecked Sendable {
    struct State {
        var expected: CapabilityCall?
        var arguments: Data?
        var typedOperation: CapabilityOperation?
        var admissionStarted = false
        var encodedResult: Data?
        var envelopeWaiter: CheckedContinuation<Data, any Error>?
        var legacyBytes = 0
        var accepted: Bool?
        var reservationDisposed = false
        var workerRunning = false
        var cancelRequested = false
        var cancelSent = false
        var callback: Data?
        var callbackReceived = false
        var exitObserved = false
        var localExit = false
        var localOutcome: GuestCapabilityCompletionV1?
        var resultHandled = false
        var acknowledged = false
        var ackFailed = false
        var deadline: ContinuousClock.Instant?
        var fatal: String?
    }
    let token: UInt64
    let operation: GuestCapabilityOperationV1
    let state = Locked(State())
    var index: Int { Int(UInt32(truncatingIfNeeded: token) - 1) }
    init(token: UInt64, operation: GuestCapabilityOperationV1) { self.token = token; self.operation = operation }
}

enum ExperimentalQueues {
    static let guest = DispatchQueue(label: "mixer.experimental.capability.guest", qos: .utility)
    static let construction = DispatchQueue(label: "mixer.experimental.capability.create", qos: .utility)
    static let close = DispatchQueue(label: "mixer.experimental.capability.close", qos: .utility)
}

/// Independent lifetime for a taken C ticket's actual exit. Dispatch sources keep
/// the owner alive until explicit close and every acknowledgement finishes.
final class NativeExitOwner: @unchecked Sendable {
    struct Control {
        var status = ExperimentalCapabilityStatus()
        var closeFinished = false
        var nativeCloseSucceeded = false
        var quarantined = false
        var hostCloseFinished = false
        var commandBusy = false
        var command: (@Sendable () -> Void)?
        var signalled = false
        var tickets: [NativeTicket?] = Array(repeating: nil, count: 8)
    }
    let native: NativeCapabilitySession
    let host: CapabilityHost
    let configuration: ExperimentalCapabilityConfiguration
    private let permit: ConstructionPermit
    let control = Locked(Control())
    private var source: DispatchSourceUserDataAdd?
    private var timer: DispatchSourceTimer?
    private var timerArmed = false
    private var started = false
    private var effectsOpen = false
    private var readyHint = false
    private var drainHint = false
    private var cursor = 0
    private var rateTokens: Double
    private var rateTime = ContinuousClock.now

    init(native: NativeCapabilitySession, host: CapabilityHost, configuration: ExperimentalCapabilityConfiguration,
         permit: ConstructionPermit) {
        self.native = native; self.host = host; self.configuration = configuration
        self.permit = permit; rateTokens = Double(configuration.dispatchBurst)
    }
    func start() {
        let source = DispatchSource.makeUserDataAddSource(queue: ExperimentalQueues.guest)
        let timer = DispatchSource.makeTimerSource(queue: ExperimentalQueues.guest)
        self.source = source; self.timer = timer
        source.setEventHandler { [self] in pump() }
        timer.setEventHandler { [self] in
            control.withLock { $0.status.timerTicks &+= 1 }; pump()
        }
        timer.schedule(deadline: .distantFuture)
        source.resume(); timer.resume()
    }
    var status: ExperimentalCapabilityStatus { control.withLock { $0.status } }
    var closed: Bool { control.withLock { $0.status.closed } }
    func signal() {
        let needsSignal = control.withLock { state in
            if state.signalled || state.status.drained { return false }
            state.signalled = true; return true
        }
        if needsSignal { source?.add(data: 1) }
    }
    func stop(_ failure: String? = nil, quarantined: Bool = false) {
        let first = control.withLock { state in
            if state.status.failure == nil { state.status.failure = failure }
            state.quarantined = state.quarantined || quarantined
            guard !state.status.closed else { return false }
            state.status.closed = true; return true
        }
        guard first else { return }
        ExperimentalQueues.close.async { [self] in
            do { try native.close(); control.withLock { $0.nativeCloseSucceeded = true } }
            catch { recordFailure(error) }
            control.withLock { $0.closeFinished = true }; signal()
        }
        Task.detached { [self] in
            await host.close()
            control.withLock { $0.hostCloseFinished = true }; signal()
        }
        signal()
    }
    private func recordFailure(_ error: any Error) {
        let code = (error as? ExperimentalCapabilityError)?.code ?? "bridge_failure"
        control.withLock { state in
            if state.status.failure == nil { state.status.failure = code }
            let status = (error as? ExperimentalCapabilityError)?.nativeStatus
            if status == nil || status == 4 { state.quarantined = true }
        }
    }
    private func fail(_ error: any Error) {
        let e = error as? ExperimentalCapabilityError
        stop(e?.code ?? "bridge_failure", quarantined: e?.nativeStatus == nil || e?.nativeStatus == 4)
    }
    private func closedRejection(_ error: any Error) -> Bool {
        // Ordinary access to a closed C generation rejects3. The synchronous
        // latch may race a call already admitted by this pump; this explains
        // only that checked status, never malformed metadata or retained ack.
        closed && (error as? ExperimentalCapabilityError)?.nativeStatus == 3
    }
    func command<Value: Sendable>(turn: Bool = false, _ body: @escaping @Sendable () throws -> Value) async throws -> Value {
        try await withCheckedThrowingContinuation { continuation in
            let accepted = control.withLock { state in
                guard !state.status.closed, !state.commandBusy else { return false }
                state.commandBusy = true
                state.command = { [self] in
                    guard !closed else {
                        control.withLock { $0.commandBusy = false }
                        continuation.resume(throwing: ExperimentalCapabilityError("closed")); return
                    }
                    do {
                        let value = try body()
                        if turn { control.withLock { $0.status.turns &+= 1 }; readyHint = true; drainHint = true }
                        control.withLock { $0.commandBusy = false }
                        continuation.resume(returning: value)
                    } catch {
                        // This closure contains only checked native operations.
                        // Ordinary API/busy rejection3 leaves the owner usable;
                        // malformed reports/values have no status and fail shut.
                        if (error as? ExperimentalCapabilityError)?.nativeStatus != 3 { fail(error) }
                        control.withLock { $0.commandBusy = false }
                        continuation.resume(throwing: error)
                    }
                }
                return true
            }
            if accepted { signal() }
            else { continuation.resume(throwing: ExperimentalCapabilityError(closed ? "closed" : "command_busy")) }
        }
    }
    func startup() async throws -> ExperimentalCapabilityInvocation {
        try await command(turn: true) { [self] in
            let result = try native.startup(); started = true; return result
        }
    }
    func enable() async throws {
        try await command { [self] in
            try native.enable()
            if !closed { effectsOpen = true }
        }
    }
    private func tickets() -> [NativeTicket] { control.withLock { $0.tickets.compactMap { $0 } } }
    private func current(_ ticket: NativeTicket) -> Bool { control.withLock { $0.tickets[ticket.index] === ticket } }
    func delivery(_ data: Data, ticket: NativeTicket) {
        let began = ContinuousClock.now
        defer {
            let elapsed = Self.nanoseconds(began.duration(to: .now))
            control.withLock { $0.status.maximumCallbackNanoseconds = max($0.status.maximumCallbackNanoseconds, elapsed) }
        }
        guard current(ticket), !closed else { return }
        let capture = ticket.state.withLock { state in
            guard !state.resultHandled, !state.acknowledged else { return false }
            if state.callbackReceived { state.fatal = "duplicate_host_callback"; return false }
            state.callbackReceived = true; return true
        }
        guard capture else { signal(); return }
        if data.count > 524288 || data.isEmpty {
            ticket.state.withLock { $0.fatal = "invalid_host_callback" }; signal(); return
        }
        // Snapshot once, outside locks; Data may be backed by foreign NSData.
        let snapshot = Data(Array(data))
        control.withLock { control in
            guard !control.status.closed, control.tickets[ticket.index] === ticket else { return }
            ticket.state.withLock { state in
                if !state.resultHandled && !state.acknowledged { state.callback = snapshot }
            }
        }
        signal()
    }
    func exited(_ ticket: NativeTicket) {
        guard current(ticket) else { return }
        ticket.state.withLock { state in
            if state.acknowledged { return }
            if state.exitObserved { state.fatal = "duplicate_host_exit" }
            state.exitObserved = true
        }
        signal()
    }
    private func armTimer(_ enabled: Bool) {
        guard enabled != timerArmed else { return }
        timerArmed = enabled
        if enabled { timer?.schedule(deadline: .now() + .milliseconds(10), repeating: .milliseconds(10)) }
        else { timer?.schedule(deadline: .distantFuture) }
    }
    private func pump() {
        control.withLock { $0.signalled = false }
        let beginning = ContinuousClock.now
        defer {
            let elapsed = Self.nanoseconds(beginning.duration(to: .now))
            control.withLock { $0.status.maximumBatchNanoseconds = max($0.status.maximumBatchNanoseconds, elapsed) }
        }
        let cutoff = beginning.advanced(by: .milliseconds(Int64(configuration.batchMilliseconds)))
        var turns = 0
        let command = control.withLock { state in let c = state.command; state.command = nil; return c }
        if let command {
            let before = status.turns; command()
            if status.turns != before { turns += 1 }
        }
        if !closed && started && ContinuousClock.now < cutoff {
            do {
                try native.expire()
                readyHint = true // Expiry can create a terminal without a native callback.
                // Cancellation controls have priority inside C. A full payload
                // scratch makes too-small impossible for valid metadata.
                for _ in 0..<16 where ContinuousClock.now < cutoff {
                    if closed { break }
                    switch try native.take() {
                    case .none: drainHint = false; break
                    case .cancel(let token, let operation):
                        guard let ticket = control.withLock({ $0.tickets[Int(UInt32(truncatingIfNeeded: token) - 1)] }),
                              ticket.token == token, ticket.operation == operation else { throw ExperimentalCapabilityError("unmapped_cancel") }
                        ticket.state.withLock { $0.cancelRequested = true }
                        readyHint = true
                        cancelIfNeeded(ticket)
                        continue
                    case .call(let token, let operation, let arguments):
                        let ticket = NativeTicket(token: token, operation: operation)
                        let installed = control.withLock { state -> Int in
                            if let old = state.tickets[ticket.index], !old.state.withLock({ $0.acknowledged && !$0.workerRunning }) { return -1 }
                            state.tickets[ticket.index] = ticket; state.status.acceptedCalls &+= 1
                            return state.status.closed ? 0 : 1
                        }
                        if installed < 0 { stop("native_ticket_reuse", quarantined: true) }
                        else if installed == 1 && effectsOpen { ticket.state.withLock { $0.arguments = arguments } }
                        else { local(ticket, outcome: .failure(.unavailable)) }
                        continue
                    }
                    break
                }
            } catch { if !closedRejection(error) { fail(error) } }
        }
        for _ in 0..<8 {
            if ContinuousClock.now >= cutoff { break }
            let index = cursor; cursor = (cursor + 1) % 8
            if let ticket = control.withLock({ $0.tickets[index] }) { process(ticket, cutoff: cutoff) }
        }
        if !closed && started && readyHint {
            while turns < Int(configuration.batchTurns) && ContinuousClock.now < cutoff {
                do {
                    if !(try native.wake()) { readyHint = false; break }
                    drainHint = true // A successful wake can publish new calls.
                    turns += 1; control.withLock { $0.status.turns &+= 1 }
                } catch {
                    if closedRejection(error) { break }
                    if let e = error as? ExperimentalCapabilityError, e.code == "session_busy" { break }
                    fail(error); break
                }
            }
        }
        control.withLock { state in
            state.status.maximumBatchTurns = max(state.status.maximumBatchTurns, turns)
            if readyHint && !state.status.closed { state.status.yields &+= 1 }
            let currentTickets: [NativeTicket] = state.tickets.compactMap { $0 }
            var retainedExits: Int = 0
            for ticket in currentTickets {
                let acknowledged: Bool = ticket.state.withLock { $0.acknowledged }
                if !acknowledged { retainedExits += 1 }
            }
            state.status.retainedExits = retainedExits
            var payloadBytes: Int = 0
            for ticket in currentTickets {
                let ticketBytes: Int = ticket.state.withLock { ticketState in
                    let callbackBytes: Int = ticketState.callback?.count ?? 0
                    let argumentBytes: Int = ticketState.arguments?.count ?? 0
                    let resultBytes: Int = ticketState.encodedResult?.count ?? 0
                    return callbackBytes + argumentBytes + resultBytes + ticketState.legacyBytes
                }
                payloadBytes += ticketBytes
            }
            state.status.retainedPayloadBytes = payloadBytes
            state.status.maximumLogicalPayloadBytes = max(state.status.maximumLogicalPayloadBytes, state.status.retainedPayloadBytes)
            var workers: Int = 0
            for ticket in currentTickets {
                let running: Bool = ticket.state.withLock { $0.workerRunning }
                if running { workers += 1 }
            }
            state.status.maximumWorkers = max(state.status.maximumWorkers, workers)
        }
        let active = tickets().contains { ticket in ticket.state.withLock { !$0.acknowledged && !$0.ackFailed } }
        if closed {
            let cleanupReady = tickets().contains { ticket in ticket.state.withLock {
                !$0.acknowledged && !$0.ackFailed && (
                    $0.envelopeWaiter != nil ||
                    (!$0.admissionStarted && !$0.workerRunning && $0.accepted == nil) ||
                    (!$0.workerRunning && ($0.exitObserved || $0.localExit))
                )
            } }
            armTimer(cleanupReady) // Park while only actual late exit/control completion can progress.
            let done = control.withLock { state in
                state.closeFinished && state.nativeCloseSucceeded && !state.quarantined && state.hostCloseFinished && !state.commandBusy && state.tickets.compactMap { $0 }.allSatisfy { $0.state.withLock { $0.acknowledged && !$0.workerRunning } }
            }
            if done {
                native.discardScratchAfterDrain()
                source?.setEventHandler {}; source?.cancel(); timer?.setEventHandler {}; timer?.cancel()
                permit.release()
                control.withLock { $0.tickets = Array(repeating: nil, count: 8); $0.status.drained = true }
            }
        } else { armTimer(active || readyHint || drainHint) }
    }
    private static func nanoseconds(_ elapsed: Duration) -> UInt64 {
        let value = elapsed.components
        guard value.seconds >= 0 else { return 0 }
        let (whole, overflow) = UInt64(value.seconds).multipliedReportingOverflow(by: 1_000_000_000)
        if overflow { return .max }
        let (total, sumOverflow) = whole.addingReportingOverflow(UInt64(max(0, value.attoseconds / 1_000_000_000)))
        return sumOverflow ? .max : total
    }

    private func local(_ ticket: NativeTicket, outcome: GuestCapabilityCompletionV1?) {
        ticket.state.withLock { state in
            state.accepted = false; state.localExit = true; state.reservationDisposed = true
            state.localOutcome = outcome; state.workerRunning = false
            state.arguments = nil; state.typedOperation = nil
            if outcome == nil { state.resultHandled = true }
        }
        readyHint = true; signal()
    }
    private func admissionPhase(_ ticket: NativeTicket, cutoff: ContinuousClock.Instant) {
        guard ticket.state.withLock({ !$0.admissionStarted && $0.accepted == nil }) else { return }
        if ticket.state.withLock({ $0.cancelRequested && !$0.admissionStarted }) {
            local(ticket, outcome: nil); return
        }
        if let bytes = ticket.state.withLock({ $0.arguments }) {
            guard ContinuousClock.now < cutoff else { return }
            do {
                let operation = try GuestCapabilityTransportCodecV1.decodeArguments(bytes, operation: ticket.operation)
                ticket.state.withLock { $0.arguments = nil; $0.typedOperation = operation }
            } catch { local(ticket, outcome: .rejected(.invalidArguments)); return }
        }
        guard let operation = ticket.state.withLock({ $0.typedOperation }) else { return }
        guard ContinuousClock.now < cutoff else { return }
        let timeout: UInt32
        if case .http(let args) = operation { timeout = args.timeoutMilliseconds }
        else { timeout = configuration.timeoutMilliseconds }
        do {
            let sample = ContinuousClock.now
            let remaining = try native.remaining(token: ticket.token, operation: ticket.operation, timeout: timeout)
            guard remaining > 0 else { local(ticket, outcome: nil); return }
            let deadline = sample.advanced(by: .milliseconds(Int64(remaining)))
            ticket.state.withLock { $0.deadline = deadline }
            let elapsed = rateTime.duration(to: sample)
            let seconds = Double(elapsed.components.seconds) + Double(elapsed.components.attoseconds) / 1e18
            rateTokens = min(Double(configuration.dispatchBurst), rateTokens + max(0, seconds) * Double(configuration.dispatchesPerSecond))
            rateTime = sample
            guard rateTokens >= 1 else { local(ticket, outcome: .failure(.quotaExceeded)); return }
            rateTokens -= 1
            ticket.state.withLock { $0.workerRunning = true; $0.admissionStarted = true }
            Task.detached { [self, ticket] in
                await performSubmit(ticket)
                finishWorker(ticket)
            }
        } catch {
            if !closedRejection(error) { fail(error) }
            local(ticket, outcome: nil) // No host reservation/worker began.
        }
    }
    private func process(_ ticket: NativeTicket, cutoff: ContinuousClock.Instant) {
        if !closed { admissionPhase(ticket, cutoff: cutoff) }
        var snapshot = ticket.state.withLock { $0 }
        if snapshot.envelopeWaiter != nil {
            guard closed || ContinuousClock.now < cutoff else { return }
            let waiter = ticket.state.withLock { state in let c = state.envelopeWaiter; state.envelopeWaiter = nil; return c }
            if let waiter {
                if closed || snapshot.cancelRequested || snapshot.deadline.map({ ContinuousClock.now >= $0 }) == true {
                    waiter.resume(throwing: ExperimentalCapabilityError("admission_stopped"))
                } else if let call = snapshot.expected {
                    do {
                        let bytes = try CapabilityCodec.encodeCall(call)
                        ticket.state.withLock { $0.legacyBytes = bytes.count }
                        waiter.resume(returning: bytes)
                    } catch { waiter.resume(throwing: error) }
                } else { waiter.resume(throwing: ExperimentalCapabilityError("missing_reserved_call")) }
            }
        }
        if let fatal = snapshot.fatal { stop(fatal) }
        if closed { ticket.state.withLock { state in
            state.callback = nil; state.arguments = nil; state.encodedResult = nil
            state.localOutcome = nil; state.resultHandled = true
            if !state.admissionStarted && !state.workerRunning && state.accepted == nil {
                // Registered take, but no host reservation or worker ever began.
                state.accepted = false; state.localExit = true; state.reservationDisposed = true
            }
            if !state.workerRunning { state.typedOperation = nil }
            // A started worker still owns its input until it observes close and
            // disposes any host reservation; never erase that cleanup handoff.
        } }
        else if !snapshot.resultHandled && snapshot.accepted != nil {
            if let bytes = snapshot.callback, let expected = snapshot.expected {
                guard ContinuousClock.now < cutoff else { return }
                ticket.state.withLock { $0.callback = nil }
                let outcome: GuestCapabilityCompletionV1
                do {
                    switch try CapabilityCodec.decodeCompletion(bytes, expected: expected).outcome {
                    case .success(let result): outcome = .success(result)
                    case .failure(let failure): outcome = .failure(failure)
                    }
                } catch { outcome = .failure(.invalidResponse) }
                ticket.state.withLock { $0.localOutcome = outcome }
            }
            snapshot = ticket.state.withLock { $0 }
            if let outcome = snapshot.localOutcome {
                guard ContinuousClock.now < cutoff else { return }
                do {
                    let bytes = try GuestCapabilityTransportCodecV1.encodeCompletion(outcome, operation: ticket.operation)
                    ticket.state.withLock { $0.localOutcome = nil; $0.encodedResult = bytes }
                } catch { fail(error); return }
            }
            snapshot = ticket.state.withLock { $0 }
            if let bytes = snapshot.encodedResult {
                guard ContinuousClock.now < cutoff else { return }
                do { try native.post(token: ticket.token, operation: ticket.operation, data: bytes) }
                catch {
                    let e = error as? ExperimentalCapabilityError
                    if !(e?.nativeStatus == 3 && (snapshot.cancelRequested || snapshot.deadline.map { ContinuousClock.now >= $0 } == true || closed)) {
                        fail(error)
                    }
                }
                ticket.state.withLock { $0.encodedResult = nil; $0.resultHandled = true }; readyHint = true
            } else if snapshot.exitObserved, let deadline = snapshot.deadline, ContinuousClock.now >= deadline {
                guard ContinuousClock.now < cutoff else { return }
                do {
                    if try native.remaining(token: ticket.token, operation: ticket.operation, timeout: configuration.timeoutMilliseconds) == 0 {
                        ticket.state.withLock { $0.resultHandled = true }; readyHint = true
                    }
                } catch { if !closedRejection(error) { fail(error) } }
            }
        }
        cancelIfNeeded(ticket)
        let canAck = ticket.state.withLock { state in
            state.resultHandled && (state.exitObserved || state.localExit) && state.accepted != nil && !state.workerRunning && !state.acknowledged && !state.ackFailed
        }
        if canAck {
            guard ContinuousClock.now < cutoff else { return }
            do {
                try native.ack(token: ticket.token, operation: ticket.operation)
                ticket.state.withLock { $0.acknowledged = true; $0.expected = nil; $0.callback = nil }
                control.withLock { $0.status.acknowledgements &+= 1 }
            } catch {
                ticket.state.withLock { $0.ackFailed = true }; fail(error)
            }
        }
    }
    private func performSubmit(_ ticket: NativeTicket) async {
        guard let (operation, deadline) = ticket.state.withLock({ state -> (CapabilityOperation, ContinuousClock.Instant)? in
            guard let operation = state.typedOperation, let deadline = state.deadline else { return nil }
            state.typedOperation = nil; return (operation, deadline)
        }) else { stop("missing_admission_state"); return }
        if closed || ticket.state.withLock({ $0.cancelRequested }) {
            localFromWorker(ticket, outcome: nil); return
        }
        if ContinuousClock.now >= deadline { localFromWorker(ticket, outcome: .failure(.deadlineExceeded)); return }
        let identity: CapabilityRequestID
        do { identity = try await host.issueRequestID() }
        catch { localFromWorker(ticket, outcome: .failure(.unavailable)); return }
        let call = CapabilityCall(identity: identity, operation: operation)
        ticket.state.withLock { $0.expected = call }
        let bytes: Data
        do {
            bytes = try await withCheckedThrowingContinuation { continuation in
                ticket.state.withLock { $0.envelopeWaiter = continuation }
                signal()
            }
        }
        catch {
            await dispose(call)
            if closed || ticket.state.withLock({ $0.cancelRequested }) || ContinuousClock.now >= deadline {
                localFromWorker(ticket, outcome: ContinuousClock.now >= deadline ? .failure(.deadlineExceeded) : nil)
            } else {
                stop("legacy_envelope_encoding"); localFromWorker(ticket, outcome: nil)
            }
            return
        }
        if closed || ContinuousClock.now >= deadline || ticket.state.withLock({ $0.cancelRequested }) {
            await dispose(call)
            localFromWorker(ticket, outcome: ContinuousClock.now >= deadline ? .failure(.deadlineExceeded) : nil); return
        }
        do {
            try await host.submitObserved(bytes, noLaterThan: deadline,
                deliver: { [self] in delivery($0, ticket: ticket) }, didExit: { [self] in exited(ticket) })
            ticket.state.withLock { $0.accepted = true }
        } catch {
            if ticket.state.withLock({ $0.callbackReceived || $0.exitObserved }) {
                stop("observed_submit_contract", quarantined: true)
            } else {
                await dispose(call); localFromWorker(ticket, outcome: .failure(.unavailable))
            }
        }
    }
    private func dispose(_ call: CapabilityCall) async {
        do { try await host.submit(CapabilityCodec.encodeCancel(call), deliver: { _ in }) }
        catch { if !closed { stop("reservation_disposal") }; await host.close() }
    }
    private func localFromWorker(_ ticket: NativeTicket, outcome: GuestCapabilityCompletionV1?) {
        ticket.state.withLock { state in
            state.accepted = false; state.localExit = true; state.reservationDisposed = true
            state.localOutcome = outcome
            if outcome == nil { state.resultHandled = true }
        }
    }
    private func finishWorker(_ ticket: NativeTicket) {
        ticket.state.withLock { $0.workerRunning = false; $0.legacyBytes = 0 }
        signal() // No old-slot action or DTO capture survives this tail boundary.
    }
    private func cancelIfNeeded(_ ticket: NativeTicket) {
        let begin = ticket.state.withLock { state -> Bool in
            guard state.cancelRequested, state.accepted == true, !state.cancelSent, !state.workerRunning,
                  !state.exitObserved, state.expected != nil else { return false }
            state.cancelSent = true; state.workerRunning = true; return true
        }
        guard begin else { return }
        Task.detached { [self, ticket] in
            await performCancel(ticket)
            finishWorker(ticket)
        }
    }
    private func performCancel(_ ticket: NativeTicket) async {
        guard let call = ticket.state.withLock({ $0.expected }) else { stop("missing_cancel_state"); return }
        do { try await host.submit(CapabilityCodec.encodeCancel(call), deliver: { _ in }) }
        catch {
            if !closed && !ticket.state.withLock({ $0.exitObserved }) { stop("accepted_cancel_failure") }
        }
    }
}
