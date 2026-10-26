#if canImport(CoreGraphics)
import CoreGraphics
import MixerUI

/// Private shared math for detached proof and the exact frames later attached.
/// It confers no native rendering/input qualification.
enum AppearanceNativeGeometryV2 {
    struct Placement { let key: String; let parent: String; var frame: CGRect; let index: Int }

    static func snapped(_ rect: CGRect, parentOrigin: CGPoint, density1024: UInt16) throws -> CGRect {
        func edge(_ value: CGFloat) throws -> CGFloat {
            let logical = try UIAppearanceGeometryV2.measuredExtent64(Double(value))
            return CGFloat(try UIAppearanceGeometryV2.pixelEdge(logical,density1024:density1024))*1024/CGFloat(density1024)
        }
        let x = try edge(rect.minX+parentOrigin.x), y = try edge(rect.minY+parentOrigin.y)
        let right = try edge(rect.maxX+parentOrigin.x), bottom = try edge(rect.maxY+parentOrigin.y)
        return CGRect(x:x-(try edge(parentOrigin.x)),y:y-(try edge(parentOrigin.y)),width:right-x,height:bottom-y)
    }

    static func prepare(_ placements: [Placement], density1024: UInt16) throws -> [Placement] {
        guard placements.count <= 16_384 else { throw UIAppearanceErrorV2.layout }
        var byKey: [String:Placement] = [:]
        for placement in placements {
            guard byKey.updateValue(placement,forKey:placement.key) == nil, placement.key != "$root" else { throw UIAppearanceErrorV2.shape }
        }
        var origins: [String:CGPoint] = ["$root":.zero]
        func origin(_ key: String) throws -> CGPoint {
            var path: [(String,CGPoint)] = [], visiting = Set<String>(), current = key
            while origins[current] == nil {
                guard visiting.insert(current).inserted, path.count <= placements.count else { throw UIAppearanceErrorV2.shape }
                if current.hasPrefix("$scroll:") {
                    path.append((current,.zero)); current = String(current.dropFirst(8))
                } else {
                    guard let placement = byKey[current] else { throw UIAppearanceErrorV2.shape }
                    path.append((current,placement.frame.origin)); current = placement.parent
                }
            }
            var value = origins[current]!
            for (key,offset) in path.reversed() {
                value = CGPoint(x:value.x+offset.x,y:value.y+offset.y); origins[key] = value
            }
            return origins[key]!
        }
        return try placements.map { placement in
            Placement(key:placement.key,parent:placement.parent,frame:try snapped(placement.frame,parentOrigin:origin(placement.parent),density1024:density1024),index:placement.index)
        }
    }

    /// Inputs are already in the final group-local coordinate system. Native
    /// local input/paint frames remain unsnapped, exactly as they will attach.
    static func validateCarrier(_ carrier: CGRect, rowBounds: CGRect) throws {
        guard [carrier.minX,carrier.minY,carrier.maxX,carrier.maxY,rowBounds.minX,rowBounds.minY,rowBounds.maxX,rowBounds.maxY].allSatisfy(\.isFinite), !carrier.isEmpty, rowBounds.contains(carrier) else { throw UIAppearanceErrorV2.layout }
    }

    static func validateCover(_ cover: CGRect, foreground: [CGRect], groupBounds: CGRect, groupPath: CGPath, density1024: UInt16) throws {
        func finite(_ rect: CGRect) -> Bool { [rect.minX,rect.minY,rect.maxX,rect.maxY].allSatisfy(\.isFinite) && !rect.isNull && !rect.isInfinite }
        guard finite(cover), !cover.isEmpty, finite(groupBounds), groupBounds.contains(cover), foreground.allSatisfy(finite) else { throw UIAppearanceErrorV2.unsupportedNativeOperation }
        let scale = CGFloat(density1024)/1024
        for corner in [CGPoint(x:cover.minX,y:cover.minY),CGPoint(x:cover.maxX,y:cover.minY),CGPoint(x:cover.minX,y:cover.maxY),CGPoint(x:cover.maxX,y:cover.maxY)] {
            guard groupPath.contains(CGPoint(x:corner.x*scale,y:corner.y*scale),using:.winding) else { throw UIAppearanceErrorV2.unsupportedNativeOperation }
        }
        guard foreground.allSatisfy({ cover.intersection($0).isEmpty }) else { throw UIAppearanceErrorV2.unsupportedNativeOperation }
    }
}
#endif
