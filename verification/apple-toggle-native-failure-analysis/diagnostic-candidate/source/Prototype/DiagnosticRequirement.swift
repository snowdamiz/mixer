/// Shared by the diagnostic fixture and executable host oracle checks.
/// This tests a verdict only; it cannot establish that UIKit delivered input.
struct DiagnosticActivationState {
    let selected: Bool
    let attachedToWindow: Bool
    let identity: String
    let primaryCount: Int
    let valueCount: Int
    let lastValue: Bool?
}
enum DiagnosticRequirement {
    static func meets(initial: Bool, expectedActivation: Bool, requiresValueEvent: Bool,
                      accessibility: Bool, returned: Bool?,
                      before: DiagnosticActivationState, after: DiagnosticActivationState) -> Bool {
        guard before.selected == initial, before.attachedToWindow, after.attachedToWindow,
              before.identity == after.identity else { return false }
        let valueDelta = after.valueCount - before.valueCount
        if expectedActivation {
            guard after.selected == !initial,
                  after.primaryCount - before.primaryCount == 1,
                  !accessibility || returned == true else { return false }
            return !requiresValueEvent || (valueDelta == 1 && after.lastValue == !initial)
        }
        return after.selected == initial && valueDelta == 0 && (!accessibility || returned == false)
    }
}
