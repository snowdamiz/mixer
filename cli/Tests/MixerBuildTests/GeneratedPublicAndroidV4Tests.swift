import Foundation
import Testing
@testable import MixerBuild

@Test func publicV4ConfigurationAndCatalogRefusalBeforeOutput() throws {
    var config = ApplicationConfiguration(name: "LongNotes", application: "example.longnotes")
    config.androidHost = .publicV4
    try config.validate()
    #expect(try JSONDecoder().decode(ApplicationConfiguration.self, from: JSONFile.data(config)).androidHost == .publicV4)
    config.targets = ["ios"]
    #expect(throws: (any Error).self) { try config.validate() }
    config.targets = ["android"]
    for name in ["dev.mixer.android.consumer", "example.class.consumer"] {
        config.application = name
        #expect(throws: (any Error).self) { try config.validate() }
    }
    // Before root binds V4, refusal precedes SDK reads and destination staging.
    if AndroidSDKCompatibility.profile.wire.public_host_profiles?.contains("MEASURED_MULTILINE_LONG_NOTES_V4") != true {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("v4-refusal-\(UUID().uuidString)")
        let absent = root.appendingPathComponent("missing-sdk")
        do {
            _ = try ProjectGenerator.create(name: "LongNotes", application: "example.longnotes", destination: root.appendingPathComponent("Created"), sdk: absent, platform: "android", androidAdapter: absent, androidHost: .publicV4)
            Issue.record("Unsupported catalog admitted V4")
        } catch let error as MixerFailure {
            #expect(error.code == "android.host-profile-unavailable")
        }
        #expect(!FileManager.default.fileExists(atPath: root.path))
    }
}

@Test func publicV4MaterializedSelectionIsExplicit() throws {
    var config = ApplicationConfiguration(name: "LongNotes", application: "example.longnotes")
    config.androidHost = .publicV4
    try config.validate()
    let files = AndroidPublicHost.files(config)
    #expect(files["public-host-v3.json"] == nil)
    #expect(files["public-host-v4.json"] == "{\"host\":\"public-v4\",\"profile\":\"MEASURED_MULTILINE_LONG_NOTES_V4\"}\n")
    // The generated app-owned bridge continues to use the general starter ABI.
    #expect(files["Sources/AppAndroid/NativeEntry.swift"]?.contains("mixer_public_android_submit") == true)
    #expect(files["Sources/AppAndroid/NativeEntry.swift"]?.contains("directoryCount") == false)
}

@Test func publicV4Pair19AuthorityMatchesSelectedInputs() throws {
    let profile = AndroidSDKCompatibility.profile
    #expect(profile.id == "mixer.android-source-pair.19")
    #expect(profile.wire.public_host_profiles == ["MEASURED_MULTILINE_LONG_NOTES_V4"])
    try AndroidSDKCompatibility.requireHost(.publicV4)
    try AndroidSDKCompatibility.admitInput(sdk: compatibilityRepository.appendingPathComponent("sdk"), adapter: compatibilityRepository.appendingPathComponent("native/android"))
}
