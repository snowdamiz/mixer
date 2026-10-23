import Foundation
#if CHECKLIST
import MixerAndroidEngine
#else
import MixerUI
import MixerAndroidRuntime
#endif

let folder = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
#if CHECKLIST
try ChecklistEngine().render().write(to: folder.appendingPathComponent("checklist.json"))
#else
let engine = try AndroidDocumentSession(state: "é\0漢字🏗️", document: { state, revision in
    VStack("root") {
        Text("text", state)
        Button("button", "Save", action: "save")
    }.document(revision: revision)
}, reduce: { _, _ in })
try engine.render().write(to: folder.appendingPathComponent("document.json"))
#endif
print("PASS: actual engine packet emitted through public API")
