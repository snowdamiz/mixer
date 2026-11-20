// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "FieldLogCalculationHost",
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(path: "../mixer/sdk"),
        .package(path: "../mixer/capability-activation"),
        .package(path: "../mixer/runtime-identity"),
        .package(path: "../mixer/updates"),
    ],
    targets: [
        .target(name: "FieldLogModels"),
        .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"]),
        .target(name: "FieldLogInstalledGuest", dependencies: [
            "FieldLogModels", "FieldLogStorage",
            .product(name: "MixerCapabilities", package: "sdk"),
            .product(name: "MixerCapabilityActivation", package: "capability-activation"),
            .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
            .product(name: "MixerUpdates", package: "updates"),
        ]),
        .executableTarget(name: "Seal", dependencies: [
            .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
            .product(name: "MixerUpdates", package: "updates"),
        ]),
        .executableTarget(name: "Probe", dependencies: [
            "FieldLogModels", "FieldLogStorage", "FieldLogInstalledGuest",
            .product(name: "MixerCapabilities", package: "sdk"),
            .product(name: "MixerCapabilityActivation", package: "capability-activation"),
            .product(name: "MixerGuest", package: "sdk"),
            .product(name: "MixerUI", package: "sdk"),
            .product(name: "MixerUpdates", package: "updates"),
        ]),
    ],
    swiftLanguageModes: [.v6]
)
