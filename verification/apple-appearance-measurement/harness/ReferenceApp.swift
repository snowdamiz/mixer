import Foundation
import SwiftUI
import UIKit
import MixerUI
import MixerApple

// Original simulator-only observation harness. All rendered content comes from
// the equal, bundled UI-v1 JSON fixture; no font, color or control style is set.
@main
struct MeasurementApp: App {
    private let fixture: String
    private let rtl: Bool
    private let host: MixerUIHost

    init() {
        let arguments = ProcessInfo.processInfo.arguments
        fixture = arguments.firstIndex(of: "--fixture").map { arguments[$0 + 1] } ?? "typography"
        rtl = arguments.contains("--rtl")
        do {
            try ReferenceEvidence.validateAllFixtures()
            host = try MixerUIHost(document: ReferenceEvidence.load(fixture).document)
        } catch { fatalError("Reference fixture admission failed: \(error)") }
    }

    var body: some Scene {
        WindowGroup {
            ReferenceView(host: host, fixture: fixture)
                .environment(\.layoutDirection, rtl ? .rightToLeft : .leftToRight)
                .environment(\.locale, Locale(identifier: rtl ? "ar" : "en_US"))
        }
    }
}

@MainActor
struct ReferenceView: View {
    let host: MixerUIHost
    let fixture: String
    @Environment(\.layoutDirection) private var direction
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        MixerNativeView(host: host, onAction: { _ in })
            .task {
                do {
                    try await Task.sleep(for: .milliseconds(1000))
                    try ReferenceEvidence.record(host: host, fixture: fixture,
                        direction: direction == .rightToLeft ? "rightToLeft" : "leftToRight",
                        dynamicType: String(describing: dynamicTypeSize),
                        colorScheme: colorScheme == .dark ? "dark" : "light")
                } catch { fatalError("Reference observation failed: \(error)") }
            }
    }
}

@MainActor
enum ReferenceEvidence {
    static let names = ["typography", "controls", "layouts", "rtl-large"]
    static var output: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }

    static func load(_ name: String) throws -> (bytes: Data, document: MixerUI.UIDocument) {
        guard names.contains(name), let url = Bundle.main.url(forResource: name, withExtension: "json", subdirectory: "Fixtures") else {
            throw NSError(domain: "ReferenceFixture", code: 1)
        }
        let bytes = try Data(contentsOf: url)
        return (bytes, try MixerUI.UIDocument.decode(bytes))
    }

    static func validateAllFixtures() throws {
        var results: [[String: Any]] = []
        var allKinds: Set<String> = []
        for name in names {
            let source = try load(name)
            let checked = try UIValidator().validate(source.document)
            let host = try MixerUIHost(document: source.document)
            guard host.snapshot.document == source.document else { throw NSError(domain: "ReferenceFixture", code: 2) }
            let kinds = kinds(in: source.document.root)
            allKinds.formUnion(kinds)
            results.append(["fixture": name, "nodeCount": checked.nodeCount,
                "kinds": kinds.sorted(), "hostSnapshotEqualsSourceDocument": true])
        }
        guard allKinds == Set(NodeKind.allCases.map(\.rawValue)) else { throw NSError(domain: "ReferenceFixture", code: 3) }
        try write(["allTenKindsValidatedByFrozenSDK": true, "fixtures": results], name: "fixture-validation.json")
    }

    static func kinds(in node: UINode) -> Set<String> {
        node.children.reduce(into: Set([node.kind.rawValue])) { $0.formUnion(kinds(in: $1)) }
    }

    static func record(host: MixerUIHost, fixture: String, direction: String, dynamicType: String, colorScheme: String) throws {
        let source = try load(fixture)
        guard host.snapshot.document == source.document,
              let scene = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene }).first,
              let window = scene.windows.first(where: \.isKeyWindow) else { throw NSError(domain: "ReferenceObservation", code: 4) }
        let screen = scene.screen
        let bounds = screen.bounds
        let windowBounds = window.bounds
        let safe = window.safeAreaInsets
        let traits = window.traitCollection
        try source.bytes.write(to: output.appendingPathComponent("rendered-document.json"), options: .atomic)
        try write([
            "fixture": fixture, "documentRevision": source.document.revision,
            "hostSnapshotEqualsSourceDocument": true,
            "systemName": UIDevice.current.systemName, "systemVersion": UIDevice.current.systemVersion,
            "model": UIDevice.current.model,
            "screenBoundsPoints": ["width": bounds.width, "height": bounds.height],
            "screenNativeBoundsPixels": ["width": screen.nativeBounds.width, "height": screen.nativeBounds.height],
            "screenScale": screen.scale, "screenNativeScale": screen.nativeScale,
            "windowBoundsPoints": ["width": windowBounds.width, "height": windowBounds.height],
            "windowSafeAreaInsetsPoints": ["top": safe.top, "bottom": safe.bottom, "left": safe.left, "right": safe.right],
            "windowTraitDisplayScale": traits.displayScale,
            "windowTraitPreferredContentSizeCategory": traits.preferredContentSizeCategory.rawValue,
            "windowTraitUserInterfaceStyle": traits.userInterfaceStyle == .dark ? "dark" : "light",
            "swiftUIColorScheme": colorScheme, "swiftUILayoutDirection": direction,
            "swiftUIDynamicTypeSize": dynamicType,
            "interfaceOrientation": scene.interfaceOrientation.rawValue,
            "processArguments": ProcessInfo.processInfo.arguments,
            "observation": "Native window/screen/environment values only; no per-node layout measurement or display-health receipt."
        ], name: "environment.json")
        try MixerAppearanceMeasurement.write(window: window, fixture: fixture)
    }

    static func write(_ value: [String: Any], name: String) throws {
        try JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes])
            .write(to: output.appendingPathComponent(name), options: .atomic)
    }
}
