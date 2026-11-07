import Foundation
import MixerUI

/// The owned UI value codec for a future qualified guest runtime. This module does
/// not compile Swift to Wasm, execute a guest, or establish native/guest equivalence.
public struct GuestUICodec: Sendable {
    public let validator: UIValidator
    public init(validator: UIValidator = UIValidator()) { self.validator = validator }

    public func encode(_ document: UIDocument) throws -> Data { try validator.encode(document) }
    public func decode(_ data: Data) throws -> ValidatedUIDocument { try validator.decode(data) }
}
