import Foundation
import MixerUI

@main
enum CanonicalFixture {
    static func main() throws {
        let validator = UIValidator(supportedTextFieldAxes: [.horizontal, .vertical], textValuePolicy: .longNoteV1)
        var reconciler = UIReconciler(validator: validator)
        try reconciler.apply(UIDocument(revision: 10, root: UINode(id: "editor", kind: .vStack, children: [
            UINode(id: "title", kind: .textField, properties: [
                "label": .string("Title"), "value": .string("日本語 👩🏽‍💻"), "axis": .string("vertical"),
            ], actions: [UIActionBinding(id: "draft", event: .textChange)]),
            UINode(id: "save", kind: .button, properties: ["label": .string("Save")],
                   actions: [UIActionBinding(id: "save-handler", event: .activate)]),
        ])))
        let snapshot = try reconciler.currentSnapshot()
        precondition(["editor", "title", "save"].compactMap { snapshot.identity(for: $0)?.generation } == [1, 2, 3])
        let bytes = try validator.encode(snapshot.document)
        try bytes.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
        print("PASS canonical SDK fixture and Swift snapshot identities")
    }
}
