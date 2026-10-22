// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "MixerCLI",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "mixer", targets: ["MixerCLI"]), .library(name: "MixerBuild", targets: ["MixerBuild"])],
    targets: [
        .target(name: "MixerBuild"),
        .executableTarget(name: "MixerCLI", dependencies: ["MixerBuild"]),
        .testTarget(name: "MixerBuildTests", dependencies: ["MixerBuild"])
    ]
)
