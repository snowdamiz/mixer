import Foundation
@_spi(S5SignedCompose) import MixerCapabilityActivation

/// One activity instance, entered by JNI on the main looper. Background work
/// returns immutable status values through the lock and never touches tickets.
private final class EditorFixture {
    private typealias Ticket = ComposeEditorWireV1.Presentation.Ticket

    private struct Status: Encodable {
        let phase: String
        var candidate: String? = nil
        var persisted: String? = nil
        var failure: String? = nil
        var refusedInstall: String? = nil
        var events: UInt64 = 0
    }

    private final class Progress: @unchecked Sendable {
        private let lock = NSLock()
        private var status = Status(phase: "idle")
        func read() -> Status { lock.withLock { status } }
        func write(_ next: Status) { lock.withLock { status = next } }
    }

    private struct Inputs: Decodable { let assets: String; let directory: String }
    private struct Selection: Decodable { let stage: SignedStage.RawValue }

    private var journey: SignedJourney?
    private let progress = Progress()
    private var job: Task<Void, Never>?
    private var presentation: S5SignedPresentation?
    private var successor: S5SignedPresentation?
    private var host = ComposeEditorWireV1.Presentation()
    private var pending: (ticket: Ticket, frame: UUID)?
    private var accepted: (ticket: Ticket, frame: UUID)?

    func call(_ op: Int32, data: Data) throws -> Data? {
        switch op {
        case 0: return try prepare()
        case 1, 2: return try observe(data, discard: op == 2)
        case 3:
            let save = try JSONDecoder().decode(ComposeEditorWireV1.Save.self, from: data)
            guard progress.read().phase != "loading", let presentation, accepted?.ticket == save.ticket else { return nil }
            let events = try save.events()
            // The pinned Compose wire routes the whole batch against the exact
            // accepted snapshot. One successful route submits one scoped batch.
            _ = try host.send(events, from: save.ticket)
            guard let accepted, presentation.submit(events[0], save: events[1], from: accepted.frame) else { return nil }
            return Data()
        case 4:
            guard let journey, pending == nil, accepted != nil, progress.read().phase == "healthy" else { return nil }
            progress.write(Status(phase: "checkingInstall"))
            job = Task { [progress] in
                do {
                    let candidate = try await journey.refuseRollback()
                    progress.write(Status(phase: "healthy", candidate: candidate, refusedInstall: "v3.signature.invalid"))
                } catch {
                    progress.write(Status(phase: "failed", failure: String(describing: error)))
                }
            }
            return Data()
        case 5:
            guard journey == nil else { return nil }
            let inputs = try JSONDecoder().decode(Inputs.self, from: data)
            journey = SignedJourney(assets: URL(fileURLWithPath: inputs.assets, isDirectory: true),
                                    directory: URL(fileURLWithPath: inputs.directory, isDirectory: true))
            return Data()
        case 6:
            var state = progress.read()
            state.events = presentation?.deliveredEvents ?? 0
            return try JSONEncoder().encode(state)
        case 7:
            let selected = try JSONDecoder().decode(Selection.self, from: data)
            guard let stage = SignedStage(rawValue: selected.stage), let journey, canSelect(stage) else { return nil }
            let presentation = S5SignedPresentation()
            successor = presentation
            progress.write(Status(phase: "preparing"))
            job = Task { [progress] in
                do {
                    let candidate = try await journey.activate(stage, presentation: presentation, retiring: {
                        progress.write(Status(phase: "loading"))
                    }, provisional: {
                        progress.write(Status(phase: "provisional"))
                    })
                    progress.write(Status(phase: "healthy", candidate: candidate))
                } catch {
                    if progress.read().phase != "preparing" { await journey.abort() }
                    progress.write(Status(phase: "failed", failure: String(describing: error)))
                }
            }
            return Data()
        case 8:
            guard let journey, progress.read().phase == "healthy" else { return nil }
            progress.write(Status(phase: "closing"))
            job = Task { [progress] in
                do {
                    let persisted = try await journey.finish()
                    progress.write(Status(phase: "closed", persisted: persisted.base64EncodedString()))
                } catch {
                    progress.write(Status(phase: "failed", failure: String(describing: error)))
                }
            }
            return Data()
        default: return nil
        }
    }

    private func canSelect(_ stage: SignedStage) -> Bool {
        let phase = progress.read().phase
        return stage == .prior ? phase == "idle" : phase == "healthy" && pending == nil
    }

    private func prepare() throws -> Data? {
        if let successor, progress.read().phase == "provisional" {
            presentation = successor
            self.successor = nil
            host = ComposeEditorWireV1.Presentation()
            pending = nil
            accepted = nil
        }
        guard let presentation else { return nil }
        presentation.pump()
        guard pending == nil, let frame = presentation.frame() else { return nil }
        let prepared = try ComposeEditorWireV1.prepare(frame.snapshot, in: host) { actions in
            guard actions.count == 2, actions[0].nodeID == "title", actions[0].event == .textChange,
                  actions[1].nodeID == "save", actions[1].event == .activate,
                  let title = actions[0].value.string else { throw ComposeEditorWireV1.WireError.editor }
            return title
        }
        pending = (prepared.ticket, frame.id)
        return prepared.bytes
    }

    private func observe(_ data: Data, discard: Bool) throws -> Data? {
        let ticket = try JSONDecoder().decode(Ticket.self, from: data)
        guard let presentation, let pending, pending.ticket == ticket, host.pending == ticket else { return nil }
        if discard {
            guard presentation.discard(pending.frame), host.discard(ticket) else { return nil }
        } else {
            guard presentation.present(pending.frame), host.didDraw(ticket) else { return nil }
            accepted = pending
        }
        self.pending = nil
        return Data()
    }

    func close() {
        let previous = job
        previous?.cancel()
        if let journey {
            Task {
                await previous?.value
                await journey.abort()
            }
        }
    }
}

@_cdecl("mixer_compose_editor_open_v1")
public func openEditor() -> UnsafeMutableRawPointer {
    Unmanaged.passRetained(EditorFixture()).toOpaque()
}

@_cdecl("mixer_compose_editor_close_v1")
public func closeEditor(_ handle: UnsafeMutableRawPointer) {
    let fixture = Unmanaged<EditorFixture>.fromOpaque(handle).takeRetainedValue()
    fixture.close()
}

@_cdecl("mixer_compose_editor_call_v1")
public func callEditor(_ handle: UnsafeMutableRawPointer, _ op: Int32,
                       _ input: UnsafePointer<UInt8>, _ count: Int,
                       _ output: UnsafeMutablePointer<UInt8>, _ capacity: Int) -> Int32 {
    guard (0...8192).contains(count), capacity == 8192 else { return -1 }
    let fixture = Unmanaged<EditorFixture>.fromOpaque(handle).takeUnretainedValue()
    guard let data = try? fixture.call(op, data: Data(bytes: input, count: count)), data.count <= capacity else { return -1 }
    data.copyBytes(to: output, count: data.count)
    return Int32(data.count)
}
