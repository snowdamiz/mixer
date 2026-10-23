// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "EnginePacketConsumer", platforms: [.macOS(.v14)],
    dependencies: [.package(path: "../native/android/engine")], targets: [.executableTarget(name: "EnginePacketConsumer",
        dependencies: [.product(name: "MixerAndroidEngine", package: "engine")], path: "Sources")], swiftLanguageModes: [.v6])
