import UIKit

/// A fixture-only operation during a real public XCTest drag. It never creates
/// touches, writes recognizer state/translation, or fabricates a pan callback.
extension PrototypeController {
    func queueNativeInterruption(_ reason: String) {
        guard reason == "panPreview", let mode = interruptionMode,
              !interruptionQueued else { return }
        interruptionQueued = true
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            let pan = self.toggle.slidePan
            let before = self.snapshot()
            let gesture = DiagnosticTrace.shared.gesture(pan)
            let nativeHeld = self.toggle.panActive && pan.numberOfTouches == 1 &&
                (pan.state == .began || pan.state == .changed)
            let started = ProcessInfo.processInfo.systemUptime
            var returned: Bool?
            // A missing or already-ended native pan is a recorded test failure,
            // never a reason to invoke a substitute input path.
            if nativeHeld {
                switch mode {
                case "arm-pan-accessibility": returned = self.toggle.accessibilityActivate()
                case "arm-pan-cancel": self.toggle.cancelAuthoredInteraction()
                case "arm-pan-disable": self.toggle.isEnabled = false
                case "arm-pan-stale": self.allowed = false; self.toggle.cancelAuthoredInteraction()
                case "arm-pan-binding": self.toggle.setOn(!self.toggle.retainedOn, animated: false)
                default: break
                }
            }
            let after = self.snapshot()
            self.nativeInterruptions.append([
                "mode": mode, "nativeHeld": nativeHeld, "before": before,
                "nativeGestureBefore": gesture, "after": after,
                "returned": returned as Any? ?? NSNull(), "startedUptime": started,
                "finishedUptime": ProcessInfo.processInfo.systemUptime,
                "traceSequenceAtCompletion": DiagnosticTrace.shared.revision
            ])
            self.interruptionMode = nil
            self.record("nativeInterruptionComplete")
        }
    }
}
