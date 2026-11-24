import Foundation
import Testing
@testable import MixerBuild

@Test func publicProfilesDeclareTheirRequiredEnvironmentFloor() throws {
    for host in [AndroidApplicationHost.publicV3, .publicV4] {
        var config = ApplicationConfiguration(name: "Floor", application: "example.floor")
        config.targets = ["android"]; config.capabilities = []; config.androidHost = host
        try config.validate()
        let files = AndroidPublicHost.files(config)
        let manifest = try #require(files["AndroidManifest.xml"])
        let xml = try XMLDocument(xmlString: manifest)
        let floor = try xml.nodes(forXPath: "/manifest/uses-sdk/@android:minSdkVersion").first?.stringValue
        #expect(floor == "36")
        let java = try #require(files["Java/example/floor/androidhost/PublicActivity.java"])
        #expect(java.contains("android.os.Build.VERSION.SDK_INT < 36"))
        #expect(java.contains("high-contrast read/listener"))
        #expect(files["README.md"]?.contains("full API 28 product acceptance is pending") == true)
        #expect(!files.values.contains(where: { $0.contains("__MIN_API__") }))
        if let outputPath = ProcessInfo.processInfo.environment["R346_OUTPUT"] {
            let output = URL(fileURLWithPath: outputPath).appendingPathComponent(host.rawValue)
            for (path, source) in files {
                let target = output.appendingPathComponent(path)
                try FileManager.default.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
                try source.write(to: target, atomically: true, encoding: .utf8)
            }
        }
        let selection = try #require(files[AndroidPublicHost.selectionFile(config)])
        #expect(selection.contains(host == .publicV4 ? "MEASURED_MULTILINE_LONG_NOTES_V4" : "MEASURED_MULTILINE_RETIREMENT_V3"))
    }
}
