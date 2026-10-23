#if canImport(AppKit) && canImport(MixerApple)
import AppKit
import SwiftUI
import Testing
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

@Suite(.serialized)
@MainActor
struct GuestUIPresentationWindowTests {
    @Test func detachedAndHiddenNativeViewsCannotEarnDisplayObservation() async throws {
        _ = NSApplication.shared
        try await withPreparedPresentation { binding in
            let exchange = try GuestUIExchangeV1(generation: 1)
            let consumer = try await binding.bind(exchange)
            try startPresentationExchange(exchange)
            try await awaitPresentation { binding.presentation.state == .displaying(revision: 1) }
            let view = NSHostingView(rootView: MixerGuestScreen(presentation: binding.presentation))
            view.frame = NSRect(x: 0, y: 0, width: 320, height: 200)
            view.layoutSubtreeIfNeeded(); view.displayIfNeeded()
            try await Task.sleep(for: .milliseconds(30))
            #expect(exchange.snapshot().pendingPresentationReceipt == nil)
            let window = NSWindow(contentRect: view.frame, styleMask: [.titled], backing: .buffered, defer: false)
            window.isReleasedWhenClosed = false; window.contentView = view
            view.layoutSubtreeIfNeeded(); view.displayIfNeeded()
            try await Task.sleep(for: .milliseconds(30))
            #expect(!window.isVisible)
            #expect(exchange.snapshot().pendingPresentationReceipt == nil)
            window.contentView = nil; window.close()
            exchange.stop(.closed); await finishPresentationInstallation(consumer)
        }
    }

    @Test(.enabled(if: ProcessInfo.processInfo.environment["MIXER_GUEST_UI_VISIBLE_WINDOW"] == "1"))
    func visibleNativeWindowCompletesDisplayAndStopPreventsLaterObservation() async throws {
        let app = NSApplication.shared
        app.setActivationPolicy(.accessory)
        app.finishLaunching()
        app.activate()
        try await withPreparedPresentation { binding in
            let exchange = try GuestUIExchangeV1(generation: 2)
            let consumer = try await binding.bind(exchange)
            try startPresentationExchange(exchange)
            try await awaitPresentation { binding.presentation.state == .displaying(revision: 1) }
            let view = NSHostingView(rootView: MixerGuestScreen(presentation: binding.presentation))
            let window = NSWindow(contentRect: NSRect(x: 40, y: 40, width: 320, height: 200),
                                  styleMask: [.titled], backing: .buffered, defer: false)
            window.isReleasedWhenClosed = false; window.contentView = view
            window.orderFrontRegardless()
            view.needsLayout = true; view.layoutSubtreeIfNeeded(); window.displayIfNeeded()
            print("native window observation: visible=\(window.isVisible), occlusion=\(window.occlusionState.rawValue), frame=\(window.frame)")
            @MainActor func nativeTree(_ native: NSView, depth: Int = 0) {
                print("native view \(depth): \(type(of: native)), bounds=\(native.bounds), window=\(native.window != nil), hidden=\(native.isHiddenOrHasHiddenAncestor)")
                for child in native.subviews { nativeTree(child, depth: depth + 1) }
            }
            nativeTree(view)
            try await awaitPresentation { exchange.snapshot().pendingPresentationReceipt != nil }
            #expect(window.isVisible)
            #expect(window.occlusionState.contains(.visible))
            #expect(exchange.snapshot().pendingPresentationReceipt?.revision == 1)
            exchange.stop(.closed); await finishPresentationInstallation(consumer)
            #expect(exchange.snapshot().pendingPresentationReceipt == nil)
            view.needsLayout = true; view.layoutSubtreeIfNeeded(); window.displayIfNeeded()
            try await Task.sleep(for: .milliseconds(30))
            #expect(exchange.snapshot().pendingPresentationReceipt == nil)
            window.contentView = nil; window.close()
        }
    }
}
#endif
