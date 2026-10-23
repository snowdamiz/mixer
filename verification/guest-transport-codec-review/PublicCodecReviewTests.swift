import Foundation
import Testing
import MixerCapabilities

private let httpHash = "fa1549c0a1e2e6b3bf4a83af1a6d37730bbefc8cddc3ffbe3c807d5e7af503f3"
private let storageHash = "4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"
private typealias Codec = GuestCapabilityTransportCodecV1
private func bytes(_ value: String) -> Data { Data(value.utf8) }
private func object(_ data: Data) throws -> [String: Any] { try #require(JSONSerialization.jsonObject(with: data) as? [String: Any]) }
private func encoded(_ object: [String: Any]) throws -> Data { try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys, .fragmentsAllowed]) }
@discardableResult private func reject<T>(_ label: String, _ body: () throws -> T) -> CapabilityWireError? {
    do { _ = try body(); Issue.record("Accepted forbidden input: \(label)"); return nil }
    catch let error as CapabilityWireError { return error }
    catch { Issue.record("Non-wire error for \(label): \(type(of: error))"); return nil }
}
private func http(url: String = "https://a.test/", method: String = "GET", headers: [Header] = [], body: String = "", timeout: UInt32 = 1) -> CapabilityOperation {
    .http(HTTPRequestArguments(url: url, method: method, headers: headers, bodyBase64: body, timeoutMilliseconds: timeout))
}
private func wrapper(_ outcome: String, operation: String = "get", capability: String = "storage.keyValue.v1", hash: String = storageHash, abi: String = "1") -> Data {
    bytes("{\"abi\":\(abi),\"capability\":\"\(capability)\",\"schemaHash\":\"\(hash)\",\"operation\":\"\(operation)\",\"outcome\":\(outcome)}")
}
private let publicBindings: [(GuestCapabilityOperationV1, CapabilityOperation, CapabilityResult, String, String, String)] = [
    (.httpRequest, http(), .http(HTTPResponse(status: 302, headers: [], bodyBase64: "AA==")), "network.http.v1", httpHash, "request"),
    (.storageGet, .get(KVGetArguments(namespace: "n", key: "k")), .get(KVGetResponse(found: false, valueBase64: "AA==")), "storage.keyValue.v1", storageHash, "get"),
    (.storagePut, .put(KVPutArguments(namespace: "n", key: "k", valueBase64: "AA==")), .put(KVMutationResponse(committed: false)), "storage.keyValue.v1", storageHash, "put"),
    (.storageDelete, .delete(KVDeleteArguments(namespace: "n", key: "k")), .delete(KVMutationResponse(committed: false)), "storage.keyValue.v1", storageHash, "delete")
]

@Test func exactTagsTypedBindingsAndClosedWrapperFields() throws {
    #expect(GuestCapabilityOperationV1.allCases.map(\.rawValue) == [1, 2, 3, 4])
    for tag: UInt32 in [0, 5, 65535, .max] { #expect(GuestCapabilityOperationV1(rawValue: tag) == nil) }
    for (tag, arguments, result, capability, hash, operation) in publicBindings {
        let payload = try Codec.encodeArguments(arguments)
        #expect(try Codec.decodeArguments(payload, operation: tag) == arguments)
        let output = try Codec.encodeCompletion(.success(result), operation: tag)
        let envelope = try object(output)
        #expect(Set(envelope.keys) == ["abi", "capability", "schemaHash", "operation", "outcome"])
        #expect(envelope["abi"] as? Int == 1 && envelope["capability"] as? String == capability)
        #expect(envelope["schemaHash"] as? String == hash && envelope["operation"] as? String == operation)
        #expect(try Codec.decodeCompletion(output, expectedOperation: tag) == .success(result))
        for (other, _, _, _, _, _) in publicBindings where other != tag {
            reject("wrong expected completion operation") { try Codec.decodeCompletion(output, expectedOperation: other) }
            reject("wrong result encoder operation") { try Codec.encodeCompletion(.success(result), operation: other) }
        }
    }
    // Get/delete arguments share their exact object shape. Their trusted external
    // tag supplies the binding; no guest identity or operation is accepted in JSON.
    let same = bytes(#"{"namespace":"n","key":"k"}"#)
    #expect(try Codec.decodeArguments(same, operation: .storageGet) == .get(KVGetArguments(namespace: "n", key: "k")))
    #expect(try Codec.decodeArguments(same, operation: .storageDelete) == .delete(KVDeleteArguments(namespace: "n", key: "k")))
    reject("get as HTTP") { try Codec.decodeArguments(same, operation: .httpRequest) }
    reject("put missing value") { try Codec.decodeArguments(same, operation: .storagePut) }
}

@Test func wrapperAndOutcomeConfusionAreRejected() throws {
    let original = try object(Codec.encodeCompletion(.failure(.ioFailure), operation: .storageGet))
    for field in ["abi", "capability", "schemaHash", "operation", "outcome"] {
        var missing = original; missing.removeValue(forKey: field)
        reject("missing \(field)") { try Codec.decodeCompletion(encoded(missing), expectedOperation: .storageGet) }
        for wrong: Any in [NSNull(), true, 0, [], [:]] {
            var changed = original; changed[field] = wrong
            reject("wrong \(field) type") { try Codec.decodeCompletion(encoded(changed), expectedOperation: .storageGet) }
        }
    }
    for field in ["identity", "session", "token", "schema", "arguments", "capabilityID"] {
        var extra = original; extra[field] = "foreign"
        reject("extra identity/routing field") { try Codec.decodeCompletion(encoded(extra), expectedOperation: .storageGet) }
    }
    for (field, wrong) in [("capability", "network.http.v1"), ("schemaHash", String(repeating: "0", count: 64)), ("operation", "put"), ("schemaHash", storageHash.uppercased())] {
        var changed = original; changed[field] = wrong
        reject("changed fixed metadata") { try Codec.decodeCompletion(encoded(changed), expectedOperation: .storageGet) }
    }
    for outcome in [#"{"kind":"failure","code":"invalidArguments"}"#, #"{"kind":"rejected","code":"ioFailure"}"#,
                    #"{"kind":"success","code":"ioFailure"}"#, #"{"kind":"failure","code":"ioFailure","value":{}}"#,
                    #"{"kind":"success","value":{"found":true,"valueBase64":""},"code":"ioFailure"}"#,
                    #"{"kind":"rejected","code":"invalidArguments","extra":false}"#, #"{"kind":"pending"}"#,
                    #"{"kind":"success","value":{"committed":true}}"#, #"{"kind":"success","value":{"found":true,"valueBase64":"","identity":{}}}"#] {
        reject("closed outcome/result") { try Codec.decodeCompletion(wrapper(outcome), expectedOperation: .storageGet) }
    }
    for tag in GuestCapabilityOperationV1.allCases {
        for code in CapabilityFailure.allCases {
            #expect(try Codec.decodeCompletion(Codec.encodeCompletion(.failure(code), operation: tag), expectedOperation: tag) == .failure(code))
        }
        #expect(try Codec.decodeCompletion(Codec.encodeCompletion(.rejected(.invalidArguments), operation: tag), expectedOperation: tag) == .rejected(.invalidArguments))
    }
}

@Test func malformedBytesAreSanitizedWireErrorsAtBothNewDecoders() {
    let malformed = [Data([0xff]), Data([0xc0, 0xaf]), bytes(""), bytes("{}x"), bytes("{}{}"), bytes("[]"), bytes("null"),
                     bytes(#"{"namespace":"n","key":"k","\u006bey":"private"}"#),
                     bytes(#"{"namespace":"n","key":"\uD800-private"}"#), bytes(#"{"namespace":"n","key":"\uDC00"}"#),
                     bytes(#"{"namespace":"n","key":"\uD800\u0041"}"#), bytes(#"{"namespace":"n","key":"\q"}"#),
                     bytes("{\"namespace\":\"n\",\"key\":\"a\nb\"}"), bytes("{\"namespace\":\"n\",\"key\":\"a\u{0}b\"}")]
    for data in malformed {
        reject("malformed argument") { try Codec.decodeArguments(data, operation: .storageGet) }
        reject("malformed wrapper") { try Codec.decodeCompletion(data, expectedOperation: .storageGet) }
    }
    let bad = bytes(#"{"namespace":"n","key":"PRIVATE\uD800"}"#)
    #expect(reject("sanitized parser error") { try Codec.decodeArguments(bad, operation: .storageGet) } == .invalid("guest transport JSON"))
    let duplicate = wrapper(#"{"kind":"failure","code":"ioFailure"}"#)
    let duplicateText = String(decoding: duplicate, as: UTF8.self).replacingOccurrences(of: "\"abi\":1", with: "\"abi\":1,\"\\u0061bi\":1")
    #expect(reject("escaped duplicate wrapper key") { try Codec.decodeCompletion(bytes(duplicateText), expectedOperation: .storageGet) } == .invalid("guest transport JSON"))
}

@Test func escapedASCIIIsDecodedWithoutNormalizationOrIdentitySmuggling() throws {
    let data = bytes(#"{"\u006eamespace":"n","key":"\u006b"}"#)
    #expect(try Codec.decodeArguments(data, operation: .storageGet) == .get(KVGetArguments(namespace: "n", key: "k")))
    #expect(try Codec.encodeArguments(Codec.decodeArguments(data, operation: .storageGet)) == bytes(#"{"key":"k","namespace":"n"}"#))
    for key in ["é", "e\u{301}", "😀", "../k", "", "a b", "a/b", "a\\b", "\u{7f}"] {
        reject("invalid programmatic identifier") { try Codec.encodeArguments(.get(KVGetArguments(namespace: "n", key: key))) }
    }
    for extra in [#""identity":{"session":"foreign"}"#, #""operation":"delete""#, #""token":1"#] {
        reject("routing smuggled through arguments") { try Codec.decodeArguments(bytes("{\"namespace\":\"n\",\"key\":\"k\",\(extra)}"), operation: .storageGet) }
    }
}

@Test func numericGrammarAndBoundsRejectCoercions() throws {
    for token in ["0", "30001", "-0", "-1", "1.0", "1e0", "4294967296", "01", "0001", "+1", "NaN", "true", "\"1\"", "null", String(repeating: "9", count: 257)] {
        let data = bytes("{\"url\":\"https://a.test/\",\"method\":\"GET\",\"headers\":[],\"bodyBase64\":\"\",\"timeoutMilliseconds\":\(token)}")
        reject("invalid timeout token \(token.prefix(12))") { try Codec.decodeArguments(data, operation: .httpRequest) }
    }
    for token in ["0", "2", "-0", "1.0", "1e0", "4294967296", "01", "true", "\"1\"", "null"] {
        reject("invalid wrapper ABI") { try Codec.decodeCompletion(wrapper(#"{"kind":"failure","code":"ioFailure"}"#, abi: token), expectedOperation: .storageGet) }
    }
    for timeout: UInt32 in [1, 30000] { #expect(try Codec.decodeArguments(Codec.encodeArguments(http(timeout: timeout)), operation: .httpRequest) == http(timeout: timeout)) }
    for timeout: UInt32 in [0, 30001, .max] { reject("arbitrary timeout DTO") { try Codec.encodeArguments(http(timeout: timeout)) } }
    for status: UInt32 in [0, 99, 600, .max] { reject("arbitrary status DTO") { try Codec.encodeCompletion(.success(.http(HTTPResponse(status: status, headers: [], bodyBase64: ""))), operation: .httpRequest) } }
}

@Test func identifierURLMethodAndHeaderCeilingsApplyToPublicDTOs() throws {
    let maxGet = CapabilityOperation.get(KVGetArguments(namespace: String(repeating: "N", count: 64), key: String(repeating: "k", count: 128)))
    #expect(try Codec.decodeArguments(Codec.encodeArguments(maxGet), operation: .storageGet) == maxGet)
    for (namespace, key) in [(String(repeating: "N", count: 65), "k"), ("n", String(repeating: "k", count: 129)), ("", "k")] {
        reject("oversized identifier DTO") { try Codec.encodeArguments(.delete(KVDeleteArguments(namespace: namespace, key: key))) }
    }
    let base = "https://a.test/", maxURL = base + String(repeating: "x", count: 4096 - base.utf8.count)
    #expect(try Codec.decodeArguments(Codec.encodeArguments(http(url: maxURL)), operation: .httpRequest) == http(url: maxURL))
    for url in [maxURL + "x", "http://a.test/", "https://A.test/", "https://a.test:443/", "https://a.test:0444/", "https://u@a.test/", "https://a.test/#a", "https://a.test/%2f", "https://a.test/%", "https://a.test/é", "https://a.test/a b"] {
        reject("invalid URL DTO") { try Codec.encodeArguments(http(url: url)) }
    }
    for method in ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"] { _ = try Codec.encodeArguments(http(method: method)) }
    for method in ["TRACE", "get", "OPTIONS", ""] { reject("method DTO") { try Codec.encodeArguments(http(method: method)) } }
    let maxHeaders = (0..<32).map { Header(name: "x-\($0)", value: String(repeating: "v", count: 4096)) }
    _ = try Codec.encodeArguments(http(headers: maxHeaders))
    _ = try Codec.encodeArguments(http(headers: [Header(name: String(repeating: "x", count: 64), value: "")]))
    for headers in [maxHeaders + [Header(name: "x-extra", value: "")], [Header(name: String(repeating: "x", count: 65), value: "")],
                    [Header(name: "x", value: String(repeating: "v", count: 4097))], [Header(name: "x", value: "a"), Header(name: "x", value: "b")],
                    [Header(name: "X", value: "a")], [Header(name: "cookie", value: "a")], [Header(name: "x", value: "a\rb")]] {
        reject("invalid header DTO") { try Codec.encodeArguments(http(headers: headers)) }
        reject("invalid result header DTO") { try Codec.encodeCompletion(.success(.http(HTTPResponse(status: 200, headers: headers, bodyBase64: ""))), operation: .httpRequest) }
    }
}

@Test func decodedByteCeilingsAndCanonicalBase64ApplyToArgumentsAndResults() throws {
    for size in [65536, 65537] {
        let body = Data(repeating: 0, count: size).base64EncodedString()
        let put = CapabilityOperation.put(KVPutArguments(namespace: "n", key: "k", valueBase64: body))
        let get = GuestCapabilityCompletionV1.success(.get(KVGetResponse(found: false, valueBase64: body)))
        if size == 65536 {
            #expect(try Codec.decodeArguments(Codec.encodeArguments(http(body: body)), operation: .httpRequest) == http(body: body))
            #expect(try Codec.decodeArguments(Codec.encodeArguments(put), operation: .storagePut) == put)
            #expect(try Codec.decodeCompletion(Codec.encodeCompletion(get, operation: .storageGet), expectedOperation: .storageGet) == get)
        } else {
            reject("request bytes") { try Codec.encodeArguments(http(body: body)) }
            reject("put bytes") { try Codec.encodeArguments(put) }
            reject("get bytes") { try Codec.encodeCompletion(get, operation: .storageGet) }
        }
    }
    for size in [262144, 262145] {
        let result = GuestCapabilityCompletionV1.success(.http(HTTPResponse(status: 302, headers: [], bodyBase64: Data(repeating: 0, count: size).base64EncodedString())))
        if size == 262144 { #expect(try Codec.decodeCompletion(Codec.encodeCompletion(result, operation: .httpRequest), expectedOperation: .httpRequest) == result) }
        else { reject("response bytes") { try Codec.encodeCompletion(result, operation: .httpRequest) } }
    }
    for body in ["AA", "A===", "AB==", "AA==\n", "AA-_", "é"] {
        reject("noncanonical DTO base64") { try Codec.encodeArguments(.put(KVPutArguments(namespace: "n", key: "k", valueBase64: body))) }
        reject("noncanonical result base64") { try Codec.encodeCompletion(.success(.get(KVGetResponse(found: true, valueBase64: body))), operation: .storageGet) }
        reject("noncanonical inbound base64") { try Codec.decodeArguments(encoded(["namespace": "n", "key": "k", "valueBase64": body]), operation: .storagePut) }
    }
}

@Test func rawParserResourcesAreEnforcedBeforeClosedDTOValidation() throws {
    let valid = bytes(#"{"namespace":"n","key":"k"}"#)
    var exact = valid; exact.append(Data(repeating: 32, count: 524288 - valid.count))
    #expect(try Codec.decodeArguments(exact, operation: .storageGet) == .get(KVGetArguments(namespace: "n", key: "k")))
    exact.append(32)
    #expect(reject("one byte over wire bound") { try Codec.decodeArguments(exact, operation: .storageGet) } == .invalid("bytes"))
    let resourceInputs = [
        "{\"x\":\"" + String(repeating: "a", count: 350001) + "\"}",
        "{\"" + String(repeating: "x", count: 65) + "\":0}",
        String(repeating: "[", count: 9) + "0" + String(repeating: "]", count: 9),
        "[" + Array(repeating: "0", count: 8193).joined(separator: ",") + "]"
    ]
    for raw in resourceInputs {
        #expect(reject("raw resource bound") { try Codec.decodeArguments(bytes(raw), operation: .storageGet) } == .invalid("guest transport JSON"))
        #expect(reject("wrapper raw resource bound") { try Codec.decodeCompletion(bytes(raw), expectedOperation: .storageGet) } == .invalid("guest transport JSON"))
    }
}

@Test func frozenValueSemanticsAreNotReinterpretedAsPolicyOrCommitRules() throws {
    for found in [false, true] {
        for body in ["", "AA=="] {
            let outcome = GuestCapabilityCompletionV1.success(.get(KVGetResponse(found: found, valueBase64: body)))
            #expect(try Codec.decodeCompletion(Codec.encodeCompletion(outcome, operation: .storageGet), expectedOperation: .storageGet) == outcome)
        }
    }
    for status: UInt32 in [100, 199, 200, 302, 399, 599] {
        let outcome = GuestCapabilityCompletionV1.success(.http(HTTPResponse(status: status, headers: [], bodyBase64: "")))
        #expect(try Codec.decodeCompletion(Codec.encodeCompletion(outcome, operation: .httpRequest), expectedOperation: .httpRequest) == outcome)
    }
    for committed in [false, true] {
        for tag in [GuestCapabilityOperationV1.storagePut, .storageDelete] {
            let result: CapabilityResult = tag == .storagePut ? .put(KVMutationResponse(committed: committed)) : .delete(KVMutationResponse(committed: committed))
            #expect(try Codec.decodeCompletion(Codec.encodeCompletion(.success(result), operation: tag), expectedOperation: tag) == .success(result))
        }
    }
}

@Test func decodedValuesOwnTheirSnapshotAndEncodingIsStable() throws {
    var input = bytes(#"{"namespace":"n","key":"k"}"#)
    let value = try Codec.decodeArguments(input, operation: .storageGet)
    input.resetBytes(in: 0..<input.count)
    #expect(value == .get(KVGetArguments(namespace: "n", key: "k")))
    #expect(try Codec.encodeArguments(value) == bytes(#"{"key":"k","namespace":"n"}"#))
    let expected = wrapper(#"{"kind":"success","value":{"found":false,"valueBase64":"AA=="}}"#)
    let decoded = try Codec.decodeCompletion(expected, expectedOperation: .storageGet)
    let output = try Codec.encodeCompletion(decoded, operation: .storageGet)
    #expect(try Codec.encodeCompletion(decoded, operation: .storageGet) == output)
}
