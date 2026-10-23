// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "MixerCapabilityActivation",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [.library(name: "MixerCapabilityActivation", targets: ["MixerCapabilityActivation"])],
    dependencies: [
        .package(path: "../experimental-capability-runtime"),
        .package(path: "../runtime-identity"),
        .package(path: "../updates"),
        .package(path: "../sdk"),
    ],
    targets: [
        .target(name: "MixerCapabilityDurableIO"),
        .target(name: "MixerCapabilityActivation", dependencies: [
            "MixerCapabilityDurableIO",
            .product(name: "MixerExperimentalCapabilityRuntime", package: "experimental-capability-runtime"),
            .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
            .product(name: "MixerUpdates", package: "updates"),
            .product(name: "MixerCapabilities", package: "sdk"),
        ]),
        .testTarget(name: "MixerCapabilityActivationTests", dependencies: ["MixerCapabilityActivation"], resources: [.copy("Fixtures")]),
    ],
    swiftLanguageModes: [.v6]
)
