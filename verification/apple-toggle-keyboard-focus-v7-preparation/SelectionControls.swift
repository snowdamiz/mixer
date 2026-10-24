import Foundation

@MainActor final class RecordingQuery: PublicSwitchQuery {
    typealias Element = Int
    var parents = 1, children = 1, nested = 0, descendants = 0
    var calls: [String] = []
    var states: [[String: Any]]
    var screen = ["x": 0.0, "y": 0.0, "width": 402.0, "height": 874.0]
    init() {
        let parent: [String: Any] = ["bundle": "com.apple.Preferences", "foreground": true, "appState": 4, "observedUptime": 10.0, "identifier": "FKAEnabledSwitch", "label": "Full Keyboard Access", "elementType": 40, "exists": true, "hittable": true, "enabled": true, "valueKind": "string", "value": "0", "frame": ["x": 36.0, "y": 146.3333282470703, "width": 330.0, "height": 28.0]]
        var leaf = parent; leaf["identifier"] = ""; leaf["label"] = ""; leaf["observedUptime"] = 10.001
        leaf["frame"] = ["x": 305.0, "y": 146.3333282470703, "width": 63.0, "height": 28.0]
        states = [parent, leaf]
    }
    func parentCount() -> Int { calls.append("parentCount"); return parents }
    func parent(at index: Int) -> Int { calls.append("parent(\(index))"); return 0 }
    func childSwitchCount(_ parent: Int) -> Int { calls.append("children(\(parent))"); return parent == 0 ? children : nested }
    func childSwitch(_ parent: Int, at index: Int) -> Int { calls.append("child(\(parent),\(index))"); return 1 }
    func descendantSwitchCount(_ leaf: Int) -> Int { calls.append("descendants(\(leaf))"); return descendants }
    func snapshot(_ element: Int) -> [String: Any] { calls.append("snapshot(\(element))"); return states[element] }
    func screenFrame() -> [String: Double] { calls.append("screen"); return screen }
    func changeFrame(_ index: Int, _ key: String, _ value: Any) {
        var f = states[index]["frame"] as! [String: Any]; f[key] = value; states[index]["frame"] = f
    }
}

@main struct SelectionControls {
    @MainActor static func main() throws {
        var ids: [String] = []
        func check(_ name: String, _ body: () throws -> Void) rethrows { try body(); ids.append(name) }
        func expectReject(_ name: String, _ modify: (RecordingQuery) -> Void) throws {
            try check(name) {
                let q = RecordingQuery(); modify(q)
                do { _ = try PublicSwitchSelection.resolve(q); fatalError("accepted \(name)") }
                catch is PublicSwitchSelection.Failure {}
            }
        }
        try check("actual-resolver-unique-public-query-and-two-point-edge-extension") {
            let q = RecordingQuery(); let r = try PublicSwitchSelection.resolve(q)
            precondition(r.parent == 0 && r.leaf == 1)
            precondition(q.calls == ["parentCount", "parent(0)", "children(0)", "child(0,0)", "children(1)", "descendants(1)", "snapshot(0)", "snapshot(1)", "screen"])
            let point = r.witness["hitPoint"] as! [String: Double]; precondition(point == ["x": 336.5, "y": 160.3333282470703])
            let encoded = try JSONSerialization.data(withJSONObject: ["snapshot": r.parentState, "switchWitness": r.witness], options: [.sortedKeys])
            try encoded.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
        }
        for count in [0, 2, -1] {
            try check("parent-count-\(count)-does-not-resolve-any-element") {
                let q = RecordingQuery(); q.parents = count
                do { _ = try PublicSwitchSelection.resolve(q); fatalError("ambiguous parent") } catch is PublicSwitchSelection.Failure {}
                precondition(q.calls == ["parentCount"])
            }
            try check("child-count-\(count)-does-not-resolve-leaf") {
                let q = RecordingQuery(); q.children = count
                do { _ = try PublicSwitchSelection.resolve(q); fatalError("ambiguous child") } catch is PublicSwitchSelection.Failure {}
                precondition(q.calls == ["parentCount", "parent(0)", "children(0)"])
            }
        }
        try expectReject("nested-immediate-switch") { $0.nested = 1 }
        try expectReject("nested-deeper-switch") { $0.descendants = 1 }
        let changes: [(String, Any)] = [("bundle", "other"), ("appState", 3), ("appState", true), ("elementType", 48), ("foreground", false), ("exists", false), ("hittable", false), ("enabled", false), ("enabled", 1), ("valueKind", "unsupported"), ("value", "2"), ("value", 0), ("observedUptime", -1.0), ("observedUptime", Double.nan)]
        for index in [0, 1] {
            for (key, value) in changes { try expectReject("snapshot-\(index)-\(key)-\(value)") { $0.states[index][key] = value } }
            try expectReject("snapshot-\(index)-identifier") { $0.states[index]["identifier"] = "wrong" }
            try expectReject("snapshot-\(index)-label") { $0.states[index]["label"] = "wrong" }
            try expectReject("snapshot-\(index)-missing-field") { $0.states[index].removeValue(forKey: "enabled") }
            try expectReject("frame-\(index)-zero-width") { $0.changeFrame(index, "width", 0.0) }
            try expectReject("frame-\(index)-negative-height") { $0.changeFrame(index, "height", -1.0) }
            try expectReject("frame-\(index)-boolean") { $0.changeFrame(index, "x", true) }
            try expectReject("frame-\(index)-nan") { $0.changeFrame(index, "x", Double.nan) }
        }
        try expectReject("value-disagreement") { $0.states[1]["value"] = "1" }
        try expectReject("leaf-time-before-parent") { $0.states[1]["observedUptime"] = 9.999 }
        try expectReject("leaf-disjoint") { $0.changeFrame(1, "x", 500.0) }
        try expectReject("parent-center-on-edge-no-tolerance") { $0.changeFrame(0, "width", 300.5) }
        try expectReject("screen-center-on-right-edge") { $0.screen["width"] = 336.5 }
        try expectReject("screen-center-on-left-edge") { $0.screen["x"] = 336.5 }
        try expectReject("screen-center-on-top-edge") { $0.screen["y"] = 160.3333282470703 }
        try expectReject("screen-center-on-bottom-edge") { $0.screen["height"] = 160.3333282470703 }
        try expectReject("screen-center-just-outside") { $0.screen["width"] = 336.5.nextDown }
        try check("screen-center-just-inside") { let q = RecordingQuery(); q.screen["width"] = 336.5.nextUp; _ = try PublicSwitchSelection.resolve(q) }
        for value in ["0", "1"] {
            try check("action-binding-fresh-and-state-\(value)") {
                let old = RecordingQuery(); old.states[0]["value"] = value; old.states[1]["value"] = value
                let before = try PublicSwitchSelection.resolve(old)
                let fresh = RecordingQuery(); fresh.states = old.states; fresh.states[0]["observedUptime"] = 11.0; fresh.states[1]["observedUptime"] = 11.001
                let action = try PublicSwitchSelection.resolve(fresh)
                try PublicSwitchSelection.validateAction(action, beforeParent: before.parentState, beforeWitness: before.witness, beforeFinished: 10.5, started: 11.01)
            }
        }
        for mode in ["stale-parent", "leaf-after-start", "state-changed", "parent-frame-changed", "leaf-frame-changed", "screen-changed"] {
            try check("action-binding-rejects-\(mode)") {
                let before = try PublicSwitchSelection.resolve(RecordingQuery()); let fresh = RecordingQuery()
                fresh.states[0]["observedUptime"] = 11.0; fresh.states[1]["observedUptime"] = 11.001
                if mode == "stale-parent" { fresh.states[0]["observedUptime"] = 10.499 }
                if mode == "leaf-after-start" { fresh.states[1]["observedUptime"] = 11.011 }
                if mode == "state-changed" { fresh.states[0]["value"] = "1"; fresh.states[1]["value"] = "1" }
                if mode == "parent-frame-changed" { fresh.changeFrame(0, "width", 331.0) }
                if mode == "leaf-frame-changed" { fresh.changeFrame(1, "width", 64.0) }
                if mode == "screen-changed" { fresh.screen["height"] = 875.0 }
                let action = try PublicSwitchSelection.resolve(fresh)
                do { try PublicSwitchSelection.validateAction(action, beforeParent: before.parentState, beforeWitness: before.witness, beforeFinished: 10.5, started: 11.01); fatalError("accepted changed action") }
                catch is PublicSwitchSelection.Failure {}
            }
        }
        for time in [10.5, 10.5.nextUp] {
            try check("action-snapshot-equal-or-after-before-finish-\(time)") {
                let before = try PublicSwitchSelection.resolve(RecordingQuery()); let fresh = RecordingQuery()
                fresh.states[0]["observedUptime"] = time; fresh.states[1]["observedUptime"] = time
                let action = try PublicSwitchSelection.resolve(fresh)
                try PublicSwitchSelection.validateAction(action, beforeParent: before.parentState, beforeWitness: before.witness, beforeFinished: 10.5, started: time)
            }
        }
        let result: [String: Any] = ["actualSwiftResolverControls": ids.count, "controlIDs": ids, "nativeExecution": false, "scope": "macOS host compiled exact native resolver with recording public-query provider; no XCUI runtime"]
        print(String(data: try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]), encoding: .utf8)!)
    }
}
