import Foundation
import CoreFoundation

/// Query operations are implemented by public XCUI APIs in the native adapter.
/// Host controls execute this exact resolver with a recording query provider.
@MainActor protocol PublicSwitchQuery {
    associatedtype Element
    func parentCount() -> Int
    func parent(at index: Int) -> Element
    func childSwitchCount(_ parent: Element) -> Int
    func childSwitch(_ parent: Element, at index: Int) -> Element
    func descendantSwitchCount(_ leaf: Element) -> Int
    func snapshot(_ element: Element) -> [String: Any]
    func screenFrame() -> [String: Double]
}

@MainActor enum PublicSwitchSelection {
    enum Failure: Error { case invalid(String) }
    struct Resolved<Element> {
        let parent: Element
        let leaf: Element
        let parentState: [String: Any]
        let witness: [String: Any]
    }
    private static func require(_ okay: Bool, _ message: String) throws {
        if !okay { throw Failure.invalid(message) }
    }
    private static func number(_ value: Any?) -> Double? {
        guard let n = value as? NSNumber, CFGetTypeID(n) != CFBooleanGetTypeID(), n.doubleValue.isFinite else { return nil }
        return n.doubleValue
    }
    private static func frame(_ value: Any?) throws -> [String: Double] {
        guard let d = value as? [String: Any], Set(d.keys) == Set(["x", "y", "width", "height"]) else { throw Failure.invalid("frame shape") }
        var out: [String: Double] = [:]
        for (key, raw) in d {
            guard let v = number(raw), abs(v) <= 10000 else { throw Failure.invalid("frame number") }
            out[key] = v
        }
        try require(out["width"]! > 0 && out["height"]! > 0, "positive frame")
        return out
    }
    private static func inside(_ point: [String: Double], _ f: [String: Double]) -> Bool {
        f["x"]! < point["x"]! && point["x"]! < f["x"]! + f["width"]! && f["y"]! < point["y"]! && point["y"]! < f["y"]! + f["height"]!
    }
    private static func valid(_ state: [String: Any], parent: Bool) throws {
        try require(Set(state.keys) == Set(["bundle", "foreground", "appState", "observedUptime", "identifier", "label", "elementType", "exists", "hittable", "enabled", "valueKind", "value", "frame"]), "snapshot fields")
        try require(state["bundle"] as? String == "com.apple.Preferences" && number(state["appState"]) == 4 && number(state["elementType"]) == 40, "Settings state/type")
        try require(["foreground", "exists", "hittable", "enabled"].allSatisfy { key in
            guard let raw = state[key] as? NSNumber else { return false }
            return CFGetTypeID(raw) == CFBooleanGetTypeID() && raw.boolValue
        }, "Settings flags")
        try require(state["identifier"] as? String == (parent ? "FKAEnabledSwitch" : "") && state["label"] as? String == (parent ? "Full Keyboard Access" : ""), "public switch identity")
        try require(state["valueKind"] as? String == "string" && ["0", "1"].contains(state["value"] as? String ?? ""), "raw switch value")
        guard let time = number(state["observedUptime"]), time >= 0 else { throw Failure.invalid("snapshot time") }
        _ = try frame(state["frame"])
    }
    static func validateAction<Element>(_ resolved: Resolved<Element>, beforeParent: [String: Any], beforeWitness: [String: Any], beforeFinished: Double, started: Double) throws {
        func comparable(_ snapshot: [String: Any]) -> NSDictionary {
            var copy = snapshot; copy.removeValue(forKey: "observedUptime"); return copy as NSDictionary
        }
        guard let priorLeaf = beforeWitness["leaf"] as? [String: Any], let leaf = resolved.witness["leaf"] as? [String: Any] else { throw Failure.invalid("binding leaf") }
        var currentBinding = resolved.witness; currentBinding.removeValue(forKey: "leaf")
        var priorBinding = beforeWitness; priorBinding.removeValue(forKey: "leaf")
        try require(comparable(resolved.parentState) == comparable(beforeParent) && comparable(leaf) == comparable(priorLeaf) && currentBinding as NSDictionary == priorBinding as NSDictionary, "action public binding changed")
        guard let p = number(resolved.parentState["observedUptime"]), let l = number(leaf["observedUptime"]) else { throw Failure.invalid("binding time") }
        try require(beforeFinished <= p && p <= l && l <= started, "action snapshots stale")
    }
    static func resolve<Q: PublicSwitchQuery>(_ query: Q) throws -> Resolved<Q.Element> {
        let parents = query.parentCount()
        try require(parents == 1, "unique exact parent")
        let parent = query.parent(at: 0)
        let children = query.childSwitchCount(parent)
        try require(children == 1, "unique immediate child switch")
        let leaf = query.childSwitch(parent, at: 0)
        let nested = query.childSwitchCount(leaf)
        let descendants = query.descendantSwitchCount(leaf)
        try require(nested == 0 && descendants == 0, "switch leaf has no switch descendants")
        let p = query.snapshot(parent)
        let l = query.snapshot(leaf)
        try valid(p, parent: true); try valid(l, parent: false)
        try require(p["value"] as? String == l["value"] as? String, "parent leaf value agreement")
        try require(number(p["observedUptime"])! <= number(l["observedUptime"])!, "public snapshot ordering")
        let pf = try frame(p["frame"]), lf = try frame(l["frame"]), screen = try frame(query.screenFrame())
        let point = ["x": lf["x"]! + lf["width"]! / 2, "y": lf["y"]! + lf["height"]! / 2]
        try require(max(pf["x"]!, lf["x"]!) < min(pf["x"]! + pf["width"]!, lf["x"]! + lf["width"]!) && max(pf["y"]!, lf["y"]!) < min(pf["y"]! + pf["height"]!, lf["y"]! + lf["height"]!), "parent leaf overlap")
        try require([pf, lf, screen].allSatisfy { inside(point, $0) }, "strict interior leaf center")
        return Resolved(parent: parent, leaf: leaf, parentState: p, witness: ["relation": "immediate-child-switch", "parentCount": parents, "leafCount": children, "leafSwitchChildCount": nested, "leafSwitchDescendantCount": descendants, "leaf": l, "screen": screen, "hitPoint": point])
    }
}
