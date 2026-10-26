import XCTest
import MixerUI

final class SharedTextProfilesV1Tests: XCTestCase {
    // Golden observations: apple-appearance-font-profile/type-profiles.json,
    // independently accepted in apple-appearance-font-profile-root-review.
    // Rows are body, headline, title, caption, section header, expanded title.
    private let observed: [[UInt32]] = [
        [14,14,25,11,14,31], [15,15,26,11,15,32], [16,16,27,11,16,33],
        [17,17,28,12,17,34], [19,19,30,14,19,36], [21,21,32,16,21,38],
        [23,23,34,18,23,40], [28,28,38,22,28,44], [33,33,43,26,33,48],
        [40,40,48,32,40,52], [47,47,53,37,47,56], [53,53,58,43,53,60],
    ]
    func testAllProfilesPreserveMeasuredRoleHierarchy() {
        XCTAssertEqual(UISharedTextProfileV1.allCases.map(\.rawValue),
                       ["xs","s","m","l","xl","xxl","xxxl","a1","a2","a3","a4","a5"])
        let weights: [UIFontWeightV1] = [.w400,.w600,.w400,.w400,.w600,.w700]
        for (profileIndex, profile) in UISharedTextProfileV1.allCases.enumerated() {
            for (roleIndex, role) in UISharedTextRoleV1.allCases.enumerated() {
                let metrics = profile.metrics(for: role)
                XCTAssertEqual(metrics.size64, observed[profileIndex][roleIndex] * 64)
                XCTAssertEqual(metrics.weight, weights[roleIndex])
            }
        }
        // Accessibility is role-specific, not a scalar applied to all roles.
        XCTAssertNotEqual(UISharedTextProfileV1.a1.metrics(for: .body).size64 * 28,
                          UISharedTextProfileV1.a1.metrics(for: .title).size64 * 17)
    }
    func testEveryAdmittedPreferenceUsesClosestAnchorAndLargerTies() throws {
        let anchors = observed.map { $0[0] * 64 }
        for requested in UInt32(14 * 64)...UInt32(53 * 64) {
            let selected = try UISharedTextProfileSelectionV1.nearest(preferredBodySize64: requested)
            let best = anchors.indices.min { left, right in
                let a = abs(Int(anchors[left]) - Int(requested))
                let b = abs(Int(anchors[right]) - Int(requested))
                return a == b ? left > right : a < b
            }!
            XCTAssertEqual(selected, UISharedTextProfileV1.allCases[best], "preference \(requested)")
        }
        for index in 1..<anchors.count {
            let midpoint = (anchors[index - 1] + anchors[index]) / 2
            XCTAssertEqual(try UISharedTextProfileSelectionV1.nearest(preferredBodySize64: midpoint),
                           UISharedTextProfileV1.allCases[index])
            XCTAssertEqual(try UISharedTextProfileSelectionV1.nearest(preferredBodySize64: midpoint - 1),
                           UISharedTextProfileV1.allCases[index - 1])
        }
    }
    func testUnsupportedPreferencesAreRejectedWithoutClamping() {
        for value: UInt32 in [0, 1, 14 * 64 - 1, 53 * 64 + 1, .max] {
            XCTAssertThrowsError(try UISharedTextProfileSelectionV1.nearest(preferredBodySize64: value)) {
                XCTAssertEqual($0 as? UISharedTextProfileErrorV1, .unsupportedBodySize)
            }
        }
        XCTAssertNil(UISharedTextProfileV1(rawValue: "unknown"))
    }
}
