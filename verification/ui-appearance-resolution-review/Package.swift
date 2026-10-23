// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "AppearanceResolutionIndependentReview",
    platforms: [.macOS(.v14)],
    targets: [
        .target(name: "MixerCore", path: "candidate-2/inputs/sdk/Sources/MixerCore"),
        .target(name: "MixerUI", dependencies: ["MixerCore"], path: "candidate-2/inputs/sdk/Sources/MixerUI"),
        .executableTarget(name: "Review", dependencies: ["MixerUI"], path: "Review"),
    ],
    swiftLanguageModes: [.v6]
)
