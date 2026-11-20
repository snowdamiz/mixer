// swift-tools-version: 6.2
import PackageDescription

let mixer = "../source/mixer/"
let package = Package(
    name: "FieldLogRotationFixture",
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(path: "../source/fieldlog"),
        .package(path: mixer + "sdk"),
        .package(path: mixer + "capability-activation"),
        .package(path: mixer + "runtime-identity"),
        .package(path: mixer + "updates"),
    ],
    targets: [
        .executableTarget(name: "SignRotation", dependencies: [
            .product(name: "MixerUpdates", package: "updates"),
            .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
        ], path: "signer"),
        .executableTarget(name: "InstalledProbe", dependencies: [
            .product(name: "FieldLogInstalledGuest", package: "fieldlog"),
            .product(name: "FieldLogStorage", package: "fieldlog"),
            .product(name: "MixerUI", package: "sdk"),
            .product(name: "MixerCapabilities", package: "sdk"),
            .product(name: "MixerCapabilityActivation", package: "capability-activation"),
            .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
            .product(name: "MixerUpdates", package: "updates"),
        ], path: "probe"),
    ]
)
