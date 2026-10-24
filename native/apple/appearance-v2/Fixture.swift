import MixerUI

// Owned all-ten deterministic document shared by the native harness and export.
enum AppearanceFixtureV2 {
    static func document(_ rev: UInt64, suffix: String = "", disabled: Bool = false, checked: Bool = true) -> MixerUI.UIDocument {
        func text(_ id:String,_ value:String,_ extra:[String:UIValue] = [:]) -> UINode {
            UINode(id:id,kind:.text,properties:extra.merging(["text":.string(value)]) { _,new in new })
        }
        let field = UINode(id:"field",kind:.textField,properties:["label":.string("Native editor"),"value":.string("alpha      omega"),"disabled":.bool(disabled)],actions:[.init(id:"edit",event:.textChange),.init(id:"submit",event:.submit)])
        let button = UINode(id:"button",kind:.button,properties:["label":.string("Activate"+suffix),"disabled":.bool(disabled)],actions:[.init(id:"activate",event:.activate)])
        let toggle = UINode(id:"toggle",kind:.toggle,properties:["label":.string("Shared switch"),"value":.bool(checked),"disabled":.bool(disabled)],actions:[.init(id:"toggle",event:.valueChange)])
        let v = UINode(id:"v",kind:.vStack,children:[text("body","Body / 日本語 / العربية / 👩🏽‍💻"),text("caption","Native caption",["style":.string("caption")])])
        let h = UINode(id:"h",kind:.hStack,children:[text("short","Short"),text("long","A substantially longer native shaped label that wraps under bounded proposals")])
        let z = UINode(id:"z",kind:.zStack,children:[text("overlay","Overlay"),text("overlaid","       second")])
        let selectable = text("selectable","Selectable native text",["selectable":.bool(true)])
        let first = UINode(id:"section",kind:.section,properties:["title":.string("Native shared appearance")],children:[field,button,toggle,v,h,z,selectable])
        let rows = (0..<12).map { text("row\($0)","Measured row \($0) — café 中文") }
        let second = UINode(id:"second",kind:.section,properties:["title":.string("Retained scroll")],children:rows)
        return MixerUI.UIDocument(revision:rev,root:UINode(id:"navigation",kind:.navigation,properties:["title":.string("Mixer Appearance")],children:[UINode(id:"list",kind:.list,children:[first,second])]))
    }
}
