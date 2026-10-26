import Foundation
import Testing
import MixerCore
import MixerUI
import MixerGuest

private let textNode = #"{"id":"text","kind":"text","properties":{"text":"A"},"children":[],"actions":[]}"#

private func duplicateRejected(_ json: String) {
    let bytes = Data(json.utf8)
    for decode in [{ try UIValidator().decode(bytes).document }, { try UIDocument.decode(bytes) },
                   { try GuestUICodec().decode(bytes).document }] {
        do { _ = try decode(); Issue.record("Duplicate JSON key was accepted") }
        catch let error as JSONInputError { #expect(error.reason == .duplicateKey) }
        catch { Issue.record("Unexpected rejection before duplicate check: \(error)") }
    }
}

@Test func everyRawUIEntryRejectsDuplicateDocumentNodePropertyAndActionKeys() {
    duplicateRejected("{\"schemaVersion\":1,\"schemaVersion\":1,\"revision\":1,\"root\":\(textNode)}")
    duplicateRejected("{\"schemaVersion\":1,\"revision\":1,\"revision\":2,\"root\":\(textNode)}")
    duplicateRejected("{\"schemaVersion\":1,\"revision\":1,\"root\":\(textNode),\"root\":\(textNode)}")
    duplicateRejected("{\"schemaVersion\":1,\"revision\":1,\"root\":\(textNode),\"\\u0072oot\":\(textNode)}")
    for node in [
        #"{"id":"a","id":"b","kind":"text","properties":{"text":"A"},"children":[],"actions":[]}"#,
        #"{"id":"a","kind":"text","properties":{"text":"A","te\u0078t":"B"},"children":[],"actions":[]}"#,
        #"{"id":"a","kind":"text","properties":{"text":"A"},"children":[],"actions":[],"actions":[]}"#,
        #"{"id":"a","kind":"button","properties":{"label":"Save"},"children":[],"actions":[{"id":"safe","id":"other","event":"activate"}]}"#,
        #"{"id":"a","kind":"button","properties":{"label":"Save"},"children":[],"actions":[{"id":"safe","event":"activate","ev\u0065nt":"submit"}]}"#,
    ] { duplicateRejected("{\"schemaVersion\":1,\"revision\":1,\"root\":\(node)}") }
}

@Test func unguardedCodableCannotBypassRawUIPreflight() throws {
    let bytes = Data("{\"schemaVersion\":1,\"revision\":1,\"root\":\(textNode)}".utf8)
    let decoder = JSONDecoder()
    #expect(throws: UIValidationError.unguardedDecoder) { try decoder.decode(UIDocument.self, from: bytes) }
    #expect(throws: UIValidationError.unguardedDecoder) { try decoder.decode(UINode.self, from: Data(textNode.utf8)) }
    #expect(throws: UIValidationError.unguardedDecoder) {
        try decoder.decode(UIActionBinding.self, from: Data(#"{"id":"save","event":"activate"}"#.utf8))
    }
    decoder.userInfo[CodingUserInfoKey(rawValue: "mixer.ui.rawPreflight")!] = true
    #expect(throws: UIValidationError.unguardedDecoder) { try decoder.decode(UIDocument.self, from: bytes) }
    #expect(try UIDocument.decode(bytes).root.id == "text")
}

@Test func rawUIRejectsInvalidUTF8AndExcessiveNesting() {
    do {
        _ = try UIDocument.decode(Data([0xff]))
        Issue.record("Invalid UTF-8 accepted")
    } catch let error as JSONInputError { #expect(error.reason == .invalidUTF8) }
    catch { Issue.record("Unexpected UTF-8 rejection: \(error)") }
    let deep = Data((String(repeating: "[", count: 300) + "0" + String(repeating: "]", count: 300)).utf8)
    #expect(throws: UIValidationError.limitExceeded("depth")) { try UIDocument.decode(deep) }
    #expect(throws: UIValidationError.limitExceeded("messageBytes")) {
        try GuestUICodec().decode(Data(repeating: 0x20, count: 1_048_577))
    }
}

@Test func guardedDecodeRetainsTheMaximumSupportedUINodeDepth() throws {
    var node = TextField("leaf", "Notes", value: "Unicode 🏗️", action: "edit", onSubmit: "save").uiNode
    for level in 1..<128 { node = UINode(id: "stack.\(level)", kind: .vStack, children: [node]) }
    let document = UIDocument(revision: 1, root: node)
    let validator = UIValidator(limits: UIValidationLimits(maximumDepth: 128))
    let encoded = try validator.encode(document)
    #expect(try UIDocument.decode(encoded, validator: validator) == document)
}
