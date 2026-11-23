import FoundationEssentials

// This adapter is specific to the cooperative executor in the pinned WASI SDK.
@_silgen_name("swift_task_donateThreadToGlobalExecutorUntil")
private func drainExecutor(
    _ completed: @convention(c) (UnsafeMutableRawPointer?) -> Bool,
    _ context: UnsafeMutableRawPointer?
)

private let eventCapacity = 1_048_576
private let frameCapacity = 4096
private nonisolated(unsafe) var input: UnsafeMutablePointer<UInt8>?
private nonisolated(unsafe) var frame: UnsafeMutablePointer<UInt8>?
private nonisolated(unsafe) var header: UnsafeMutablePointer<UInt32>?

@MainActor
private enum Session {
    static var journey: Journey?
    static var step = 0

    static func start() async throws -> Journey.Result {
        precondition(journey == nil)
        let opened = Journey()
        journey = opened
        return opened.result
    }

    static func advance(_ event: Int) async throws -> Journey.Result {
        guard let journey, event == step + 1 else {
            preconditionFailure("Unexpected spike event")
        }

        switch event {
        case 1:
            await journey.load()
        case 2:
            journey.openRecord()
        case 3:
            journey.tryBlankSave()
        case 4:
            journey.saveEdit()
        case 5:
            try journey.reopen()
        default:
            preconditionFailure("Unknown spike event")
        }

        step = event
        return journey.result
    }
}

private final class Output: @unchecked Sendable {
    // The Wasm SDK runs the caller and the executor cooperatively on one thread.
    var bytes: Data?
}

private func publish(
    _ action: @escaping @MainActor () async throws -> Journey.Result
) -> UInt32 {
    let output = Output()
    let context = Unmanaged.passUnretained(output).toOpaque()
    Task { @MainActor in
        let encoder = JSONEncoder()
        encoder.outputFormatting = .sortedKeys
        do {
            output.bytes = try await encoder.encode(action())
        } catch {
            preconditionFailure("Failed to encode the spike frame: \(error)")
        }
    }
    drainExecutor({ context in
        Unmanaged<Output>.fromOpaque(context!).takeUnretainedValue().bytes != nil
    }, context)
    guard let bytes = output.bytes, bytes.count <= frameCapacity,
          let frame, let header
    else { preconditionFailure("Missing or oversized spike frame") }

    _ = bytes.copyBytes(to: UnsafeMutableBufferPointer(start: frame, count: bytes.count))
    header[3] = UInt32(bytes.count)
    return UInt32(UInt(bitPattern: header))
}

@_cdecl("mixer_guest_ui_start_v3")
func reactorStart() -> UInt32 {
    precondition(header == nil)
    let eventBuffer = UnsafeMutablePointer<UInt8>.allocate(capacity: eventCapacity)
    let frameBuffer = UnsafeMutablePointer<UInt8>.allocate(capacity: frameCapacity)
    let words = UnsafeMutablePointer<UInt32>.allocate(capacity: 8)
    words.initialize(repeating: 0, count: 8)
    words[0] = 0x3349554d
    words[1] = 32
    words[2] = UInt32(UInt(bitPattern: frameBuffer))
    words[4] = UInt32(UInt(bitPattern: eventBuffer))
    words[5] = UInt32(eventCapacity)
    input = eventBuffer
    frame = frameBuffer
    header = words
    return publish { try await Session.start() }
}

@_cdecl("mixer_guest_ui_event_v3")
func reactorEvent(_ length: UInt32) -> UInt32 {
    guard length == 1, let input else { return 0 }
    let event = Int(input.pointee)
    return publish { try await Session.advance(event) }
}

@_cdecl("mixer_guest_ui_ready_v3")
func reactorReady() {}
