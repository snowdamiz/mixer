import Foundation
import MixerCore
import MixerUI

/// Unselected host/data candidate. No installed identity, VM validator or runner selects this API.
@_spi(GuestUIV2) public enum GuestUIProtocolV2 {
    public static let contractDependency = "mixer.guest-ui-event-v2"
    public static let headerDependency = "mixer.guest-ui-native-header-v2"
    public static let startupExport = "mixer_guest_ui_start_v2"
    public static let eventExport = "mixer_guest_ui_event_v2"
    public static let readyExport = "mixer_guest_capability_ready_v1"
    public static let maximumBytes = 1_048_576
    public static let magic: UInt32 = 0x3249554d // little-endian MUI2
}

@_spi(GuestUIV2) public enum GuestUIEditorErrorV2: Error, Equatable {
    case messageTooLarge, malformed, fields, integer, identifier, value, routing, axis, header, range, bufferChanged
}

/// Shape of the two wire variants; only GuestUIEventV2 can admit a payload.
@_spi(GuestUIV2) public enum GuestUIEventPayloadV2: Sendable {
    case activate
    case textChange(String)
}

@_spi(GuestUIV2) public struct GuestUIDocumentCodecV2: Sendable {
    public let textValuePolicy: UITextValuePolicy
    public let validator: UIValidator
    /// Explicit policy is required; construction grants no runtime authority.
    public init(textValuePolicy: UITextValuePolicy) {
        self.textValuePolicy = textValuePolicy
        validator = UIValidator(limits: UIValidationLimits(maximumMessageBytes: GuestUIProtocolV2.maximumBytes,
            maximumNodes: 256, maximumDepth: 16, maximumChildrenPerNode: 64, maximumStringBytes: 4096),
            supportedKinds: [.vStack, .text, .button, .textField],
            supportedTextFieldAxes: [.horizontal, .vertical], textValuePolicy: textValuePolicy)
    }
    public func decode(_ data: Data) throws -> ValidatedUIDocument {
        let result = try GuestUICodec(validator: validator).decode(data)
        try check(result.document)
        return result
    }
    public func encode(_ document: UIDocument) throws -> Data {
        try check(document)
        return try GuestUICodec(validator: validator).encode(document)
    }
    private func check(_ document: UIDocument) throws {
        guard document.revision > 0 else { throw GuestUIEditorErrorV2.integer }
        var pending = [document.root]
        var count = 0
        while let node = pending.popLast() {
            count += 1
            guard count <= 256, pending.count + node.children.count <= 256 else { throw GuestUIEditorErrorV2.value }
            if node.kind == .textField {
                guard let axis = node.properties["axis"]?.string,
                      axis == "vertical" || axis == "horizontal" else { throw GuestUIEditorErrorV2.axis }
            }
            // Existing UI-v1 permits submit; this candidate deliberately has only two event variants.
            guard node.actions.allSatisfy({ $0.event == .activate || $0.event == .textChange }) else {
                throw GuestUIEditorErrorV2.routing
            }
            for value in node.properties.values {
                if case .string(let string) = value, string.utf8.contains(0) { throw GuestUIEditorErrorV2.value }
            }
            pending.append(contentsOf: node.children)
        }
    }
    func node(id: String, in document: UIDocument) -> UINode? {
        var pending = [document.root]
        while let node = pending.popLast() {
            if node.id.utf8.elementsEqual(id.utf8) { return node }
            pending.append(contentsOf: node.children)
        }
        return nil
    }
    func accepts(_ action: RoutedUIAction, envelope: UIEventEnvelope, document: UIDocument) -> Bool {
        guard action.nodeID.utf8.elementsEqual(envelope.identity.id.utf8),
              let node = node(id: action.nodeID, in: document) else { return false }
        switch (action.event, action.value) {
        case (.activate, .null): return node.kind == .button
        case (.textChange, .string(let value)):
            return node.kind == .textField && !value.utf8.contains(0) &&
                textValuePolicy.accepts(value, for: node, maximumStringBytes: 4096)
        default: return false
        }
    }
}

/// No Codable entry point. IDs and action authority derive from a checked routed node.
@_spi(GuestUIV2) public struct GuestUIEventV2: Sendable {
    public let sequence: UInt64
    public let revision: UInt64
    public let nodeID: String
    public let actionID: String
    public let payload: GuestUIEventPayloadV2
    public init(sequence: UInt64, revision: UInt64, node: UINode,
                payload: GuestUIEventPayloadV2, textValuePolicy: UITextValuePolicy) throws {
        guard sequence > 0, revision > 0 else { throw GuestUIEditorErrorV2.integer }
        let codec = GuestUIDocumentCodecV2(textValuePolicy: textValuePolicy)
        _ = try codec.encode(UIDocument(revision: revision, root: node))
        let event: UIEventKind
        switch payload {
        case .activate:
            guard node.kind == .button else { throw GuestUIEditorErrorV2.routing }; event = .activate
        case .textChange(let value):
            guard node.kind == .textField, !value.utf8.contains(0),
                  textValuePolicy.accepts(value, for: node, maximumStringBytes: 4096) else {
                throw GuestUIEditorErrorV2.value
            }
            event = .textChange
        }
        guard guestUIIdentifierV1(node.id), let binding = node.actions.first(where: { $0.event == event }),
              guestUIIdentifierV1(binding.id) else { throw GuestUIEditorErrorV2.identifier }
        self.sequence = sequence; self.revision = revision; nodeID = node.id
        actionID = binding.id; self.payload = payload
    }
}

@_spi(GuestUIV2) public enum GuestUIEventCodecV2 {
    public static func encode(_ value: GuestUIEventV2) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.withoutEscapingSlashes]
        var bytes = Data(#"{"actionID":"#.utf8); bytes.append(try encoder.encode(value.actionID))
        switch value.payload {
        case .activate: bytes.append(Data(#","event":"activate","nodeID":"#.utf8))
        case .textChange: bytes.append(Data(#","event":"textChange","nodeID":"#.utf8))
        }
        bytes.append(try encoder.encode(value.nodeID))
        bytes.append(Data(",\"revision\":\(value.revision),\"schemaVersion\":1,\"sequence\":\(value.sequence),\"value\":".utf8))
        switch value.payload {
        case .activate: bytes.append(Data("null".utf8))
        case .textChange(let text): bytes.append(try encoder.encode(text))
        }
        bytes.append(125)
        guard bytes.count <= GuestUIProtocolV2.maximumBytes else { throw GuestUIEditorErrorV2.messageTooLarge }
        return bytes
    }
    /// The original UI-v1 envelope schema is retained; V2 selection uses separate exports/dependencies/header.
    public static func decode(_ data: Data, node: UINode, textValuePolicy: UITextValuePolicy) throws -> GuestUIEventV2 {
        guard data.count <= GuestUIProtocolV2.maximumBytes else { throw GuestUIEditorErrorV2.messageTooLarge }
        do {
            try JSONInputGuard.validate(data, limits: JSONInputLimits(maximumBytes: GuestUIProtocolV2.maximumBytes,
                maximumDepth: 1, maximumValues: 8, maximumStringBytes: textValuePolicy == .longNoteV1 ? 100_000 : 4096,
                maximumKeyBytes: 32))
            var parser = GuestUIFlatEventV1(bytes: Array(data))
            let fields = try parser.object()
            guard Set(fields.keys) == ["schemaVersion", "sequence", "revision", "nodeID", "actionID", "event", "value"],
                  fields["schemaVersion"] == .literal("1"),
                  case .string(let nodeID)? = fields["nodeID"], case .string(let actionID)? = fields["actionID"] else {
                throw GuestUIEditorErrorV2.fields
            }
            let payload: GuestUIEventPayloadV2
            switch (fields["event"], fields["value"]) {
            case (.string("activate")?, .literal("null")?): payload = .activate
            case (.string("textChange")?, .string(let text)?): payload = .textChange(text)
            default: throw GuestUIEditorErrorV2.fields
            }
            func positive(_ key: String) throws -> UInt64 {
                guard case .literal(let raw)? = fields[key], let first = raw.utf8.first,
                      (49...57).contains(first), raw.utf8.allSatisfy({ (48...57).contains($0) }),
                      raw.utf8.count <= 20, let value = UInt64(raw), value > 0 else { throw GuestUIEditorErrorV2.integer }
                return value
            }
            let result = try GuestUIEventV2(sequence: positive("sequence"), revision: positive("revision"),
                node: node, payload: payload, textValuePolicy: textValuePolicy)
            guard nodeID.utf8.elementsEqual(result.nodeID.utf8), actionID.utf8.elementsEqual(result.actionID.utf8) else {
                throw GuestUIEditorErrorV2.routing
            }
            return result
        } catch let error as GuestUIEditorErrorV2 { throw error }
        catch { throw GuestUIEditorErrorV2.malformed }
    }
}

/// Pure checked 32-byte header. Actual guest copying/exports/validation are not implemented here.
@_spi(GuestUIV2) public struct GuestUIHeaderV2: Sendable {
    public let headerOffset: UInt32
    public let documentOffset: UInt32
    public let documentLength: UInt32
    public let eventOffset: UInt32
    public static func decode(_ bytes: Data, at headerOffset: UInt32, memoryBytes: UInt64,
                              previous: GuestUIHeaderV2? = nil) throws -> GuestUIHeaderV2 {
        guard bytes.count == 32 else { throw GuestUIEditorErrorV2.header }
        let raw = Array(bytes)
        func u32(_ offset: Int) -> UInt32 {
            (0..<4).reduce(UInt32(0)) { $0 | UInt32(raw[offset + $1]) << ($1 * 8) }
        }
        guard u32(0) == GuestUIProtocolV2.magic, u32(4) == 32,
              u32(20) == UInt32(GuestUIProtocolV2.maximumBytes), u32(24) == 0, u32(28) == 0,
              (1...UInt32(GuestUIProtocolV2.maximumBytes)).contains(u32(12)) else { throw GuestUIEditorErrorV2.header }
        guard memoryBytes <= UInt64(UInt32.max) + 1 else { throw GuestUIEditorErrorV2.range }
        let ranges: [(UInt64, UInt64)] = [(UInt64(headerOffset), 32),
            (UInt64(u32(8)), UInt64(u32(12))), (UInt64(u32(16)), UInt64(u32(20)))]
        for (start, length) in ranges {
            guard start + length <= memoryBytes, start + length <= UInt64(UInt32.max) + 1 else { throw GuestUIEditorErrorV2.range }
        }
        for i in 0..<3 { for j in (i + 1)..<3 {
            guard ranges[i].0 + ranges[i].1 <= ranges[j].0 || ranges[j].0 + ranges[j].1 <= ranges[i].0 else {
                throw GuestUIEditorErrorV2.range
            }
        } }
        if let previous {
            guard previous.headerOffset == headerOffset, previous.eventOffset == u32(16) else {
                throw GuestUIEditorErrorV2.bufferChanged
            }
        }
        return GuestUIHeaderV2(headerOffset: headerOffset, documentOffset: u32(8), documentLength: u32(12), eventOffset: u32(16))
    }
}
