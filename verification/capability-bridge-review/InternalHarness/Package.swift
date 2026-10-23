// swift-tools-version: 6.2
import PackageDescription

// This package only builds against the labelled review-derived bridge copy.
// The production public harness has no @testable or internal-hook dependency.
let package = Package(
    name: "MixerCapabilityBridgeInternalReview",
    platforms: [.macOS(.v14), .iOS(.v17)],
    dependencies: [
        .package(path: "../../../experimental-capability-runtime"),
        .package(path: "../../../sdk"),
    ],
    targets: [
        .testTarget(name: "CapabilityBridgeInternalReviewTests", dependencies: [
            .product(name: "MixerExperimentalCapabilityRuntime", package: "experimental-capability-runtime"),
            .product(name: "MixerCapabilities", package: "sdk"),
        ], path: "Tests", resources: [.copy("Fixtures")]),
    ],
    swiftLanguageModes: [.v6]
)
