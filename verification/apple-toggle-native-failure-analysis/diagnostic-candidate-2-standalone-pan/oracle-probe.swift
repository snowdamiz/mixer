import Foundation

func state(_ selected: Bool, _ primary: Int = 0, _ value: Int = 0, _ last: Bool? = nil, identity: String = "same", attached: Bool = true) -> DiagnosticActivationState {
    DiagnosticActivationState(selected: selected, attachedToWindow: attached, identity: identity, primaryCount: primary, valueCount: value, lastValue: last)
}
func result(initial: Bool, before: DiagnosticActivationState, after: DiagnosticActivationState, active: Bool = true, value: Bool = true, ax: Bool = false, returned: Bool? = nil) -> Bool {
    DiagnosticRequirement.meets(initial: initial, expectedActivation: active, requiresValueEvent: value, accessibility: ax, returned: returned, before: before, after: after)
}
let checks: [(String, Bool)] = [
    ("off-to-on native state and one event", result(initial: false, before: state(false), after: state(true, 1, 1, true))),
    ("on-to-off independent premise", result(initial: true, before: state(true), after: state(false, 1, 1, false))),
    ("original off-to-off is rejected", !result(initial: false, before: state(false), after: state(false, 1, 1, false))),
    ("original false-positive second test is rejected", !result(initial: true, before: state(false, 1, 1, false), after: state(false, 2, 2, false))),
    ("no on-to-off transition is rejected", !result(initial: true, before: state(true), after: state(true, 1, 1, true))),
    ("duplicate primary action rejected", !result(initial: false, before: state(false), after: state(true, 2, 1, true))),
    ("duplicate value event rejected", !result(initial: false, before: state(false), after: state(true, 1, 2, true))),
    ("wrong event value rejected", !result(initial: false, before: state(false), after: state(true, 1, 1, false))),
    ("binding state write without action rejected", !result(initial: false, before: state(false), after: state(true))),
    ("identity replacement rejected", !result(initial: false, before: state(false), after: state(true, 1, 1, true, identity: "replacement"))),
    ("unattached native reference rejected", !result(initial: false, before: state(false, attached: false), after: state(true, 1, 1, true))),
    ("gate rejection leaves state and event count", result(initial: false, before: state(false), after: state(false, 1), active: false)),
    ("gate violation rejects emitted event", !result(initial: false, before: state(false), after: state(false, 1, 1, false), active: false)),
    ("accessibility requires successful return", !result(initial: false, before: state(false), after: state(true, 1, 1, true), ax: true, returned: false)),
    ("accessibility successful state and count", result(initial: false, before: state(false), after: state(true, 1, 1, true), ax: true, returned: true)),
    ("disabled accessibility must return false", !result(initial: false, before: state(false), after: state(false), active: false, ax: true, returned: true)),
    ("plain UIKit value event is observed separately", result(initial: false, before: state(false), after: state(true, 1), value: false))
]
let output: [String: Any] = ["scope": "Diagnostic verdict logic only; no UIKit or input runtime", "checks": checks.map { ["name": $0.0, "pass": $0.1] }]
print(String(data: try JSONSerialization.data(withJSONObject: output, options: [.prettyPrinted, .sortedKeys]), encoding: .utf8)!)
if !checks.allSatisfy({ $0.1 }) { exit(1) }
