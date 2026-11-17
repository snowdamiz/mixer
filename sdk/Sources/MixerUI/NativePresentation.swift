import Foundation

/// Package-issued domain identity, not a claim of pixel or device qualification.
public struct NativePresentationRequest: Sendable {
    public let document: ValidatedUIDocument
    public let id: UUID
    private let domain: NativePresentationDomain
    package init(document: ValidatedUIDocument) {
        self.document = document; id = UUID(); domain = NativePresentationDomain()
    }
    package func accepts(_ acknowledgement: NativeDisplayAcknowledgement) -> Bool {
        domain === acknowledgement.domain && id == acknowledgement.requestID
    }
    package func acknowledgement(snapshot: UIRenderSnapshot) -> NativeDisplayAcknowledgement {
        NativeDisplayAcknowledgement(snapshot: snapshot, domain: domain, requestID: id)
    }
}
private final class NativePresentationDomain: Sendable {}
public struct NativeDisplayAcknowledgement: Sendable {
    public let snapshot: UIRenderSnapshot
    fileprivate let domain: NativePresentationDomain
    fileprivate let requestID: UUID
}
