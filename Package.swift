// swift-tools-version: 6.0
import PackageDescription

// Public source package. Development packages in sdk/, runtime/ and updates/
// remain independently usable; this entry point exports only the owned SDK.
let package = Package(
    name: "Mixer",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "MixerCore", targets: ["MixerCore"]),
        .library(name: "MixerUI", targets: ["MixerUI"]),
        .library(name: "MixerApple", targets: ["MixerApple"]),
        .library(name: "MixerGuest", targets: ["MixerGuest"]),
        .library(name: "MixerCapabilities", targets: ["MixerCapabilities"]),
    ],
    targets: [
        .target(name: "MixerCore", path: "sdk/Sources/MixerCore"),
        .target(name: "MixerCapabilityIO", path: "sdk/Sources/MixerCapabilities/NativeIO"),
        .target(name: "MixerCapabilities", dependencies: ["MixerCore", .target(name: "MixerCapabilityIO", condition: .when(platforms: [.iOS, .macOS, .linux, .android]))], path: "sdk/Sources/MixerCapabilities", exclude: ["NativeIO"]),
        .target(name: "MixerUI", dependencies: ["MixerCore"], path: "sdk/Sources/MixerUI"),
        .target(name: "MixerApple", dependencies: ["MixerCore", "MixerUI"], path: "sdk/Sources/MixerApple"),
        .target(name: "MixerGuest", dependencies: ["MixerCore", "MixerUI"], path: "sdk/Sources/MixerGuest"),
        .testTarget(name: "MixerCoreTests", dependencies: ["MixerCore"], path: "sdk/Tests/MixerCoreTests"),
        .testTarget(name: "MixerUITests", dependencies: ["MixerCore", "MixerUI", "MixerGuest"], path: "sdk/Tests/MixerUITests"),
        .testTarget(name: "MixerAppleTests", dependencies: ["MixerApple", "MixerUI"], path: "sdk/Tests/MixerAppleTests"),
    ],
    swiftLanguageModes: [.v6]
)
