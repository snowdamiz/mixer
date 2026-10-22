// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Mixer",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "MixerCore", targets: ["MixerCore"]),
        .library(name: "MixerUI", targets: ["MixerUI"]),
        .library(name: "MixerApple", targets: ["MixerApple"]),
        .library(name: "MixerGuest", targets: ["MixerGuest"]),
    ],
    targets: [
        .target(name: "MixerCore"),
        .target(name: "MixerUI", dependencies: ["MixerCore"]),
        .target(name: "MixerApple", dependencies: ["MixerCore", "MixerUI"]),
        .target(name: "MixerGuest", dependencies: ["MixerCore", "MixerUI"]),
        .testTarget(name: "MixerCoreTests", dependencies: ["MixerCore"]),
        .testTarget(name: "MixerUITests", dependencies: ["MixerCore", "MixerUI", "MixerGuest"]),
        .testTarget(name: "MixerAppleTests", dependencies: ["MixerApple", "MixerUI"]),
    ],
    swiftLanguageModes: [.v6]
)
