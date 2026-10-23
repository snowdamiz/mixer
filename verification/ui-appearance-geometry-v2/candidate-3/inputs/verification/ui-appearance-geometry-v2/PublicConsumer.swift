import Foundation
import MixerUI

typealias G = UIAppearanceGeometryV2
func output(_ object: [String: Any]) throws {
    let data = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
    print(String(decoding: data, as: UTF8.self))
}
func command(_ value: G.Command) -> [String: Any] {
    func p(_ point: G.Point) -> [UInt32] { [point.x64, point.y64] }
    switch value {
    case let .move(point): return ["op":"move", "points64":[p(point)]]
    case let .line(point): return ["op":"line", "points64":[p(point)]]
    case let .cubic(a,b,c): return ["op":"cubic", "points64":[p(a),p(b),p(c)]]
    case .close: return ["op":"close", "points64":[]]
    }
}
let extents: [UInt32] = [0,1,2,3,5,63,64,127,128,1792,3328,23680,65536,2147483647]
for w in extents {
    for h in extents {
        for radius: UInt32 in [0,1,16,1664,65536] {
            let path = try G.group(width64:w,height64:h,radius64:radius)
            try output(["kind":"group","w":w,"h":h,"r":radius,"commands":path.commands.map(command)])
        }
    }
}
for path in [G.track(),G.thumb()] {
    try output(["kind":"fixed","name":path.shape.rawValue,"w":path.width64,"h":path.height64,"commands":path.commands.map(command)])
}
for checked in [false,true] {
    for direction: UILayoutDirectionV1 in [.leftToRight,.rightToLeft] {
        let p=G.thumbOrigin(checked:checked,direction:direction)
        try output(["kind":"thumbOrigin","checked":checked,"rtl":direction == .rightToLeft,"x":p.x64,"y":p.y64])
    }
}
for density: UInt16 in [128,512,1024,1536,3072,16384] {
    for coordinate: UInt32 in [0,1,31,32,33,63,64,65,125,1664,65536,2147483647] {
        try output(["kind":"pixel","c":coordinate,"d":density,"edge":try G.pixelEdge(coordinate,density1024:density),"continuous":try G.pixelCoordinate(coordinate,density1024:density)])
    }
}
