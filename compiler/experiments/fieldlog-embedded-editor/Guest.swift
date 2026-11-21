nonisolated(unsafe) private var editor = EditorBoundary(titleGeneration: 0, cancelGeneration: 0)
nonisolated(unsafe) private let buffer = UnsafeMutablePointer<UInt8>.allocate(
    capacity: EditorBoundary.bufferBytes
)

@_cdecl("fieldlog_editor_open")
public func openEditor(_ titleGeneration: UInt64, _ cancelGeneration: UInt64) -> UnsafeMutablePointer<UInt8> {
    editor = EditorBoundary(titleGeneration: titleGeneration, cancelGeneration: cancelGeneration)
    return buffer
}

@_cdecl("fieldlog_editor_send")
public func sendEditor(
    _ revision: UInt64, _ node: Int32, _ generation: UInt64,
    _ event: Int32, _ kind: Int32, _ length: UInt32
) -> UInt32 {
    guard length <= EditorBoundary.bufferBytes else { return EditorReply.invalidValue.rawValue }
    let input = UnsafeBufferPointer(start: buffer, count: Int(length))
    return editor.send(revision: revision, node: node, generation: generation,
                       event: event, kind: kind, input: input).rawValue
}

@_cdecl("fieldlog_editor_snapshot")
public func editorSnapshot() -> Int {
    editor.snapshot(into: buffer)
}
