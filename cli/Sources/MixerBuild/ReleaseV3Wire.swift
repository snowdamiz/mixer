import Foundation
import MixerUpdates

protocol ReleaseV3Envelope {
    static var field: String { get }
}

struct ReleaseV3SignedJSON<Envelope: ReleaseV3Envelope> {
    let bytes: Data
    let value: [String: CanonicalValue]

    init(_ bytes: Data) throws {
        let field = Envelope.field
        let maximum = ReleaseRESTV3.signedDocumentMaximumBytes
        guard let document = try? StrictJSON.decode(CanonicalValue.self, from: bytes, maximumBytes: maximum),
              let envelope = document.object, Set(envelope.keys) == [field, "signature"],
              let value = envelope[field]?.object, value["schema"]?.uint == 3,
              let signature = envelope["signature"]?.text,
              let decoded = Data(base64Encoded: signature), decoded.count == 64,
              decoded.base64EncodedString() == signature else {
            throw MixerFailure("update.signed-input", "Expected a bounded v3 signed \(field) JSON document.")
        }
        self.bytes = bytes
        self.value = value
    }
}

struct ReleaseV3Operation<Response: Decodable> {
    let stage: String
    let method: String
    let path: String
    let body: Data
    let statuses: Set<Int>
    let reason: String?

    func urlRequest(origin: URL, token: String) -> URLRequest {
        var request = URLRequest(url: origin.appending(path: path), cachePolicy: .reloadIgnoringLocalCacheData)
        request.httpMethod = method
        request.httpBody = body
        request.setValue(ReleaseRESTV3.mediaType, forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
        request.setValue(reason, forHTTPHeaderField: "X-Mixer-Reason")

        // The origin deduplicates exact method, path and body in the tenant.
        // Include the reason here because the origin reads it from a header.
        let intent = Data("mixer-local-release-v3\u{0}\(method)\u{0}\(path)\u{0}\(reason ?? "")\u{0}".utf8)
        request.setValue(SourceDigest.sha256(intent + body), forHTTPHeaderField: "Idempotency-Key")
        return request
    }

    func decodeSuccess(_ data: Data) throws -> Response {
        try StrictJSON.decode(Response.self, from: data, maximumBytes: ReleaseRESTV3.responseMaximumBytes)
    }
}

enum ReleaseV3Wire {
    static func validID(_ value: String) -> Bool {
        (1...128).contains(value.utf8.count) && value != "." && value != ".." &&
            value.utf8.allSatisfy { (48...57).contains($0) || (65...90).contains($0) ||
                (97...122).contains($0) || $0 == 45 || $0 == 46 || $0 == 95 }
    }

    static func validDigest(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }

    static func checkedID(_ value: String) throws -> String {
        guard validID(value) else { throw MixerFailure("update.arguments", "Invalid v3 route identifier.") }
        return value
    }

    static func checkedDigest(_ value: String) throws -> String {
        guard validDigest(value) else { throw MixerFailure("update.arguments", "Invalid v3 artifact digest.") }
        return value
    }

    static func requireFields(_ fields: Set<String>, from decoder: any Decoder) throws {
        let object = try decoder.container(keyedBy: JSONKey.self)
        guard Set(object.allKeys.map(\.stringValue)) == fields else {
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "Unexpected v3 JSON fields."))
        }
    }

    private struct JSONKey: CodingKey {
        let stringValue: String
        var intValue: Int? { nil }

        init(stringValue: String) { self.stringValue = stringValue }
        init?(intValue: Int) { return nil }
    }
}
