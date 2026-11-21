// State projection of the historical TaskEditor and TaskEditorPresentation.
// replay.py supplies the title case directly from the pinned TaskEditor blob.

enum EditorReply: UInt32 {
    case accepted, closed, staleRevision, staleIdentity, unboundEvent, invalidValue
}

enum EditorNode: Int32 {
    case title = 1, cancel
}

enum EditorEvent: Int32 {
    case textChange = 1, activate
}

enum EditorValue: Int32 {
    case null, text, boolean
}

struct TitleState {
    var title = ""
    let saving = false
    let saved = false
    var failure: String?
}

struct EditorBoundary {
    static let maximumTitleBytes = 16_384
    static let headerBytes = 10
    static let bufferBytes = headerBytes + maximumTitleBytes

    private let titleGeneration: UInt64
    private let cancelGeneration: UInt64
    private var state = TitleState()
    private var publishedTitle = ""
    private var revision: UInt64 = 1
    private var cancelled = false

    init(titleGeneration: UInt64, cancelGeneration: UInt64) {
        self.titleGeneration = titleGeneration
        self.cancelGeneration = cancelGeneration
    }

    mutating func send(
        revision: UInt64, node: Int32, generation: UInt64,
        event: Int32, kind: Int32, input: UnsafeBufferPointer<UInt8>
    ) -> EditorReply {
        guard !cancelled else { return .closed }
        guard revision == self.revision else { return .staleRevision }
        switch EditorNode(rawValue: node) {
        case .title:
            guard generation == titleGeneration else { return .staleIdentity }
            guard event == EditorEvent.textChange.rawValue else { return .unboundEvent }
            guard kind == EditorValue.text.rawValue,
                  input.count <= Self.maximumTitleBytes,
                  let title = String(validating: input, as: UTF8.self) else {
                return .invalidValue
            }
            state.changeTitle(title)
            // Swift equality can suppress an observer update while the store
            // still retains the new spelling. Cancel publishes the store value.
            if state.title != publishedTitle {
                publishedTitle = state.title
                self.revision += 1
            }
        case .cancel:
            guard generation == cancelGeneration else { return .staleIdentity }
            guard event == EditorEvent.activate.rawValue else { return .unboundEvent }
            guard kind == EditorValue.null.rawValue, input.isEmpty else { return .invalidValue }
            // F05 Cancel publishes the existing state with an empty route stack.
            cancelled = true
            publishedTitle = state.title
            self.revision += 1
        case nil:
            return .staleIdentity
        }
        return .accepted
    }

    mutating func snapshot(into bytes: UnsafeMutablePointer<UInt8>) -> Int {
        // u64le revision, u8 outcome (editing/cancelled), u8 active route count, UTF-8 title.
        for index in 0..<8 {
            bytes[index] = UInt8(truncatingIfNeeded: revision >> (index * 8))
        }
        bytes[8] = cancelled ? 1 : 0
        bytes[9] = cancelled ? 0 : 1
        return Self.headerBytes + publishedTitle.withUTF8 { title in
            if let base = title.baseAddress {
                (bytes + Self.headerBytes).update(from: base, count: title.count)
            }
            return title.count
        }
    }
}
