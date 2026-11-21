#if os(macOS) && MIXER_PRIVATE_FIELDLOG_EDITOR
import Foundation
import MixerUI

extension GuestUIExchangeCodec {
    static var fieldLogEditor: Self {
        let document = FeatureDocumentV3(textValuePolicy: .standard)
        return Self(issuedEventByteLimit: 4096, maximumBytes: 65_536, decode: document.decode,
            accepts: { action, envelope, frame in
                guard document.accepts(action, envelope: envelope, document: frame) else { return false }
                switch (action.nodeID, action.actionID, action.event, action.value) {
                case ("task.title", "task.title.change", .textChange, .string(let value)):
                    return !value.utf8.contains(13)
                case ("task.cancel", "task.cancel", .activate, .null),
                     ("task.save", "task.save", .activate, .null):
                    return true
                default:
                    return false
                }
            }, encodeEvent: { sequence, action, _ in
                let payload: GuestUIEventPayloadV2
                switch (action.event, action.value) {
                case (.activate, .null): payload = .activate
                case (.textChange, .string(let value)): payload = .textChange(value)
                default: throw GuestUIEditorErrorV2.routing
                }
                return try GuestUIEventCodecV2.encode(sequence: sequence, revision: action.revision,
                    nodeID: action.nodeID, actionID: action.actionID, payload: payload)
            })
    }
}
#endif
