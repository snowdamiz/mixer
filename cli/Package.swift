// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "MixerCLI",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "mixer", targets: ["MixerCLI"]), .library(name: "MixerBuild", targets: ["MixerBuild"])],
    dependencies: [.package(path: "../sdk"), .package(path: "../updates")],
    targets: [
        .target(name: "MixerBuild", dependencies: [.product(name: "MixerCore", package: "sdk"), .product(name: "MixerUpdates", package: "updates")]),
        .executableTarget(name: "MixerCLI", dependencies: ["MixerBuild"]),
        .testTarget(name: "MixerBuildTests", dependencies: ["MixerBuild"], resources: [.copy("Fixtures")])
    ]
)
