#if os(macOS) && MIXER_PRIVATE_FIELDLOG_EDITOR
import Foundation
import MixerUI

enum GuestUIFieldLogNoteFixture {
    static let field = "entry.f1100000-0000-4000-8000-000000000001.note"
    static let action = "entry.note.change"
    static let original = "Café e\u{0301} 👩🏽‍🔬\n東京\n\nLast line\n"
    static let edited = original + "Edited"

    static let codec = GuestUIExchangeCodec(maximumBytes: 4096, decode: { bytes in
        let validator = UIValidator(limits: .init(maximumMessageBytes: 4096, maximumNodes: 2,
            maximumDepth: 2, maximumChildrenPerNode: 1, maximumStringBytes: 256),
            supportedKinds: [.vStack, .textField], supportedTextFieldAxes: [.vertical])
        let frame = try GuestUICodec(validator: validator).decode(bytes)
        let root = frame.document.root
        let revision = frame.document.revision
        guard revision == 1 || revision == 2,
              root.id == "entry-editor", root.kind == .vStack, root.actions.isEmpty,
              root.properties.isEmpty, root.children.count == 1,
              let note = root.children.first, note.id == field, note.kind == .textField,
              note.children.isEmpty, note.actions == [.init(id: action, event: .textChange)],
              Set(note.properties.keys) == ["axis", "label", "value"],
              note.properties["axis"] == .string("vertical"), note.properties["label"] == .string("Note"),
              note.properties["value"]?.string?.utf8.elementsEqual((revision == 1 ? original : edited).utf8) == true
        else { throw GuestUIEditorErrorV2.routing }
        return frame
    }, accepts: { routed, _, frame in
        guard routed.nodeID == field, routed.actionID == action, routed.event == .textChange,
              routed.revision == 1, frame.revision == 1,
              case .string(let value) = routed.value else { return false }
        return value.utf8.elementsEqual(edited.utf8)
    }, encodeEvent: { sequence, routed, _ in
        guard case .string(let value) = routed.value else { throw GuestUIEditorErrorV2.routing }
        return try GuestUIEventCodecV2.encode(sequence: sequence, revision: routed.revision,
            nodeID: routed.nodeID, actionID: routed.actionID, payload: .textChange(value))
    })

    static func admitsFirstDocument(_ frame: UIDocument) -> Bool { frame.revision == 1 }
}
#endif
