import Foundation
import Testing
@testable import MixerUI
struct IndependentJavaReturnTests {
    @Test func javaReturnedFullUInt64Event() throws {
        let path=try #require(ProcessInfo.processInfo.environment["MIXER_REVIEW_JAVA_EVENT"])
        let bytes=try Data(contentsOf:URL(fileURLWithPath:path))
        let event=try JSONDecoder().decode(UIEventEnvelope.self,from:bytes)
        #expect(event.revision == UInt64.max)
        #expect(event.identity == UINodeIdentity(id:"full",generation:UInt64.max))
        #expect(event.event == .activate);#expect(event.value == .null)
        let node=UINode(id:"full",kind:.button,properties:["label":.string("Wire café 東京")],actions:[UIActionBinding(id:"activate",event:.activate)])
        let snapshot=UIRenderSnapshot(document:UIDocument(revision:UInt64.max,root:node),nodes:["full":ReconciledNode(node:node,identity:event.identity,parent:nil,index:0,disabled:false)],maximumStringBytes:16_384)
        #expect(try snapshot.route(event).actionID == "activate")
        print("JAVA_RETURNED_FULL_UINT64_EVENT_ACCEPTED")
    }
}
