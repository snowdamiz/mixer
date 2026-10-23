// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "PacketConsumer", platforms: [.macOS(.v14)],
    dependencies: [.package(path: "../sdk")], targets: [.executableTarget(name: "PacketConsumer",
        dependencies: [.product(name: "MixerUI", package: "sdk")], path: "Sources")],
    swiftLanguageModes: [.v6])
