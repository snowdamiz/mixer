import Foundation
import SwiftUI
import UIKit
import CoreText

// Verification-only probe. No platform-private names, selectors, KVC or reflection.
@MainActor
struct MeasurementProbe: View {
    let nodeID: String
    let kind: String
    let explicitFont: Font?
    @Environment(\.font) private var environmentFont
    @Environment(\.fontResolutionContext) private var fontContext
    @Environment(\.defaultMinListRowHeight) private var rowMinimum
    @Environment(\.defaultMinListHeaderHeight) private var headerMinimum
    @Environment(\.isEnabled) private var enabled

    var body: some View {
        GeometryReader { geometry in
            let frame = geometry.frame(in: .global)
            Color.clear
                .onAppear { record(frame) }
                .onChange(of: frame) { _, new in record(new) }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }

    private func record(_ frame: CGRect) {
        var data: [String: Any] = ["id": nodeID, "kind": kind,
            "frameGlobalPoints": MixerAppearanceMeasurement.rect(frame),
            "isEnabled": enabled, "defaultMinListRowHeight": rowMinimum,
            "fontSource": explicitFont != nil ? "explicit-renderer-semantic-font" :
                (environmentFont != nil ? "public-environment-font; contextual-label-may-override" : "unresolved-environment-font-nil")]
        if let headerMinimum { data["defaultMinListHeaderHeight"] = headerMinimum }
        if #available(iOS 26.0, *), let observed = explicitFont ?? environmentFont {
            let resolved = observed.resolve(in: fontContext)
            data["font"] = MixerAppearanceMeasurement.ctFont(resolved.ctFont)
                .merging(["pointSize": resolved.pointSize, "isBold": resolved.isBold,
                    "isItalic": resolved.isItalic, "isMonospaced": resolved.isMonospaced], uniquingKeysWith: { _, new in new })
        }
        MixerAppearanceMeasurement.nodes[nodeID] = data
    }
}

@MainActor
public enum MixerAppearanceMeasurement {
    static var nodes: [String: [String: Any]] = [:]
    static func rect(_ r: CGRect) -> [String: CGFloat] {
        ["x": r.origin.x, "y": r.origin.y, "width": r.width, "height": r.height]
    }
    static func ctFont(_ f: CTFont) -> [String: Any] {
        let traits = CTFontCopyTraits(f) as NSDictionary
        return ["postScriptName": CTFontCopyPostScriptName(f) as String,
            "familyName": CTFontCopyFamilyName(f) as String, "size": CTFontGetSize(f),
            "ascent": CTFontGetAscent(f), "descent": CTFontGetDescent(f), "leading": CTFontGetLeading(f),
            "capHeight": CTFontGetCapHeight(f), "xHeight": CTFontGetXHeight(f),
            "traitWeight": traits[kCTFontWeightTrait] ?? NSNull(),
            "traitWidth": traits[kCTFontWidthTrait] ?? NSNull()]
    }
    static func uiFont(_ f: UIFont) -> [String: Any] {
        ["fontName": f.fontName, "familyName": f.familyName, "pointSize": f.pointSize,
            "lineHeight": f.lineHeight, "ascender": f.ascender, "descender": f.descender,
            "leading": f.leading, "capHeight": f.capHeight, "xHeight": f.xHeight,
            "symbolicTraits": f.fontDescriptor.symbolicTraits.rawValue,
            "traits": (f.fontDescriptor.object(forKey: .traits) as? [UIFontDescriptor.TraitKey: Any])?.reduce(into: [String: Any]()) { $0[$1.key.rawValue] = $1.value } ?? [:]]
    }
    static func color(_ color: UIColor?, traits: UITraitCollection) -> Any {
        guard let color else { return NSNull() }
        let resolved = color.resolvedColor(with: traits)
        var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
        guard resolved.getRed(&r, green: &g, blue: &b, alpha: &a) else {
            return ["resolvedAsRGB": false]
        }
        return ["red": r, "green": g, "blue": b, "alpha": a,
            "rgba8": [r,g,b,a].map { Int(($0 * 255).rounded()) }]
    }
    static func native(_ view: UIView, window: UIWindow, path: String, records: inout [[String: Any]]) {
        let traits = view.traitCollection
        var data: [String: Any] = ["publicSubviewPath": path,
            "frameInWindowPoints": rect(view.convert(view.bounds, to: window)),
            "hidden": view.isHidden, "alpha": view.alpha,
            "backgroundColor": color(view.backgroundColor, traits: traits),
            "tintColor": color(view.tintColor, traits: traits)]
        if let identifier = view.accessibilityIdentifier { data["accessibilityIdentifier"] = identifier }
        var include = false
        if let label = view as? UILabel {
            include = true; data["publicType"] = "UILabel"
            data["text"] = label.text ?? ""; data["font"] = uiFont(label.font)
            data["textColor"] = color(label.textColor, traits: traits)
            data["numberOfLines"] = label.numberOfLines; data["textAlignment"] = label.textAlignment.rawValue
        } else if let field = view as? UITextField {
            include = true; data["publicType"] = "UITextField"
            data["text"] = field.text ?? ""; data["placeholder"] = field.placeholder ?? ""
            data["font"] = field.font.map(uiFont) ?? [:]
            data["textColor"] = color(field.textColor, traits: traits)
            data["borderStyle"] = field.borderStyle.rawValue
            data["textRectPoints"] = rect(field.textRect(forBounds: field.bounds))
            data["editingRectPoints"] = rect(field.editingRect(forBounds: field.bounds))
        } else if let toggle = view as? UISwitch {
            include = true; data["publicType"] = "UISwitch"
            data["isOn"] = toggle.isOn; data["isEnabled"] = toggle.isEnabled
            data["onTintColor"] = color(toggle.onTintColor, traits: traits)
            data["thumbTintColor"] = color(toggle.thumbTintColor, traits: traits)
            data["intrinsicSize"] = ["width": toggle.intrinsicContentSize.width, "height": toggle.intrinsicContentSize.height]
        } else if let bar = view as? UINavigationBar {
            include = true; data["publicType"] = "UINavigationBar"
            data["prefersLargeTitles"] = bar.prefersLargeTitles
            data["topItemTitle"] = bar.topItem?.title ?? ""
            data["largeTitleDisplayMode"] = bar.topItem?.largeTitleDisplayMode.rawValue ?? -1
            data["titleTextAttributesSet"] = bar.titleTextAttributes != nil
            data["largeTitleTextAttributesSet"] = bar.largeTitleTextAttributes != nil
        } else if let collection = view as? UICollectionView {
            include = true; data["publicType"] = "UICollectionView"
            data["contentSize"] = ["width": collection.contentSize.width, "height": collection.contentSize.height]
            data["adjustedContentInset"] = ["top": collection.adjustedContentInset.top, "bottom": collection.adjustedContentInset.bottom,
                "left": collection.adjustedContentInset.left, "right": collection.adjustedContentInset.right]
            data["visibleCellFramesPoints"] = collection.visibleCells.map { rect($0.convert($0.bounds, to: window)) }
        } else if let table = view as? UITableView {
            include = true; data["publicType"] = "UITableView"
            data["rowHeight"] = table.rowHeight; data["sectionHeaderHeight"] = table.sectionHeaderHeight
        }
        if include { records.append(data) }
        for (i, child) in view.subviews.enumerated() { native(child, window: window, path: path + "." + String(i), records: &records) }
    }
    public static func write(window: UIWindow, fixture: String) throws {
        var nativeRecords: [[String: Any]] = []
        native(window, window: window, path: "window", records: &nativeRecords)
        let colors: [(String, UIColor)] = [("label", .label), ("secondaryLabel", .secondaryLabel),
            ("tertiaryLabel", .tertiaryLabel), ("systemBlue", .systemBlue), ("systemRed", .systemRed),
            ("systemGreen", .systemGreen), ("systemBackground", .systemBackground),
            ("secondarySystemBackground", .secondarySystemBackground), ("systemGroupedBackground", .systemGroupedBackground),
            ("secondarySystemGroupedBackground", .secondarySystemGroupedBackground), ("separator", .separator),
            ("opaqueSeparator", .opaqueSeparator), ("systemFill", .systemFill)]
        let fonts: [(String, UIFont.TextStyle)] = [("body", .body), ("headline", .headline), ("title1", .title1),
            ("caption1", .caption1), ("largeTitle", .largeTitle)]
        let result: [String: Any] = ["format": "mixer.apple-appearance-measurement.1", "fixture": fixture,
            "nodeCoordinateSpace": "SwiftUI GeometryProxy.frame(in: .global), points; sectionHeader is explicit header Text",
            "nodes": nodes.values.sorted { ($0["id"] as! String) < ($1["id"] as! String) },
            "publicUIKitObservations": nativeRecords,
            "semanticUIColorReferences": Dictionary(uniqueKeysWithValues: colors.map { ($0.0, color($0.1, traits: window.traitCollection)) }),
            "semanticUIFontReferences": Dictionary(uniqueKeysWithValues: fonts.map {
                ($0.0, uiFont(UIFont.preferredFont(forTextStyle: $0.1, compatibleWith: window.traitCollection))) }),
            "limits": ["background geometry is laid-out view bounds, not glyph ink bounds or hit target",
                "semantic UIColor and preferred UIFont references are public platform values, not assertions that a particular SwiftUI node uses them",
                "environment Font may be nil or contextual control internals may override it; explicit text font resolution is stronger evidence",
                "UIKit classes are cast using public API; no private class-to-node mapping or assumption about SwiftUI backing views",
                "section as structural List content has no measured aggregate frame",
                "no physical device, input, accessibility workflow, signed presentation or parity qualification"]]
        let output = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("measurements.json")
        try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]).write(to: output, options: .atomic)
    }
}
