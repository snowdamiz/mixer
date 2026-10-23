import Foundation
import SwiftUI
import UIKit
import CoreText

@MainActor
public enum FontProfileEvidence {
    static var lineBoxes: [String: [String: CGFloat]] = [:]
    static let candidateEnabled = ProcessInfo.processInfo.arguments.contains("--candidate-fonts")
    public static func write(context: Font.Context, fixture: String, dynamicType: String) throws {
        guard #available(iOS 26.0, *),
            let scene = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene }).first,
            let window = scene.windows.first(where: \.isKeyWindow) else { throw NSError(domain: "FontProfile", code: 1) }
        let roles: [(String, Font)] = [("body",.body),("headline",.headline),("title",.title),("caption",.caption),
            ("sectionHeaderCandidate",.headline),("controlLabelCandidate",.body),("expandedNavigationCandidate",.largeTitle.bold())]
        var fonts: [String: Any] = [:]
        for (role,font) in roles {
            let resolved = font.resolve(in: context)
            let ct = resolved.ctFont
            var data = MixerAppearanceMeasurement.ctFont(ct)
            data["pointSize"] = resolved.pointSize;data["isBold"] = resolved.isBold
            data["isItalic"] = resolved.isItalic;data["isMonospaced"] = resolved.isMonospaced
            data["metricAscentPlusDescentPoints"] = CTFontGetAscent(ct) + CTFontGetDescent(ct)
            data["metricBaselineAdvanceIncludingLeadingPoints"] = CTFontGetAscent(ct) + CTFontGetDescent(ct) + CTFontGetLeading(ct)
            data["metricAscentPlusDescentCeilAtDisplayScalePoints"] = ceil((CTFontGetAscent(ct) + CTFontGetDescent(ct)) * window.screen.scale) / window.screen.scale
            fonts[role] = data
        }
        var native: [[String: Any]] = []
        MixerAppearanceMeasurement.native(window, window: window, path: "window", records: &native)
        let title = native.first { $0["publicType"] as? String == "UINavigationBar" }?["topItemTitle"] as? String
        let labels = native.filter { $0["publicType"] as? String == "UILabel" && $0["text"] as? String == title }
        let largest = labels.max { a,b in
            let af = a["font"] as? [String: Any], bf = b["font"] as? [String: Any]
            return (af?["pointSize"] as? CGFloat ?? 0) < (bf?["pointSize"] as? CGFloat ?? 0)
        }
        guard lineBoxes.count == 8 else { throw NSError(domain: "FontProfileLineBoxes", code: 2) }
        let result: [String: Any] = ["format":"mixer.apple-font-profile-observation.1", "fixture":fixture,
            "candidateFontsApplied":candidateEnabled,"swiftUIDynamicTypeSize":dynamicType,
            "nativePreferredContentSizeCategory":window.traitCollection.preferredContentSizeCategory.rawValue,
            "screenScale":window.screen.scale,"resolvedSemanticFonts":fonts,
            "nativeLineBoxProbes":lineBoxes,
            "nativeLineBoxProbeScope":"Hidden fixed-size Text Ag and Ag\nAg, explicit body/headline/title/caption, current environment. Heights are actual SwiftUI layout; two-minus-one is an observed repeat-line height increment, not a general glyph fallback guarantee.",
            "actualNavigationTitleUILabels":labels,"largestNavigationTitleUILabel":largest ?? [:],
            "bounds":"Public Font metrics and actual UIKit label properties; largest-label selection is recorded explicitly. Not a glyph fallback or collapsed navigation test.",
            "lineBoxLimit":"Ascent+descent, rounded extent and advance including leading are separate font metric references, not universal text-view line boxes."]
        let output = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("font-profile.json")
        try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys,.withoutEscapingSlashes]).write(to:output,options:.atomic)
    }
}
