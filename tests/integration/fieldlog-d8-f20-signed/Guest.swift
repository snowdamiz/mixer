@_extern(c, "fieldlog_storage_get")
func storageGet(_ bytes: UnsafeRawPointer, _ count: UInt32, _ token: UnsafeMutablePointer<UInt64>) -> UInt32
@_extern(c, "fieldlog_poll")
func poll(_ token: UInt64, _ bytes: UnsafeMutableRawPointer, _ capacity: UInt32, _ length: UnsafeMutablePointer<UInt32>) -> UInt32

private let header = 32
private let eventLimit = 4096
private let documentOffset = 4128
private let documentLimit = 8192
private nonisolated(unsafe) var ui = InlineArray<12320, UInt8>(repeating: 0)
private nonisolated(unsafe) var reply = InlineArray<4096, UInt8>(repeating: 0)
private nonisolated(unsafe) var page = InlineArray<2800, UInt8>(repeating: 0)
private nonisolated(unsafe) var rows = InlineArray<20, TaskRow>(repeating: TaskRow())
private nonisolated(unsafe) var token: UInt64 = 0
private nonisolated(unsafe) var waiting = false
private nonisolated(unsafe) var revision: UInt64 = 1
private nonisolated(unsafe) var sequence: UInt64 = 1
private nonisolated(unsafe) var total: UInt64 = 0
private nonisolated(unsafe) var count = 0
private nonisolated(unsafe) var draftsIndex: UInt64 = 0
private nonisolated(unsafe) var entriesIndex: UInt64 = 0
private nonisolated(unsafe) var screen = Screen.home

private enum Screen { case home, drafts, entries, detail }

@_cdecl("mixer_guest_ui_start_v1")
public func guestStart() -> UInt32 {
    withUnsafeMutableBytes(of: &ui) { buffer in
        let base = UInt32(UInt(bitPattern: buffer.baseAddress!))
        buffer.storeBytes(of: UInt32(0x3155494d), as: UInt32.self)
        buffer.storeBytes(of: UInt32(header), toByteOffset: 4, as: UInt32.self)
        buffer.storeBytes(of: base + UInt32(header), toByteOffset: 16, as: UInt32.self)
        buffer.storeBytes(of: UInt32(eventLimit), toByteOffset: 20, as: UInt32.self)
        return base
    }
}

@_cdecl("mixer_guest_ui_hydrate_v1")
public func hydrate() -> UInt32 {
    request("workspace", suffix: .init(start: nil, count: 0)) ? 0 : 1
}

@_cdecl("mixer_guest_ui_event_v1")
public func guestEvent(_ length: UInt32) -> UInt32 {
    #if FIELDLOG_UPDATED
    guard !waiting, length > 0, length <= UInt32(eventLimit) else { return 1 }
    let accepted = withUnsafeBytes(of: &ui) { buffer in
        let event = UnsafeRawBufferPointer(start: buffer.baseAddress! + header, count: Int(length))
        return navigate(event)
    }
    guard accepted else { return 1 }
    revision += 1
    sequence += 1
    if !waiting { publish() }
    return 0
    #else
    return 1
    #endif
}

private func matches(_ bytes: UnsafeRawBufferPointer, _ id: StaticString,
                     suffix: UnsafeRawBufferPointer = .init(start: nil, count: 0)) -> Bool {
    var reader = TaskWireReader(bytes)
    return reader.consume(#"{"actionID":""#) && reader.consume(id) && reader.consume(suffix)
        && reader.consume(#"","event":"activate","nodeID":""#) && reader.consume(id) && reader.consume(suffix)
        && reader.consume(#"","revision":"#) && reader.consume(revision)
        && reader.consume(#","schemaVersion":1,"sequence":"#) && reader.consume(sequence)
        && reader.consume(#","value":null}"#) && reader.atEnd
}

private func navigate(_ event: UnsafeRawBufferPointer) -> Bool {
    if screen == .home {
        return matches(event, "workspace.entries") && requestPage(.drafts, draftsIndex)
    }
    if screen == .detail {
        return matches(event, "detail.back") && requestPage(.drafts, draftsIndex)
    }
    if matches(event, "workspace.tasks") { screen = .home; return true }
    if screen == .drafts {
        if matches(event, "show.entries") { return requestPage(.entries, entriesIndex) }
        if matches(event, "drafts.next"), (draftsIndex + 1) &* 20 < total {
            return requestPage(.drafts, draftsIndex + 1)
        }
        if matches(event, "drafts.previous"), draftsIndex > 0 {
            return requestPage(.drafts, draftsIndex - 1)
        }
        return withUnsafeBytes(of: &page) { data in
            for index in 0..<count {
                let id = UnsafeRawBufferPointer(rebasing: data[rows[index].id])
                if matches(event, "draft.", suffix: id) {
                    guard request("draft-", suffix: id) else { return false }
                    screen = .detail
                    return true
                }
            }
            return false
        }
    }
    if matches(event, "show.drafts") { return requestPage(.drafts, draftsIndex) }
    if matches(event, "entries.next"), (entriesIndex + 1) &* 20 < total {
        return requestPage(.entries, entriesIndex + 1)
    }
    return matches(event, "entries.previous") && entriesIndex > 0 && requestPage(.entries, entriesIndex - 1)
}

private func requestPage(_ destination: Screen, _ index: UInt64) -> Bool {
    guard index <= 2 else { return false }
    let digit = UInt8(index) + 48
    let accepted = withUnsafeBytes(of: digit) {
        request(destination == .drafts ? "drafts-" : "entries-", suffix: $0)
    }
    guard accepted else { return false }
    screen = destination
    if screen == .drafts { draftsIndex = index } else { entriesIndex = index }
    return true
}

private func request(_ prefix: StaticString, suffix: UnsafeRawBufferPointer) -> Bool {
    withUnsafeMutableBytes(of: &reply) { data in
        var out = TaskWireWriter(data)
        out.append(#"{"key":""#)
        out.append(prefix)
        out.append(suffix)
        out.append(#"","namespace":"fieldlog-f20-v1"}"#)
        waiting = storageGet(data.baseAddress!, UInt32(out.count), &token) == 0
        return waiting
    }
}

@_cdecl("mixer_guest_capability_ready_v1")
public func guestReady() {
    guard waiting else { return }
    var length: UInt32 = 0
    let status = withUnsafeMutableBytes(of: &reply) {
        poll(token, $0.baseAddress!, UInt32($0.count), &length)
    }
    if status == 1 { return }
    precondition(status == 0 && readResult(length))
    waiting = false
    publish()
}

private func readResult(_ length: UInt32) -> Bool {
    withUnsafeBytes(of: &reply) { reply in
        guard length <= reply.count else { return false }
        var envelope = TaskWireReader(.init(rebasing: reply[..<Int(length)]))
        guard envelope.consume(#"{"abi":1,"capability":"storage.keyValue.v1","operation":"get","outcome":{"kind":"success","value":{"found":true,"valueBase64":""#) else { return false }
        return withUnsafeMutableBytes(of: &page) { page in
            guard let length = envelope.decodeBase64(into: page),
                  envelope.consume(#""}},"schemaHash":"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"}"#),
                  envelope.atEnd else { return false }
            var data = TaskWireReader(.init(rebasing: page[..<length]))
            guard let totalRecords = data.revisionLine(), let rowCount = data.revisionLine(),
                  totalRecords <= 60, rowCount <= 20 else { return false }
            if screen == .home {
                guard totalRecords == 46, rowCount == 0 else { return false }
            } else if screen == .detail {
                guard totalRecords == 2, rowCount == 2 else { return false }
            } else {
                let index = screen == .drafts ? draftsIndex : entriesIndex
                guard index &* 20 < totalRecords, rowCount == min(20, totalRecords - index &* 20) else { return false }
            }
            for index in 0..<Int(rowCount) {
                guard let row = data.row() else { return false }
                rows[index] = row
            }
            guard data.atEnd else { return false }
            total = totalRecords
            count = Int(rowCount)
            return true
        }
    }
}

private func publish() {
    withUnsafeMutableBytes(of: &ui) { buffer in
        var out = TaskWireWriter(.init(start: buffer.baseAddress! + documentOffset, count: documentLimit))
        out.append(#"{"schemaVersion":1,"revision":"#)
        out.append(revision)
        out.append(#","root":{"id":"entries.host","kind":"vStack","properties":{},"actions":[],"children":["#)
        render(&out)
        out.append("]}}")
        let base = UInt32(UInt(bitPattern: buffer.baseAddress!))
        buffer.storeBytes(of: base + UInt32(documentOffset), toByteOffset: 8, as: UInt32.self)
        buffer.storeBytes(of: UInt32(out.count), toByteOffset: 12, as: UInt32.self)
    }
}

private func render(_ out: inout TaskWireWriter) {
    if screen == .home {
        #if FIELDLOG_UPDATED
        node("workspace.entries", button: true, &out) { $0.append("Entries") }
        #else
        node("workspace.home", button: false, &out) { $0.append("Workspace") }
        #endif
        return
    }
    if screen == .detail {
        node("detail.back", button: true, &out) { $0.append("Saved drafts") }
        out.append(",")
        renderRow(0, id: "draft.title", includeID: false, button: false, &out)
        out.append(",")
        renderRow(1, id: "draft.note", includeID: false, button: false, &out)
        return
    }

    let drafts = screen == .drafts
    let index = drafts ? draftsIndex : entriesIndex
    node("workspace.tasks", button: true, &out) { $0.append("Tasks") }
    out.append(",")
    node(drafts ? "show.entries" : "show.drafts", button: true, &out) {
        $0.append(drafts ? "Saved entries" : "Saved drafts")
    }
    out.append(",")
    node(drafts ? "drafts.position" : "entries.position", button: false, &out) {
        $0.append("Page ")
        $0.append(index + 1)
        $0.append(" of ")
        $0.append((total + 19) / 20)
        $0.append(" · ")
        $0.append(total)
        $0.append(drafts ? " drafts" : " entries")
    }
    out.append(",")
    node(drafts ? "drafts.previous" : "entries.previous", button: true, disabled: index == 0, &out) {
        $0.append(drafts ? "Previous drafts" : "Previous entries")
    }
    out.append(",")
    node(drafts ? "drafts.next" : "entries.next", button: true, disabled: (index + 1) &* 20 >= total, &out) {
        $0.append(drafts ? "Next drafts" : "Next entries")
    }
    for index in 0..<count {
        out.append(",")
        renderRow(index, id: drafts ? "draft." : "entry.", includeID: true, button: drafts, &out)
    }
}

private func renderRow(_ index: Int, id: StaticString, includeID: Bool, button: Bool, _ out: inout TaskWireWriter) {
    withUnsafeBytes(of: &page) { data in
        let row = rows[index]
        let suffix = includeID ? UnsafeRawBufferPointer(rebasing: data[row.id]) : .init(start: nil, count: 0)
        node(id, suffix: suffix, button: button, &out) {
            $0.appendEscapedTitle(.init(rebasing: data[row.title]))
        }
    }
}

private func node(_ id: StaticString, suffix: UnsafeRawBufferPointer = .init(start: nil, count: 0),
                  button: Bool, disabled: Bool = false, _ out: inout TaskWireWriter,
                  label: (inout TaskWireWriter) -> Void) {
    out.append(#"{"id":""#)
    out.append(id)
    out.append(suffix)
    out.append(button ? #"","kind":"button","properties":{"label":""# : #"","kind":"text","properties":{"text":""#)
    label(&out)
    if button {
        out.append(disabled ? #"","disabled":true},"actions":[{"id":""# : #"","disabled":false},"actions":[{"id":""#)
        out.append(id)
        out.append(suffix)
        out.append(#"","event":"activate"}],"children":[]}"#)
    } else {
        out.append(#""},"actions":[],"children":[]}"#)
    }
}
