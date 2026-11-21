// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "FieldLogAppleCommitReplay",
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(path: "../fieldlog"),
        .package(path: "../mixer/capability-activation"),
        .package(path: "../mixer/sdk"),
        .package(path: "../mixer/updates"),
        .package(path: "../mixer/runtime-identity"),
    ],
    targets: [
        .executableTarget(name: "Replay", dependencies: [
            .product(name: "FieldLogModels", package: "fieldlog"),
            .product(name: "FieldLogStorage", package: "fieldlog"),
            .product(name: "FieldLogEntrySaving", package: "fieldlog"),
            .product(name: "MixerCapabilities", package: "sdk"),
            .product(name: "MixerUI", package: "sdk"),
            .product(name: "MixerCapabilityActivation", package: "capability-activation"),
            .product(name: "MixerUpdates", package: "updates"),
            .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
        ]),
    ]
)
