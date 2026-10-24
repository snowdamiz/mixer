// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "MixerExperimentalCapabilityRuntime",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [.library(name: "MixerExperimentalCapabilityRuntime", targets: ["MixerExperimentalCapabilityRuntime"])],
    dependencies: [.package(path: "../sdk")],
    targets: [
        .target(name: "CMixerVMCapability", publicHeadersPath: "include", linkerSettings: [
            .linkedLibrary("mixer_vm_capability_experimental"),
            .linkedLibrary("m", .when(platforms: [.linux, .android])),
            .linkedLibrary("dl", .when(platforms: [.linux, .android])),
        ]),
        .target(name: "MixerExperimentalCapabilityRuntime", dependencies: [
            "CMixerVMCapability",
            .product(name: "MixerCapabilities", package: "sdk"),
            .product(name: "MixerGuest", package: "sdk"),
            .product(name: "MixerUI", package: "sdk"),
        ]),
        .testTarget(name: "MixerExperimentalCapabilityRuntimeTests", dependencies: ["MixerExperimentalCapabilityRuntime", .product(name: "MixerCapabilities", package: "sdk")]),
    ],
    swiftLanguageModes: [.v6]
)
