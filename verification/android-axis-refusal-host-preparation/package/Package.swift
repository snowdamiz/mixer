// swift-tools-version: 6.0
import PackageDescription

// Isolated host-only test assembly. No public product or source-pair selection.
let package = Package(
    name: "MixerAndroidAxisHostCheck",
    platforms: [.macOS(.v14)],
    targets: [
        .target(name: "MixerCore"),
        .target(name: "MixerUI", dependencies: ["MixerCore"]),
        .target(name: "MixerAndroidRuntime", dependencies: ["MixerCore", "MixerUI"]),
        .testTarget(name: "MixerAndroidRuntimeTests", dependencies: ["MixerAndroidRuntime", "MixerUI"]),
    ],
    swiftLanguageModes: [.v6]
)
