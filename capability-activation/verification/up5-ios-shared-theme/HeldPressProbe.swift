import SwiftUI
import UIKit

struct HeldPressProbe: UIViewRepresentable {
    let actionCount: () -> Int
    let report: (String) -> Void

    func makeUIView(context: Context) -> Attachment {
        Attachment()
    }

    func updateUIView(_ view: Attachment, context: Context) {
        view.touch.actionCount = actionCount
        view.touch.report = report
    }

    static func discardPreviousCapture() throws {
        let url = TouchObserver.captureURL
        if FileManager.default.fileExists(atPath: url.path) {
            try FileManager.default.removeItem(at: url)
        }
    }

    final class Attachment: UIView {
        let touch = TouchObserver()

        override func didMoveToWindow() {
            super.didMoveToWindow()
            touch.view?.removeGestureRecognizer(touch)
            window?.addGestureRecognizer(touch)
        }
    }

    final class TouchObserver: UIGestureRecognizer {
        static let captureURL = URL.cachesDirectory.appendingPathComponent("UP5-held-press.png")

        var actionCount: () -> Int = { 0 }
        var report: (String) -> Void = { _ in }
        private var captureTask: Task<Void, Never>?
        private var captured = false

        init() {
            super.init(target: nil, action: nil)
            cancelsTouchesInView = false
            delaysTouchesBegan = false
            delaysTouchesEnded = false
        }

        override func canPrevent(_ preventedGestureRecognizer: UIGestureRecognizer) -> Bool { false }
        override func canBePrevented(by preventingGestureRecognizer: UIGestureRecognizer) -> Bool { false }

        override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent) {
            guard !captured, captureTask == nil, touches.count == 1, let touch = touches.first,
                  let window = view as? UIWindow else {
                state = .failed
                return
            }
            let point = touch.location(in: window)
            let started = ProcessInfo.processInfo.systemUptime
            captureTask = Task { @MainActor [weak self, weak window] in
                do {
                    try await Task.sleep(for: .milliseconds(450))
                    guard let self, let window, state == .possible,
                          touch.phase == .began || touch.phase == .stationary || touch.phase == .moved,
                          abs(touch.location(in: window).x - point.x) < 3,
                          abs(touch.location(in: window).y - point.y) < 3 else { return }
                    captured = true
                    try capture(in: window, around: point, started: started)
                } catch is CancellationError {
                    return
                } catch {
                    self?.report("capture failed: \(error)")
                }
            }
        }

        override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent) { state = .failed }
        override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent) { state = .failed }

        override func reset() {
            captureTask?.cancel()
            captureTask = nil
            super.reset()
        }

        private func capture(in window: UIWindow, around point: CGPoint, started: TimeInterval) throws {
            // The 144-point fixture button is centered under the touch. Sample inside
            // its left fill, away from the label, outline, and rounded corners.
            let patch = CGRect(x: point.x - 64, y: point.y - 5, width: 8, height: 10)
            let format = UIGraphicsImageRendererFormat()
            format.scale = window.traitCollection.displayScale
            var drew = false
            let image = UIGraphicsImageRenderer(bounds: window.bounds, format: format).image { _ in
                drew = window.drawHierarchy(in: window.bounds, afterScreenUpdates: true)
            }
            let elapsed = ProcessInfo.processInfo.systemUptime - started
            guard drew, let screen = image.cgImage, let png = image.pngData() else {
                throw CaptureError.incompleteWindow
            }
            let scale = CGAffineTransform(scaleX: format.scale, y: format.scale)
            guard let slice = screen.cropping(to: patch.applying(scale).integral) else {
                throw CaptureError.missingPatch
            }
            let pixels = try ThemePixels(slice)
            let pressed = pixels.fraction(of: .init(58, 27, 97))
            let resting = pixels.fraction(of: .init(82, 36, 138))
            try png.write(to: Self.captureURL, options: .atomic)
            report("captured \(pressed) \(resting) \(actionCount()) \(elapsed)")
        }

        private enum CaptureError: Error {
            case incompleteWindow, missingPatch
        }
    }
}
