import Foundation
@testable import MixerUI

enum ReviewFailure: Error { case assertion(String) }
func check(_ value: @autoclosure () -> Bool, _ message: String) throws { if !value() { throw ReviewFailure.assertion(message) } }
func rejects(_ snapshot: UIRenderSnapshot, _ message: String) throws {
    do { _ = try UIAppearanceResolverV2.prepare(snapshot: snapshot, configuration: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), environment: env(), platform: .iOS) }
    catch is UIAppearanceErrorV2 { return }
    throw ReviewFailure.assertion(message)
}
func env(_ generation: UInt64 = 0, bold: Bool = false) -> UIAppearanceEnvironmentV2 {
    UIAppearanceEnvironmentV2(scheme: .dark, direction: .rightToLeft, profile: .a5, density1024: 16384,
        viewport: UIAppearanceViewportV2(width64: 1, height64: 1), safeArea64: UIInsets64V1(top: 1, leading: 1, bottom: 0, trailing: 0),
        localeIdentifier: "é", accessibility: UIAppearanceAccessibilityV2(boldText: bold, increasedContrast: false, reduceMotion: true), generation: generation)
}
@main struct Adversarial {
    static func main() throws {
        var button=UINode(id: "button", kind: .button, properties: ["label": .string("Original")], actions: [UIActionBinding(id: "action", event: .activate)])
        let root=UINode(id: "root", kind: .vStack, children: [button])
        var reconciler=UIReconciler();try reconciler.apply(UIDocument(revision: 23, root: root))
        let snapshot=try reconciler.currentSnapshot()
        let identity=snapshot.identity(for: "button")!
        let original=try UIAppearanceResolverV2.prepare(snapshot: snapshot, configuration: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), environment: env(), platform: .iOS)
        // The mutable UINode.properties member is a value copy, including when
        // a caller extracts it through the snapshot's public document.
        button.properties["label"] = .string("Caller later mutation")
        var extracted=snapshot.document.root.children[0]
        extracted.properties["label"] = .string("Extracted later mutation")
        try check(snapshot.document.root.children[0].properties["label"]?.string == "Original", "snapshot alias")
        try check(original.node(for: "button")?.identity == identity, "initial identity")
        let changed=try UIAppearanceResolverV2.prepare(snapshot: snapshot, configuration: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), environment: env(.max), platform: .android)
        try check(changed.nodes == original.nodes, "environment-only identity/recipe mutation")
        try check(changed.environment.generation == .max && original.environment.generation == 0, "raw generation changed")
        for _ in 0..<100 { _ = original.style(nodeID: "button", pressed: true, focused: true) }
        try check(changed.nodes == original.nodes, "style call mutated nodes")
        let routed=try snapshot.route(UIEventEnvelope(revision: 23, identity: identity, event: .activate))
        try check(routed.actionID == "action", "style changed action routing")
        do { _ = try UIAppearanceResolverV2.prepare(snapshot: snapshot, configuration: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), environment: env(1,bold: true), platform: .iOS);throw ReviewFailure.assertion("bold accepted") }
        catch UIAppearanceErrorV2.unsupportedNativeOperation {}
        try check(reconciler.snapshot?.document.revision == 23 && reconciler.snapshot?.identity(for: "button") == identity, "failure mutated reconciler")

        // Internal corruption probes exercise admission independently of public
        // constructor restrictions; they do not assert public forgeability.
        var nodes=snapshot.nodes
        nodes.removeValue(forKey: "button")
        try rejects(UIRenderSnapshot(document: snapshot.document,nodes: nodes,maximumStringBytes: 16384),"missing record accepted")
        nodes=snapshot.nodes
        nodes["extra"]=ReconciledNode(node: button,identity: UINodeIdentity(id:"extra",generation:1),parent:nil,index:0,disabled:false)
        try rejects(UIRenderSnapshot(document: snapshot.document,nodes: nodes,maximumStringBytes: 16384),"extra record accepted")
        nodes=snapshot.nodes
        nodes["button"]=ReconciledNode(node: snapshot.document.root.children[0],identity: UINodeIdentity(id:"other",generation:identity.generation),parent:"root",index:0,disabled:false)
        try rejects(UIRenderSnapshot(document: snapshot.document,nodes: nodes,maximumStringBytes: 16384),"identity alias accepted")
        nodes=snapshot.nodes
        nodes["button"]=ReconciledNode(node: button,identity: identity,parent:"root",index:0,disabled:false)
        try rejects(UIRenderSnapshot(document: snapshot.document,nodes: nodes,maximumStringBytes: 16384),"changed content accepted")
        // Pure raw data preserves UInt64 identity generations without claiming
        // that an external caller can mint a render snapshot.
        let single=UIDocument(revision: .max, root: snapshot.document.root.children[0])
        let internalSnapshot=UIRenderSnapshot(document:single,nodes:["button":ReconciledNode(node:single.root,identity:UINodeIdentity(id:"button",generation:.max),parent:nil,index:0,disabled:false)],maximumStringBytes:16384)
        let maxPlan=try UIAppearanceResolverV2.prepare(snapshot: internalSnapshot,configuration:UIAppearanceDescriptorCodecV2.mixerDefaultV2(),environment:env(.max),platform:.iOS)
        try check(maxPlan.revision == .max && maxPlan.node(for:"button")?.identity.generation == .max,"unsigned identity truncated")

        guard case let .shared(theme)=try UIAppearanceDescriptorCodecV2.mixerDefaultV2().mode else { throw ReviewFailure.assertion("default mode") }
        let invalid=UIThemeV2(recipe:theme.recipe,typography:theme.typography,light:theme.light,dark:theme.dark,
            stacks:UIStackMetricsV2(defaultGap64:65537,bodyCaptionGap64:0,missingVStackGap:.bodyThenCaptionPairOtherwiseDefault,vStackAlignment:.center,hStackAlignment:.center,zStackAlignment:.center),
            groupedList:theme.groupedList,button:theme.button,field:theme.field,toggle:theme.toggle,navigation:theme.navigation)
        for platform in [UIAppearancePlatformV2.iOS,.android] {
            let config=UIAppearanceConfigurationV2(id:"invalid.unselected",mode:.platformSpecific(iOS:platform == .iOS ? theme:invalid,android:platform == .android ? theme:invalid,reason:"Unselected invalid theme"))
            do { _=try UIAppearanceResolverV2.prepare(snapshot:snapshot,configuration:config,environment:env(),platform:platform);throw ReviewFailure.assertion("unselected invalid theme accepted") }
            catch is UIAppearanceErrorV2 {}
        }
        // No path read is needed by this data-only API. A syntactically valid
        // nonexistent resource reference is retained as metadata, with no
        // installed-resource or native-support witness produced.
        let resource=UIAppearanceResourceV1(id:"metadata",kind:.iconPNG,path:"does-not-exist/icon.png",sha256:String(repeating:"f",count:64),bytes:1,provenance:"Independent metadata probe",scale:1,locale:"und",direction:.neutral)
        let metadata=try UIAppearanceResolverV2.prepare(snapshot:snapshot,configuration:UIAppearanceConfigurationV2(id:"metadata",mode:.shared(theme),resources:[resource]),environment:env(),platform:.iOS)
        try check(metadata.resources == [resource],"metadata reference changed")
        print("PASS 9 independent value/routing invariants, 4 corrupted snapshots rejected, 2 unselected typed themes rejected, unsupported accessibility rejected; raw data only")
    }
}
