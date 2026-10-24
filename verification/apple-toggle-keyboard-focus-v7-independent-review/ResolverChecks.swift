import Foundation

@MainActor final class IndependentQuery: PublicSwitchQuery {
    typealias Element = String
    var parentTotal=1, childTotal=1, nestedTotal=0, descendantTotal=0
    var calls:[String]=[]
    var parent:[String:Any]
    var leaf:[String:Any]
    var screen=["x":0.0,"y":0.0,"width":402.0,"height":874.0]
    init() {
        parent=["bundle":"com.apple.Preferences","foreground":true,"appState":4,"observedUptime":50.0,"identifier":"FKAEnabledSwitch","label":"Full Keyboard Access","elementType":40,"exists":true,"hittable":true,"enabled":true,"valueKind":"string","value":"0","frame":["x":36.0,"y":146.3333282470703,"width":330.0,"height":28.0]]
        leaf=parent;leaf["identifier"]="";leaf["label"]="";leaf["observedUptime"]=50.001
        leaf["frame"]=["x":305.0,"y":146.3333282470703,"width":63.0,"height":28.0]
    }
    func parentCount()->Int {calls.append("parent-count");return parentTotal}
    func parent(at index:Int)->String {calls.append("parent-handle-\(index)");return "selected-parent"}
    func childSwitchCount(_ parent:String)->Int {calls.append("child-count-"+parent);return parent=="selected-parent" ? childTotal:nestedTotal}
    func childSwitch(_ parent:String,at index:Int)->String {calls.append("child-handle-\(parent)-\(index)");return "selected-leaf"}
    func descendantSwitchCount(_ leaf:String)->Int {calls.append("descendants-"+leaf);return descendantTotal}
    func snapshot(_ element:String)->[String:Any] {calls.append("snapshot-"+element);return element=="selected-parent" ? parent:leaf}
    func screenFrame()->[String:Double] {calls.append("screen");return screen}
    func leafFrame(_ key:String,_ value:Any) {var f=leaf["frame"] as! [String:Any];f[key]=value;leaf["frame"]=f}
    func parentFrame(_ key:String,_ value:Any) {var f=parent["frame"] as! [String:Any];f[key]=value;parent["frame"]=f}
}

@main struct IndependentResolverChecks {
    @MainActor static func main() throws {
        var controls:[String]=[]
        func rejects(_ name:String,_ change:(IndependentQuery)->Void) throws {
            let q=IndependentQuery();change(q)
            do {_ = try PublicSwitchSelection.resolve(q);fatalError("accepted "+name)}
            catch is PublicSwitchSelection.Failure {}
            controls.append(name)
        }
        let q=IndependentQuery();let result=try PublicSwitchSelection.resolve(q)
        precondition(result.parent=="selected-parent" && result.leaf=="selected-leaf")
        precondition(q.calls==["parent-count","parent-handle-0","child-count-selected-parent","child-handle-selected-parent-0","child-count-selected-leaf","descendants-selected-leaf","snapshot-selected-parent","snapshot-selected-leaf","screen"])
        precondition((result.witness["hitPoint"] as! [String:Double]) == ["x":336.5,"y":160.3333282470703])
        let data=try JSONSerialization.data(withJSONObject:["snapshot":result.parentState,"switchWitness":result.witness],options:[.sortedKeys])
        try data.write(to:URL(fileURLWithPath:CommandLine.arguments[1]))
        controls.append("actual-query-order-and-selected-opaque-handles-two-point-extension")
        for total in [-1,0,2,Int.max] {
            let p=IndependentQuery();p.parentTotal=total
            do {_ = try PublicSwitchSelection.resolve(p);fatalError("accepted parent count")}
            catch is PublicSwitchSelection.Failure {}
            precondition(p.calls==["parent-count"]);controls.append("parent-count-short-circuit-\(total)")
            try rejects("child-count-\(total)") {$0.childTotal=total}
        }
        try rejects("nested-immediate-switch") {$0.nestedTotal=1}
        try rejects("nested-descendant-switch") {$0.descendantTotal=1}
        let changes:[(String,Any)]=[("bundle","wrong"),("foreground",false),("appState",true),("appState",3),("elementType",true),("elementType",75),("exists",false),("hittable",false),("enabled",1),("valueKind","unsupported"),("value",1),("value","2"),("observedUptime",Double.infinity),("observedUptime",-1.0)]
        for (key,value) in changes {
            try rejects("parent-\(key)-\(value)") {$0.parent[key]=value}
            try rejects("leaf-\(key)-\(value)") {$0.leaf[key]=value}
        }
        try rejects("wrong-parent-identifier") {$0.parent["identifier"]="Full Keyboard Access"}
        try rejects("wrong-parent-label") {$0.parent["label"]="Full Keyboard Access, Off"}
        try rejects("identified-leaf") {$0.leaf["identifier"]="FKAEnabledSwitch"}
        try rejects("labeled-leaf") {$0.leaf["label"]="Full Keyboard Access"}
        try rejects("disagreed-value") {$0.leaf["value"]="1"}
        try rejects("leaf-before-parent") {$0.leaf["observedUptime"]=50.0.nextDown}
        try rejects("leaf-disjoint") {$0.leafFrame("x",500.0)}
        try rejects("leaf-zero") {$0.leafFrame("width",0.0)}
        try rejects("parent-center-edge") {$0.parentFrame("width",300.5)}
        try rejects("screen-right-edge") {$0.screen["width"]=336.5}
        try rejects("screen-right-just-outside") {$0.screen["width"]=336.5.nextDown}
        try rejects("screen-left-edge") {$0.screen["x"]=336.5}
        try rejects("screen-top-edge") {$0.screen["y"]=160.3333282470703}
        try rejects("screen-bottom-edge") {$0.screen["height"]=160.3333282470703}
        let barelyInside=IndependentQuery();barelyInside.screen["width"]=336.5.nextUp;_ = try PublicSwitchSelection.resolve(barelyInside);controls.append("screen-right-one-ulp-inside")
        for mode in ["fresh","equal","stale-parent","late-leaf","screen-change","frame-change","value-change"] {
            let before=try PublicSwitchSelection.resolve(IndependentQuery());let fresh=IndependentQuery()
            fresh.parent["observedUptime"]=51.0;fresh.leaf["observedUptime"]=51.001
            if mode=="equal" {fresh.parent["observedUptime"]=50.5;fresh.leaf["observedUptime"]=50.5}
            if mode=="stale-parent" {fresh.parent["observedUptime"]=50.5.nextDown}
            if mode=="late-leaf" {fresh.leaf["observedUptime"]=51.01.nextUp}
            if mode=="screen-change" {fresh.screen["height"]=875}
            if mode=="frame-change" {fresh.parentFrame("width",331.0)}
            if mode=="value-change" {fresh.parent["value"]="1";fresh.leaf["value"]="1"}
            let action=try PublicSwitchSelection.resolve(fresh)
            if mode=="fresh" || mode=="equal" {try PublicSwitchSelection.validateAction(action,beforeParent:before.parentState,beforeWitness:before.witness,beforeFinished:50.5,started:51.01)}
            else {
                do {try PublicSwitchSelection.validateAction(action,beforeParent:before.parentState,beforeWitness:before.witness,beforeFinished:50.5,started:51.01);fatalError("accepted changed action")}
                catch is PublicSwitchSelection.Failure {}
            }
            controls.append("actual-action-binding-"+mode)
        }
        print(String(data:try JSONSerialization.data(withJSONObject:["independentActualResolverControls":controls.count,"controls":controls,"syntheticHostOnly":true,"nativeExecuted":false],options:[.sortedKeys]),encoding:.utf8)!)
    }
}
