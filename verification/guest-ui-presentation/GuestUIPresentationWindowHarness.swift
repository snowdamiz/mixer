import AppKit
import SwiftUI
import Foundation
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

/// A real NSApplication run loop, separate from XCTest's occluded host process.
/// This qualifies only native Mac layout/display; it is not a compositor proof.
@main
@MainActor
enum GuestUIPresentationWindowHarness {
    private static let delegate = HarnessDelegate()
    static func main() {
        let app = NSApplication.shared
        app.setActivationPolicy(.regular)
        app.delegate = delegate
        app.run()
    }
}

@MainActor
private final class HarnessDelegate: NSObject, NSApplicationDelegate {
    private var window: NSWindow?
    func applicationDidFinishLaunching(_ notification: Notification) {
        Task { @MainActor in
            do { try await exercise() }
            catch { write(["status": "failed", "error": String(describing: error)]) }
            NSApplication.shared.terminate(nil)
        }
    }
    private func write(_ result: [String: Any]) {
        guard CommandLine.arguments.count == 2,
              let bytes = try? JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys]) else { return }
        try? bytes.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
    }
    private func exercise() async throws {
        let binding = CapabilityGuestUIPresentationBinding()
        let exchange = try GuestUIExchangeV1(generation: 1)
        let consumer = try await binding.bind(exchange)
        let startup = try exchange.claimStartup()
        let bytes = Data("{\"schemaVersion\":1,\"revision\":1,\"root\":{\"id\":\"root\",\"kind\":\"vStack\",\"properties\":{},\"actions\":[],\"children\":[{\"id\":\"status\",\"kind\":\"text\",\"properties\":{\"text\":\"Ready\"},\"children\":[],\"actions\":[]},{\"id\":\"save\",\"kind\":\"button\",\"properties\":{\"label\":\"Save sample\"},\"children\":[],\"actions\":[{\"id\":\"sample.save\",\"event\":\"activate\"}]}]}}".utf8)
        try exchange.finishTurn(startup, documentBytes: bytes)
        try exchange.enterEffectsIntent(generation: 1)
        try exchange.confirmEffectsEnabled(generation: 1)
        let screen = NSHostingView(rootView: MixerGuestScreen(presentation: binding.presentation))
        let window = NSWindow(contentRect: NSRect(x: 180, y: 180, width: 360, height: 240),
                              styleMask: [.titled, .closable], backing: .buffered, defer: false)
        self.window = window
        window.title = "Mixer native presentation verification"
        window.isReleasedWhenClosed = false
        window.contentView = screen
        window.makeKeyAndOrderFront(nil)
        NSApplication.shared.activate()
        let deadline = ContinuousClock.now + .seconds(10)
        while exchange.snapshot().pendingPresentationReceipt == nil && ContinuousClock.now < deadline {
            try await Task.sleep(for: .milliseconds(10))
            screen.needsLayout = true
            screen.layoutSubtreeIfNeeded()
            window.displayIfNeeded()
        }
        let receipt = exchange.snapshot().pendingPresentationReceipt
        var labels: [String] = []
        func accessibility(_ value: Any, depth: Int = 0) {
            guard depth < 32, let element = value as? any NSAccessibilityProtocol else { return }
            if let label = element.accessibilityLabel() { labels.append(label) }
            if let value = element.accessibilityValue() as? String { labels.append(value) }
            for child in element.accessibilityChildren() ?? [] { accessibility(child, depth: depth + 1) }
        }
        accessibility(screen)
        let status = receipt != nil && labels.contains("Ready") && labels.contains("Save sample") ? "passed" : "failed"
        write(["status": status, "windowVisible": window.isVisible,
               "windowOcclusionRaw": window.occlusionState.rawValue,
               "windowOcclusionVisible": window.occlusionState.contains(.visible),
               "observedRevision": receipt?.revision as Any? ?? NSNull(), "accessibilityLabels": labels])
        exchange.stop(.closed); await consumer.value
        window.close(); self.window = nil
    }
}
