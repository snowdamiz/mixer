// State projection of the historical TaskEditor and TaskEditorPresentation.
// replay.py supplies the title and successful Save transitions from the pinned editor.

enum EditorReply: UInt32 {
    case accepted, closed, staleRevision, staleIdentity, unboundEvent, invalidValue, disabled
}

enum EditorNode: Int32 {
    case title = 1, cancel, save
}

enum EditorEvent: Int32 {
    case textChange = 1, activate
}

enum EditorValue: Int32 {
    case null, text, boolean
}

struct TitleState {
    var title = ""
    let responsible = ""
    var saving = false
    var saved = false
    var failure: String?
}

struct SaveTaskEffect {
    let title: String
    let responsible: String
}

struct EditorBoundary {
    static let maximumTitleBytes = 16_384
    static let headerBytes = 10
    static let bufferBytes = headerBytes + maximumTitleBytes

    private let titleGeneration: UInt64
    private let cancelGeneration: UInt64
    private let saveGeneration: UInt64
    private var state = TitleState()
    private var publishedTitle = ""
    private var revision: UInt64 = 1
    private var cancelled = false
    private var pendingSave: SaveTaskEffect?

    init(titleGeneration: UInt64, cancelGeneration: UInt64, saveGeneration: UInt64 = 0) {
        self.titleGeneration = titleGeneration
        self.cancelGeneration = cancelGeneration
        self.saveGeneration = saveGeneration
    }

    mutating func send(
        revision: UInt64, node: Int32, generation: UInt64,
        event: Int32, kind: Int32, input: UnsafeBufferPointer<UInt8>
    ) -> EditorReply {
        guard !cancelled && !state.saved else { return .closed }
        guard revision == self.revision else { return .staleRevision }
        switch EditorNode(rawValue: node) {
        case .title:
            guard generation == titleGeneration else { return .staleIdentity }
            guard !state.saving else { return .disabled }
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
            guard !state.saving else { return .disabled }
            guard event == EditorEvent.activate.rawValue else { return .unboundEvent }
            guard kind == EditorValue.null.rawValue, input.isEmpty else { return .invalidValue }
            // F05 Cancel publishes the existing state with an empty route stack.
            cancelled = true
            publishedTitle = state.title
            self.revision += 1
        case .save:
            guard saveGeneration != 0, generation == saveGeneration else { return .staleIdentity }
            guard !state.saving && !state.title.isEmpty else { return .disabled }
            guard event == EditorEvent.activate.rawValue else { return .unboundEvent }
            guard kind == EditorValue.null.rawValue, input.isEmpty else { return .invalidValue }
            // The successful Save projection admits unpadded printable ASCII titles only.
            let title = state.title.utf8
            guard title.count <= 240, title.first != 32, title.last != 32,
                  title.allSatisfy({ (32...126).contains($0) }) else { return .invalidValue }
            pendingSave = state.beginSave()
            publishedTitle = state.title
            self.revision += 1
        case nil:
            return .staleIdentity
        }
        return .accepted
    }

    mutating func takeSave(into bytes: UnsafeMutablePointer<UInt8>) -> Int {
        guard let effect = pendingSave, effect.responsible.isEmpty else { return 0 }
        pendingSave = nil
        return copyUTF8(effect.title, into: bytes)
    }

    mutating func completeSave() -> EditorReply {
        guard state.saving, pendingSave == nil else { return .closed }
        state.finishSave()
        revision += 1
        return .accepted
    }

    mutating func snapshot(into bytes: UnsafeMutablePointer<UInt8>) -> Int {
        // u64le revision, u8 phase (editing/cancelled/saving/saved), u8 route count, UTF-8 title.
        for index in 0..<8 {
            bytes[index] = UInt8(truncatingIfNeeded: revision >> (index * 8))
        }
        bytes[8] = cancelled ? 1 : state.saving ? 2 : state.saved ? 3 : 0
        bytes[9] = cancelled || state.saved ? 0 : 1
        return Self.headerBytes + copyUTF8(publishedTitle, into: bytes + Self.headerBytes)
    }

    private func copyUTF8(_ value: String, into bytes: UnsafeMutablePointer<UInt8>) -> Int {
        var value = value
        return value.withUTF8 { title in
            if let base = title.baseAddress {
                bytes.update(from: base, count: title.count)
            }
            return title.count
        }
    }
}
