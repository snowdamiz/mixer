// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "UP4ComposeRuntimeFixture",
    products: [.library(name: "MixerComposeEditor", type: .dynamic, targets: ["MixerComposeEditor"])],
    targets: [
        .target(name: "MixerCore"),
        .target(name: "MixerUI", dependencies: ["MixerCore"]),
        .target(name: "MixerAndroid", dependencies: ["MixerUI"]),
        .target(name: "MixerComposeEditor", dependencies: ["MixerAndroid", "MixerUI"]),
    ],
    swiftLanguageModes: [.v6]
)
