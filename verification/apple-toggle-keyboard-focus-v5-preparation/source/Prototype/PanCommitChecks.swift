import UIKit

/// Fixture callbacks from real native pan release only. No synthetic touch,
/// recognizer state or translation is supplied by this fixture.
extension PrototypeController {
    func exercisePanCommitHook(_ reason: String) {
        guard let mode = panCommitMode, !panCommitHookFired else { return }
        let expectedReason = mode == "arm-commit-after-event-rebind" ? "panAccepted" : "selection"
        guard reason == expectedReason, toggle.slidePan.state == .ended else { return }
        panCommitHookFired = true
        let before = snapshot()
        let gesture = DiagnosticTrace.shared.gesture(toggle.slidePan)
        let started = ProcessInfo.processInfo.systemUptime
        var returned: Bool?
        switch mode {
        case "arm-commit-rebind": toggle.setOn(panCommitInitial, animated: false)
        case "arm-commit-stale": allowed = false
        case "arm-commit-disable": toggle.isEnabled = false
        case "arm-commit-cancel": toggle.cancelAuthoredInteraction()
        case "arm-commit-direction":
            toggle.direction = toggle.direction == .leftToRight ? .rightToLeft : .leftToRight
        case "arm-commit-nested-primary": toggle.performPrimaryAction()
        case "arm-commit-nested-accessibility": returned = toggle.accessibilityActivate()
        case "arm-commit-after-event-rebind": toggle.setOn(panCommitInitial, animated: false)
        default: break
        }
        panCommitRecords.append([
            "mode": mode, "reason": reason, "initial": panCommitInitial,
            "before": before, "after": snapshot(), "nativeGestureAtHook": gesture,
            "returned": returned as Any? ?? NSNull(), "startedUptime": started,
            "finishedUptime": ProcessInfo.processInfo.systemUptime,
            "traceSequenceAtCompletion": DiagnosticTrace.shared.revision
        ])
        panCommitMode = nil
        record("panCommitHookComplete")
    }
}
