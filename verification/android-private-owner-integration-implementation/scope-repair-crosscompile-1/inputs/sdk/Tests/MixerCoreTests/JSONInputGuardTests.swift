import Foundation
import Testing
import MixerCore

private func rejects(_ data: Data, reason: JSONInputError.Reason, limits: JSONInputLimits = JSONInputLimits()) {
    do {
        try JSONInputGuard.validate(data, limits: limits)
        Issue.record("Expected strict JSON rejection: \(reason)")
    } catch let error as JSONInputError { #expect(error.reason == reason) }
    catch { Issue.record("Unexpected JSON error: \(error)") }
}

@Test func duplicateKeysCompareDecodedEscapesAndSurrogatePairs() throws {
    for json in [
        #"{"a":1,"a":2}"#,
        #"{"text":1,"\u0074ext":2}"#,
        #"{"😀":1,"\uD83D\uDE00":2}"#,
        #"{"a/b":1,"a\/b":2}"#,
        #"{"a\"b":1,"a\u0022b":2}"#,
        #"{"a\\b":1,"a\u005cb":2}"#,
        #"{"outer":{"value":false,"val\u0075e":true}}"#,
        #"{"":1,"":2}"#,
    ] { rejects(Data(json.utf8), reason: .duplicateKey) }
    try JSONInputGuard.validate(Data(#"[{"a":1},{"a":2}]"#.utf8))
    // Distinct scalar sequences remain distinct; the guard does not normalize bytes.
    try JSONInputGuard.validate(Data(#"{"é":1,"e\u0301":2}"#.utf8))
}

@Test func strictJSONAcceptsItsGrammarWithoutRewritingInput() throws {
    for json in [#"[null,true,false,-42,0,-0,1.25,1e3,-2.5E-4]"#,
                 #"{"escaped":"\b\f\n\r\t\\\/\"","emoji":"\ud83d\ude00","unicode":"Café 🏗️"}"#,
                 " \r\n\t {\"a\": []} \n"] {
        let bytes = Data(json.utf8)
        try JSONInputGuard.validate(bytes)
        #expect(bytes == Data(json.utf8))
    }
}

@Test func malformedJSONAndUnpairedUnicodeFailBeforeFoundationDecoding() {
    for json in ["", " ", "[1,]", #"{"a":1,}"#, #"{a:1}"#, "[", "0 1", "truefalse", "//comment\n0",
                 "+1", "01", "-01", "1.", ".1", "1e", "1e+", "NaN", "Infinity", "[false true]",
                 #""\q""#, #""\u123""#, #""\ud800""#, #""\udc00""#, #""\ud800\u0041""#,
                 #""\ud800x""#, "\"line\nfeed\"", "\u{feff}{}"] {
        rejects(Data(json.utf8), reason: .syntax)
    }
}

@Test func invalidUTF8IsNeverRepaired() {
    for bytes: [UInt8] in [[0x22, 0xff, 0x22], [0x22, 0xc0, 0x80, 0x22],
                           [0x22, 0xed, 0xa0, 0x80, 0x22], [0x22, 0xf4, 0x90, 0x80, 0x80, 0x22]] {
        rejects(Data(bytes), reason: .invalidUTF8)
    }
}

@Test func strictJSONResourceLimitsApplyBeforeSemanticDecode() throws {
    rejects(Data(repeating: 0x20, count: 1_048_577), reason: .byteLimit)
    let depth = JSONInputLimits(maximumDepth: 2)
    try JSONInputGuard.validate(Data(#"[{"a":1}]"#.utf8), limits: depth)
    rejects(Data(#"[{"a":[]}]"#.utf8), reason: .depthLimit, limits: depth)
    let deep = String(repeating: "[", count: 300) + "0" + String(repeating: "]", count: 300)
    rejects(Data(deep.utf8), reason: .depthLimit, limits: JSONInputLimits(maximumDepth: 128))
    try JSONInputGuard.validate(Data("[0,1]".utf8), limits: JSONInputLimits(maximumValues: 3))
    rejects(Data("[0,1,2]".utf8), reason: .valueLimit, limits: JSONInputLimits(maximumValues: 3))
    rejects(Data(#""😀""#.utf8), reason: .stringLimit, limits: JSONInputLimits(maximumStringBytes: 3))
    rejects(Data(#""\ud83d\ude00""#.utf8), reason: .stringLimit, limits: JSONInputLimits(maximumStringBytes: 3))
    try JSONInputGuard.validate(Data(#""\ud83d\ude00""#.utf8), limits: JSONInputLimits(maximumStringBytes: 4))
    rejects(Data(#"{"😀":0}"#.utf8), reason: .stringLimit, limits: JSONInputLimits(maximumKeyBytes: 3))
    rejects(Data(String(repeating: "1", count: 257).utf8), reason: .numberLimit)
    rejects(Data("[]".utf8), reason: .invalidLimits, limits: JSONInputLimits(maximumDepth: 385))
}
