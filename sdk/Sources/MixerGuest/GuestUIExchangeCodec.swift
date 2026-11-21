import Foundation
import MixerUI

// Wire witnesses contain no revision, presentation, effect or event-slot state.
struct GuestUIExchangeCodec: Sendable {
    enum StartupPresentation { case afterEffects, beforeEffects }
    var startupPresentation: StartupPresentation = .afterEffects
    var issuedEventByteLimit: Int? = nil
    let maximumBytes: Int
    let decode: @Sendable (Data) throws -> ValidatedUIDocument
    let accepts: @Sendable (RoutedUIAction, UIEventEnvelope, UIDocument) -> Bool
    let encodeEvent: @Sendable (UInt64, RoutedUIAction, UIDocument) throws -> Data
    static let legacy: Self = {
        let validator = UIValidator(limits: UIValidationLimits(maximumMessageBytes: 65536,
            maximumNodes: 256, maximumDepth: 16, maximumChildrenPerNode: 64, maximumStringBytes: 4096),
            supportedKinds: [.vStack, .text, .button])
        return Self(maximumBytes: 65536, decode: { try GuestUICodec(validator: validator).decode($0) },
            accepts: { action, _, _ in action.event == .activate && action.value == .null },
            encodeEvent: { sequence, action, _ in try GuestUIEventCodecV1.encode(GuestUIEventV1(
                sequence: sequence, revision: action.revision, nodeID: action.nodeID, actionID: action.actionID)) })
    }()
    static func editor(_ codec: GuestUIDocumentCodecV2) -> Self {
        Self(maximumBytes: GuestUIProtocolV2.maximumBytes, decode: { try codec.decode($0) },
            accepts: { codec.accepts($0, envelope: $1, document: $2) }, encodeEvent: { sequence, action, document in
                guard let node = codec.node(id: action.nodeID, in: document) else { throw GuestUIEditorErrorV2.routing }
                let payload: GuestUIEventPayloadV2
                switch (action.event, action.value) {
                case (.activate, .null): payload = .activate
                case (.textChange, .string(let value)): payload = .textChange(value)
                default: throw GuestUIEditorErrorV2.value
                }
                return try GuestUIEventCodecV2.encode(GuestUIEventV2(sequence: sequence, revision: action.revision,
                    node: node, payload: payload, textValuePolicy: codec.textValuePolicy))
            })
    }
    static func feature(_ codec: FeatureDocumentV3) -> Self {
        Self(startupPresentation: .beforeEffects, maximumBytes: GuestUIProtocolV3.maximumBytes, decode: { try codec.decode($0) },
            accepts: { codec.accepts($0, envelope: $1, document: $2) }, encodeEvent: { sequence, action, document in
                guard let node = codec.node(id: action.nodeID, in: document) else { throw GuestUIFeatureErrorV3.routing }
                let payload: GuestUIEventPayloadV3
                switch (action.event, action.value) {
                case (.activate, .null): payload = .activate
                case (.textChange, .string(let value)): payload = .textChange(value)
                default: throw GuestUIFeatureErrorV3.value
                }
                return try GuestUIEventCodecV3.encode(GuestUIEventV3(sequence: sequence, revision: action.revision,
                    node: node, payload: payload, textValuePolicy: codec.textValuePolicy))
            })
    }
}
