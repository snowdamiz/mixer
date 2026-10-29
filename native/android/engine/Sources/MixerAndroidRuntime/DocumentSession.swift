import Foundation
import MixerCore
import MixerUI

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
    private var reconciler = UIReconciler()
    private let document: @Sendable (State, UInt64) -> MixerUI.UIDocument
    private let reduce: @Sendable (inout State, RoutedUIAction) throws -> Void

    public init(state: State,
                document: @escaping @Sendable (State, UInt64) -> MixerUI.UIDocument,
                reduce: @escaping @Sendable (inout State, RoutedUIAction) throws -> Void) throws {
        self.state = state; self.document = document; self.reduce = reduce
        let initial = document(state, 1)
        try Self.requireAndroidProfile(initial)
        guard initial.revision == 1 else { throw AndroidDocumentError.invalidEvent }
        try reconciler.apply(initial)
        _ = try render()
    }
    public func render() throws -> Data { try Self.encode(reconciler.currentSnapshot()) }

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
        try Self.requireAndroidProfile(nextDocument)
        var next = reconciler
        try next.apply(nextDocument)
        let result = try Self.encode(next.currentSnapshot())
        state = candidate; revision += 1; reconciler = next
        return result
    }
    private static func encode(_ snapshot: UIRenderSnapshot) throws -> Data {
        do { return try snapshot.encodeNativePacketV1() }
        catch UINativePacketEncodingError.outputLimit { throw AndroidDocumentError.outputLimit }
        catch UINativePacketEncodingError.missingIdentity { throw AndroidDocumentError.invalidEvent }
    }
    /// These restrictions mirror android-profile-v1 and its owned Java decoder.
    /// Complete property/schema validation remains UIReconciler's responsibility.
    private static func requireAndroidProfile(_ document: MixerUI.UIDocument) throws {
        _ = try UIValidator().validate(document)
        var pending = [(document.root, false)]
        while let (node, inList) = pending.popLast() {
            // Android's native packet decoder does not admit an explicit axis key.
            if node.kind == .textField, node.properties["axis"] != nil { throw AndroidDocumentError.unsupportedUI }
            if node.kind == .list && inList { throw AndroidDocumentError.unsupportedUI }
            if node.kind == .hStack,
               let alignment = node.properties["alignment"]?.string,
               ["firstTextBaseline", "lastTextBaseline"].contains(alignment) { throw AndroidDocumentError.unsupportedUI }
            pending.append(contentsOf: node.children.map { ($0, inList || node.kind == .list) })
        }
    }
}
