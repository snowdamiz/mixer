// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "MixerRuntime",
    platforms: [.iOS("26.0"), .macOS(.v14)],
    products: [.library(name: "MixerRuntime", targets: ["MixerRuntime"])],
    targets: [
        .target(name: "CMixerVM", publicHeadersPath: "include", linkerSettings: [
            .linkedLibrary("mixer_vm"),
            .linkedLibrary("m", .when(platforms: [.linux, .android])),
            .linkedLibrary("dl", .when(platforms: [.linux, .android])),
        ]),
        .target(name: "MixerRuntime", dependencies: ["CMixerVM"]),
        .testTarget(name: "MixerRuntimeTests", dependencies: ["MixerRuntime"]),
    ],
    swiftLanguageModes: [.v6]
)
