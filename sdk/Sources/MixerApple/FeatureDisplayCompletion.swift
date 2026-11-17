#if canImport(SwiftUI)
import SwiftUI
import QuartzCore

// The bridge is attached to MixerNativeView. An unmounted view never acknowledges.
// Completion is a platform display-transaction fact, not pixel qualification.
#if canImport(AppKit)
import AppKit
@MainActor internal struct FeatureDisplayCompletion: NSViewRepresentable {
    let id: UUID?
    let complete: @MainActor (UUID) -> Void
    func makeNSView(context: Context) -> DisplayView { DisplayView() }
    func updateNSView(_ view: DisplayView, context: Context) { view.request(id, completion: complete) }
    @MainActor final class DisplayView: NSView {
        private var id: UUID?
        private var completion: (@MainActor (UUID) -> Void)?
        func request(_ id: UUID?, completion: @escaping @MainActor (UUID) -> Void) {
            self.id = id; self.completion = completion; scheduleDisplay()
        }
        override func viewDidMoveToWindow() { super.viewDidMoveToWindow(); scheduleDisplay() }
        private func scheduleDisplay() {
            guard let id, window != nil else { return }
            DispatchQueue.main.async { [weak self] in
                guard let self, self.id == id, let window = self.window else { return }
                CATransaction.begin()
                CATransaction.setCompletionBlock { [weak self] in
                    Task { @MainActor in
                        guard let self, self.id == id, self.window != nil else { return }
                        self.id = nil; self.completion?(id)
                    }
                }
                window.contentView?.layoutSubtreeIfNeeded()
                window.displayIfNeeded()
                CATransaction.commit()
            }
        }
    }
}
#elseif canImport(UIKit)
import UIKit
@MainActor internal struct FeatureDisplayCompletion: UIViewRepresentable {
    let id: UUID?
    let complete: @MainActor (UUID) -> Void
    func makeUIView(context: Context) -> DisplayView { DisplayView() }
    func updateUIView(_ view: DisplayView, context: Context) { view.request(id, completion: complete) }
    @MainActor final class DisplayView: UIView {
        private var id: UUID?
        private var completion: (@MainActor (UUID) -> Void)?
        func request(_ id: UUID?, completion: @escaping @MainActor (UUID) -> Void) {
            self.id = id; self.completion = completion; scheduleDisplay()
        }
        override func didMoveToWindow() { super.didMoveToWindow(); scheduleDisplay() }
        private func scheduleDisplay() {
            guard let id, window != nil else { return }
            DispatchQueue.main.async { [weak self] in
                guard let self, self.id == id, let window = self.window else { return }
                CATransaction.begin()
                CATransaction.setCompletionBlock { [weak self] in
                    Task { @MainActor in
                        guard let self, self.id == id, self.window != nil else { return }
                        self.id = nil; self.completion?(id)
                    }
                }
                window.layoutIfNeeded(); window.layer.displayIfNeeded()
                CATransaction.commit()
            }
        }
    }
}
#endif
#endif
