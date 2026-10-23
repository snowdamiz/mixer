// swift-tools-version: 6.2
import PackageDescription

// Review-owned public consumer. No @testable imports, private C target or
// MixerRuntime dependency: the experimental package supplies its one archive.
let package = Package(
    name: "MixerCapabilityBridgeIndependentReview",
    platforms: [.macOS(.v14), .iOS(.v17)],
    dependencies: [
        .package(path: "../../experimental-capability-runtime"),
        .package(path: "../../sdk"),
    ],
    targets: [
        .testTarget(name: "CapabilityBridgePublicReviewTests", dependencies: [
            .product(name: "MixerExperimentalCapabilityRuntime", package: "experimental-capability-runtime"),
            .product(name: "MixerCapabilities", package: "sdk"),
        ], path: "PublicHarness", resources: [.copy("Fixtures")]),
    ],
    swiftLanguageModes: [.v6]
)
