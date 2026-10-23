import Foundation
import MixerUI

func require(_ condition: Bool, _ message: String) throws {
    if !condition { throw NSError(domain: "PacketConsumer", code: 1, userInfo: [NSLocalizedDescriptionKey: message]) }
}

func snapshot(_ document: UIDocument) throws -> UIRenderSnapshot {
    var reconciler = UIReconciler()
    try reconciler.apply(document)
    return try reconciler.currentSnapshot()
}

func allKinds() throws -> UIRenderSnapshot {
    try snapshot(Navigation("navigation", title: "Project") {
        List("list") {
            Section("section", title: "Notes") {
                VStack("vertical", alignment: .leading, spacing: 12.75) {
                    HStack("horizontal", alignment: .center, spacing: 2.5) {
                        Text("text", "Café 🏗️", style: .headline, selectable: true, maximumLines: 3)
                        Button("button", "Save", action: "save", role: .destructive)
                    }
                    ZStack("overlay", alignment: .topTrailing) {
                        TextField("input", "Title", value: "Draft", action: "edit", onSubmit: "submit")
                        Toggle("toggle", "Done", value: false, action: "toggle")
                    }
                }
            }
        }
    }.document(revision: .max))
}

let output = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
if CommandLine.arguments[1] == "emit" {
    try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
    func write(_ name: String, _ value: UIRenderSnapshot) throws {
        try value.encodeNativePacketV1().write(to: output.appendingPathComponent(name + ".json"))
    }
    try write("all-kinds", allKinds())
    let controls = String(String.UnicodeScalarView((0..<32).map { UnicodeScalar($0)! }))
    try write("unicode", snapshot(Text("e\u{301}", controls + "\\\"/é e\u{301} 漢字 🏗️ \u{2028}\u{2029}").document(revision: 0)))
    var reconciler = UIReconciler()
    try reconciler.apply(VStack("root") { Button("a", "A", action: "a"); Button("b", "B", action: "b") }.document(revision: 1))
    try write("first", reconciler.currentSnapshot())
    try reconciler.apply(VStack("root") { Button("b", "Changed", action: "b"); Button("a", "A", action: "a") }.document(revision: 2))
    try write("second", reconciler.currentSnapshot())
    try reconciler.apply(VStack("root") { Button("b", "B", action: "b") }.document(revision: 3))
    try write("removed", reconciler.currentSnapshot())
    try reconciler.apply(VStack("root") { Button("a", "A", action: "a") }.document(revision: 4))
    try write("reinserted", reconciler.currentSnapshot())
    try write("baseline-unsupported", snapshot(HStack("root", alignment: .firstTextBaseline) { Text("a", "A") }.document(revision: 1)))
    var deep = Text("leaf", "ok").uiNode
    for index in 0..<63 { deep = UINode(id: "depth.\(index)", kind: .vStack, children: [deep]) }
    try write("depth64", snapshot(UIDocument(revision: 1, root: deep)))
    var values = Array(repeating: String(repeating: "\0", count: 16_384), count: 10) + Array(repeating: "", count: 4)
    func large() throws -> UIRenderSnapshot {
        try snapshot(VStack("root") {
            for (index, value) in values.enumerated() { Text("node.\(index)", value) }
        }.document(revision: 1))
    }
    var padding = 1_048_576 - (try large().encodeNativePacketV1().count)
    for index in 10..<14 {
        let count = min(padding, 16_384)
        values[index] = String(repeating: "x", count: count)
        padding -= count
    }
    try require(padding == 0, "output boundary fixture")
    try write("exact-limit", large())
    print("PASS: emitted nine public snapshot packets")
} else if CommandLine.arguments[1] == "verify-events" {
    let value = try allKinds()
    for (name, action) in [("activate", "save"), ("textChange", "edit"), ("valueChange", "toggle")] {
        let data = try Data(contentsOf: output.appendingPathComponent(name + ".json"))
        let event = try JSONDecoder().decode(UIEventEnvelope.self, from: data)
        try require(event.revision == UInt64.max, "unsigned revision preserved")
        let routed = try value.route(event)
        try require(routed.actionID == action, "native decoder event returns to original binding")
        if name == "textChange" { try require(routed.value == .string("é\0漢字🏗️"), "native text event bytes") }
        if name == "valueChange" { try require(routed.value == .bool(true), "native toggle event") }
    }
    print("PASS: three Java events routed by original Swift snapshot")
} else {
    throw NSError(domain: "PacketConsumer", code: 2)
}
