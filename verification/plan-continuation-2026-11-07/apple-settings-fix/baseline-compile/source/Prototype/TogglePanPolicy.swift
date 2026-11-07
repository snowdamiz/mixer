import CoreGraphics
import MixerUI

/// Shared by the actual UIKit recognizer and executable host policy probes.
/// Passing this policy does not prove that a runtime delivered native input.
enum TogglePanPolicy {
    static let horizontalAdmissionThreshold: CGFloat = 6
    static let horizontalDominance: CGFloat = 1.2
    static let verticalExitAllowance: CGFloat = 22

    static func admits(_ translation: CGPoint) -> Bool {
        abs(translation.x) >= horizontalAdmissionThreshold && abs(translation.x) > abs(translation.y) * horizontalDominance
    }
    static func previewX(startX: CGFloat, translationX: CGFloat) -> CGFloat {
        min(24, max(2, startX + translationX))
    }
    static func checked(x: CGFloat, previous: Bool, direction: UILayoutDirectionV1) -> Bool {
        x == 13 ? previous : ((x > 13) != (direction == .rightToLeft))
    }
    static func permitsRelease(y: CGFloat, height: CGFloat) -> Bool {
        y >= -verticalExitAllowance && y <= height + verticalExitAllowance
    }
}
