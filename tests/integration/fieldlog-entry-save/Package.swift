// swift-tools-version: 6.2
import PackageDescription

let package = Package(name: "FieldLogEntrySaveReplay", platforms: [.macOS(.v14)],
    products: [.executable(name: "fieldlog-entry-save", targets: ["Replay"])],
    dependencies: [
        .package(path: "../Mixer/sdk"), .package(path: "../Mixer/capability-activation"),
        .package(path: "../Mixer/runtime-identity"), .package(path: "../Mixer/updates"),
        .package(path: "../swift-crypto"),
    ],
    targets: [
        .target(name: "FieldLogModels"),
        .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"]),
        .target(name: "FieldLogFeatures", dependencies: ["FieldLogModels",
            .product(name: "MixerCore", package: "sdk"), .product(name: "MixerUI", package: "sdk")]),
        .target(name: "FieldLogInstalledGuest", dependencies: ["FieldLogStorage", "FieldLogModels",
            .product(name: "MixerCapabilities", package: "sdk"),
            .product(name: "MixerCapabilityActivation", package: "capability-activation"),
            .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
            .product(name: "MixerUpdates", package: "updates")]),
        .executableTarget(name: "Replay", dependencies: [
            "FieldLogFeatures", "FieldLogModels", "FieldLogStorage", "FieldLogInstalledGuest",
            .product(name: "MixerCore", package: "sdk"),
            .product(name: "MixerUI", package: "sdk"),
            .product(name: "MixerAndroid", package: "sdk"),
            .product(name: "MixerCapabilities", package: "sdk"),
            .product(name: "MixerCapabilityActivation", package: "capability-activation"),
            .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
            .product(name: "MixerUpdates", package: "updates"),
            .product(name: "Crypto", package: "swift-crypto"),
        ]),
    ], swiftLanguageModes: [.v6])
