import CoreGraphics
import Foundation

/// Private qualification admission state. UIKit still owns recognition and all
/// post-admission translation. Coordinates are public UIWindow points.
struct TogglePanAdmission {
    struct Context: Equatable {
        let carrier: String
        let window: String
        let binding: UInt64
        let frameInWindow: CGRect
        let carrierBounds: CGRect
        let carrierTransform: CGAffineTransform
        let windowBounds: CGRect
        let basisInWindow: [CGPoint]

        var finite: Bool {
            let numbers = [frameInWindow.minX, frameInWindow.minY, frameInWindow.width, frameInWindow.height,
                           carrierBounds.minX, carrierBounds.minY, carrierBounds.width, carrierBounds.height,
                           carrierTransform.a, carrierTransform.b, carrierTransform.c, carrierTransform.d,
                           carrierTransform.tx, carrierTransform.ty,
                           windowBounds.minX, windowBounds.minY, windowBounds.width, windowBounds.height]
            return numbers.allSatisfy(\.isFinite) && basisInWindow.count == 3 && basisInWindow.allSatisfy { $0.x.isFinite && $0.y.isFinite } && frameInWindow.width > 0 && frameInWindow.height > 0
                && carrierBounds.width > 0 && carrierBounds.height > 0 && windowBounds.width > 0 && windowBounds.height > 0
        }
    }
    struct Origin {
        let touch: String
        let point: CGPoint
        let timestamp: TimeInterval
        let context: Context
        let attempt: UInt64
    }
    struct Decision {
        let origin: Origin?
        let current: CGPoint
        let displacement: CGPoint?
        let accepted: Bool
        let reason: String
        let attempt: UInt64
    }
    private(set) var origin: Origin?
    private(set) var invalidated = false
    private(set) var attempt: UInt64 = 0
    private var initialPolicyDecision: Bool?

    mutating func reset() { origin = nil; invalidated = false; initialPolicyDecision = nil; attempt &+= 1 }
    mutating func invalidate() { invalidated = true }
    mutating func capture(touch: String, point: CGPoint, timestamp: TimeInterval, context: Context) {
        guard origin == nil, !invalidated, point.x.isFinite, point.y.isFinite,
              timestamp.isFinite, context.finite else { invalidated = true; return }
        attempt &+= 1
        origin = Origin(touch: touch, point: point, timestamp: timestamp, context: context, attempt: attempt)
    }
    mutating func decide(touch: String?, current: CGPoint, timestamp: TimeInterval,
                         context: Context?, touchCount: Int, touchActive: Bool, enabled: Bool, allowed: Bool) -> Decision {
        let captured = origin
        let displacement = captured.map { CGPoint(x: current.x - $0.point.x, y: current.y - $0.point.y) }
        let reason: String
        if invalidated { reason = "invalidated-or-multiple-touches" }
        else if captured == nil { reason = "missing-origin" }
        else if !enabled || !allowed { reason = "input-gate" }
        else if touchCount != 1 || !touchActive || touch != captured?.touch { reason = "touch-identity-or-lifecycle" }
        else if context != captured?.context || context?.finite != true { reason = "carrier-window-binding-or-geometry-changed" }
        else if !current.x.isFinite || !current.y.isFinite || !timestamp.isFinite || timestamp < captured!.timestamp { reason = "invalid-point-or-time" }
        else {
            // UIView and delegate routing may ask more than once. A repeated
            // query rechecks every fence and keeps this attempt's initial policy
            // result; it cannot authorize a new touch, geometry or binding.
            if initialPolicyDecision == nil { initialPolicyDecision = TogglePanPolicy.admits(displacement!) }
            reason = initialPolicyDecision == true ? "accepted" : "horizontal-policy"
        }
        if reason != "accepted" && reason != "horizontal-policy" { invalidated = true }
        let decision = Decision(origin: captured, current: current, displacement: displacement,
                                accepted: reason == "accepted", reason: reason, attempt: attempt)
        return decision
    }
}
