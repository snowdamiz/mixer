import Foundation
import Testing
@testable import MixerUI

private func reviewSnapshot(_ document: UIDocument, nodes: Int = 4096) throws -> UIRenderSnapshot {
    var reconciler = UIReconciler(validator: UIValidator(limits: UIValidationLimits(maximumNodes: nodes)))
    try reconciler.apply(document)
    return try reconciler.currentSnapshot()
}

@Test func reviewCustomCombPreflightRejectsBeforeOutput() throws {
    var spine = Text("spine.leaf", "x").uiNode
    for level in (0..<9).reversed() {
        var children = [spine]
        for index in 0..<999 { children.append(Text("sibling.\(level).\(index)", "x").uiNode) }
        spine = UINode(id: "spine.\(level)", kind: .vStack, children: children)
    }
    let snapshot = try reviewSnapshot(UIDocument(revision: .max, root: spine), nodes: 65_536)
    #expect(snapshot.nodeCount == 9001)
    #expect(throws: UIValidationError.limitExceeded("nodes")) { try snapshot.encodeNativePacketV1() }
    print("ui_review_comb_input_nodes=\(snapshot.nodeCount); standard encoding rejects nodes")
}

@Test func reviewExactNodeAndNumericUnicodeBoundaries() throws {
    func document(extra: Bool) -> UIDocument {
        var groups: [UINode] = []
        for g in 0..<5 {
            let count = g == 4 ? 90 + (extra ? 1 : 0) : 1000
            groups.append(UINode(id: "group.\(g)", kind: .vStack,
                children: (0..<count).map { Text("n.\(g).\($0)", "x").uiNode }))
        }
        return UIDocument(revision: .max, root: UINode(id: "root", kind: .vStack, children: groups))
    }
    let exact = try reviewSnapshot(document(extra: false))
    #expect(exact.nodeCount == 4096)
    let bytes = try exact.encodeNativePacketV1()
    #expect(bytes.count <= 1_048_576)
    let object = try #require(JSONSerialization.jsonObject(with: bytes) as? [String: Any])
    #expect((object["identities"] as? [Any])?.count == 4096)
    let larger = try reviewSnapshot(document(extra: true), nodes: 65_536)
    #expect(throws: UIValidationError.limitExceeded("nodes")) { try larger.encodeNativePacketV1() }
    for spacing in [0.0, -0.0, Double.leastNonzeroMagnitude, Double.ulpOfOne, 12.75, 256.0] {
        let text = Text("q\"\\é", "\u{0000}\u{001f}é😀/")
        let value = try reviewSnapshot(VStack("r", spacing: spacing) { text }.document(revision: .max))
        let packet = try value.encodeNativePacketV1()
        let object = try #require(JSONSerialization.jsonObject(with: packet) as? [String: Any])
        let body = try #require(object["document"] as? [String: Any])
        #expect((body["revision"] as? NSNumber)?.uint64Value == UInt64.max)
        let root = try #require(body["root"] as? [String: Any])
        let props = try #require(root["properties"] as? [String: Any])
        #expect((props["spacing"] as? NSNumber)?.doubleValue == spacing)
        let decoded = try UIDocument.decode(JSONSerialization.data(withJSONObject: body, options: [.sortedKeys, .withoutEscapingSlashes]))
        #expect(decoded == value.document)
        #expect(packet == (try value.encodeNativePacketV1()))
    }
    print("ui_review_exact4096_plus1_and_numeric_unicode_boundaries=pass")
}
