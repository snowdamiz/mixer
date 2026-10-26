// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Mixer",
    platforms: [.iOS("26.0"), .macOS(.v14)],
    products: [
        .library(name: "MixerCore", targets: ["MixerCore"]),
        .library(name: "MixerUI", targets: ["MixerUI"]),
        .library(name: "MixerApple", targets: ["MixerApple"]),
        .library(name: "MixerGuest", targets: ["MixerGuest"]),
        .library(name: "MixerCapabilities", targets: ["MixerCapabilities"]),
    ],
    targets: [
        .target(name: "MixerCore"),
        .target(name: "MixerCapabilityIO", path: "Sources/MixerCapabilities/NativeIO"),
        .target(name: "MixerCapabilities", dependencies: ["MixerCore", .target(name: "MixerCapabilityIO", condition: .when(platforms: [.iOS, .macOS, .linux, .android]))], exclude: ["NativeIO"]),
        .target(name: "MixerUI", dependencies: ["MixerCore"], path: "Sources/UnreviewedUI"),
        .target(name: "MixerApple", dependencies: ["MixerCore", "MixerUI"]),
        .target(name: "MixerGuest", dependencies: ["MixerCore", "MixerUI"]),
        .testTarget(name: "MixerCoreTests", dependencies: ["MixerCore"]),
        .testTarget(name: "MixerUITests", dependencies: ["MixerCore", "MixerUI", "MixerGuest"]),
        .testTarget(name: "MixerAppleTests", dependencies: ["MixerApple", "MixerUI"]),
    ],
    swiftLanguageModes: [.v6]
)
