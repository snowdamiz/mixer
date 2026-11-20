// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "FieldLogAndroidPacketReplay",
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(path: "../mixer/sdk"),
        .package(path: "../mixer/capability-activation"),
        .package(path: "../mixer/runtime-identity"),
    ],
    targets: [
        .target(name: "FieldLogModels"),
        .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"]),
        .target(name: "FieldLogFeatures", dependencies: [
            "FieldLogModels", .product(name: "MixerCore", package: "sdk"), .product(name: "MixerUI", package: "sdk"),
        ]),
        .target(name: "FieldLogInstalledGuest", dependencies: [
            "FieldLogModels", "FieldLogStorage", .product(name: "MixerCapabilities", package: "sdk"),
        ]),
        .executableTarget(name: "FieldLogPacketReplay", dependencies: [
            "FieldLogModels", "FieldLogStorage", "FieldLogFeatures", "FieldLogInstalledGuest",
            .product(name: "MixerAndroid", package: "sdk"),
            .product(name: "MixerCapabilities", package: "sdk"),
            .product(name: "MixerUI", package: "sdk"),
            .product(name: "MixerCapabilityActivation", package: "capability-activation"),
            .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
        ]),
    ],
    swiftLanguageModes: [.v6]
)
