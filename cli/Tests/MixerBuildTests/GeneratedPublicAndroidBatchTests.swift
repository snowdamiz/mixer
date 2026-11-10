import Foundation
import Testing
@testable import MixerBuild

@Test func generatedPublicBatchUsesOptionalAtomicCapabilityAndOriginalFIFOBytes() throws {
    let files = AndroidPublicHost.files(ApplicationConfiguration(name: "BatchApp", application: "example.batchapp"))
    let factory = try #require(files["Sources/AppAndroid/PublicFactory.swift"])
    let entry = try #require(files["Sources/AppAndroid/NativeEntry.swift"])
    let activity = try #require(files["Java/example/batchapp/androidhost/PublicActivity.java"])
    #expect(factory.contains("ProjectPresentation: AndroidUIBatchPresentation"))
    #expect(factory.contains("for action in actions { try ProjectFeature.handle(action, state: &state) }"))
    #expect(entry.contains("try application.sendBatch(owner: token, originalEnvelopes: event)"))
    #expect(entry.contains("try application.send(owner: token, originalEnvelope: event)"))
    #expect(activity.contains("ArrayDeque<CapturedEvent>"))
    #expect(activity.contains("MAX_EVENTS = 32, MAX_BYTES = 131072"))
    #expect(activity.contains("System.arraycopy(event.envelope"))
    #expect(!activity.contains("eventPending") && !activity.contains("JSONObject"))
    #expect(files["Bridge/PublicBridge.c"]?.contains("en>131072") == true)
}
