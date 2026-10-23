import Foundation
import Testing
import MixerCapabilities

private let transportValues: [(GuestCapabilityOperationV1, CapabilityOperation, CapabilityResult)] = [
    (.httpRequest, .http(HTTPRequestArguments(url: "https://api.example.test/v1", method: "POST", headers: [], bodyBase64: "8J+YgA==", timeoutMilliseconds: 30_000)),
     .http(HTTPResponse(status: 302, headers: [], bodyBase64: ""))),
    (.storageGet, .get(KVGetArguments(namespace: "notes", key: "entry_1")),
     .get(KVGetResponse(found: false, valueBase64: "YQ=="))),
    (.storagePut, .put(KVPutArguments(namespace: "notes", key: "entry_1", valueBase64: "")),
     .put(KVMutationResponse(committed: false))),
    (.storageDelete, .delete(KVDeleteArguments(namespace: "notes", key: "entry_1")),
     .delete(KVMutationResponse(committed: true))),
]

@Test func transportFixedOperationTagsAndTypedRoundtripsPreserveV1Values() throws {
    #expect(GuestCapabilityOperationV1.allCases.map(\.rawValue) == [1, 2, 3, 4])
    for invalid: UInt32 in [0, 5, .max] { #expect(GuestCapabilityOperationV1(rawValue: invalid) == nil) }
    for (operation, arguments, result) in transportValues {
        let encodedArguments = try GuestCapabilityTransportCodecV1.encodeArguments(arguments)
        #expect(try GuestCapabilityTransportCodecV1.decodeArguments(encodedArguments, operation: operation) == arguments)
        #expect(try GuestCapabilityTransportCodecV1.encodeArguments(arguments) == encodedArguments)
        let encodedResult = try GuestCapabilityTransportCodecV1.encodeCompletion(.success(result), operation: operation)
        #expect(try GuestCapabilityTransportCodecV1.decodeCompletion(encodedResult, expectedOperation: operation) == .success(result))
        #expect(try GuestCapabilityTransportCodecV1.encodeCompletion(.success(result), operation: operation) == encodedResult)
        let object = try #require(JSONSerialization.jsonObject(with: encodedResult) as? [String: Any])
        #expect(Set(object.keys) == ["abi", "capability", "schemaHash", "operation", "outcome"])
        #expect(object["abi"] as? Int == 1)
    }
    // The HTTP302 and found=false/nonempty values above are intentionally valid
    // at the type boundary. Native redirect/store policy is a separate layer.
}

@Test func transportEncoderRejectsInvalidDirectlyConstructedArgumentsAndResults() throws {
    let invalidArguments: [CapabilityOperation] = [
        .http(HTTPRequestArguments(url: "http://api.example.test/", method: "GET", headers: [], bodyBase64: "", timeoutMilliseconds: 1)),
        .http(HTTPRequestArguments(url: "https://api.example.test/", method: "OPTIONS", headers: [], bodyBase64: "", timeoutMilliseconds: 1)),
        .http(HTTPRequestArguments(url: "https://api.example.test/", method: "GET", headers: [], bodyBase64: "", timeoutMilliseconds: 0)),
        .http(HTTPRequestArguments(url: "https://api.example.test/", method: "GET", headers: [Header(name: "cookie", value: "fixture")], bodyBase64: "", timeoutMilliseconds: 1)),
        .get(KVGetArguments(namespace: "../notes", key: "entry")),
        .put(KVPutArguments(namespace: "notes", key: "entry", valueBase64: "YR==")),
        .delete(KVDeleteArguments(namespace: "notes", key: String(repeating: "k", count: 129))),
    ]
    for value in invalidArguments {
        #expect(throws: (any Error).self) { try GuestCapabilityTransportCodecV1.encodeArguments(value) }
    }
    let invalidResults: [(GuestCapabilityOperationV1, CapabilityResult)] = [
        (.httpRequest, .http(HTTPResponse(status: 99, headers: [], bodyBase64: ""))),
        (.httpRequest, .http(HTTPResponse(status: 600, headers: [], bodyBase64: ""))),
        (.httpRequest, .http(HTTPResponse(status: 200, headers: [Header(name: "x-tag", value: "a"), Header(name: "x-tag", value: "b")], bodyBase64: ""))),
        (.storageGet, .get(KVGetResponse(found: true, valueBase64: "YQ"))),
        (.storageGet, .get(KVGetResponse(found: false, valueBase64: "__8="))),
    ]
    for (operation, result) in invalidResults {
        #expect(throws: (any Error).self) { try GuestCapabilityTransportCodecV1.encodeCompletion(.success(result), operation: operation) }
    }
}

@Test func transportWrongOperationResultCasesAndEveryOutcomeRemainBound() throws {
    for (sourceOperation, _, result) in transportValues {
        let encoded = try GuestCapabilityTransportCodecV1.encodeCompletion(.success(result), operation: sourceOperation)
        for destination in GuestCapabilityOperationV1.allCases where sourceOperation != destination {
            #expect(throws: (any Error).self) { try GuestCapabilityTransportCodecV1.encodeCompletion(.success(result), operation: destination) }
            #expect(throws: (any Error).self) { try GuestCapabilityTransportCodecV1.decodeCompletion(encoded, expectedOperation: destination) }
        }
        let outcomes = CapabilityFailure.allCases.map(GuestCapabilityCompletionV1.failure) + [.rejected(.invalidArguments)]
        for outcome in outcomes {
            let encodedOutcome = try GuestCapabilityTransportCodecV1.encodeCompletion(outcome, operation: sourceOperation)
            #expect(try GuestCapabilityTransportCodecV1.decodeCompletion(encodedOutcome, expectedOperation: sourceOperation) == outcome)
            for destination in GuestCapabilityOperationV1.allCases where sourceOperation != destination {
                #expect(throws: (any Error).self) { try GuestCapabilityTransportCodecV1.decodeCompletion(encodedOutcome, expectedOperation: destination) }
            }
        }
    }
    // put and delete share a DTO but not a result enum case or operation identity.
}

@Test func transportStandaloneAndWrapperExactByteBoundsReachActualCodec() throws {
    let arguments = CapabilityOperation.get(KVGetArguments(namespace: "notes", key: "entry"))
    let encoded = try GuestCapabilityTransportCodecV1.encodeArguments(arguments)
    let exact = encoded + Data(repeating: 32, count: 524_288 - encoded.count)
    #expect(exact.count == 524_288)
    #expect(try GuestCapabilityTransportCodecV1.decodeArguments(exact, operation: .storageGet) == arguments)
    #expect(throws: (any Error).self) { try GuestCapabilityTransportCodecV1.decodeArguments(exact + Data([32]), operation: .storageGet) }
    let completion = try GuestCapabilityTransportCodecV1.encodeCompletion(.rejected(.invalidArguments), operation: .storagePut)
    let exactCompletion = completion + Data(repeating: 32, count: 524_288 - completion.count)
    #expect(try GuestCapabilityTransportCodecV1.decodeCompletion(exactCompletion, expectedOperation: .storagePut) == .rejected(.invalidArguments))
    #expect(throws: (any Error).self) { try GuestCapabilityTransportCodecV1.decodeCompletion(exactCompletion + Data([32]), expectedOperation: .storagePut) }
    for bytes in [Data([0xff]), Data([0xef, 0xbb, 0xbf]) + encoded,
                  Data(#"{"namespace":"notes","key":"\uD800"}"#.utf8), encoded + Data("{}".utf8)] {
        #expect(throws: (any Error).self) { try GuestCapabilityTransportCodecV1.decodeArguments(bytes, operation: .storageGet) }
    }
}

@Test func transportEncoderUsesDecodedByteLimitsAndNoInventedGetDependency() throws {
    for size in [65_536, 65_537] {
        let body = Data(repeating: 0, count: size).base64EncodedString()
        let request = CapabilityOperation.put(KVPutArguments(namespace: "notes", key: "entry", valueBase64: body))
        let result = CapabilityResult.get(KVGetResponse(found: false, valueBase64: body))
        if size == 65_536 {
            #expect(try GuestCapabilityTransportCodecV1.decodeArguments(GuestCapabilityTransportCodecV1.encodeArguments(request), operation: .storagePut) == request)
            #expect(try GuestCapabilityTransportCodecV1.decodeCompletion(GuestCapabilityTransportCodecV1.encodeCompletion(.success(result), operation: .storageGet), expectedOperation: .storageGet) == .success(result))
        } else {
            #expect(throws: (any Error).self) { try GuestCapabilityTransportCodecV1.encodeArguments(request) }
            #expect(throws: (any Error).self) { try GuestCapabilityTransportCodecV1.encodeCompletion(.success(result), operation: .storageGet) }
        }
    }
    for size in [262_144, 262_145] {
        let result = CapabilityResult.http(HTTPResponse(status: 302, headers: [], bodyBase64: Data(repeating: 0, count: size).base64EncodedString()))
        if size == 262_144 {
            #expect(try GuestCapabilityTransportCodecV1.decodeCompletion(GuestCapabilityTransportCodecV1.encodeCompletion(.success(result), operation: .httpRequest), expectedOperation: .httpRequest) == .success(result))
        } else {
            #expect(throws: (any Error).self) { try GuestCapabilityTransportCodecV1.encodeCompletion(.success(result), operation: .httpRequest) }
        }
    }
}

@Test func transportConversionStartsFromLegacyCompletionBoundToActualCall() throws {
    let identity = CapabilityRequestID(session: "01234567-89ab-4cde-8fab-0123456789ab", slot: 0, generation: 1)
    for (operation, arguments, result) in transportValues {
        let call = CapabilityCall(identity: identity, operation: arguments)
        let bytes = try CapabilityCodec.encodeCompletion(CapabilityCompletion(call: call, outcome: .success(result)))
        let decoded = try CapabilityCodec.decodeCompletion(bytes, expected: call)
        guard case .success(let validatedResult) = decoded.outcome else { Issue.record("Expected native success"); continue }
        let wrapper = try GuestCapabilityTransportCodecV1.encodeCompletion(.success(validatedResult), operation: operation)
        #expect(try GuestCapabilityTransportCodecV1.decodeCompletion(wrapper, expectedOperation: operation) == .success(result))
        let stale = CapabilityCall(identity: CapabilityRequestID(session: identity.session, slot: identity.slot, generation: 2), operation: arguments)
        #expect(throws: (any Error).self) { try CapabilityCodec.decodeCompletion(bytes, expected: stale) }
    }
}

@Test func transportMalformedInputThrowsOnlySanitizedWireErrors() throws {
    let malformedArguments = [
        Data([0xff]),
        Data(#"{"namespace":"notes","key":"one","\u006bey":"two"}"#.utf8),
        Data(#"{"namespace":"notes","key":"\uD800"}"#.utf8),
        Data((String(repeating: "[", count: 9) + "0" + String(repeating: "]", count: 9)).utf8),
        Data(#"{"namespace":"notes","key":"entry","extra":1}"#.utf8),
    ]
    for bytes in malformedArguments {
        #expect(throws: CapabilityWireError.self) { try GuestCapabilityTransportCodecV1.decodeArguments(bytes, operation: .storageGet) }
    }
    let http = #"{"url":"https://api.example.test/","method":"GET","headers":[],"bodyBase64":"","timeoutMilliseconds":1e0}"#
    #expect(throws: CapabilityWireError.self) { try GuestCapabilityTransportCodecV1.decodeArguments(Data(http.utf8), operation: .httpRequest) }

    let good = try GuestCapabilityTransportCodecV1.encodeCompletion(.failure(.ioFailure), operation: .storageGet)
    let text = String(decoding: good, as: UTF8.self)
    let malformedCompletions = [
        Data([0xff]),
        Data(text.replacingOccurrences(of: "\"abi\":1", with: "\"abi\":1,\"\\u0061bi\":1").utf8),
        Data(text.replacingOccurrences(of: "ioFailure", with: "ioF\\uD800ailure").utf8),
        Data(text.replacingOccurrences(of: "\"abi\":1", with: "\"abi\":1.0").utf8),
        Data((String(text.dropLast()) + ",\"session\":\"forbidden\"}").utf8),
        Data((String(repeating: "[", count: 9) + "0" + String(repeating: "]", count: 9)).utf8),
    ]
    for bytes in malformedCompletions {
        #expect(throws: CapabilityWireError.self) { try GuestCapabilityTransportCodecV1.decodeCompletion(bytes, expectedOperation: .storageGet) }
    }
    // Preflight errors are deliberately sanitized only by the new entry points.
    do {
        _ = try GuestCapabilityTransportCodecV1.decodeArguments(Data([0xff]), operation: .storageGet)
        Issue.record("Expected invalid UTF8 to fail")
    } catch let failure as CapabilityWireError {
        #expect(failure == .invalid("guest transport JSON"))
    }
}
