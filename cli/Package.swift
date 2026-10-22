// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "MixerCLI",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "mixer", targets: ["MixerCLI"]), .library(name: "MixerBuild", targets: ["MixerBuild"])],
    dependencies: [.package(path: "../sdk")],
    targets: [
        .target(name: "MixerBuild", dependencies: [.product(name: "MixerCore", package: "sdk")]),
        .executableTarget(name: "MixerCLI", dependencies: ["MixerBuild"]),
        .testTarget(name: "MixerBuildTests", dependencies: ["MixerBuild"])
    ]
)
