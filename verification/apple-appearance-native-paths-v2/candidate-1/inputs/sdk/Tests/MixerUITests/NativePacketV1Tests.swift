import Foundation
import Testing
@testable import MixerUI

private func nativePacketSnapshot(_ document: UIDocument,
                                  limits: UIValidationLimits = .standard) throws -> UIRenderSnapshot {
    var reconciler = UIReconciler(validator: UIValidator(limits: limits))
    try reconciler.apply(document)
    return try reconciler.currentSnapshot()
}

private func nativePacketObject(_ data: Data) throws -> [String: Any] {
    try #require(JSONSerialization.jsonObject(with: data) as? [String: Any])
}

@Test func nativePacketV1PreservesAllCurrentNodeValuesAndAuthoritativeIdentities() throws {
    let document = Navigation("navigation", title: "Project") {
        List("list") {
            Section("section", title: "Notes") {
                VStack("vertical", alignment: .leading, spacing: 12.75) {
                    HStack("horizontal", alignment: .lastTextBaseline, spacing: 2.5) {
                        Text("text", "Café 🏗️", style: .headline, selectable: true, maximumLines: 3)
                        Button("button", "Save", action: "save", role: .destructive).disabled()
                    }
                    ZStack("overlay", alignment: .topTrailing) {
                        TextField("input", "Title", value: "Draft", action: "edit", onSubmit: "submit")
                        Toggle("toggle", "Done", value: false, action: "toggle")
                    }
                }
            }
        }
    }.document(revision: .max)
    let snapshot = try nativePacketSnapshot(document)
    let bytes = try snapshot.encodeNativePacketV1()
    #expect(bytes == (try snapshot.encodeNativePacketV1()))
    let packet = try nativePacketObject(bytes)
    #expect(Set(packet.keys) == ["schemaVersion", "document", "identities"])
    #expect((packet["schemaVersion"] as? NSNumber)?.intValue == 1)
    let body = try #require(packet["document"] as? [String: Any])
    #expect((body["revision"] as? NSNumber)?.uint64Value == UInt64.max)
    let bodyBytes = try JSONSerialization.data(withJSONObject: body, options: [.sortedKeys, .withoutEscapingSlashes])
    #expect(try UIDocument.decode(bodyBytes) == document)
    let identities = try #require(packet["identities"] as? [[String: Any]])
    #expect(identities.count == snapshot.nodeCount)
    #expect(identities.compactMap { $0["id"] as? String } ==
            ["navigation", "list", "section", "vertical", "horizontal", "text", "button", "overlay", "input", "toggle"])
    for identity in identities {
        let id = try #require(identity["id"] as? String)
        #expect((identity["generation"] as? NSNumber)?.uint64Value == snapshot.identity(for: id)?.generation)
    }
}

@Test func nativePacketV1DoesNotReconcileOrReassignGenerations() throws {
    var reconciler = UIReconciler()
    try reconciler.apply(VStack("root") {
        Button("a", "A", action: "a"); Button("b", "B", action: "b")
    }.document(revision: 1))
    let first = try reconciler.currentSnapshot()
    try reconciler.apply(VStack("root") {
        Button("b", "Changed", action: "b"); Button("a", "A", action: "a")
    }.document(revision: 2))
    let second = try reconciler.currentSnapshot()
    _ = try first.encodeNativePacketV1()
    let packet = try nativePacketObject(second.encodeNativePacketV1())
    let ids = try #require(packet["identities"] as? [[String: Any]])
    #expect(ids.compactMap { $0["id"] as? String } == ["root", "b", "a"])
    #expect(first.identity(for: "a") == second.identity(for: "a"))
    #expect(try reconciler.currentSnapshot().document == second.document)
    #expect(try second.route(UIEventEnvelope(revision: 2, identity: #require(second.identity(for: "a")),
                                            event: .activate)).actionID == "a")
    try reconciler.apply(VStack("root") { Button("b", "B", action: "b") }.document(revision: 3))
    try reconciler.apply(VStack("root") { Button("a", "A", action: "a") }.document(revision: 4))
    let replaced = try reconciler.currentSnapshot()
    #expect(replaced.identity(for: "a") != first.identity(for: "a"))
    _ = try replaced.encodeNativePacketV1()
}

@Test func nativePacketV1PreservesUnicodeBytesAndEscapesEveryJSONControl() throws {
    let controls = String(String.UnicodeScalarView((0..<32).map { UnicodeScalar($0)! }))
    let text = controls + "\\\"/é e\u{301} 漢字 🏗️ \u{2028}\u{2029}"
    for id in ["é", "e\u{301}"] {
        let snapshot = try nativePacketSnapshot(Text(id, text).document(revision: 0))
        let packet = try nativePacketObject(snapshot.encodeNativePacketV1())
        let body = try #require(packet["document"] as? [String: Any])
        let root = try #require(body["root"] as? [String: Any])
        let properties = try #require(root["properties"] as? [String: Any])
        #expect(Array(try #require(root["id"] as? String).utf8) == Array(id.utf8))
        #expect(Array(try #require(properties["text"] as? String).utf8) == Array(text.utf8))
    }
    // This remains the existing Swift canonical-identity rule, not a new alias policy.
    #expect(throws: UIValidationError.duplicateIdentity("e\u{301}")) {
        try nativePacketSnapshot(VStack("root") { Text("é", "one"); Text("e\u{301}", "two") }.document(revision: 1))
    }
}

@Test func nativePacketV1BoundsEscapedOutputAtExactlyOneMiB() throws {
    var texts = Array(repeating: String(repeating: "\0", count: 16_384), count: 10)
    texts += Array(repeating: "", count: 4)
    func snapshot(_ values: [String]) throws -> UIRenderSnapshot {
        try nativePacketSnapshot(VStack("root") {
            for (index, text) in values.enumerated() { Text("node.\(index)", text) }
        }.document(revision: 1))
    }
    let ceiling = 1_048_576
    let baseline = try snapshot(texts).encodeNativePacketV1().count
    var remaining = ceiling - baseline
    #expect(remaining > 0 && remaining < 4 * 16_384)
    for index in 10..<14 {
        let count = min(remaining, 16_384)
        texts[index] = String(repeating: "a", count: count)
        remaining -= count
    }
    #expect(remaining == 0)
    #expect(try snapshot(texts).encodeNativePacketV1().count == ceiling)
    texts[13] += "x"
    #expect(throws: UINativePacketEncodingError.outputLimit) { try snapshot(texts).encodeNativePacketV1() }
}

@Test func nativePacketV1NarrowsCustomSnapshotLimitsBeforeEncoding() throws {
    let large = try nativePacketSnapshot(Text("text", String(repeating: "x", count: 16_385)).document(revision: 1),
                                        limits: UIValidationLimits(maximumStringBytes: 32_768))
    #expect(throws: UIValidationError.limitExceeded("stringBytes")) { try large.encodeNativePacketV1() }
    var node = Text("leaf", "ok").uiNode
    for index in 0..<64 { node = UINode(id: "level.\(index)", kind: .vStack, children: [node]) }
    let deep = try nativePacketSnapshot(UIDocument(revision: 1, root: node), limits: UIValidationLimits(maximumDepth: 128))
    #expect(throws: UIValidationError.limitExceeded("depth")) { try deep.encodeNativePacketV1() }
    let wide = try nativePacketSnapshot(VStack("root") {
        for index in 0..<1001 { Text("text.\(index)", "ok") }
    }.document(revision: 1), limits: UIValidationLimits(maximumChildrenPerNode: 2000))
    #expect(throws: UIValidationError.limitExceeded("children")) { try wide.encodeNativePacketV1() }
}

@Test func nativePacketV1RejectsMissingOrByteAliasedInternalIdentities() throws {
    let snapshot = try nativePacketSnapshot(Text("é", "value").document(revision: 1))
    let missing = UIRenderSnapshot(document: snapshot.document, nodes: [:], maximumStringBytes: 16_384)
    #expect(throws: UINativePacketEncodingError.missingIdentity) { try missing.encodeNativePacketV1() }
    let original = try #require(snapshot.nodes["é"])
    let alias = ReconciledNode(node: original.node, identity: UINodeIdentity(id: "e\u{301}", generation: 1),
                               parent: nil, index: 0, disabled: false)
    let mismatched = UIRenderSnapshot(document: snapshot.document, nodes: ["é": alias], maximumStringBytes: 16_384)
    #expect(throws: UINativePacketEncodingError.missingIdentity) { try mismatched.encodeNativePacketV1() }
}

@Test func nativePacketV1PreservesFullUnsignedGenerationInInternalEncodingFixture() throws {
    // Data encoder boundary fixture only: no claim a reconciler performed 2^64 inserts.
    let document = Text("text", "value").document(revision: .max)
    let node = ReconciledNode(node: document.root, identity: UINodeIdentity(id: "text", generation: .max),
                              parent: nil, index: 0, disabled: false)
    let snapshot = UIRenderSnapshot(document: document, nodes: ["text": node], maximumStringBytes: 16_384)
    let packet = try nativePacketObject(snapshot.encodeNativePacketV1())
    let identities = try #require(packet["identities"] as? [[String: Any]])
    #expect((identities[0]["generation"] as? NSNumber)?.uint64Value == UInt64.max)
}

private func nativePacketComb(invalidDeepLeaf: Bool = false) -> UIDocument {
    var node = Text(invalidDeepLeaf ? "" : "leaf", "ok").uiNode
    for level in 0..<9 {
        let siblings = (0..<999).map { Text("sibling.\(level).\($0)", "").uiNode }
        node = UINode(id: "spine.\(level)", kind: .vStack, children: [node] + siblings)
    }
    return UIDocument(revision: 1, root: node)
}

@Test func nativePacketV1NarrowsCustomCombBeforePendingFrontierExceedsStandardLimit() throws {
    let document = nativePacketComb()
    let snapshot = try nativePacketSnapshot(document, limits: UIValidationLimits(maximumNodes: 16_384))
    #expect(snapshot.nodeCount == 9_001)
    #expect(throws: UIValidationError.limitExceeded("nodes")) { try snapshot.encodeNativePacketV1() }
    // An invalid deep descendant must not be reached through an over-budget
    // pending frontier. The old visited-only guard reached its empty identifier.
    #expect(throws: UIValidationError.limitExceeded("nodes")) {
        try UIValidator().validate(nativePacketComb(invalidDeepLeaf: true))
    }
}

@Test func nativePacketV1AcceptsExactStandardNodeCountAndRejectsOneMore() throws {
    func document(extra: Bool) -> UIDocument {
        let sizes = [1000, 1000, 1000, 1000, extra ? 91 : 90]
        let groups = sizes.enumerated().map { group, count in
            UINode(id: "group.\(group)", kind: .vStack,
                   children: (0..<count).map { Text("leaf.\(group).\($0)", "").uiNode })
        }
        return UIDocument(revision: 1, root: UINode(id: "root", kind: .vStack, children: groups))
    }
    let exact = try nativePacketSnapshot(document(extra: false))
    #expect(exact.nodeCount == 4096)
    let object = try nativePacketObject(exact.encodeNativePacketV1())
    #expect((object["identities"] as? [Any])?.count == 4096)
    #expect(throws: UIValidationError.limitExceeded("nodes")) { try nativePacketSnapshot(document(extra: true)) }
}
