// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "FieldLogD2Host",
    platforms: [.macOS(.v15)],
    products: [.executable(name: "fieldlog-d2-host", targets: ["ReplayedApp"])],
    dependencies: [
        .package(name: "FieldLog", path: "../ordinary"),
        .package(path: "../mixer/sdk"),
        .package(path: "../mixer/capability-activation"),
        .package(path: "../mixer/runtime-identity"),
        .package(path: "../mixer/updates"),
        .package(path: "../swift-crypto"),
    ],
    targets: [
        .target(name: "FieldLogHostTest"),
        .target(name: "FieldLogInstalledGuest", dependencies: [
            .product(name: "FieldLogModels", package: "FieldLog"),
            .product(name: "FieldLogStorage", package: "FieldLog"),
            .product(name: "MixerCapabilities", package: "sdk"),
            .product(name: "MixerCapabilityActivation", package: "capability-activation"),
            .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
            .product(name: "MixerUpdates", package: "updates"),
        ], swiftSettings: [.define("FIELDLOG_ENTRY_COMMIT_HOST_TEST")]),
        .executableTarget(name: "ReplayedApp", dependencies: [
            "FieldLogInstalledGuest", "FieldLogHostTest",
            .product(name: "FieldLogModels", package: "FieldLog"),
            .product(name: "FieldLogStorage", package: "FieldLog"),
            .product(name: "FieldLogFeatures", package: "FieldLog"),
            .product(name: "MixerCore", package: "sdk"),
            .product(name: "MixerUI", package: "sdk"),
            .product(name: "MixerAndroid", package: "sdk"),
            .product(name: "MixerCapabilities", package: "sdk"),
            .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
            .product(name: "MixerUpdates", package: "updates"),
            .product(name: "Crypto", package: "swift-crypto"),
        ], swiftSettings: [.define("FIELDLOG_SIGNED_CHECKLIST")])
    ], swiftLanguageModes: [.v6])
