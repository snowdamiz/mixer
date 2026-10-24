import Foundation
import Testing
@_spi(GuestUIV1) @testable import MixerGuest

private let guestUIEventExample = #"{"schemaVersion":1,"sequence":1,"revision":1,"nodeID":"save","actionID":"sample.save","event":"activate","value":null}"#

@Test func guestUIEventCodecHasExactDeterministicBytes() throws {
    let value = try GuestUIEventV1(sequence: 1, revision: 1, nodeID: "save", actionID: "sample.save")
    let canonical = #"{"actionID":"sample.save","event":"activate","nodeID":"save","revision":1,"schemaVersion":1,"sequence":1,"value":null}"#
    #expect(try GuestUIEventCodecV1.encode(value) == Data(canonical.utf8))
    #expect(try GuestUIEventCodecV1.decode(Data(guestUIEventExample.utf8)) == value)
    #expect(try GuestUIEventCodecV1.decode(Data((" \n" + guestUIEventExample + "\t").utf8)) == value)
    let escaped = guestUIEventExample.replacingOccurrences(of: "nodeID", with: #"node\u0049D"#)
    #expect(try GuestUIEventCodecV1.decode(Data(escaped.utf8)) == value)
}

@Test func guestUIEventCodecPreservesUnicodeAndUInt64WithoutNormalization() throws {
    for id in ["é", "e\u{301}", "🏗️", "quote\"/\\", String(repeating: "é", count: 64)] {
        let value = try GuestUIEventV1(sequence: .max, revision: .max, nodeID: id, actionID: id)
        let bytes = try GuestUIEventCodecV1.encode(value)
        let decoded = try GuestUIEventCodecV1.decode(bytes)
        #expect(Array(decoded.nodeID.utf8) == Array(id.utf8))
        #expect(Array(decoded.actionID.utf8) == Array(id.utf8))
        #expect(decoded.sequence == .max && decoded.revision == .max)
        #expect(!String(decoding: bytes, as: UTF8.self).contains(#"\/"#))
        #expect(bytes.count <= 4096)
    }
    let composed = try GuestUIEventCodecV1.encode(GuestUIEventV1(sequence: 1, revision: 1, nodeID: "é", actionID: "a"))
    let decomposed = try GuestUIEventCodecV1.encode(GuestUIEventV1(sequence: 1, revision: 1, nodeID: "e\u{301}", actionID: "a"))
    #expect(composed != decomposed)
    for id in ["", "\n", "\u{7f}", String(repeating: "é", count: 65)] {
        #expect(throws: GuestUIEventCodecErrorV1.identifier) {
            try GuestUIEventV1(sequence: 1, revision: 1, nodeID: id, actionID: "a")
        }
    }
}

@Test func guestUIEventCodecRejectsNumericCoercionAndWrongValues() {
    let numbers = ["0", "-1", "-0", "+1", "01", "1.0", "1e0", "1E0", "true", "false", "null", #""1""#,
                   "18446744073709551616", "9999999999999999999999999999999999999999999999"]
    for field in ["sequence", "revision"] {
        for number in numbers {
            let input = guestUIEventExample.replacingOccurrences(of: "\"\(field)\":1", with: "\"\(field)\":\(number)")
            #expect(throws: (any Error).self) { try GuestUIEventCodecV1.decode(Data(input.utf8)) }
        }
    }
    for replacement in ["0", "2", "true", "1.0", "1e0", #""1""#] {
        let input = guestUIEventExample.replacingOccurrences(of: "\"schemaVersion\":1", with: "\"schemaVersion\":\(replacement)")
        #expect(throws: (any Error).self) { try GuestUIEventCodecV1.decode(Data(input.utf8)) }
    }
    for replacement in ["true", "false", "0", #""null""#, "{}", "[]"] {
        let input = guestUIEventExample.replacingOccurrences(of: "\"value\":null", with: "\"value\":\(replacement)")
        #expect(throws: (any Error).self) { try GuestUIEventCodecV1.decode(Data(input.utf8)) }
    }
    let wrongEvent = guestUIEventExample.replacingOccurrences(of: "activate", with: "submit")
    #expect(throws: (any Error).self) { try GuestUIEventCodecV1.decode(Data(wrongEvent.utf8)) }
}

@Test func guestUIEventCodecRejectsAmbiguousMalformedAndUnboundedBytes() {
    let duplicate = guestUIEventExample.dropLast() + #", "sche\u006daVersion":1}"#
    let unknown = guestUIEventExample.dropLast() + #", "callback":"run"}"#
    let missing = guestUIEventExample.replacingOccurrences(of: #""value":null"#, with: "")
    let invalidSurrogate = guestUIEventExample.replacingOccurrences(of: #""save""#, with: #""\ud800""#)
    let control = guestUIEventExample.replacingOccurrences(of: #""save""#, with: #""\u0000""#)
    let trailing = guestUIEventExample + "{}"
    for input in [String(duplicate), String(unknown), missing, invalidSurrogate, control, trailing,
                  "[]", "null", "{}", "[" + guestUIEventExample + "]", String(guestUIEventExample.dropLast())] {
        #expect(throws: (any Error).self) { try GuestUIEventCodecV1.decode(Data(input.utf8)) }
    }
    for input in [Data([0xef, 0xbb, 0xbf]) + Data(guestUIEventExample.utf8), Data([0xff]), Data(repeating: 32, count: 4097)] {
        #expect(throws: (any Error).self) { try GuestUIEventCodecV1.decode(input) }
    }
}
