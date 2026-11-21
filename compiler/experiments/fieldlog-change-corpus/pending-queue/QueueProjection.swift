// FieldLog F10 projection. This file is compiled unchanged by both Swift hosts.
// The application boundary supplies only ordered pending IDs, kinds and task titles.
struct QueuePage {
    static let size = 20
    static let maximumRecords = 50_000
    // Count (u16 LE), followed by up to 20 rows: 36 ASCII ID bytes,
    // kind (u8), title length (u8), then exactly that many UTF-8 title bytes.
    static let maximumBytes = 2 + size * (38 + 240)

    let index: Int
    let total: Int
    var last: Int { max(0, (total - 1) / Self.size) }
    var start: Int { index * Self.size }
    var count: Int { min(Self.size, total - start) }

    init?(index: Int, total: Int) {
        guard (0...Self.maximumRecords).contains(total), index >= 0,
              index <= max(0, (total - 1) / Self.size) else { return nil }
        self.index = index
        self.total = total
    }
}

enum QueueAction {
    case open, tasks, entries, previous, next
    var id: StaticString {
        switch self {
        case .open: "workspace.queue"
        case .tasks: "workspace.back"
        case .entries: "workspace.entries"
        case .previous: "queue.previous"
        case .next: "queue.next"
        }
    }
}

struct QueueNavigation {
    enum Screen { case tasks, queue, entries }
    private(set) var screen: Screen = .tasks
    var page = 0

    // An unavailable action leaves navigation and the repository untouched.
    mutating func activate(_ action: QueueAction, current: QueuePage) -> Bool {
        switch (screen, action) {
        case (.tasks, .open): screen = .queue
        case (.queue, .tasks): screen = .tasks
        case (.queue, .entries): screen = .entries
        case (.queue, .previous) where current.index > 0: page = current.index - 1
        case (.queue, .next) where current.index < current.last: page = current.index + 1
        default: return false
        }
        return true
    }

    func render(revision: UInt64, pageIndex: Int, payload: UnsafeRawBufferPointer,
                into destination: UnsafeMutableRawBufferPointer, loading: Bool = false,
                historicalLayout: Bool = false) -> Int {
        var input = QueueBytes(payload)
        guard let low = input.byte(), let high = input.byte(),
              let page = QueuePage(index: pageIndex, total: Int(low) + 256 * Int(high)) else { return 0 }

        var out = QueueOutput(destination)
        out.write(#"{"schemaVersion":1,"revision":"#)
        out.decimal(revision)
        if historicalLayout && screen == .queue {
            out.write(#","root":{"id":"task.screen","kind":"navigation","properties":{"title":"On device"},"actions":[],"children":[{"id":"task.form","kind":"list","properties":{},"actions":[],"children":[{"id":"queue.summary","kind":"section","properties":{"title":"On device"},"actions":[],"children":["#)
        } else {
            out.write(#","root":{"id":"task.screen","kind":"vStack","properties":{},"actions":[],"children":["#)
        }
        switch screen {
        case .tasks:
            out.button(.open, disabled: false, accessibility: "workspace-on-device") { text in
                text.write("On device · ")
                text.decimal(UInt64(page.total))
                text.write(" pending changes · Not sent")
            }
        case .entries:
            // The feature hands off to the existing Entries route at this boundary.
            out.text("workspace.entries.destination") { $0.write("Entries") }
        case .queue:
            out.text("queue.explanation") {
                $0.write("Your records are saved locally. Cloud sync isn't connected. Nothing in this queue has been sent to a server.")
            }
            out.write(",")
            out.button(.tasks, disabled: historicalLayout ? nil : loading, accessibility: "workspace-tasks") {
                $0.write("Tasks")
            }
            out.write(",")
            out.button(.entries, disabled: historicalLayout ? nil : loading, accessibility: "workspace-entries") {
                $0.write("Entries")
            }
            if historicalLayout {
                out.write(#"]},{"id":"queue.changes","kind":"section","properties":{"title":"Pending changes ("#)
            } else {
                out.write(#",{"id":"queue.changes","kind":"text","properties":{"text":"Pending changes ("#)
            }
            out.decimal(UInt64(page.total))
            out.write(historicalLayout ? #")"},"actions":[],"children":["# : #")"},"actions":[],"children":[]},"#)
            out.text("queue.position") { text in
                text.write("Page ")
                text.decimal(UInt64(page.index + 1))
                text.write(" of ")
                text.decimal(UInt64(page.last + 1))
                text.write(" · Changes ")
                text.decimal(UInt64(page.total == 0 ? 0 : page.start + 1))
                text.write("–")
                text.decimal(UInt64(page.start + page.count))
                text.write(" of ")
                text.decimal(UInt64(page.total))
                text.write(" · Newest first")
            }
            out.write(",")
            out.button(.previous, disabled: loading || page.index == 0, accessibility: "queue.previous") {
                $0.write("Previous")
            }
            out.write(",")
            out.button(.next, disabled: loading || page.index == page.last, accessibility: "queue.next") {
                $0.write("Next")
            }
            if page.total == 0 {
                out.write(",")
                out.text("queue.empty") { $0.write("Changes you make will appear here.") }
            }
        }
        // Walk the same page grammar regardless of the currently displayed route.
        for _ in 0..<page.count {
            guard let id = input.take(36), let kind = input.byte(), kind <= 3,
                  let length = input.byte(), length <= 240,
                  let title = input.take(Int(length)),
                  (kind == 1) == !title.isEmpty else { return 0 }
            if screen != .queue { continue }
            out.write(#",{"id":"pending."#)
            for byte in id { out.append(byte) }
            out.write(#"","kind":"text","properties":{"text":""#)
            switch kind {
            case 0: out.write("Project created")
            case 1:
                out.write("Task updated: ")
                for byte in title { out.escape(byte) }
            case 2: out.write("Checklist reordered")
            default: out.write("Entry saved")
            }
            out.write(#" — Saved on device · Not sent"},"actions":[],"children":[]}"#)
        }
        guard input.atEnd else { return 0 }
        if historicalLayout && screen == .queue { out.write("]}]}") }
        out.write("]}}")
        return out.result
    }
}

struct QueueBytes {
    private let bytes: UnsafeRawBufferPointer
    private var offset = 0
    var atEnd: Bool { offset == bytes.count }

    init(_ bytes: UnsafeRawBufferPointer) { self.bytes = bytes }

    mutating func take(_ count: Int) -> UnsafeRawBufferPointer? {
        guard count <= bytes.count - offset else { return nil }
        defer { offset += count }
        return UnsafeRawBufferPointer(rebasing: bytes[offset..<(offset + count)])
    }

    mutating func byte() -> UInt8? { take(1)?[0] }

    mutating func expect(_ text: StaticString) -> Bool {
        guard let candidate = take(text.utf8CodeUnitCount) else { return false }
        for index in 0..<candidate.count where candidate[index] != text.utf8Start[index] { return false }
        return true
    }
}

struct QueueOutput {
    private let bytes: UnsafeMutableRawBufferPointer
    private(set) var count = 0
    var result: Int { count <= bytes.count ? count : 0 }

    init(_ bytes: UnsafeMutableRawBufferPointer) { self.bytes = bytes }

    mutating func append(_ byte: UInt8) {
        if count < bytes.count { bytes[count] = byte }
        count += 1
    }

    mutating func write(_ text: StaticString) {
        for index in 0..<text.utf8CodeUnitCount { append(text.utf8Start[index]) }
    }

    mutating func decimal(_ value: UInt64) {
        var divisor: UInt64 = 1
        while value / divisor >= 10 { divisor &*= 10 }
        while divisor > 0 {
            append(48 + UInt8((value / divisor) % 10))
            divisor /= 10
        }
    }

    mutating func escape(_ byte: UInt8) {
        switch byte {
        case 34, 92: append(92); append(byte)
        case 0...31:
            write(#"\u00"#)
            let hex: StaticString = "0123456789abcdef"
            append(hex.utf8Start[Int(byte >> 4)])
            append(hex.utf8Start[Int(byte & 15)])
        default: append(byte)
        }
    }

    mutating func text(_ id: StaticString, label: (inout Self) -> Void) {
        write(#"{"id":""#)
        write(id)
        write(#"","kind":"text","properties":{"text":""#)
        label(&self)
        write(#""},"actions":[],"children":[]}"#)
    }

    mutating func button(_ action: QueueAction, disabled: Bool?, accessibility: StaticString,
                         label: (inout Self) -> Void) {
        write(#"{"id":""#)
        write(action.id)
        write(#"","kind":"button","properties":{"label":""#)
        label(&self)
        write(#"","role":"normal","accessibilityIdentifier":""#)
        write(accessibility)
        write("\"")
        if let disabled {
            write(#","disabled":"#)
            write(disabled ? "true" : "false")
        }
        write(#"},"children":[],"actions":[{"id":""#)
        write(action.id)
        write(#"","event":"activate"}]}"#)
    }
}
