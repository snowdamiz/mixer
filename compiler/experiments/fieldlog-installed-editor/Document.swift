// Mirrors the original TaskEditorPresentation hierarchy and keeps the missing
// axis in F05 distinct from the explicitly vertical title in F06.
func render(_ output: inout EditorWireOutput, revision: UInt64, phase: UInt8, title: UnsafeBufferPointer<UInt8>) {
    let inactive = phase != 0
    let saving = phase == 2
    let hasTitle = String(validating: title, as: UTF8.self)?.unicodeScalars.contains { scalar in
        switch scalar.value {
        case 9...13, 32, 0x85, 0xa0, 0x1680, 0x2000...0x200b, 0x2028, 0x2029, 0x202f, 0x205f, 0x3000:
            return false
        default: return true
        }
    } ?? false

    output.write(#"{"featureSchemaVersion":3,"document":{"revision":"#)
    output.decimal(revision)
    output.write(#","schemaVersion":1,"root":{"id":"task.screen","kind":"navigation","properties":{"title":"New task"},"actions":[],"children":["#)
    output.write(#"{"id":"task.form","kind":"list","properties":{},"actions":[],"children":["#)
    output.write(#"{"id":"task.fields","kind":"section","properties":{"title":"Task"},"actions":[],"children":["#)
    output.write(#"{"id":"task.title","kind":"textField","actions":[{"id":"task.title.change","event":"textChange"}],"children":[],"properties":{"label":"What needs to happen?","accessibilityIdentifier":"task-title","#)
#if FIELDLOG_F06
    output.write(#""axis":"vertical","#)
#endif
    output.write(#""disabled":"#)
    output.boolean(inactive)
    output.write(#","value":"#)
    output.title(title)
    output.write(#"}},{"id":"task.responsible","kind":"textField","actions":[{"id":"task.responsible.change","event":"textChange"}],"children":[],"properties":{"label":"Responsible person (optional)","value":"","disabled":"#)
    output.boolean(inactive)
    output.write(#"}}]},"#)
    output.write(#"{"id":"task.disclosure","kind":"section","properties":{},"actions":[],"children":[{"id":"task.disclosure.message","kind":"text","actions":[],"children":[],"properties":{"text":"A responsibility label is stored locally. It does not invite or notify another person.","style":"caption","selectable":false}}]},"#)
    output.write(#"{"id":"task.actions","kind":"section","properties":{},"actions":[],"children":["#)
    output.write(#"{"id":"task.cancel","kind":"button","actions":[{"id":"task.cancel","event":"activate"}],"children":[],"properties":{"label":"Cancel","role":"cancel","disabled":"#)
    output.boolean(inactive)
    output.write(#"}},{"id":"task.save","kind":"button","actions":[{"id":"task.save","event":"activate"}],"children":[],"properties":{"role":"normal","disabled":"#)
    output.boolean(inactive || !hasTitle)
    output.write(#","label":"#)
    output.write(saving ? #""Saving…""# : #""Add""#)
    output.write(#"}}]}]}]}}}"#)
}
