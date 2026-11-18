import AppKit
import ApplicationServices
import FieldLogFeatures
import MixerApple
import MixerUI
import SwiftUI

struct Element: Encodable {
    let role: String
    let id: String
    let label: String
    let title: String
    let placeholder: String
    let help: String
    let value: String
    let ancestors: [String]

    static func read(_ element: AXUIElement, ancestors: [String] = []) -> [Element] {
        guard ancestors.count < 25 else { return [] }
        func get(_ name: String) -> CFTypeRef? {
            var result: CFTypeRef?
            return AXUIElementCopyAttributeValue(element, name as CFString, &result) == .success
                ? result : nil
        }
        func string(_ name: String) -> String { get(name) as? String ?? "" }
        let role = string("AXRole"), id = string("AXIdentifier")
        let row = Element(role: role, id: id, label: string("AXDescription"), title: string("AXTitle"),
                          placeholder: string("AXPlaceholderValue"), help: string("AXHelp"),
                          value: string("AXValue"), ancestors: ancestors)
        let childKey = ancestors.isEmpty ? "AXWindows" : "AXChildren"
        let children = get(childKey) as? [AXUIElement] ?? []
        return [row] + children.flatMap { read($0, ancestors: ancestors + [role + ":" + id]) }
    }
}

@MainActor
func observe(_ name: String, _ view: some SwiftUI.View) throws {
    let window = NSWindow(contentRect: NSRect(x: 40, y: 40, width: 610, height: 460),
                          styleMask: [.titled], backing: .buffered, defer: false)
    window.title = "Mixer AX probe " + name
    window.isReleasedWhenClosed = false
    defer { window.close() }
    let hosting = NSHostingView(rootView: view)
    window.contentView = hosting
    window.orderFront(nil)
    hosting.layoutSubtreeIfNeeded()
    let deadline = Date(timeIntervalSinceNow: 2)
    var elements: [Element] = []
    repeat {
        RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.08))
        elements = Element.read(AXUIElementCreateApplication(getpid()))
        if elements.contains(where: { $0.role == "AXTextField" || $0.role == "AXTextArea" }) { break }
    } while Date() < deadline
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.sortedKeys]
    print(name, String(decoding: try encoder.encode(elements), as: UTF8.self))
}

@MainActor
func makeSection(title: String?, id: String) throws -> MixerUIHost {
    let section = MixerUI.Section("section.node", title: title) {
        MixerUI.TextField("probe.first.node", "Probe first", value: "", action: "probe.first.change")
            .accessibilityIdentifier("probe.first").accessibilityLabel("First field label")
        MixerUI.TextField("probe.second", "Probe second", value: "", action: "probe.second.change")
    }.accessibilityIdentifier(id).accessibilityLabel("Section label")
        .accessibilityHint("Section hint").accessibilityValue("Section value")
    return try MixerUIHost(document: section.document(revision: 1))
}

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
app.finishLaunching()
guard AXIsProcessTrusted() else {
    print("AXIsProcessTrusted=false")
    exit(2)
}
print("AXIsProcessTrusted=true")
let editor = try TaskEditorAppleFieldsHost { _, _ in .saved }
defer { try? editor.close() }
try observe("fieldlog-form", Form {
    TaskEditorNativeFields(owner: editor)
    SwiftUI.Section { SwiftUI.Text("A responsibility label is stored locally.") }
})
let titled = try makeSection(title: "Probe title", id: "probe.section")
try observe("titled-form", Form { MixerNativeView(host: titled, onAction: { _ in }) })
let untitled = try makeSection(title: nil, id: "probe.headerless")
try observe("headerless-form", Form { MixerNativeView(host: untitled, onAction: { _ in }) })
try observe("headerless-stack", VStack { MixerNativeView(host: untitled, onAction: { _ in }) })
