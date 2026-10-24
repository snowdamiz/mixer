import UIKit

/// Actual UIKit callback checks. No fabricated touch or recognizer state.
@MainActor extension PrototypeController {
    func semanticActivationChecks() -> [[String: Any]] {
        var rows: [[String: Any]] = []
        let originalObserver = toggle.stateChanged
        let oldRecording = recording
        recording = true
        defer {
            toggle.stateChanged = originalObserver
            allowed = true; toggle.isEnabled = true; toggle.setOn(false, animated: false)
            recording = oldRecording
        }
        func capture() -> [String: Any] {
            ["selected": toggle.isOn, "retained": toggle.retainedOn, "primary": toggle.primaryCount,
             "accepted": toggle.acceptedCount, "events": eventCount, "lastValue": eventValues.last as Any? ?? NSNull(),
             "identity": String(describing: ObjectIdentifier(toggle)), "enabled": toggle.isEnabled, "allowed": allowed,
             "selectedTrait": toggle.accessibilityTraits.contains(.selected), "disabledTrait": toggle.accessibilityTraits.contains(.notEnabled),
             "buttonTrait": toggle.accessibilityTraits.contains(.button), "toggleTrait": toggle.accessibilityTraits.contains(.toggleButton),
             "nativeAutomaticSelection": toggle.changesSelectionAsPrimaryAction,
             "label": toggle.accessibilityLabel ?? "", "hint": toggle.accessibilityHint ?? ""]
        }
        func run(_ mode: String, initial: Bool, accessibility: Bool, enabled: Bool = true, input: Bool = true) {
            toggle.stateChanged = originalObserver
            allowed = true; toggle.isEnabled = true; toggle.setOn(initial, animated: false)
            allowed = input; toggle.isEnabled = enabled
            let before = capture()
            var fired = false
            var nestedReturn: Bool?
            toggle.stateChanged = { [unowned self] reason in
                originalObserver?(reason)
                let trigger = mode.hasSuffix("-cancel") ? "cancel" : "selection"
                guard reason == trigger, !fired else { return }
                switch mode {
                case "reentrant-primary": fired = true; self.toggle.performPrimaryAction()
                case "reentrant-accessibility": fired = true; nestedReturn = self.toggle.accessibilityActivate()
                case "rebind-selection": fired = true; self.toggle.setOn(initial, animated: false)
                case "rebind-cancel": fired = true; self.toggle.setOn(!initial, animated: false)
                case "close-selection", "close-cancel": fired = true; self.allowed = false
                default: break
                }
            }
            let returned: Bool?
            if accessibility { returned = toggle.accessibilityActivate() }
            else { toggle.performPrimaryAction(); returned = nil }
            let after = capture()
            toggle.stateChanged = originalObserver
            rows.append(["index": rows.count, "mode": mode, "initial": initial, "accessibility": accessibility,
                         "enabled": enabled, "input": input, "hookFired": fired,
                         "returned": returned as Any? ?? NSNull(), "nestedReturn": nestedReturn as Any? ?? NSNull(),
                         "before": before, "after": after])
        }
        // Four admitted and twelve disabled/stale/both-blocked combinations.
        for initial in [false, true] {
            for accessibility in [false, true] {
                run("admitted", initial: initial, accessibility: accessibility)
                run("blocked", initial: initial, accessibility: accessibility, enabled: false)
                run("blocked", initial: initial, accessibility: accessibility, input: false)
                run("blocked", initial: initial, accessibility: accessibility, enabled: false, input: false)
            }
        }
        // Reentry occurs in the real selected-property observer during dispatch.
        for initial in [false, true] {
            run("reentrant-primary", initial: initial, accessibility: false)
            run("reentrant-accessibility", initial: initial, accessibility: false)
        }
        // Rebind/input closure both before proposal and after selected assignment.
        for mode in ["rebind-selection", "rebind-cancel", "close-selection", "close-cancel"] {
            for initial in [false, true] {
                for accessibility in [false, true] { run(mode, initial: initial, accessibility: accessibility) }
            }
        }
        return rows
    }
}
