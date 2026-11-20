// swift-tools-version: 6.2
import PackageDescription
let package = Package(name: "FieldLogPublicAndroid",
    products: [.library(name: "mixer_public_android_jni", type: .dynamic, targets: ["FieldLogAndroid"])],
    dependencies: [
        .package(path: "../mixer/sdk"), .package(path: "../mixer/capability-activation"),
        .package(path: "../mixer/runtime-identity"), .package(path: "../mixer/updates"),
    ],
    targets: [
        .target(name: "FieldLogModels"),
        .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"]),
        .target(name: "FieldLogFeatures", dependencies: ["FieldLogModels",
            .product(name: "MixerCore", package: "sdk"), .product(name: "MixerUI", package: "sdk")],
            exclude: ["TaskEditorAppleFieldsHost.swift", "EntryEditorAppleHost.swift"]),
        .target(name: "FieldLogInstalledGuest", dependencies: ["FieldLogModels", "FieldLogStorage",
            .product(name: "MixerCapabilities", package: "sdk"),
            .product(name: "MixerCapabilityActivation", package: "capability-activation"),
            .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
            .product(name: "MixerUpdates", package: "updates")]),
        .target(name: "FieldLogAndroid", dependencies: ["FieldLogModels", "FieldLogStorage", "FieldLogFeatures",
            "FieldLogInstalledGuest", .product(name: "MixerAndroid", package: "sdk"),
            .product(name: "MixerCore", package: "sdk"), .product(name: "MixerUI", package: "sdk"),
            .product(name: "MixerCapabilities", package: "sdk")]),
    ], swiftLanguageModes: [.v6])
