import Foundation
import SwiftUI
import UIKit

// Verification-only public API observations. No private classes or selectors.
@MainActor
enum ShapeProbe {
    static func layer(_ value: CALayer) -> [String: Any] {
        ["boundsPoints": MixerAppearanceMeasurement.rect(value.bounds),
         "cornerRadius": value.cornerRadius, "cornerCurve": value.cornerCurve.rawValue,
         "maskedCornersRaw": value.maskedCorners.rawValue, "masksToBounds": value.masksToBounds,
         "borderWidth": value.borderWidth, "shadowOpacity": value.shadowOpacity,
         "shadowRadius": value.shadowRadius]
    }
    static func view(_ value: UIView?, window: UIWindow) -> Any {
        guard let value else { return NSNull() }
        return ["frameInWindowPoints": MixerAppearanceMeasurement.rect(value.convert(value.bounds, to: window)),
                "layer": layer(value.layer), "hidden": value.isHidden, "alpha": value.alpha,
                "backgroundColor": MixerAppearanceMeasurement.color(value.backgroundColor, traits: value.traitCollection)]
    }
    static func collection(_ value: UICollectionView, window: UIWindow) -> [String: Any] {
        var data: [[String: Any]] = []
        for cell in value.visibleCells {
            let index = value.indexPath(for: cell)
            var record: [String: Any] = ["section": index?.section ?? -1, "item": index?.item ?? -1,
                "frameInWindowPoints": MixerAppearanceMeasurement.rect(cell.convert(cell.bounds, to: window)),
                "cellLayer": layer(cell.layer), "contentViewLayer": layer(cell.contentView.layer),
                "backgroundView": view(cell.backgroundView, window: window),
                "selectedBackgroundView": view(cell.selectedBackgroundView, window: window),
                "layoutMargins": ["top": cell.layoutMargins.top, "left": cell.layoutMargins.left,
                    "bottom": cell.layoutMargins.bottom, "right": cell.layoutMargins.right]]
            if let bg = cell.backgroundConfiguration {
                record["backgroundConfiguration"] = ["cornerRadius": bg.cornerRadius,
                    "backgroundInsets": ["top": bg.backgroundInsets.top, "leading": bg.backgroundInsets.leading,
                        "bottom": bg.backgroundInsets.bottom, "trailing": bg.backgroundInsets.trailing],
                    "strokeWidth": bg.strokeWidth,
                    "backgroundColor": MixerAppearanceMeasurement.color(bg.backgroundColor, traits: cell.traitCollection)]
            } else { record["backgroundConfiguration"] = NSNull() }
            if let list = cell as? UICollectionViewListCell {
                record["publicListCellSeparatorGuideInWindowPoints"] = MixerAppearanceMeasurement.rect(
                    cell.convert(list.separatorLayoutGuide.layoutFrame, to: window))
            }
            data.append(record)
        }
        return ["cells": data.sorted { a,b in
            let sa = a["section"] as! Int, sb = b["section"] as! Int
            return sa == sb ? (a["item"] as! Int) < (b["item"] as! Int) : sa < sb
        }]
    }

    static func path(_ value: CGPath) -> [[String: Any]] {
        var commands: [[String: Any]] = []
        value.applyWithBlock { item in
            let item = item.pointee
            let kind: String
            let count: Int
            switch item.type {
            case .moveToPoint: kind = "move"; count = 1
            case .addLineToPoint: kind = "line"; count = 1
            case .addQuadCurveToPoint: kind = "quad"; count = 2
            case .addCurveToPoint: kind = "cubic"; count = 3
            case .closeSubpath: kind = "close"; count = 0
            @unknown default: fatalError("Unknown public path element")
            }
            commands.append(["op": kind, "points": (0..<count).map { ["x": item.points[$0].x, "y": item.points[$0].y] }])
        }
        return commands
    }

    static func writeCandidates(to folder: URL) throws {
        let definitions: [(String, CGSize, CGFloat)] = [
            ("track-continuous-r14", CGSize(width: 63, height: 28), 14),
            ("thumb-continuous-r12", CGSize(width: 37, height: 24), 12),
            ("group-continuous-r26", CGSize(width: 370, height: 208), 26),
            ("cell52-continuous-r26", CGSize(width: 370, height: 52), 26),
            ("cell63third-continuous-r26", CGSize(width: 370, height: 63 + 2.0/3.0), 26),
            ("cell101-continuous-r26", CGSize(width: 370, height: 101), 26)]
        var records: [[String: Any]] = []
        for (name, size, radius) in definitions {
            let rect = CGRect(origin: .zero, size: size)
            let shape = RoundedRectangle(cornerRadius: radius, style: .continuous).path(in: rect).cgPath
            let format = UIGraphicsImageRendererFormat()
            format.scale = 3; format.opaque = true
            let image = UIGraphicsImageRenderer(size: size, format: format).image { ctx in
                UIColor.black.setFill(); ctx.fill(rect)
                UIColor.white.setFill(); ctx.cgContext.addPath(shape); ctx.cgContext.fillPath()
            }
            try image.pngData()!.write(to: folder.appendingPathComponent(name + ".png"), options: .atomic)
            records.append(["name": name, "source": "public SwiftUI RoundedRectangle.path(in:).cgPath; authored hypothesis, not native path",
                "width": size.width, "height": size.height, "requestedCornerRadius": radius,
                "pathBounds": MixerAppearanceMeasurement.rect(shape.boundingBoxOfPath), "elements": path(shape)])
        }
        let data: [String: Any] = ["format": "mixer.authored-public-shape-paths.1", "scale": 3,
            "scope": "Authored candidate public paths rendered offscreen; no mutation of the displayed native UI", "shapes": records]
        try JSONSerialization.data(withJSONObject: data, options: [.prettyPrinted, .sortedKeys])
            .write(to: folder.appendingPathComponent("candidate-paths.json"), options: .atomic)
    }
}
