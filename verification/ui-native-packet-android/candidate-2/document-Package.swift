// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "EnginePacketConsumer", platforms: [.macOS(.v14)],
    dependencies: [.package(path: "../native/android/engine"), .package(path: "../sdk")], targets: [.executableTarget(name: "EnginePacketConsumer",
        dependencies: [.product(name: "MixerAndroidRuntime", package: "engine"), .product(name: "MixerUI", package: "sdk")], path: "Sources")], swiftLanguageModes: [.v6])
