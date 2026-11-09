import Foundation
import MixerCore
import MixerUI
import MixerAndroid

public enum AndroidDocumentError: Error { case invalidEvent, revisionExhausted, outputLimit, unsupportedUI }

/// One value-owned app state and its reconciled native UI. The app supplies both
/// shared document construction and the typed reducer; Android owns no app logic.
/// State must use value semantics with no shared mutable references. Closures must
/// be synchronous, non-reentrant and free of I/O/async/external side effects. Failed
/// candidates roll back value state only; arbitrary reference graphs/effects are
/// not transactionally isolated merely because State conforms to Sendable.
public struct AndroidDocumentSession<State: Sendable>: AndroidApplicationEngine {
    public private(set) var state: State
    public private(set) var revision: UInt64 = 1
    private let profile: AndroidUIProfile
    private var reconciler: UIReconciler
    private let document: @Sendable (State, UInt64) -> MixerUI.UIDocument
    private let reduce: @Sendable (inout State, RoutedUIAction) throws -> Void

    public init(state: State,
                document: @escaping @Sendable (State, UInt64) -> MixerUI.UIDocument,
                reduce: @escaping @Sendable (inout State, RoutedUIAction) throws -> Void) throws {
        try self.init(state: state, profile: .legacyHorizontal, document: document, reduce: reduce)
    }

    /// Select the exact matching native adapter profile for this session's lifetime.
    /// Selection admits packet data only; it does not establish native support.
    public init(state: State, profile: AndroidUIProfile,
                document: @escaping @Sendable (State, UInt64) -> MixerUI.UIDocument,
                reduce: @escaping @Sendable (inout State, RoutedUIAction) throws -> Void) throws {
        self.profile = profile
        self.reconciler = UIReconciler(validator: UIValidator(supportedTextFieldAxes: profile.capabilities.textFieldAxes))
        self.state = state; self.document = document; self.reduce = reduce
        let initial = document(state, 1)
        try Self.requireAndroidProfile(initial, profile: profile)
        guard initial.revision == 1 else { throw AndroidDocumentError.invalidEvent }
        try reconciler.apply(initial)
        _ = try render()
    }
    public func render() throws -> Data { try Self.encode(reconciler.currentSnapshot(), profile: profile) }

    public mutating func dispatch(_ input: Data) throws -> Data {
        guard input.count <= 131_072 else { throw AndroidDocumentError.invalidEvent }
        try JSONInputGuard.validate(input, limits: JSONInputLimits(maximumDepth: 8, maximumValues: 64))
        guard let object = try JSONSerialization.jsonObject(with: input) as? [String: Any],
              Set(object.keys) == ["revision", "identity", "event", "value"],
              let identity = object["identity"] as? [String: Any],
              Set(identity.keys) == ["id", "generation"] else { throw AndroidDocumentError.invalidEvent }
        let action = try reconciler.currentSnapshot().route(JSONDecoder().decode(UIEventEnvelope.self, from: input))
        guard revision < UInt64.max else { throw AndroidDocumentError.revisionExhausted }
        var candidate = state
        try reduce(&candidate, action)
        let nextDocument = document(candidate, revision + 1)
        guard nextDocument.revision == revision + 1 else { throw AndroidDocumentError.invalidEvent }
        try Self.requireAndroidProfile(nextDocument, profile: profile)
        var next = reconciler
        try next.apply(nextDocument)
        let result = try Self.encode(next.currentSnapshot(), profile: profile)
        state = candidate; revision += 1; reconciler = next
        return result
    }
    private static func encode(_ snapshot: UIRenderSnapshot, profile: AndroidUIProfile) throws -> Data {
        do { return try snapshot.encodeNativePacketV1(supportedTextFieldAxes: profile.capabilities.textFieldAxes) }
        catch UINativePacketEncodingError.outputLimit { throw AndroidDocumentError.outputLimit }
        catch UINativePacketEncodingError.missingIdentity { throw AndroidDocumentError.invalidEvent }
    }
    /// Preserve the legacy axis-key restriction alongside the selected capabilities.
    /// Complete property/schema validation remains UIReconciler's responsibility.
    private static func requireAndroidProfile(_ document: MixerUI.UIDocument, profile: AndroidUIProfile) throws {
        _ = try UIValidator(supportedTextFieldAxes: profile.capabilities.textFieldAxes).validate(document)
        var pending = [(document.root, false)]
        while let (node, inList) = pending.popLast() {
            // The legacy decoder rejects every explicit axis key, including horizontal.
            if profile == .legacyHorizontal, node.kind == .textField, node.properties["axis"] != nil { throw AndroidDocumentError.unsupportedUI }
            if node.kind == .list && inList { throw AndroidDocumentError.unsupportedUI }
            if node.kind == .hStack,
               let alignment = node.properties["alignment"]?.string,
               ["firstTextBaseline", "lastTextBaseline"].contains(alignment) { throw AndroidDocumentError.unsupportedUI }
            pending.append(contentsOf: node.children.map { ($0, inList || node.kind == .list) })
        }
    }
}
